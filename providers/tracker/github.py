"""GitHub Issues tracker provider for vteam (installed as .vteam/providers/tracker_github.py).

Env: GITHUB_TOKEN (or GH_TOKEN) — a PAT with Issues read/write; repo from
GITHUB_REPO=owner/repo or derived from `git remote get-url origin` (github.com
remotes only — anything else is a loud error, never a guess). GHE: set
GITHUB_API_URL=https://<host>/api/v3.

KEY MAPPING — vteam keeps its <PREFIX>-<number> ticket keys; GitHub has bare
issue numbers. `project.key` from vteam.config.yaml is the prefix, and the
NUMBER is the GitHub issue number: PROJ-123 ⇄ issue #123 in $GITHUB_REPO.
A key whose prefix is not project.key dies loudly (it would silently address
the wrong issue), and every key passes valid_key() BEFORE a URL is built.

STATUS CONVENTION — GitHub issues have two states, vteam has four categories;
labels carry the difference:
    open  + label `in-progress` → in_progress        open + `in-review` → in_review
    open  + neither             → todo               closed             → done
transition() does that label math (and closes/reopens); state is authoritative
for done — tracker.done_statuses is NOT consulted because GitHub's own state
machine already says what "done" is (documented deviation, not an oversight).

Other provider-specific knowledge kept here, out of the gates:
  · comments: the API lists ASCENDING with 100/page — this provider paginates
    to the end and REVERSES to honor the interface's NEWEST-FIRST contract;
  · links: no native blocked-by — link() prepends a `- [ ] Blocked by #<n>`
    task-list line to the blocked issue's body and READS IT BACK;
  · attachments: the Issues API cannot upload files — attach() posts a
    `vteam-attachment:` pointer comment (read back) and then exits LOUDLY:
    the committed evidence dir (paths.evidence) is the attachment of record;
  · estimate: no native field — a label `estimate:<value>` is read as one;
  · worklogs: none — worklog() returns False (callers skip LOUDLY);
  · judged_at: closed_at on the issue — good enough for stale_verdict;
  · a token must never follow a redirect (repo renames 301) — refused loudly;
  · search results mix in PRs — filtered out (vteam keys map to ISSUES).

Selftest (NO network — the _req boundary is replaced by an in-memory GitHub):
    python3 providers/tracker/github.py --selftest
"""
from __future__ import annotations

import hashlib
import json
import re
import subprocess
import urllib.parse
import urllib.request
from pathlib import Path

import sys
_here = Path(__file__).resolve()
for _lib in (_here.parent.parent / "scripts" / "lib",             # installed: .vteam/providers/
             _here.parents[2] / "core" / "scripts" / "lib"):      # framework repo: providers/tracker/
    if _lib.is_dir():
        sys.path.insert(0, str(_lib))
        break
from tracker import Tracker, valid_key  # noqa: E402


class _RefuseRedirect(urllib.request.HTTPRedirectHandler):
    """Bearer auth must never be re-sent to a host we didn't choose: urllib's
    default handler re-issues the original headers (Authorization included) to
    the redirect target. Refuse loudly instead — GitHub 301s renamed repos, so
    a redirect means GITHUB_REPO points at a stale name."""
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise urllib.error.HTTPError(
            req.full_url, code,
            f"redirect to {newurl} refused — the token is never re-sent on a "
            f"redirect; update GITHUB_REPO/GITHUB_API_URL to the final name", headers, fp)


_OPENER = urllib.request.build_opener(_RefuseRedirect)

# status-carrying labels (the convention in the module docstring)
_CATEGORY_LABEL = {"in_progress": "in-progress", "in_review": "in-review"}
_BLOCKED_RE = re.compile(r"^[ \t]*(?:-\s*\[[ xX]\]\s*)?Blocked by #(\d+)\b", re.M)
_ATTACH_RE = re.compile(r"^vteam-attachment: (.+?) \(md5 ", re.M)


def _parse_remote(url: str):
    """owner/repo from a github.com remote (https/ssh/scp-like), else None.
    Host is anchored — `evil.com/github.com/…` must not parse."""
    url = url.strip()
    m = re.fullmatch(r"(?:ssh://)?git@github\.com[:/]([A-Za-z0-9_.-]+)/([A-Za-z0-9_.-]+?)(?:\.git)?/?", url)
    if not m:
        m = re.fullmatch(r"(?:https|http|git)://(?:[^/@]+@)?github\.com/"
                         r"([A-Za-z0-9_.-]+)/([A-Za-z0-9_.-]+?)(?:\.git)?/?", url)
    return f"{m.group(1)}/{m.group(2)}" if m else None


