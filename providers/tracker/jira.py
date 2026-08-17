"""Jira Cloud tracker provider for vteam (installed as .vteam/providers/tracker_jira.py).

Env: JIRA_BASE_URL, JIRA_EMAIL, JIRA_API_TOKEN (+ project key from vteam config).
Provider-specific knowledge kept here, out of the gates:
  · descriptions are ADF — flattened to text here;
  · comments use API **v2** (plain text bodies), everything else v3;
  · attachments need `X-Atlassian-Token: no-check`;
  · a 200 response is NOT proof of API access — some Atlassian UI hosts answer
    200 HTML on every path, so ping() asserts real JSON with an accountId;
  · for a `Blocks` issue link, the **inwardIssue is the BLOCKING side** — and a
    whole batch of links once shipped reversed because the sent parameters were
    trusted, so link() re-reads the blocked issue to confirm direction.
"""
from __future__ import annotations

import base64
import hashlib
import json
import mimetypes
import urllib.parse
import urllib.request
import uuid
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts" / "lib"))
from tracker import Tracker  # noqa: E402


def _adf_text(node) -> str:
    """Flatten an ADF document to plain text."""
    if node is None:
        return ""
    if isinstance(node, str):
        return node
    out = []
    if isinstance(node, dict):
        if node.get("text"):
            out.append(node["text"])
        for ch in node.get("content", []) or []:
            out.append(_adf_text(ch))
        if node.get("type") in ("paragraph", "heading", "listItem", "tableRow"):
            out.append("\n")
    elif isinstance(node, list):
        out.extend(_adf_text(x) for x in node)
    return "".join(out)


