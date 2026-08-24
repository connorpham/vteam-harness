#!/usr/bin/env python3
"""graph_check.py — the work graph must be coherent (the MAST gate).

Why: the Berkeley MAST taxonomy (arXiv 2503.13657, NeurIPS 2025) catalogued 14
ways multi-agent systems actually fail. Ten of them already have a vteam gate.
This gate closes the four that need GRAPH structure to be checkable at all —
each check below names its MAST mode:

  1. EDGES RESOLVE + ACYCLIC (graph integrity — the precondition for the rest):
     every `blocked-by` target exists; no dependency cycles (a cycle is a
     deadlock the PM lane would orbit forever). Markdown tracker only — with a
     remote tracker the edges live there, and this gate says so LOUDLY instead
     of pretending it checked them.
  2. CLOSURE COHERENCE (MAST 1.2, disobey role specification): a ticket judged
     done must carry a QA verdict — REPORT.md whose H1 holds PASS (word-
     boundary, the same H1-only rule as evd_check/board; '# PASSPORT…' is not
     a PASS). Only QA closes (raci §2), and QA's act IS the verdict — a done
     ticket without one means some lane closed outside its rights.
  3. STEP REPETITION (MAST 1.3): two ledger rows with the identical
     (lane, actor, item, result) are the machine-visible form of an agent
     re-doing a phase and re-claiming the same outcome — the exact failure the
     taxonomy documents. Legitimate re-dispatch changes SOMETHING (the result
     text, the date's work, the lane); byte-identical repetition is a loop.
  4. LOOP BUDGET AS DATA (MAST 1.5, unaware of termination conditions): more
     than `team.loop_budget_per_day` (config; default 4) dispatches of the same
     item on one date is thrash, not persistence. The budget is a NUMBER in
     config — a termination condition prose cannot silently ignore.
  5. SCOPE DERAILMENT (MAST 2.3, task derailment): if a ticket's tasksheet
     declares `CODE-SCOPE: <path> <path>…` ({paths.evidence}/<KEY>/dev/
     tasksheet.md), commits naming that ticket may only touch files under the
     declared paths (plus the always-legal homes: evidence, docs, .vteam,
     .githooks, .github, the config). A commit outside the declared scope is
     the machine-visible form of "the dev self-expanded the task". No
     CODE-SCOPE line → the ticket is SKIPPED LOUDLY, never silently green —
     scope enforcement is opt-in per ticket, silence about it is not.

Exit 0 = coherent; 1 = violations listed. Runs in gate.sh (graph step).
Selftest: graph_check.py --selftest  (green fixture + 7 mutations that must red
+ the loud-skip paths).
"""
from __future__ import annotations

import re
import subprocess
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "lib"))
import ledger  # noqa: E402 — the canonical ledger row grammar
from ctx import Ctx  # noqa: E402
from tracker import KEY_RE  # noqa: E402 — the one ticket-key grammar

# MUST match evd_check.py VERDICT_PAT / board.mjs parseReport: H1 only,
# word-boundary (audit L1 — '# PASSPORT verification' is NOT a PASS).
VERDICT_PAT = re.compile(r"\b(PASS|FAIL|PARTIAL|NEW-BUG|BLOCKED|UNCLEAR)\b")
SCOPE_PAT = re.compile(r"^CODE-SCOPE:\s*(.+)$", re.M)
# paths every ticket may always touch — process artifacts, never product code
ALWAYS_LEGAL = ("docs/", "evd/", ".vteam/", ".githooks/", ".github/",
                "vteam.config.yaml", ".gitattributes", ".gitignore")


def read_backlog(c: Ctx) -> dict[str, dict]:
    """key → {status_category, blocked_by} from the markdown backlog."""
    backlog = c.root / str(c.cfg("paths.backlog", "docs/backlog"))
    if not backlog.is_dir():
        return {}
    import tracker as trk
    t = trk.load(c)
    out = {}
    for f in sorted(backlog.glob("*.md")):
        if not KEY_RE.fullmatch(f.stem):
            continue
        issue = t.get_issue(f.stem)
        out[f.stem.upper()] = {
            "status_category": issue["status_category"],
            "blocked_by": [k.upper() for k in issue["links"]["blocked_by"]],
        }
    return out