class Provider(Tracker):
    def __init__(self, c):
        super().__init__(c)
        self.token = c.env("GITHUB_TOKEN") or c.env("GH_TOKEN")
        if not self.token:
            # Fallback: the developer's own gh CLI session (field-trial friction:
            # gh was signed in, yet the provider demanded a hand-rolled .env token).
            # stderr suppressed; a missing/logged-out gh just falls through.
            import subprocess
            try:
                r = subprocess.run(["gh", "auth", "token"], capture_output=True, text=True)
                if r.returncode == 0 and r.stdout.strip():
                    self.token = r.stdout.strip()
            except FileNotFoundError:
                pass  # no gh CLI installed — the error below names both paths
        if not self.token:
            raise SystemExit("tracker(github): no token — set GITHUB_TOKEN/GH_TOKEN in .env, "
                             "or sign in once with `gh auth login` (the provider borrows "
                             "`gh auth token` when the env is empty)")
        self.base = (c.env("GITHUB_API_URL") or "https://api.github.com").rstrip("/")
        if not self.base.startswith("https://"):
            # Bearer auth over plain http mails the token to the network.
            if self.base.startswith("http://") and c.env("GITHUB_ALLOW_HTTP") == "1":
                print("⚠️  tracker(github): plain-http GITHUB_API_URL allowed by "
                      "GITHUB_ALLOW_HTTP=1 — the token travels UNENCRYPTED", file=sys.stderr)
            else:
                raise SystemExit("tracker(github): GITHUB_API_URL must be https:// "
                                 "(Bearer auth over http leaks the token; lab-only "
                                 "override: GITHUB_ALLOW_HTTP=1)")
        repo = c.env("GITHUB_REPO")
        if not repo:
            out = subprocess.run(["git", "-C", str(c.root), "remote", "get-url", "origin"],
                                 capture_output=True, text=True)
            if out.returncode != 0:
                raise SystemExit("tracker(github): no GITHUB_REPO in .env and no origin "
                                 "remote — set GITHUB_REPO=owner/repo")
            url = out.stdout.strip()
            repo = _parse_remote(url)
            if not repo:
                shown = re.sub(r"(://)[^/@]+@", r"\1", url)  # remotes may embed PATs — never print them
                raise SystemExit(f"tracker(github): origin {shown!r} is not a github.com "
                                 f"remote — set GITHUB_REPO=owner/repo in .env")
        if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repo):
            raise SystemExit(f"tracker(github): GITHUB_REPO must be owner/repo (got {repo!r})")
        self.repo = repo
        self.prefix = str(c.cfg("project.key")).upper()

    def _req(self, path: str, data=None, method="GET", headers=None):
        h = {"Authorization": f"Bearer {self.token}",  # header, NEVER in a URL
             "Accept": "application/vnd.github+json",
             "X-GitHub-Api-Version": "2022-11-28"}
        if data is not None:
            h["Content-Type"] = "application/json"
        h.update(headers or {})
        req = urllib.request.Request(
            self.base + path,
            data=json.dumps(data).encode() if data is not None else None,
            headers=h, method=method)
        with _OPENER.open(req, timeout=60) as r:  # redirects refused, never re-authed
            text = r.read().decode()
        return json.loads(text) if text else {}

    def _num(self, key: str) -> int:
        """<PREFIX>-<n> → GitHub issue number n. valid_key() dies on traversal/
        malformed keys BEFORE any URL is built; a foreign prefix dies too —
        it would silently address the wrong project's issue numbers."""
        key = valid_key(key)
        prefix, num = key.rsplit("-", 1)
        if prefix != self.prefix:
            raise SystemExit(f"tracker(github): key {key} has prefix {prefix!r} but "
                             f"project.key is {self.prefix!r} — refusing to map it "
                             f"onto {self.repo} issue numbers")
        return int(num)

    def _status(self, state: str, labels: list[str]) -> tuple[str, str]:
        """(status, status_category) from the documented state+label convention."""
        if state == "closed":
            return "Closed", "done"
        for lbl, status, cat in (("in-review", "In Review", "in_review"),
                                 ("in-progress", "In Progress", "in_progress")):
            if lbl in labels:
                return status, cat
        return "To Do", "todo"

    def _comments(self, n: int) -> list[str]:
        """All comment bodies, NEWEST-FIRST. The API lists ascending, 100/page —
        paginate to the end, then reverse (interface contract, not a choice)."""
        out, page = [], 1
        while True:
            batch = self._req(f"/repos/{self.repo}/issues/{n}/comments?per_page=100&page={page}")
            out.extend(batch)
            if len(batch) < 100:
                break
            page += 1
            if page > 50:
                raise SystemExit(f"tracker(github): issue #{n} has more than 5000 "
                                 f"comments — refusing to page further")
        return [cm.get("body", "") for cm in reversed(out)]

    # -- interface -------------------------------------------------------------
    def ping(self) -> tuple[bool, str]:
        try:
            d = self._req(f"/repos/{self.repo}")
        except Exception as exc:
            return False, f"API unreachable ({exc}) — bad GITHUB_TOKEN or repo {self.repo} not visible"
        if not isinstance(d, dict) or str(d.get("full_name", "")).lower() != self.repo.lower():
            return False, (f"{self.base}/repos/{self.repo} answered but not with that repo's "
                           f"JSON — wrong GITHUB_API_URL or renamed repo")
        if not d.get("has_issues"):
            return False, f"repo {self.repo} has issues DISABLED — enable them or point GITHUB_REPO elsewhere"
        return True, f"token OK, repo {d['full_name']} readable, issues enabled"

    def get_issue(self, key: str) -> dict:
        n = self._num(key)
        d = self._req(f"/repos/{self.repo}/issues/{n}")
        if "pull_request" in d:
            raise SystemExit(f"tracker(github): #{n} is a pull request, not an issue — "
                             f"vteam keys map to ISSUE numbers")
        labels = [l["name"] if isinstance(l, dict) else str(l) for l in d.get("labels", []) or []]
        status, cat = self._status(d.get("state", "open"), labels)
        body = d.get("body") or ""
        comments = self._comments(n)
        return {
            "key": f"{self.prefix}-{n}",
            "summary": d.get("title", ""),
            "description": body,
            "status": status,
            "status_category": cat,
            "assignee": (d.get("assignee") or {}).get("login", ""),
            "labels": labels,
            "estimate": next((l.split(":", 1)[1] for l in labels if l.startswith("estimate:")), ""),
            "links": {"blocked_by": [f"{self.prefix}-{m}" for m in _BLOCKED_RE.findall(body)]},
            "comments": comments,
            "attachments": [m for cm in comments for m in _ATTACH_RE.findall(cm)],
        }

    def search(self, query: str) -> list[dict]:
        q = query if "repo:" in query else f"repo:{self.repo} {query}".strip()
        d = self._req(f"/search/issues?q={urllib.parse.quote(q)}&per_page=100")
        out = []
        for it in d.get("items", []):
            if "pull_request" in it:
                continue  # vteam keys map to issues, never PRs
            labels = [l["name"] if isinstance(l, dict) else str(l) for l in it.get("labels", []) or []]
            status, cat = self._status(it.get("state", "open"), labels)
            out.append({"key": f"{self.prefix}-{it['number']}", "summary": it.get("title", ""),
                        "status": status, "status_category": cat, "labels": labels,
                        "assignee": (it.get("assignee") or {}).get("login", "")})
        return out

    def transition(self, key: str, category: str) -> None:
        n = self._num(key)
        if category not in ("todo", "in_progress", "in_review", "done"):
            raise SystemExit(f"tracker(github): unknown transition category {category!r}")
        cur = self._req(f"/repos/{self.repo}/issues/{n}")
        labels = [l["name"] if isinstance(l, dict) else str(l) for l in cur.get("labels", []) or []]
        labels = [l for l in labels if l not in _CATEGORY_LABEL.values()]  # drop old status labels
        if category in _CATEGORY_LABEL:
            labels.append(_CATEGORY_LABEL[category])
        payload = {"labels": labels, "state": "closed" if category == "done" else "open"}
        if category == "done":
            payload["state_reason"] = "completed"
        self._req(f"/repos/{self.repo}/issues/{n}", payload, "PATCH")
        # read back — the tracker's word, never the sent parameters
        after = self.get_issue(key)
        if after["status_category"] != category:
            raise SystemExit(f"tracker(github): transition({key}, {category}) did not stick — "
                             f"issue #{n} reads back as {after['status_category']!r}")

    def comment(self, key: str, body: str):
        n = self._num(key)
        self._req(f"/repos/{self.repo}/issues/{n}/comments", {"body": body}, "POST")
        # read back — posting without read-back doesn't count as posted
        for cm in self._comments(n)[:5]:
            if body.strip()[:80] in cm:
                return cm
        return None

    def attach(self, key: str, path: Path):
        """The GitHub Issues API cannot upload files — implemented HONESTLY:
        a `vteam-attachment:` pointer comment is posted (and read back), then
        this exits loudly. The committed evidence dir (paths.evidence) is the
        attachment of record; get_issue() lists pointer names as attachments."""
        n = self._num(key)
        md5 = hashlib.md5(path.read_bytes()).hexdigest()
        evd = str(self.c.cfg("paths.evidence", "evd"))
        try:
            shown = str(path.resolve().relative_to(self.c.root))
        except ValueError:
            shown = path.name
        pointer = (f"vteam-attachment: {path.name} (md5 {md5})\n\n"
                   f"GitHub Issues cannot host file uploads — the file is committed in "
                   f"this repo at `{shown}` (evidence dir `{evd}/`).")
        if self.comment(key, pointer) is None:
            raise SystemExit(f"tracker(github): attach({key}) pointer comment read-back "
                             f"FAILED on #{n} — nothing was recorded")
        raise SystemExit(f"tracker(github): the GitHub Issues API cannot upload files — "
                         f"{path.name} stays in the committed evidence dir ({evd}/) and a "
                         f"pointer comment (read back OK) now sits on #{n}. Treat the "
                         f"{evd}/ copy as the attachment of record.")

    def link(self, blocker: str, blocked: str) -> None:
        bn, dn = self._num(blocker), self._num(blocked)
        cur = self._req(f"/repos/{self.repo}/issues/{dn}")
        body = cur.get("body") or ""
        if not re.search(rf"Blocked by #{bn}\b", body):
            self._req(f"/repos/{self.repo}/issues/{dn}",
                      {"body": f"- [ ] Blocked by #{bn}\n{body}"}, "PATCH")
        # read back and confirm — never trust the sent parameters
        issue = self.get_issue(blocked)
        if f"{self.prefix}-{bn}" not in [k.upper() for k in issue["links"]["blocked_by"]]:
            raise SystemExit(f"tracker(github): link read-back FAILED — issue #{dn} body "
                             f"does not carry 'Blocked by #{bn}'")

    def worklog(self, key: str, minutes: int) -> bool:
        return False  # GitHub has no worklogs — interface contract: False = skip LOUDLY

    # -- extras used by stale_verdict_check ------------------------------------
    def judged_at(self, key: str):
        """closed_at from the issue — on GitHub, the judged status IS the closed
        state. Returns (iso_timestamp, description) or None while open."""
        d = self._req(f"/repos/{self.repo}/issues/{self._num(key)}")
        ts = d.get("closed_at")
        if not ts:
            return None
        reason = d.get("state_reason")
        return ts, f"closed ({reason})" if reason else "closed"


