"""Tracker provider interface + the built-in `markdown` provider.

Gates never speak HTTP or provider dialects — they call this SEMANTIC interface
(DESIGN.md §3). Providers are selected by `tracker.provider` in vteam.config.yaml:

    markdown  — built in here: a ticket is a file {paths.pm}/../backlog/<KEY>.md
                (dir configurable via paths.backlog, default docs/backlog) with a
                frontmatter-ish header block. Zero external services — the demo,
                e2e, and no-tracker fallback path.
    jira, github, linear — loaded from .vteam/providers/tracker_<name>.py
                (jira ships in Phase 4); must subclass Tracker.

Interface (all providers):
    get_issue(key)   -> Issue dict: {key, summary, description, status,
                        status_category, assignee, labels, estimate, links,
                        comments, attachments}
    search(query)    -> [Issue]  (provider-native query string)
    transition(key, category)      # category: in_progress|in_review|done|todo
    comment(key, body) -> the body as READ BACK from the tracker (None = failed)
    attach(key, path)  -> {name, md5, url} as READ BACK (None = failed)
    link(blocker_key, blocked_key)  # direction fixed by the interface
    worklog(key, minutes) -> bool   # False = provider lacks worklogs (skip LOUDLY)

status_category maps provider-specific status names via config:
`tracker.done_statuses`, `tracker.review_status`.
"""
from __future__ import annotations

import hashlib
import importlib.util
import re
import shutil
from pathlib import Path

from ctx import Ctx


class Tracker:
    def __init__(self, c: Ctx):
        self.c = c

    # -- required interface ---------------------------------------------------
    def get_issue(self, key: str) -> dict: raise NotImplementedError
    def search(self, query: str) -> list[dict]: raise NotImplementedError
    def transition(self, key: str, category: str) -> None: raise NotImplementedError
    def comment(self, key: str, body: str): raise NotImplementedError
    def attach(self, key: str, path: Path): raise NotImplementedError
    def link(self, blocker: str, blocked: str) -> None: raise NotImplementedError
    def worklog(self, key: str, minutes: int) -> bool: return False

    # -- shared helpers --------------------------------------------------------
    def status_category(self, status: str) -> str:
        s = status.strip().lower()
        done = [str(x).lower() for x in self.c.cfg("tracker.done_statuses", ["Done", "Closed", "Resolved"])]
        review = str(self.c.cfg("tracker.review_status", "In Review")).lower()
        if s in done:
            return "done"
        if s == review:
            return "in_review"
        if s in ("in progress", "doing"):
            return "in_progress"
        return "todo"