def find_cycles(edges: dict[str, list[str]]) -> list[list[str]]:
    """Every distinct blocked-by cycle, as a path [A, B, …, A]."""
    cycles, state = [], {}  # 0 visiting, 1 done
    def dfs(node, stack):
        state[node] = 0
        stack.append(node)
        for nxt in edges.get(node, []):
            if nxt not in edges:
                continue
            if state.get(nxt) == 0:
                cycles.append(stack[stack.index(nxt):] + [nxt])
            elif nxt not in state:
                dfs(nxt, stack)
        stack.pop()
        state[node] = 1
    for n in sorted(edges):
        if n not in state:
            dfs(n, [])
    return cycles


def check_graph(tickets: dict[str, dict], evd_dir: Path) -> list[str]:
    errs = []
    edges = {k: v["blocked_by"] for k, v in tickets.items()}
    for k, targets in sorted(edges.items()):
        for t in targets:
            if t not in tickets:
                errs.append(f"{k}: blocked-by {t} which does not exist — a dangling "
                            f"edge blocks {k} forever (fix the key or drop the link)")
    for cyc in find_cycles(edges):
        errs.append("dependency cycle: " + " → ".join(cyc) +
                    " — a cycle is a deadlock; no lane can ever start these")
    for k, v in sorted(tickets.items()):
        if v["status_category"] != "done":
            continue
        report = evd_dir / k / "REPORT.md"
        if not report.is_file():
            errs.append(f"{k}: judged done with NO {report.relative_to(evd_dir.parent)} "
                        f"— only QA closes (raci §2), and QA's act IS the verdict "
                        f"(MAST 1.2: a lane closed outside its rights)")
            continue
        h1 = next((ln for ln in report.read_text(encoding="utf-8", errors="replace")
                   .splitlines() if ln.startswith("# ")), "")
        m = VERDICT_PAT.search(h1.upper())
        if not m or m.group(1) != "PASS":
            errs.append(f"{k}: done but the verdict in REPORT.md's H1 is "
                        f"{(m.group(1) if m else 'MISSING')!r}, not PASS — "
                        f"closure does not match the evidence (MAST 1.2)")
    return errs


def check_ledger(text: str, budget: int) -> list[str]:
    errs, seen, per_day = [], Counter(), Counter()
    shape = None
    for n, line in enumerate(text.splitlines(), 1):
        hs = ledger.header_shape(line)
        if hs is not None:
            shape = hs
            continue
        if shape is None:
            continue
        row = ledger.parse_row(line)
        if row is None or row.get("malformed"):
            continue  # log_check owns row hygiene; this gate reads shape only
        ident = (row["lane"], row["actor"] or "", row["item"], row["result"])
        seen[ident] += 1
        if seen[ident] == 2:
            errs.append(f"line {n}: identical dispatch repeated — "
                        f"{row['lane']} · {row['item']} · {row['result'][:40]!r} "
                        f"(MAST 1.3: re-doing a phase and re-claiming the same "
                        f"outcome is a loop, not progress)")
        per_day[(row["date"], row["item"])] += 1
        if per_day[(row["date"], row["item"])] == budget + 1:
            errs.append(f"line {n}: {row['item']} dispatched >{budget}× on "
                        f"{row['date']} — over team.loop_budget_per_day "
                        f"(MAST 1.5: a termination condition is a number in "
                        f"config, not a sentence agents can talk past)")
    return errs