# -- selftest (house rule: green fixture + red mutations, NO network) -----------
class _StubCtx:
    """Offline stand-in for ctx.Ctx — just enough surface for the provider."""
    def __init__(self, env, cfg):
        self.root = Path("/vteam-selftest-does-not-exist")
        self._env, self._cfg = env, cfg

    def env(self, key, default=None):
        return self._env.get(key, default)

    def cfg(self, dotted, default=None):
        return self._cfg.get(dotted, default)


class _FakeHub:
    """The _req boundary replaced by a stateful in-memory GitHub. drop_writes
    simulates a tracker that answers 2xx but persists nothing — read-backs
    must catch exactly that."""
    def __init__(self, repo_json=None, issues=None, comments=None, drop_writes=False):
        self.repo_json = repo_json if repo_json is not None else {"full_name": "octo/demo", "has_issues": True}
        self.issues = issues or {}
        self.comments = comments or {}
        self.drop_writes = drop_writes
        self.calls = []

    def __call__(self, path, data=None, method="GET", headers=None):
        self.calls.append((method, path))
        u = urllib.parse.urlsplit(path)
        parts = u.path.strip("/").split("/")
        if parts[0] == "search":
            return {"items": [dict(v) for v in self.issues.values()]}
        assert parts[:3] == ["repos", "octo", "demo"], f"unrouted path {path}"
        if len(parts) == 3:                      # GET /repos/o/r
            return dict(self.repo_json)
        n = int(parts[4])
        if len(parts) == 5:                      # /repos/o/r/issues/N
            if method == "PATCH" and not self.drop_writes:
                self.issues[n].update({k: v for k, v in (data or {}).items() if k != "labels"})
                if "labels" in (data or {}):
                    self.issues[n]["labels"] = [{"name": x} for x in data["labels"]]
            return dict(self.issues[n])
        if parts[5] == "comments":               # /repos/o/r/issues/N/comments
            if method == "POST":
                if not self.drop_writes:
                    self.comments.setdefault(n, []).append({"body": data["body"]})
                return {"id": 1, "body": data["body"]}
            q = urllib.parse.parse_qs(u.query)
            page = int(q.get("page", ["1"])[0])
            per = int(q.get("per_page", ["100"])[0])
            return list(self.comments.get(n, []))[(page - 1) * per: page * per]
        raise AssertionError(f"fake hub: unrouted {method} {path}")


