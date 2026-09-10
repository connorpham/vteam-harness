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
     tasksheet.md), commits BELONGING to that ticket may only touch files under
     the declared paths (plus the always-legal homes: evidence, docs, .vteam,
     .githooks, .github, the config). A commit outside the declared scope is
     the machine-visible form of "the dev self-expanded the task". No
     CODE-SCOPE line → the ticket is SKIPPED LOUDLY, never silently green —
     scope enforcement is opt-in per ticket, silence about it is not.
     "Belonging" is the key LEADING the subject (`TB-5 …`, `feat(TB-5): …`,
     `[TB-5] …`) — see `attributes()`. A subject that merely MENTIONS the key in
     prose is another lane's commit; judging it against this ticket's scope was
     a false derailment red, and a gate that cries wolf gets ignored.

Exit 0 = coherent; 1 = violations listed. Runs in gate.sh (graph step).
Selftest: graph_check.py --selftest  (green fixture + 7 mutations that must red
+ the loud-skip paths + the attribution table and its end-to-end negative).
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


def attributes(subject: str, key: str) -> bool:
    """Does this commit subject BELONG to `key` (vs merely mention it)?

    A commit belongs to a ticket when the key LEADS the subject:
      · bare          `TB-5 fix the thing` / `TB-5: fix the thing`
      · type-prefixed `chore: TB-5 …`
      · conventional  `feat(TB-5): …`, `fix(TB-5)!: …` — and the key may be ANY
                      scope in a multi-scope group: `feat(api,TB-5): …`,
                      `merge(TB-5,TB-9): …`. Missing that shape was a silent
                      FALSE NEGATIVE: the derailment gate simply stopped
                      watching a real, standard commit, which is the more
                      dangerous direction of the two.
      · bracketed     `[TB-5] …`
      · a revert       `Revert "feat(TB-5): …"` / `Reapply "…"` — undoing TB-5's
                      work is TB-5's work, judged against TB-5's scope.

    A subject that mentions the key in PROSE is someone else's work — a PM's
    `chore: drop the leftover found by the TB-5 worker` was attributed to TB-5
    and reded as derailment, because the old test was `\\bTB-5\\b` anywhere in
    the subject. Judging one ticket's scope against another lane's commit is a
    false red, and a false red on a derailment gate teaches agents to ignore it.

    Longer keys are safe by construction: `TB-5` does not lead `TB-50 …`,
    because the trailing boundary cannot fall between two digits. Keys cannot
    carry regex metacharacters either (`tracker.KEY_RE` is
    `[A-Za-z][A-Za-z0-9]*-[0-9]+`), and `re.escape` guards it regardless.

    NOT attributed, deliberately: `Merge branch 'feat/TB-5-x'` and
    `Merge pull request #12 from …/feat/TB-5-x`. A merge commit shows no files
    under `git show --name-only --format=`, so attributing it would change no
    verdict; the integration commit belongs to whoever integrated. Also not
    attributed: `(TB-5) …` with no colon, which is not a conventional-commit
    header in any spelling.
    """
    s = subject.strip()
    # `Revert "<original subject>"` (and git's newer `Reapply "…"`) — judge the
    # revert against the scope of the work it undoes.
    m = re.match(r'^(?:revert|reapply)\s+"(.*)"\s*$', s, re.I)
    if m:
        s = m.group(1).strip()
    k = re.escape(key)
    if re.match(rf"^\[{k}\]", s, re.I):                                # [KEY] …
        return True
    m = re.match(r"^\w+\(([^)]*)\)!?:", s)                             # type(a,KEY)!: …
    if m and any(re.fullmatch(k, part.strip(), re.I) for part in m.group(1).split(",")):
        return True
    # bare `KEY …` / `KEY: …`, optionally behind a `type:` / `type(scope):` prefix
    return re.match(rf"^(?:\w+(?:\([^)]*\))?:\s*)?{k}\b", s, re.I) is not None


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
            # the raw file, so a closure can be checked for the decision it cites
            "text": f.read_text(encoding="utf-8", errors="replace"),
        }
    return out


