#!/usr/bin/env python3
"""stale_verdict_check.py — catch tickets judged done whose code changed AFTER judgment.

Principle: **a verdict is valid only for the code it examined.** Code changed
afterward → the verdict expired and the ticket returns to the verify queue — not
to blame anyone, but because what's running has never been examined. (Provenance:
a ticket sat in Done while its whole UI was rebuilt; nothing noticed until the
owner asked "did anyone re-test this?".)

Anchor preference:
  1. The COMMIT sha pinned in {paths.evidence}/<T>/REPORT.md — precise, and the
     only anchor that also covers pre-merge verdicts (time-based anchors get
     "washed" by post-verdict pre-merge commits).
  2. Fallback: the tracker's changelog (last move into a judged status) — only
     for providers that keep one; the markdown provider doesn't, and this gate
     says so instead of guessing.

"Code changed after" = commits touching the configured code paths, mentioning
<TICKET> in the subject, later than the anchor.

Usage:
  stale_verdict_check.py                 # scan every evidence dir with the project key
  stale_verdict_check.py PROJ-21         # one ticket
  stale_verdict_check.py --fix           # return hits to In Review + explanatory comment
Exit 0 = no stale verdicts; 1 = stale found (and not --fix).

Selftest: --selftest (temp repo: verdict-then-untouched green, verdict-then-code-
changed red, --fix returns the ticket to In Review).
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "lib"))
from ctx import Ctx  # noqa: E402
import tracker as trk  # noqa: E402


def git(root: Path, *args: str) -> str:
    return subprocess.run(["git", "-C", str(root), *args],
                          capture_output=True, text=True).stdout.strip()


def code_paths(c: Ctx) -> list[str]:
    return [str(p).rstrip("/") for p in c.cfg("git.code_paths", ["src/", "prisma/"])]


def pinned_commit(c: Ctx, ticket: str) -> str | None:
    p = c.path("evidence") / ticket / "REPORT.md"
    if not p.is_file():
        return None
    m = re.search(r"COMMIT\s*[:：]\s*([0-9a-f]{7,40})\b",
                  p.read_text(encoding="utf-8", errors="replace"), re.I)
    return m.group(1) if m else None


def hits_from_log(out: str, ticket: str, min_iso: str = "") -> list[str]:
    hits = []
    for line in out.split("\n"):
        if not line.strip():
            continue
        h, iso, subject = line.split("|", 2)
        if min_iso and iso <= min_iso:
            continue
        if re.search(rf"\b{re.escape(ticket)}\b", subject, re.IGNORECASE):
            hits.append(f"{h[:7]} {iso[:16].replace('T', ' ')}  {subject}")
    return hits


def changes_after_sha(c: Ctx, ticket: str, sha: str) -> list[str] | None:
    if subprocess.run(["git", "-C", str(c.root), "cat-file", "-e", f"{sha}^{{commit}}"],
                      capture_output=True).returncode != 0:
        return None
    out = git(c.root, "log", f"{sha}..HEAD", "--format=%H|%cI|%s", "--", *code_paths(c))
    return hits_from_log(out, ticket)


def changes_after_time(c: Ctx, ticket: str, since_iso: str) -> list[str]:
    out = git(c.root, "log", f"--since={since_iso}", "--format=%H|%cI|%s", "--", *code_paths(c))
    return hits_from_log(out, ticket, since_iso)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("ticket", nargs="?")
    ap.add_argument("--fix", action="store_true")
    args = ap.parse_args()

    c = Ctx()
    t = trk.load(c)
    key = str(c.cfg("project.key"))
    evd = c.path("evidence")
    tickets = [args.ticket.upper()] if args.ticket else sorted(
        d.name for d in evd.iterdir()
        if d.is_dir() and re.match(rf"^{re.escape(key)}-\d+$", d.name)
    ) if evd.is_dir() else []
    if not tickets:
        print(f"no evidence dirs with key {key}- under {evd}")
        return 0

    stale: list[tuple[str, str, list[str]]] = []
    for tk in tickets:
        issue = t.get_issue(tk)
        sha = pinned_commit(c, tk)
        if sha:
            after = changes_after_sha(c, tk, sha)
            if after is None:
                print(f"⚠️  {tk}: REPORT.md pins commit {sha[:12]} but the local repo "
                      f"lacks it (missing fetch?) — refusing to conclude clean, check by hand")
                continue
            if after:
                stale.append((tk, f"{issue['status']} · REPORT pins {sha[:7]}", after))
            continue
        if issue["status_category"] != "done":
            continue  # no pinned sha and never judged — nothing to be stale
        anchor = t.judged_at(tk)
        if anchor is None:
            print(f"⚠️  {tk}: judged done but no pinned COMMIT and this tracker keeps "
                  f"no changelog — cannot date the verdict; pin COMMIT in REPORT.md")
            continue
        iso, desc = anchor
        after = changes_after_time(c, tk, iso)
        if after:
            stale.append((tk, f"{issue['status']} · {desc} at {iso[:16].replace('T', ' ')}", after))

    if not stale:
        print(f"✅ no stale verdicts — examined {len(tickets)} evidenced tickets")
        return 0

    print(f"⚠️  {len(stale)} tickets were judged, then the CODE CHANGED\n")
    for tk, ctx_s, commits in stale:
        print(f"  {tk}  ({ctx_s})")
        for cm in commits:
            print(f"      ↳ {cm}")
        print()

    if not args.fix:
        print("A verdict is valid only for the code it examined.")
        print("Re-run with --fix to return them to In Review, or handle by hand with a reason.")
        return 1

    for tk, _, commits in stale:
        t.transition(tk, "in_review")
        body = ("*Auto-reopened — the verdict is older than the code*\n\n"
                "This ticket was judged, but code mentioning it changed afterward:\n\n"
                + "\n".join(f"- {cm}" for cm in commits)
                + "\n\nA verdict is valid only for the code it examined. The running "
                "version has never been examined, so the ticket returns to the verify queue.\n\n"
                "_Detected by stale_verdict_check._")
        if t.comment(tk, body) is None:
            print(f"  {tk} → In Review, but the comment read-back FAILED — post it by hand")
        else:
            print(f"  {tk} → In Review, commented")
    return 0


def _selftest():
    """Mutation proof in a throwaway repo: a pinned verdict with no later code
    is green; a commit touching code_paths and naming the ticket AFTER the pin
    is red; --fix returns the ticket to In Review through the tracker."""
    import os
    import tempfile

    self_path = Path(__file__).resolve()

    def sh(cwd: Path, *args: str) -> str:
        r = subprocess.run(list(args), cwd=cwd, capture_output=True, text=True)
        assert r.returncode == 0, f"{args}: {r.stderr}"
        return r.stdout.strip()

    def run_gate(cwd: Path, *args: str) -> subprocess.CompletedProcess:
        return subprocess.run([sys.executable, str(self_path), *args],
                              cwd=cwd, capture_output=True, text=True)

    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        sh(root, "git", "init", "-q", ".")
        sh(root, "git", "config", "user.email", "t@t.t")
        sh(root, "git", "config", "user.name", "t")
        (root / "vteam.config.yaml").write_text(
            "version: 1\nproject:\n  key: PROJ\n"
            "paths:\n  evidence: evd\n  backlog: docs/backlog\n"
            "git:\n  code_paths: [src/]\n"
            "tracker:\n  provider: markdown\n  done_statuses: [Done]\n"
            "  review_status: \"In Review\"\n", encoding="utf-8")
        (root / "docs" / "backlog").mkdir(parents=True)
        (root / "docs" / "backlog" / "PROJ-1.md").write_text(
            "# PROJ-1: demo\n- status: Done\n\nbody\n", encoding="utf-8")
        (root / "src").mkdir()
        (root / "src" / "a.txt").write_text("v1\n", encoding="utf-8")
        sh(root, "git", "add", "-A")
        sh(root, "git", "commit", "-qm", "PROJ-1 implement")
        sha = sh(root, "git", "rev-parse", "HEAD")
        (root / "evd" / "PROJ-1").mkdir(parents=True)
        (root / "evd" / "PROJ-1" / "REPORT.md").write_text(
            f"VERDICT: PASS\nCOMMIT: {sha}\n", encoding="utf-8")

        env = {**os.environ}
        # green: nothing changed after the pinned commit
        r = run_gate(root)
        assert r.returncode == 0, f"untouched verdict should pass:\n{r.stdout}{r.stderr}"

        # mutation: code naming the ticket lands AFTER the verdict → must RED
        (root / "src" / "a.txt").write_text("v2\n", encoding="utf-8")
        sh(root, "git", "add", "-A")
        sh(root, "git", "commit", "-qm", "PROJ-1 rework the flow")
        r = run_gate(root)
        assert r.returncode == 1, f"post-verdict code change should RED:\n{r.stdout}{r.stderr}"
        assert "PROJ-1" in r.stdout

        # mutation: a post-verdict commit OUTSIDE code_paths must stay green
        (root / "README.md").write_text("docs only\n", encoding="utf-8")
        sh(root, "git", "add", "README.md")
        sh(root, "git", "commit", "-qm", "PROJ-1 docs touch-up")
        # (still red from src change — but prove the docs commit alone wouldn't flag:
        #  the red listing must NOT include the docs-only commit)
        r = run_gate(root)
        assert "docs touch-up" not in r.stdout, "commit outside code_paths was flagged"

        # --fix: ticket returns to In Review with a read-back-verified comment
        r = run_gate(root, "--fix")
        assert r.returncode == 0, f"--fix should exit 0:\n{r.stdout}{r.stderr}"
        ticket = (root / "docs" / "backlog" / "PROJ-1.md").read_text(encoding="utf-8")
        assert "- status: In Review" in ticket, ticket
        assert "Auto-reopened" in ticket, "explanatory comment missing from ticket"
        _ = env
    print("stale_verdict_check selftest: OK (pinned verdict green + post-verdict "
          "code change red + out-of-code-paths ignored + --fix reopens via tracker)")


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        _selftest()
        sys.exit(0)
    sys.exit(main())