def check_scope(c: Ctx, tickets: list[str], evd_dir: Path) -> tuple[list, list]:
    errs, notes = [], []
    for k in tickets:
        sheet = evd_dir / k / "dev" / "tasksheet.md"
        if not sheet.is_file():
            continue
        m = SCOPE_PAT.search(sheet.read_text(encoding="utf-8", errors="replace"))
        if not m:
            notes.append(f"{k}: tasksheet has no CODE-SCOPE line — derailment "
                         f"unguarded for this ticket (declare it to arm MAST 2.3)")
            continue
        scope = tuple(p.strip().rstrip("/") + ("/" if p.strip().endswith("/") else "")
                      for p in re.split(r"[,\s]+", m.group(1)) if p.strip())
        log = subprocess.run(
            ["git", "-C", str(c.root), "log", "--format=%H|%s", "-200"],
            capture_output=True, text=True).stdout
        shas = [ln.split("|", 1)[0] for ln in log.splitlines()
                if re.search(rf"\b{re.escape(k)}\b", ln.split('|', 1)[1], re.I)]
        for sha in shas:
            files = subprocess.run(
                ["git", "-C", str(c.root), "show", "--name-only", "--format=", sha],
                capture_output=True, text=True).stdout.split()
            out = [f for f in files
                   if not f.startswith(ALWAYS_LEGAL)
                   and not any(f == s.rstrip("/") or f.startswith(s if s.endswith("/") else s + "/")
                               for s in scope)]
            if out:
                errs.append(f"{k}: commit {sha[:8]} touches outside the declared "
                            f"CODE-SCOPE ({', '.join(scope)}): {', '.join(sorted(out)[:5])}"
                            f" (MAST 2.3: the task self-expanded — widen the "
                            f"declared scope in the tasksheet, deliberately, or "
                            f"split the ticket)")
    return errs, notes


def main() -> int:
    c = Ctx()
    provider = str(c.cfg("tracker.provider", "markdown"))
    raw_budget = c.cfg("team.loop_budget_per_day", 4)
    try:
        budget = int(raw_budget)
    except (TypeError, ValueError):
        sys.exit(f"graph_check: team.loop_budget_per_day {raw_budget!r} is not an integer")
    if budget <= 0:
        sys.exit(f"graph_check: team.loop_budget_per_day must be > 0 (got {budget})")

    errs, notes = [], []
    evd_dir = c.path("evidence")

    if provider == "markdown":
        tickets = read_backlog(c)
        errs += check_graph(tickets, evd_dir)
        keys = sorted(tickets)
    else:
        notes.append(f"tracker={provider}: blocked-by edges and statuses live in "
                     f"the tracker — edge/closure checks NOT run here (loud skip, "
                     f"never a silent green)")
        keys = sorted(d.name for d in evd_dir.iterdir()
                      if d.is_dir() and KEY_RE.fullmatch(d.name)) if evd_dir.is_dir() else []

    log = c.path("pm") / "log.md"
    if log.is_file():
        errs += check_ledger(log.read_text(encoding="utf-8"), budget)

    scope_errs, scope_notes = check_scope(c, keys, evd_dir)
    errs += scope_errs
    notes += scope_notes

    for w in notes:
        print(f"⚠️  {w}")
    if errs:
        print(f"❌ graph_check: {len(errs)} coherence violations")
        for e in errs:
            print(f"   - {e}")
        return 1
    print(f"✅ graph_check: work graph coherent ({len(keys)} tickets, "
          f"loop budget {budget}/day, scope armed where declared)")
    return 0