class MarkdownTracker(Tracker):
    """Tickets as markdown files — the zero-service provider.

    File shape (`<backlog>/<KEY>.md`):
        # <KEY>: <summary>
        - status: To Do
        - assignee: <name>
        - labels: a, b
        - estimate: 1d
        - blocked-by: KEY-2, KEY-3

        <description…>

        ## Comments
        ### <timestamp>
        <body>
    """

    def __init__(self, c: Ctx):
        super().__init__(c)
        self.dir = c.root / str(c.cfg("paths.backlog", "docs/backlog"))

    def _file(self, key: str) -> Path:
        return self.dir / f"{key.upper()}.md"

    def _parse(self, key: str, text: str) -> dict:
        def field(name, default=""):
            m = re.search(rf"^- {name}:\s*(.*)$", text, re.M)
            return m.group(1).strip() if m else default
        h1 = re.search(r"^# \S+?:\s*(.*)$", text, re.M)
        comments = re.findall(r"^### .*?\n(.*?)(?=^### |\Z)", text.split("## Comments", 1)[-1],
                              re.M | re.S) if "## Comments" in text else []
        status = field("status", "To Do")
        return {
            "key": key.upper(),
            "summary": h1.group(1) if h1 else "",
            "description": text,
            "status": status,
            "status_category": self.status_category(status),
            "assignee": field("assignee"),
            "labels": [x.strip() for x in field("labels").split(",") if x.strip()],
            "estimate": field("estimate"),
            "links": {"blocked_by": [x.strip().upper() for x in field("blocked-by").split(",") if x.strip()]},
            "comments": [c.strip() for c in comments],
            "attachments": sorted(p.name for p in (self.dir / "attachments" / key.upper()).glob("*"))
                           if (self.dir / "attachments" / key.upper()).is_dir() else [],
        }

    def get_issue(self, key: str) -> dict:
        f = self._file(key)
        if not f.is_file():
            raise SystemExit(f"tracker(markdown): no ticket file {f.relative_to(self.c.root)}")
        return self._parse(key, f.read_text(encoding="utf-8"))

    def search(self, query: str) -> list[dict]:
        out = []
        for f in sorted(self.dir.glob("*.md")):
            issue = self._parse(f.stem, f.read_text(encoding="utf-8"))
            if not query or query.lower() in (issue["summary"] + " " + " ".join(issue["labels"])).lower():
                out.append(issue)
        return out

    def transition(self, key: str, category: str) -> None:
        names = {"todo": "To Do", "in_progress": "In Progress",
                 "in_review": str(self.c.cfg("tracker.review_status", "In Review")),
                 "done": str(self.c.cfg("tracker.done_statuses", ["Done"])[0]
                             if isinstance(self.c.cfg("tracker.done_statuses", ["Done"]), list) else "Done")}
        f = self._file(key)
        text = f.read_text(encoding="utf-8")
        new = re.sub(r"^- status:.*$", f"- status: {names[category]}", text, count=1, flags=re.M)
        if new == text and "- status:" not in text:
            raise SystemExit(f"tracker(markdown): {f.name} has no '- status:' line")
        f.write_text(new, encoding="utf-8")

    def comment(self, key: str, body: str):
        from datetime import datetime, timezone
        f = self._file(key)
        text = f.read_text(encoding="utf-8")
        if "## Comments" not in text:
            text += "\n## Comments\n"
        stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
        f.write_text(text + f"\n### {stamp}\n{body}\n", encoding="utf-8")
        # read back — posting without read-back doesn't count as posted
        issue = self.get_issue(key)
        return body if any(body.strip() in c for c in issue["comments"]) else None

    def attach(self, key: str, path: Path):
        dest_dir = self.dir / "attachments" / key.upper()
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest = dest_dir / path.name
        shutil.copy2(path, dest)
        if not dest.is_file():  # read back
            return None
        return {"name": path.name,
                "md5": hashlib.md5(dest.read_bytes()).hexdigest(),
                "url": str(dest.relative_to(self.c.root))}

    def link(self, blocker: str, blocked: str) -> None:
        f = self._file(blocked)
        text = f.read_text(encoding="utf-8")
        m = re.search(r"^- blocked-by:\s*(.*)$", text, re.M)
        if m:
            existing = [x.strip() for x in m.group(1).split(",") if x.strip()]
            if blocker.upper() not in [x.upper() for x in existing]:
                new_val = ", ".join(existing + [blocker.upper()])
                text = text[:m.start()] + f"- blocked-by: {new_val}" + text[m.end():]
        else:
            text = re.sub(r"^(- status:.*)$", rf"\1\n- blocked-by: {blocker.upper()}",
                          text, count=1, flags=re.M)
        f.write_text(text, encoding="utf-8")


def load(c: Ctx) -> Tracker:
    name = str(c.cfg("tracker.provider", "markdown"))
    if name == "markdown":
        return MarkdownTracker(c)
    mod_path = c.root / ".vteam" / "providers" / f"tracker_{name}.py"
    if not mod_path.is_file():
        raise SystemExit(f"tracker: provider {name!r} not installed ({mod_path} missing) — "
                         f"run `npx vteam init` or switch tracker.provider to 'markdown'")
    spec = importlib.util.spec_from_file_location(f"tracker_{name}", mod_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod.Provider(c)