def read_decisions(c: Ctx) -> dict[str, str]:
    """key → status text, from the decision queue (`Q3`, `D11`, `A2`…).

    Two real states had no way to be written down before this. A ticket can be
    **blocked by a decision** rather than by another ticket (TB-9 waiting on "is high
    contrast a supported target?"), and a ticket can be **closed by a decision instead
    of a verdict** — a won't-fix is an owner's call, and QA never verified it. Both were
    being expressed in prose because `blocked-by` only took a ticket key and any
    terminal status demanded a QA REPORT.md. Prose is invisible to a gate, which is how
    a blocked ticket looks startable and a won't-fix looks like a lane closing outside
    its rights.
    """
    f = c.root / str(c.cfg("paths.pm", "docs/pm")) / "decisions.md"
    if not f.is_file():
        return {}
    out = {}
    for line in f.read_text(encoding="utf-8", errors="replace").splitlines():
        m = re.match(r"^\|\s*([QDA]\d+)\s*\|", line)
        if m:
            out[m.group(1).upper()] = line
    return out


def decision_settled(row: str) -> bool:
    """A decision counts as settled only when it is DECIDED — provisional and open do
    not release anything. `✅ DECIDED` is the vocabulary decisions.md declares."""
    return "DECIDED" in row.upper()


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