def _selftest():
    import os
    import tempfile

    self_path = Path(__file__).resolve()

    def sh(cwd, *args):
        r = subprocess.run(list(args), cwd=cwd, capture_output=True, text=True)
        assert r.returncode == 0, f"{args}: {r.stderr}"
        return r.stdout.strip()

    def run_gate(cwd):
        return subprocess.run([sys.executable, str(self_path)],
                              cwd=cwd, capture_output=True, text=True)

    def mk(td, *, budget=4):
        root = Path(td)
        sh(root, "git", "init", "-q", ".")
        sh(root, "git", "config", "user.email", "t@t.t")
        sh(root, "git", "config", "user.name", "t")
        (root / "vteam.config.yaml").write_text(
            "version: 1\nproject:\n  key: PROJ\n  adopted: 2026-01-01\n"
            "paths:\n  pm: docs/pm\n  evidence: evd\n  backlog: docs/backlog\n"
            f"team:\n  loop_budget_per_day: {budget}\n"
            "tracker:\n  provider: markdown\n  done_statuses: [Done]\n"
            "  review_status: \"In Review\"\n", encoding="utf-8")
        (root / "docs" / "backlog").mkdir(parents=True)
        (root / "docs" / "pm").mkdir(parents=True)
        return root

    def ticket(root, key, status, blocked_by=""):
        extra = f"- blocked-by: {blocked_by}\n" if blocked_by else ""
        (root / "docs" / "backlog" / f"{key}.md").write_text(
            f"# {key}: t\n- status: {status}\n{extra}\nbody\n", encoding="utf-8")

    def report(root, key, verdict="PASS"):
        d = root / "evd" / key
        d.mkdir(parents=True, exist_ok=True)
        (d / "REPORT.md").write_text(
            f"# Verification report {key} — {verdict}\nCOMMIT: deadbeef\n"
            f"VERIFIED-AT: 2026-01-02T10:00:00+00:00\n", encoding="utf-8")

    LEDGER_HEAD = ("| Date | Lane | Actor | Item | Result | Link |\n"
                   "|---|---|---|---|---|---|\n")

    with tempfile.TemporaryDirectory() as td:
        root = mk(td)
        ticket(root, "PROJ-1", "Done")
        report(root, "PROJ-1", "PASS")
        ticket(root, "PROJ-2", "To Do", blocked_by="PROJ-1")
        (root / "docs" / "pm" / "log.md").write_text(
            LEDGER_HEAD +
            "| 2026-01-02 | DEV | An | PROJ-1 | done (workhorse) · tok ≈ 9k | PR #1 |\n"
            "| 2026-01-03 | QA | An | PROJ-1 | done · tok ≈ 2k | PROJ-1 |\n",
            encoding="utf-8")
        r = run_gate(root)
        assert r.returncode == 0, f"clean graph should pass:\n{r.stdout}{r.stderr}"

        # m1: dangling edge
        ticket(root, "PROJ-3", "To Do", blocked_by="GHOST-9")
        r = run_gate(root)
        assert r.returncode == 1 and "does not exist" in r.stdout, r.stdout
        (root / "docs" / "backlog" / "PROJ-3.md").unlink()

        # m2: cycle
        ticket(root, "PROJ-4", "To Do", blocked_by="PROJ-5")
        ticket(root, "PROJ-5", "To Do", blocked_by="PROJ-4")
        r = run_gate(root)
        assert r.returncode == 1 and "cycle" in r.stdout, r.stdout
        (root / "docs" / "backlog" / "PROJ-4.md").unlink()
        (root / "docs" / "backlog" / "PROJ-5.md").unlink()

        # m3: done without a verdict (MAST 1.2)
        ticket(root, "PROJ-6", "Done")
        r = run_gate(root)
        assert r.returncode == 1 and "MAST 1.2" in r.stdout, r.stdout
        # …and a FAIL verdict on a done ticket is also a closure mismatch
        report(root, "PROJ-6", "FAIL")
        r = run_gate(root)
        assert r.returncode == 1 and "not PASS" in r.stdout, r.stdout
        report(root, "PROJ-6", "PASS")
        r = run_gate(root)
        assert r.returncode == 0, f"PASS verdict should clear it:\n{r.stdout}"

        # m4: identical repeated dispatch (MAST 1.3)
        log = root / "docs" / "pm" / "log.md"
        base = log.read_text(encoding="utf-8")
        log.write_text(base +
            "| 2026-01-04 | DEV | An | PROJ-2 | blocked: Q1 open | PROJ-2 |\n"
            "| 2026-01-04 | DEV | An | PROJ-2 | blocked: Q1 open | PROJ-2 |\n",
            encoding="utf-8")
        r = run_gate(root)
        assert r.returncode == 1 and "MAST 1.3" in r.stdout, r.stdout

        # m5: loop budget (MAST 1.5) — 5 distinct dispatches, one day, budget 4
        rows = "".join(f"| 2026-01-05 | DEV | An | PROJ-2 | blocked: Q{i} open | PROJ-2 |\n"
                       for i in range(1, 6))
        log.write_text(base + rows, encoding="utf-8")
        r = run_gate(root)
        assert r.returncode == 1 and "MAST 1.5" in r.stdout \
            and "loop_budget_per_day" in r.stdout, r.stdout
        log.write_text(base, encoding="utf-8")

        # m6/m7: scope derailment (MAST 2.3) — armed by CODE-SCOPE in the tasksheet
        (root / "src" / "auth").mkdir(parents=True)
        (root / "src" / "billing").mkdir(parents=True)
        sheet = root / "evd" / "PROJ-2" / "dev"
        sheet.mkdir(parents=True)
        (sheet / "tasksheet.md").write_text(
            "# tasksheet PROJ-2\nCODE-SCOPE: src/auth/\n", encoding="utf-8")
        (root / "src" / "auth" / "a.js").write_text("in scope\n")
        env = {**os.environ, "GIT_AUTHOR_DATE": "2026-01-06T10:00:00+00:00",
               "GIT_COMMITTER_DATE": "2026-01-06T10:00:00+00:00"}
        subprocess.run(["git", "add", "-A"], cwd=root, check=True, capture_output=True)
        subprocess.run(["git", "commit", "-qm", "PROJ-2 auth work"],
                       cwd=root, check=True, capture_output=True, env=env)
        r = run_gate(root)
        assert r.returncode == 0, f"in-scope commit must stay green:\n{r.stdout}"
        (root / "src" / "billing" / "b.js").write_text("out of scope\n")
        subprocess.run(["git", "add", "-A"], cwd=root, check=True, capture_output=True)
        subprocess.run(["git", "commit", "-qm", "PROJ-2 sneaky billing change"],
                       cwd=root, check=True, capture_output=True, env=env)
        r = run_gate(root)
        assert r.returncode == 1 and "MAST 2.3" in r.stdout \
            and "src/billing/b.js" in r.stdout, r.stdout
        # undeclared scope is a LOUD note, never silent: drop the scope line
        (sheet / "tasksheet.md").write_text("# tasksheet PROJ-2\n", encoding="utf-8")
        subprocess.run(["git", "commit", "-aqm", "PROJ-2 drop scope"],
                       cwd=root, check=True, capture_output=True, env=env)
        r = run_gate(root)
        assert r.returncode == 0 and "derailment unguarded" in r.stdout, r.stdout

    # non-markdown tracker: edge/closure checks skip LOUDLY, ledger checks still run
    with tempfile.TemporaryDirectory() as td:
        root = mk(td)
        (root / "vteam.config.yaml").write_text(
            (root / "vteam.config.yaml").read_text().replace(
                "provider: markdown", "provider: jira"), encoding="utf-8")
        (root / "docs" / "pm" / "log.md").write_text(
            LEDGER_HEAD +
            "| 2026-01-02 | DEV | An | PROJ-1 | done · tok ≈ 9k | PR #1 |\n"
            "| 2026-01-02 | DEV | An | PROJ-1 | done · tok ≈ 9k | PR #1 |\n",
            encoding="utf-8")
        r = run_gate(root)
        assert "edge/closure checks NOT run" in r.stdout, r.stdout
        assert r.returncode == 1 and "MAST 1.3" in r.stdout, \
            f"ledger checks must run even with a remote tracker:\n{r.stdout}"

    print("graph_check selftest: OK (coherent graph green + 7 reds: dangling, "
          "cycle, done-sans-verdict, done-with-FAIL, identical repeat, loop "
          "budget, out-of-scope commit — + loud skips: undeclared scope, "
          "remote tracker)")


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        _selftest()
        sys.exit(0)
    sys.exit(main())