def _must_exit(fn, what):
    try:
        fn()
    except SystemExit:
        return
    raise AssertionError(f"{what} should have exited loudly")


def _selftest():
    cfg = {"project.key": "PROJ", "paths.evidence": "evd"}
    p = Provider(_StubCtx({"GITHUB_TOKEN": "t0k", "GITHUB_REPO": "octo/demo"}, cfg))

    # origin-remote parsing: github.com forms parse, anything else refuses
    assert _parse_remote("https://github.com/octo/demo.git") == "octo/demo"
    assert _parse_remote("git@github.com:octo/demo.git") == "octo/demo"
    assert _parse_remote("ssh://git@github.com/octo/demo") == "octo/demo"
    assert _parse_remote("https://x-access-token:tok@github.com/octo/demo") == "octo/demo"
    assert _parse_remote("https://gitlab.com/octo/demo.git") is None
    assert _parse_remote("https://evil.com/github.com/octo/demo") is None

    # mutation: an http:// base must die at construction (token would travel plaintext)
    _must_exit(lambda: Provider(_StubCtx({"GITHUB_TOKEN": "t", "GITHUB_REPO": "o/r",
                                          "GITHUB_API_URL": "http://api.github.com"}, cfg)),
               "http:// GITHUB_API_URL")

    # get_issue mapping: state+labels → status, body → blocked_by, estimate label
    issue42 = {"number": 42, "title": "Demo issue", "state": "open",
               "body": "- [ ] Blocked by #7\n\nThe body.",
               "labels": [{"name": "in-review"}, {"name": "bug"}, {"name": "estimate:2d"}],
               "assignee": {"login": "octocat"}, "closed_at": None}
    hub = _FakeHub(issues={42: issue42},
                   comments={42: [{"body": f"comment number {i}"} for i in range(1, 104)]})
    p._req = hub
    it = p.get_issue("PROJ-42")
    assert it["key"] == "PROJ-42" and it["summary"] == "Demo issue", it
    assert it["status_category"] == "in_review" and it["status"] == "In Review", it
    assert it["links"]["blocked_by"] == ["PROJ-7"], it["links"]
    assert it["estimate"] == "2d" and "bug" in it["labels"], it
    assert it["assignee"] == "octocat"
    # comments NEWEST-FIRST — across the 100-per-page boundary (103 on file)
    assert len(it["comments"]) == 103, len(it["comments"])
    assert it["comments"][0] == "comment number 103", it["comments"][0]
    assert it["comments"][-1] == "comment number 1", it["comments"][-1]

    # comment + read-back lands newest-first
    assert p.comment("PROJ-42", "hello from the gate")
    assert p.get_issue("PROJ-42")["comments"][0] == "hello from the gate"

    # transition label math: old status label out, new in, others kept; done closes
    p.transition("PROJ-42", "in_progress")
    names = [l["name"] for l in hub.issues[42]["labels"]]
    assert "in-progress" in names and "in-review" not in names and "bug" in names, names
    p.transition("PROJ-42", "done")
    assert hub.issues[42]["state"] == "closed"
    p.transition("PROJ-42", "todo")
    names = [l["name"] for l in hub.issues[42]["labels"]]
    assert hub.issues[42]["state"] == "open" and "in-progress" not in names and "in-review" not in names

    # judged_at ⇄ closed_at (with and without a state_reason)
    hub.issues[42].update({"state": "closed", "closed_at": "2026-01-02T03:04:05Z"})
    ts, why = p.judged_at("PROJ-42")
    assert ts == "2026-01-02T03:04:05Z" and why == "closed (completed)", (ts, why)
    hub.issues[42]["state_reason"] = None
    assert p.judged_at("PROJ-42") == ("2026-01-02T03:04:05Z", "closed")
    hub.issues[42].update({"state": "open", "closed_at": None})
    assert p.judged_at("PROJ-42") is None

    # link: task-list line prepended to the blocked body, then read back
    hub.issues[9] = {"number": 9, "title": "blocked one", "state": "open", "body": "", "labels": []}
    hub.comments[9] = []
    p.link("PROJ-42", "PROJ-9")
    assert hub.issues[9]["body"].startswith("- [ ] Blocked by #42"), hub.issues[9]["body"]
    assert "PROJ-42" in p.get_issue("PROJ-9")["links"]["blocked_by"]

    # mutations: a tracker that answers 2xx but persists NOTHING must go red
    dead = _FakeHub(issues={9: {"number": 9, "title": "b", "state": "open", "body": "", "labels": []}},
                    comments={9: []}, drop_writes=True)
    p._req = dead
    _must_exit(lambda: p.link("PROJ-42", "PROJ-9"), "link read-back on a dropped write")
    _must_exit(lambda: p.transition("PROJ-9", "in_review"), "transition read-back on a dropped write")
    assert p.comment("PROJ-9", "will vanish") is None  # comment read-back: None = failed

    # attach: pointer comment posted + read back, then a LOUD documented exit
    p._req = hub
    hub.comments[9] = []
    me = Path(__file__)  # github.py in the framework repo, tracker_github.py installed
    _must_exit(lambda: p.attach("PROJ-9", me), "attach on GitHub")
    assert any(cm["body"].startswith(f"vteam-attachment: {me.name}") for cm in hub.comments[9]), hub.comments[9]
    assert me.name in p.get_issue("PROJ-9")["attachments"]

    # search maps issues and filters PRs out
    hub.issues[50] = {"number": 50, "title": "a PR", "state": "open", "body": "",
                      "labels": [], "pull_request": {"url": "x"}}
    found = {i["key"] for i in p.search("anything")}
    assert "PROJ-42" in found and "PROJ-9" in found and "PROJ-50" not in found, found
    _must_exit(lambda: p.get_issue("PROJ-50"), "get_issue on a PR number")

    # mutations: bad/foreign keys die BEFORE any URL is built — zero requests
    counter = _FakeHub(issues={}, comments={})
    p._req = counter
    for bad in ("../../etc/passwd", "PROJ-1/../2", "PROJ_1", "PROJ-", "-1", "PROJ-1x", "OTHER-1"):
        for op in (lambda k: p.get_issue(k), lambda k: p.comment(k, "x"),
                   lambda k: p.link(k, "PROJ-9"), lambda k: p.transition(k, "done")):
            _must_exit(lambda: op(bad), f"key {bad!r}")
    assert counter.calls == [], f"a bad key still built a request: {counter.calls}"

    # ping honesty: real repo JSON green; disabled issues / lookalike JSON red
    p._req = _FakeHub()
    ok, msg = p.ping()
    assert ok, msg
    p._req = _FakeHub(repo_json={"full_name": "octo/demo", "has_issues": False})
    ok, msg = p.ping()
    assert not ok and "DISABLED" in msg, msg
    p._req = _FakeHub(repo_json={"message": "Not Found"})
    ok, _ = p.ping()
    assert not ok

    assert p.worklog("PROJ-42", 30) is False  # no worklogs on GitHub — honest skip

    print("tracker(github) selftest: OK (mapping, comments NEWEST-FIRST across pages, "
          "transition label math, link/transition/comment read-backs red on dropped "
          "writes, attach honest-exit, 7 bad keys × 4 ops die pre-URL, http refused, "
          "ping honesty)")


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        _selftest()
    else:
        print(__doc__)