def check_graph(tickets: dict[str, dict], evd_dir: Path,
                decisions: dict[str, str] | None = None,
                pm_dir: str = "docs/pm") -> list[str]:
    decisions = decisions or {}
    ticket_text = {k: v.get("text", "") for k, v in tickets.items()}
    blocked_on_decision: list[tuple[str, str]] = []
    errs = []
    edges = {k: v["blocked_by"] for k, v in tickets.items()}
    for k, targets in sorted(edges.items()):
        for t in targets:
            if t in tickets:
                continue
            if t in decisions:
                # a decision edge is legitimate; it releases when the row says DECIDED
                if not decision_settled(decisions[t]):
                    blocked_on_decision.append((k, t))
                continue
            errs.append(f"{k}: blocked-by {t} which is neither a ticket nor a row in the "
                        f"decision queue — a dangling edge blocks {k} forever (fix the key, "
                        f"add the decision, or drop the link)")
    for cyc in find_cycles(edges):
        errs.append("dependency cycle: " + " → ".join(cyc) +
                    " — a cycle is a deadlock; no lane can ever start these")
    for k, v in sorted(tickets.items()):
        if v["status_category"] != "done":
            continue
        report = evd_dir / k / "REPORT.md"
        if not report.is_file():
            # A ticket may be terminal WITHOUT a verdict when an owner decided not to do
            # it. That is not a lane closing outside its rights — it is the one case where
            # there is nothing for QA to verify. It must cite a SETTLED decision, so the
            # closure still rests on a written, dated record rather than on a status change.
            cited = [d for d in decisions
                     if re.search(rf"\b{d}\b", ticket_text.get(k, ""), re.I)]
            settled = [d for d in cited if decision_settled(decisions[d])]
            if settled:
                continue
            if cited:
                errs.append(f"{k}: terminal with no REPORT.md, and the decision(s) it cites "
                            f"({', '.join(cited)}) are not DECIDED yet — a ticket cannot be "
                            f"closed by a question")
                continue
            errs.append(f"{k}: judged done with NO {report.relative_to(evd_dir.parent)} "
                        f"— only QA closes (raci §2), and QA's act IS the verdict "
                        f"(MAST 1.2: a lane closed outside its rights). If it was closed "
                        f"without being built, cite the DECIDED row in {pm_dir}"
                        f"/decisions.md that says so.")
            continue
        h1 = next((ln for ln in report.read_text(encoding="utf-8", errors="replace")
                   .splitlines() if ln.startswith("# ")), "")
        m = VERDICT_PAT.search(h1.upper())
        if not m or m.group(1) != "PASS":
            errs.append(f"{k}: done but the verdict in REPORT.md's H1 is "
                        f"{(m.group(1) if m else 'MISSING')!r}, not PASS — "
                        f"closure does not match the evidence (MAST 1.2)")
    for k, d in sorted(blocked_on_decision):
        print(f"   ⏸  {k} is blocked by decision {d}, which is not DECIDED yet — "
              f"the edge is real, so this is a state, not a fault")
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
                if attributes(ln.split('|', 1)[1], k)]
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
        errs += check_graph(tickets, evd_dir, read_decisions(c),
                            str(c.cfg('paths.pm', 'docs/pm')))
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

    # --- attribution: the key must LEAD the subject (MAST 2.3 precision) ------
    # The rule AC 5 states as seven cases, asserted as seven cases. Cheap here;
    # in the git fixture below each case would cost a commit.
    for subj in ("TB-5 fix the thing",
                 "TB-5: fix the thing",
                 "feat(TB-5): fix the thing",
                 "merge(TB-5): integrate",
                 "fix(TB-5)!: breaking",
                 "[TB-5] fix the thing",
                 "chore: TB-5 housekeeping",
                 "  feat(TB-5): leading whitespace tolerated",
                 "\tTB-5 leading tab tolerated",
                 "tb-5 lowercase is the same ticket",
                 # MULTI-SCOPE conventional commits — a standard shape whose
                 # absence was a silent false negative (the gate stopped
                 # watching), not a false red
                 "feat(api,TB-5): x",
                 "feat(TB-5,api): x",
                 "feat(TB-5, api): x",
                 "fix(TB-5,other)!: message",
                 "merge(TB-5,TB-9): combine",
                 # undoing TB-5's work is judged against TB-5's scope
                 'Revert "feat(TB-5): fix the thing"',
                 'Reapply "feat(TB-5): fix the thing"'):
        assert attributes(subj, "TB-5"), f"must be attributed: {subj!r}"
    for subj in ("chore: drop the leftover found by the TB-5 worker",
                 "docs: explain why TB-5 needed two rounds",
                 "feat(TB-50): a longer key is a different ticket",
                 "TB-50 also a different ticket",
                 "feat(api,TB-50): a longer key in a scope group",
                 "fix(other): unrelated",
                 "fix a bug for TB-5",
                 "TB-9 and TB-5: the leading key owns it",
                 "TB-5fix: no separator is not the key",
                 # a merge commit shows no files, so attribution would change
                 # nothing; the integration belongs to whoever integrated
                 "Merge branch 'feat/TB-5-x'",
                 "Merge pull request #12 from user/feat/TB-5-x",
                 'Revert "chore: mentions TB-5 in prose"'):
        assert not attributes(subj, "TB-5"), f"must NOT be attributed: {subj!r}"
    # the same rule, keyed to the other direction: TB-50's own commits still land
    assert attributes("feat(TB-50): real work", "TB-50")
    assert not attributes("feat(TB-5): real work", "TB-50")
    # a key cannot smuggle regex metacharacters (tracker.KEY_RE forbids them),
    # and re.escape guards it anyway: a literal dot must not match any char
    assert not attributes("feat(TBx5): x", "TB.5")
    # hostile length: prose mention stays unattributed, leading key stays attributed
    assert not attributes("chore: " + "x" * 10000 + " TB-5", "TB-5")
    assert attributes("TB-5 " + "x" * 10000, "TB-5")

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

        # m1: dangling edge — neither a ticket nor a decision
        ticket(root, "PROJ-3", "To Do", blocked_by="GHOST-9")
        r = run_gate(root)
        assert r.returncode == 1 and "neither a ticket nor a row in the decision queue" in r.stdout, r.stdout
        (root / "docs" / "backlog" / "PROJ-3.md").unlink()

        # m1b: an edge onto a DECISION is legitimate, and an unsettled one is a state
        dec = root / "docs" / "pm" / "decisions.md"
        dec.parent.mkdir(parents=True, exist_ok=True)
        dec.write_text("| Q1 | is this supported? | none | 🔴 OPEN | 2026-02-01 |\n"
                       "| Q2 | do we ship it? | none | ✅ DECIDED 2026-01-05 — yes | — |\n",
                       encoding="utf-8")
        ticket(root, "PROJ-7", "To Do", blocked_by="Q1")
        r = run_gate(root)
        assert r.returncode == 0, f"an edge onto an OPEN decision is a state, not a fault:\n{r.stdout}"
        assert "blocked by decision Q1" in r.stdout, r.stdout
        (root / "docs" / "backlog" / "PROJ-7.md").unlink()

        # m1c: terminal with no REPORT.md but citing a DECIDED row — a won't-fix, allowed
        ticket(root, "PROJ-8", "Done")
        t8 = root / "docs" / "backlog" / "PROJ-8.md"
        t8.write_text(t8.read_text(encoding="utf-8") +
                      "\n## Closed won't-fix (decision Q2)\n", encoding="utf-8")
        r = run_gate(root)
        assert r.returncode == 0, f"a won't-fix citing a DECIDED row must pass:\n{r.stdout}"

        # m1d: the same closure citing an UNSETTLED decision must red
        t8.write_text(t8.read_text(encoding="utf-8").replace("Q2", "Q1"), encoding="utf-8")
        r = run_gate(root)
        assert r.returncode == 1 and "cannot be closed by a question" in r.stdout, r.stdout
        t8.unlink()

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
        # AC 5 END-TO-END, as a boundary pair on the SAME out-of-scope directory:
        # a subject that only MENTIONS the key is another lane's commit → GREEN…
        (root / "src" / "billing" / "mentioned.js").write_text("another lane\n")
        subprocess.run(["git", "add", "-A"], cwd=root, check=True, capture_output=True)
        subprocess.run(["git", "commit", "-qm",
                        "chore: drop the leftover found by the PROJ-2 worker"],
                       cwd=root, check=True, capture_output=True, env=env)
        r = run_gate(root)
        assert r.returncode == 0, \
            f"a prose mention is another lane's commit, not derailment:\n{r.stdout}"
        assert "mentioned.js" not in r.stdout, \
            f"the mentioned commit's files must not be judged here:\n{r.stdout}"
        # …and a MULTI-SCOPE conventional subject IS the ticket's own commit, so
        # the same out-of-scope directory must RED under it (a reviewer proved
        # this shape slipped past the gate entirely)
        (root / "src" / "billing" / "multi.js").write_text("multi scope\n")
        subprocess.run(["git", "add", "-A"], cwd=root, check=True, capture_output=True)
        subprocess.run(["git", "commit", "-qm", "fix(PROJ-2,billing)!: sneaky multi-scope"],
                       cwd=root, check=True, capture_output=True, env=env)
        r = run_gate(root)
        assert r.returncode == 1 and "src/billing/multi.js" in r.stdout, \
            f"a multi-scope conventional commit must be judged:\n{r.stdout}"
        # …while the very same directory, under a LEADING key, still reds (m7)
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

    print("graph_check selftest: OK (coherent graph green + 9 reds + 2 new greens: dangling, "
          "cycle, done-sans-verdict, done-with-FAIL, identical repeat, loop "
          "budget, out-of-scope commit — + loud skips: undeclared scope, "
          "remote tracker — + attribution, 17 positive / 12 negative: leading key "
          "attributed (bare/`type:`-prefixed/`feat(KEY):`/multi-scope "
          "`feat(a,KEY):`/`[KEY]`/`Revert \"…\"`), prose mention + longer key + "
          "merge-commit NOT, both directions proven end-to-end on the same "
          "out-of-scope directory)")


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        _selftest()
        sys.exit(0)
    sys.exit(main())
