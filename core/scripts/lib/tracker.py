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
                        `comments` is NEWEST-FIRST — a fixed interface
                        semantic, not a provider choice: comment_check reads
                        comments[:5] as "the latest 5". jira orders with
                        orderBy=-created; the markdown provider appends
                        oldest-first on disk and REVERSES at parse time.
    search(query)    -> [Issue]  (provider-native query string)
    transition(key, category)      # category: in_progress|in_review|done|todo
    comment(key, body) -> the body as READ BACK from the tracker (None = failed)
    attach(key, path)  -> {name, md5, url} as READ BACK (None = failed)
    link(blocker_key, blocked_key)  # direction fixed by the interface
    worklog(key, minutes) -> bool   # False = provider lacks worklogs (skip LOUDLY)

status_category maps provider-specific status names via config:
`tracker.done_statuses`, `tracker.review_status`.

Ticket keys are UNTRUSTED input (agents copy them from tracker/branch content):
valid_key() rejects anything but <letters+digits>-<number> BEFORE a path or URL
is built from a key — see MarkdownTracker._file/attach/link and the jira
provider. Selftest: python3 tracker.py --selftest.
"""
from __future__ import annotations

import hashlib
import importlib.util
import re
import shutil
import sys
from pathlib import Path

from ctx import Ctx

KEY_RE = re.compile(r"^[A-Za-z][A-Za-z0-9]*-[0-9]+$")


def valid_key(key: str) -> str:
    """Validate a ticket key BEFORE any filesystem path or URL is built from it.

    Keys flow in from argv, plan.yaml and tracker content — all agent-writable —
    so '../../x' or 'PROJ-1/../..' must die LOUDLY here, never traverse a path
    or bend a request URL. Returns the canonical UPPERCASE key."""
    k = str(key).strip()
    if not KEY_RE.fullmatch(k):
        raise SystemExit(f"tracker: invalid ticket key {key!r} — expected "
                         f"<PREFIX>-<number> (letters/digits prefix, e.g. PROJ-12); "
                         f"refusing to build a path or URL from it")
    return k.upper()


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
    def ping(self) -> tuple[bool, str]: return True, "no ping implemented"
    def judged_at(self, key: str):
        """(iso_timestamp, description) of the last move into a judged status, or
        None when the provider keeps no changelog (callers must then rely on the
        pinned COMMIT sha)."""
        return None

    # -- shared helpers --------------------------------------------------------
    def status_category(self, status: str) -> str:
        s = status.strip().lower()
        raw = self.c.cfg("tracker.done_statuses", ["Done", "Closed", "Resolved"])
        if isinstance(raw, str):
            raw = [raw]  # scalar config value = ONE status, never its characters (H5)
        done = [str(x).lower() for x in raw]
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

    File appends are oldest-first; the parsed `comments` list is REVERSED to
    honor the interface's newest-first contract (comment_check reads
    comments[:5] as "the latest 5" — oldest-first would false-red every ticket
    past 5 comments).
    """

    def __init__(self, c: Ctx):
        super().__init__(c)
        self.dir = c.root / str(c.cfg("paths.backlog", "docs/backlog"))

    def _file(self, key: str) -> Path:
        return self.dir / f"{valid_key(key)}.md"

    def ping(self) -> tuple[bool, str]:
        if self.dir.is_dir():
            return True, f"backlog dir {self.dir.relative_to(self.c.root)} ({len(list(self.dir.glob('*.md')))} tickets)"
        return False, f"backlog dir {self.dir.relative_to(self.c.root)} missing — mkdir it or set paths.backlog"

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
            # file order is oldest-first (appends) — interface wants NEWEST-FIRST
            "comments": [c.strip() for c in reversed(comments)],
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
        done_raw = self.c.cfg("tracker.done_statuses", ["Done"])
        if isinstance(done_raw, str):
            done_raw = [done_raw]  # scalar config value = ONE status name (H5)
        names = {"todo": "To Do", "in_progress": "In Progress",
                 "in_review": str(self.c.cfg("tracker.review_status", "In Review")),
                 "done": str(done_raw[0]) if done_raw else "Done"}
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
        dest_dir = self.dir / "attachments" / valid_key(key)
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest = dest_dir / path.name
        shutil.copy2(path, dest)
        if not dest.is_file():  # read back
            return None
        return {"name": path.name,
                "md5": hashlib.md5(dest.read_bytes()).hexdigest(),
                "url": str(dest.relative_to(self.c.root))}

    def link(self, blocker: str, blocked: str) -> None:
        blocker = valid_key(blocker)  # written into the ticket file — validate first
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
        # framework-repo dev fallback: providers/tracker/<name>.py next to core/
        dev = Path(__file__).resolve().parents[3] / "providers" / "tracker" / f"{name}.py"
        if dev.is_file():
            mod_path = dev
        else:
            raise SystemExit(f"tracker: provider {name!r} not installed ({mod_path} missing) — "
                             f"run `npx vteam-harness init` or switch tracker.provider to 'markdown'")
    spec = importlib.util.spec_from_file_location(f"tracker_{name}", mod_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod.Provider(c)


def _selftest():
    import subprocess
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        subprocess.run(["git", "init", "-q", str(root)], check=True)
        (root / "vteam.config.yaml").write_text(
            "version: 1\nproject:\n  key: PROJ\npaths:\n  backlog: docs/backlog\n"
            "tracker:\n  provider: markdown\n", encoding="utf-8")
        bl = root / "docs" / "backlog"
        bl.mkdir(parents=True)
        (bl / "PROJ-1.md").write_text("# PROJ-1: demo ticket\n- status: To Do\n\nbody\n",
                                      encoding="utf-8")
        t = MarkdownTracker(Ctx(start=root))

        # ordering contract: comments() is NEWEST-FIRST, including past 5 comments
        for i in range(1, 7):
            assert t.comment("PROJ-1", f"comment number {i}") is not None, "read-back failed"
        issue = t.get_issue("PROJ-1")
        assert len(issue["comments"]) == 6, issue["comments"]
        assert "comment number 6" in issue["comments"][0], issue["comments"][0]
        assert "comment number 1" in issue["comments"][-1], issue["comments"][-1]
        # the comment_check contract — the latest post must sit inside [:5]
        assert any("comment number 6" in b for b in issue["comments"][:5]), \
            "newest comment fell outside the latest-5 window — ordering broken"

        # mutations — traversal/malformed keys must die BEFORE any path is built
        for bad in ("../../etc/passwd", "PROJ-1/../../x", "PROJ_1", "PROJ-", "-1", "PROJ-1x"):
            for op in (lambda k: t._file(k),
                       lambda k: t.attach(k, root / "vteam.config.yaml"),
                       lambda k: t.link(k, "PROJ-1")):
                try:
                    op(bad)
                    raise AssertionError(f"key {bad!r} should have exited")
                except SystemExit:
                    pass
        assert not (bl / "attachments").exists(), "a bad key still created a directory"

        # transition + read-back still work after validation
        t.transition("PROJ-1", "in_review")
        assert t.get_issue("PROJ-1")["status_category"] == "in_review"

        # H5: a SCALAR done_statuses (legal in every config parser) means ONE
        # status — never its characters. Before this fixture, `done_statuses:
        # Done` made status_category iterate "D","o","n","e" and the
        # stale-verdict gate went falsely green on every judged ticket.
        (root / "vteam.config.yaml").write_text(
            "version: 1\nproject:\n  key: PROJ\npaths:\n  backlog: docs/backlog\n"
            "tracker:\n  provider: markdown\n  done_statuses: Finished\n",
            encoding="utf-8")
        t2 = MarkdownTracker(Ctx(start=root))
        t2.transition("PROJ-1", "done")
        issue = t2.get_issue("PROJ-1")
        assert issue["status"] == "Finished", \
            f"transition must honor the scalar done status, wrote {issue['status']!r}"
        assert issue["status_category"] == "done", \
            f"scalar done_statuses must categorize as done, got {issue['status_category']!r}"
    print("tracker selftest: OK (markdown comments NEWEST-FIRST incl. >5 window, "
          "read-back, 6 bad keys × 3 ops all red, transition, scalar done_statuses)")


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        _selftest()
    else:
        print(__doc__)