class Provider(Tracker):
    def __init__(self, c):
        super().__init__(c)
        self.base = (c.env("JIRA_BASE_URL") or "").rstrip("/")
        email, token = c.env("JIRA_EMAIL"), c.env("JIRA_API_TOKEN")
        if not (self.base and email and token):
            raise SystemExit("tracker(jira): JIRA_BASE_URL/JIRA_EMAIL/JIRA_API_TOKEN missing from .env")
        self._auth = base64.b64encode(f"{email}:{token}".encode()).decode()

    def _req(self, path: str, data=None, method="GET", headers=None, raw_body: bytes | None = None):
        h = {"Authorization": f"Basic {self._auth}", "Accept": "application/json"}
        if data is not None:
            h["Content-Type"] = "application/json"
        h.update(headers or {})
        req = urllib.request.Request(
            self.base + path,
            data=raw_body if raw_body is not None else (json.dumps(data).encode() if data is not None else None),
            headers=h, method=method)
        with urllib.request.urlopen(req, timeout=60) as r:
            text = r.read().decode()
        return json.loads(text) if text else {}

    # -- interface -------------------------------------------------------------
    def ping(self) -> tuple[bool, str]:
        try:
            me = self._req("/rest/api/3/myself")
        except Exception as exc:
            return False, f"API unreachable ({exc}) — wrong token or BASE_URL"
        if not isinstance(me, dict) or not me.get("accountId"):
            return False, (f"{self.base} answered but not with API JSON — that's a UI "
                           f"link, not the API host (use https://<site>.atlassian.net)")
        key = str(self.c.cfg("project.key"))
        try:
            proj = self._req(f"/rest/api/3/project/{key}")
            if proj.get("key") != key:
                return False, f"project {key} not found"
        except Exception:
            return False, f"project {key} not queryable — wrong key?"
        return True, f"signed in, project {key} exists"

    def get_issue(self, key: str) -> dict:
        fields = "summary,description,status,assignee,labels,timetracking,issuelinks,attachment"
        d = self._req(f"/rest/api/3/issue/{key}?fields={fields}")
        f = d["fields"]
        blocked_by = []
        for ln in f.get("issuelinks", []) or []:
            if (ln.get("type", {}).get("name") == "Blocks") and "inwardIssue" in ln:
                blocked_by.append(ln["inwardIssue"]["key"])
        comments = self._req(f"/rest/api/2/issue/{key}/comment?orderBy=-created&maxResults=20")
        status = f["status"]["name"]
        return {
            "key": d["key"],
            "summary": f.get("summary", ""),
            "description": _adf_text(f.get("description")),
            "status": status,
            "status_category": self.status_category(status),
            "assignee": (f.get("assignee") or {}).get("displayName", ""),
            "labels": f.get("labels", []) or [],
            "estimate": (f.get("timetracking") or {}).get("originalEstimate", ""),
            "links": {"blocked_by": blocked_by},
            "comments": [c.get("body", "") for c in comments.get("comments", [])],
            "attachments": [a["filename"] for a in f.get("attachment", []) or []],
        }

    def search(self, query: str) -> list[dict]:
        d = self._req("/rest/api/3/search/jql",
                      {"jql": query, "fields": ["summary", "status", "labels", "assignee"],
                       "maxResults": 100}, "POST")
        out = []
        for it in d.get("issues", []):
            f = it["fields"]
            status = f["status"]["name"]
            out.append({"key": it["key"], "summary": f.get("summary", ""),
                        "status": status, "status_category": self.status_category(status),
                        "labels": f.get("labels", []) or [],
                        "assignee": (f.get("assignee") or {}).get("displayName", "")})
        return out

    def transition(self, key: str, category: str) -> None:
        trs = self._req(f"/rest/api/3/issue/{key}/transitions")["transitions"]
        want = {"in_review": lambda n: "review" in n,
                "in_progress": lambda n: "progress" in n,
                "done": lambda n: n in [s.lower() for s in
                                        self.c.cfg("tracker.done_statuses", ["Done"])] or n == "done",
                "todo": lambda n: n in ("to do", "open", "backlog")}[category]
        target = next((t for t in trs if want(t["name"].lower())), None)
        if not target:
            raise SystemExit(f"tracker(jira): {key} has no transition toward {category!r} "
                             f"(available: {[t['name'] for t in trs]})")
        self._req(f"/rest/api/3/issue/{key}/transitions",
                  {"transition": {"id": target["id"]}}, "POST")

    def comment(self, key: str, body: str):
        self._req(f"/rest/api/2/issue/{key}/comment", {"body": body}, "POST")
        # read back — posting without read-back doesn't count as posted
        latest = self._req(f"/rest/api/2/issue/{key}/comment?orderBy=-created&maxResults=5")
        for cm in latest.get("comments", []):
            if body.strip()[:80] in cm.get("body", ""):
                return cm.get("body")
        return None

    def attach(self, key: str, path: Path):
        boundary = uuid.uuid4().hex
        data = path.read_bytes()
        ctype = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        body = ((f"--{boundary}\r\nContent-Disposition: form-data; name=\"file\"; "
                 f"filename=\"{path.name}\"\r\nContent-Type: {ctype}\r\n\r\n").encode()
                + data + f"\r\n--{boundary}--\r\n".encode())
        uploaded = self._req(f"/rest/api/3/issue/{key}/attachments", method="POST",
                             raw_body=body,
                             headers={"X-Atlassian-Token": "no-check",
                                      "Content-Type": f"multipart/form-data; boundary={boundary}"})
        url = next((a.get("content", "") for a in uploaded if a.get("filename") == path.name), "")
        # read back
        onit = self._req(f"/rest/api/3/issue/{key}?fields=attachment")
        names = {a["filename"] for a in onit["fields"].get("attachment", [])}
        if path.name not in names:
            return None
        return {"name": path.name, "md5": hashlib.md5(data).hexdigest(),
                "url": url or "(see fields.attachment)"}

    def link(self, blocker: str, blocked: str) -> None:
        # For `Blocks`, inwardIssue is the BLOCKING side.
        self._req("/rest/api/3/issueLink",
                  {"type": {"name": "Blocks"},
                   "inwardIssue": {"key": blocker}, "outwardIssue": {"key": blocked}}, "POST")
        # read back and confirm direction — never trust the sent parameters
        issue = self.get_issue(blocked)
        if blocker.upper() not in [k.upper() for k in issue["links"]["blocked_by"]]:
            raise SystemExit(f"tracker(jira): link read-back FAILED — {blocked} does not "
                             f"show 'blocked by {blocker}'; check link direction")

    def worklog(self, key: str, minutes: int) -> bool:
        self._req(f"/rest/api/3/issue/{key}/worklog", {"timeSpent": f"{minutes}m"}, "POST")
        return True

    # -- extras used by stale_verdict_check ------------------------------------
    def judged_at(self, key: str):
        """Last time the ticket moved into a judged status, from the changelog.
        Returns (iso_timestamp, description) or None."""
        judged = {s.lower() for s in self.c.cfg("tracker.done_statuses", ["Done", "Closed", "Resolved"])}
        d = self._req(f"/rest/api/3/issue/{key}?expand=changelog&fields=status")
        best = None
        for entry in d.get("changelog", {}).get("histories", []):
            for item in entry.get("items", []):
                if item.get("field") == "status" and (item.get("toString") or "").lower() in judged:
                    if best is None or entry["created"] > best[0]:
                        best = (entry["created"], f"moved to {item['toString']}")
        if best is None:
            return None
        return best[0].replace(".000", ""), best[1]
