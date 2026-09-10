#!/usr/bin/env python3
"""log_check.py — the ledger must not contain fabricated reports.

Why: the PM workflow declares the ledger's Result column "machine-countable", and
a rule no machine counts gets eroded (measured in the source project: rows outside
the value set, token accounting on 7/20 rows). This gate makes it red-able.

Checks, for every data row of the table in {paths.pm}/log.md:
  1. Column count matches the table's own header — legacy
     `| Date | Lane | Item | Result | Link |` (5) or v2 with an Actor column
     (6). With `team.size > 1` the Actor column is MANDATORY (the v2 header +
     a non-empty Actor cell on every row) — this is the machine consumer the
     config knob was missing: per-person accountability is a gate, not prose.
     Date is ISO YYYY-MM-DD (a range "2026-08-07/08" allowed).
  2. Result starts with: done | blocked: | failed:   (the 3 canonical values —
     the grammar lives in lib/ledger.py, the ONE home shared with perf_report
     and mirrored by board.mjs; audit H4).
  3. Link column non-empty — "done" pointing at no live evidence is fabrication.
     Rows dated ≥ project.adopted: the link must be RECOGNIZABLE
     (PR #n / <KEY>-nn / URL / repo path); a repo path missing on disk warns only
     (later legitimate cleanup must not redden history).
  4. Rows ≥ project.adopted: a `done` result must carry `tok ≈ N` or `tok ≈ Nk`
     token accounting (one space each side of ≈ — lib/ledger.py's space rule).
     Older rows: warn, don't block (grandfathered history).
  5. Dates must be non-decreasing top-to-bottom — the ledger is APPEND-AT-END
     (prepended rows are merge-conflict seeds between sessions).

Exit 0 = clean; 1 = the violating rows. Runs inside gate.sh (ledger step).
Selftest: log_check.py --selftest  (green fixture + 8 mutations that must red).
"""
from __future__ import annotations

import re
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "lib"))
import ledger  # noqa: E402 — the canonical row grammar (one rule, one home)
from ctx import Ctx  # noqa: E402

DATE_PAT = re.compile(r"^(\d{4})-(\d{2})-(\d{2})(?:/\d{2})?$")


def decision_keys(root: Path | None, pm_dir: str = "docs/pm") -> set[str]:
    """The Q/D/A row keys the decision queue actually holds.

    A row can cite a decision to justify itself — "blocked: Q5 unanswered", "→ D13".
    Nothing checked that the cited row exists, and the failure is silent in the worst
    way: on 2026-09-10 a script writing a new D-row raised on a percent sign, the row
    was never written, and the commit plus the ledger entry both pointed at it anyway.
    The ledger looked complete and cited nothing.
    """
    if root is None:
        return set()
    f = root / pm_dir / "decisions.md"
    if not f.is_file():
        return set()
    return {m.group(1).upper() for m in
            re.finditer(r"^\|\s*([QDA]\d+)\s*\|", f.read_text(encoding="utf-8", errors="replace"), re.M)}


def check_text(text: str, key: str, adopted: date, root: Path | None,
               team_size: int = 1) -> tuple[list, list]:
    errs, warns = [], []
    known_decisions = decision_keys(root)
    shape, prev_date = None, None
    # project.key is config-supplied text, not a regex — escape it (audit M15;
    # review_check and stale_verdict_check already do)
    link_pat = re.compile(rf"PR #\d+|{re.escape(key)}-\d+|https?://|[\w./-]+/[\w./-]+")
    for n, line in enumerate(text.splitlines(), 1):
        hs = ledger.header_shape(line)
        if hs is not None:
            shape = hs
            if team_size > 1 and shape == 5:
                errs.append(f"line {n}: team.size > 1 but the ledger header has no "
                            f"Actor column — per-person accountability needs "
                            f"`| Date | Lane | Actor | Item | Result | Link |`")
            continue
        if shape is None:
            continue
        row = ledger.parse_row(line)
        if row is None:
            continue
        if row.get("malformed"):
            errs.append(f"line {n}: {row['columns']} columns (need {shape})")
            continue
        cols = 6 if row["actor"] is not None else 5
        if cols != shape:
            errs.append(f"line {n}: {cols} columns under a {shape}-column header — "
                        f"every row matches the table's own header")
            continue
        if shape == 6 and not row["actor"]:
            errs.append(f"line {n}: empty Actor cell — the row's human is not "
                        f"optional (VTEAM_ACTOR env or `git config user.name`)")
        day, result, link = row["date"], row["result"], row["link"]
        m = DATE_PAT.match(day)
        if not m:
            errs.append(f"line {n}: date {day!r} not YYYY-MM-DD")
            continue
        d = date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
        if prev_date and d < prev_date:
            errs.append(f"line {n}: date {day} earlier than previous row "
                        f"({prev_date.isoformat()}) — the ledger is append-AT-END")
        prev_date = max(prev_date, d) if prev_date else d
        if row["kind"] == "other":
            errs.append(f"line {n}: result must start with 'done' | 'blocked: …' | "
                        f"'failed: …' — saw {result[:40]!r}")
        if not link:
            errs.append(f"line {n}: empty Link column — a result pointing at no "
                        f"evidence is a fabricated report")
        elif d >= adopted:
            if not link_pat.search(link):
                errs.append(f"line {n}: link {link!r} is not recognizable evidence "
                            f"(need PR #n / {key}-nn / URL / repo path)")
            elif root is not None:
                for path in re.findall(r"\b((?:docs|evd|src|prisma|\.vteam)/[\w./-]+)", link):
                    if not (root / path).exists():
                        warns.append(f"line {n}: path {path} no longer exists — "
                                     f"verify, or accept if deliberate cleanup")
            blob = " ".join(str(row.get(f) or "") for f in ("item", "result", "link"))
            cited = {m.group(1).upper() for m in re.finditer(r"\b([QDA]\d+)\b", blob)}
            unknown = sorted(c for c in cited if c not in known_decisions)
            if unknown and known_decisions:
                # A row about ANOTHER project legitimately cites that project's queue: this
                # repo's ledger records field-trial work whose decisions live in the trial
                # repo. The tell is in the row itself — it names a ticket key that is not
                # this project's. Flagged as a warning there, because the citation cannot be
                # resolved from here and silence would be worse than a soft note.
                # ANY foreign key, not the first key found: a row's Item almost always
                # starts with this project's own key, so `search` would never see the
                # other project mentioned later in the same row.
                keys = {m.group(1).upper() for m in re.finditer(r"\b([A-Z][A-Z0-9]{1,9})-\d+\b", blob)}
                foreign_keys = sorted(keys - {key.upper()})
                foreign_key = bool(foreign_keys)
                msg = (f"line {n}: cites {', '.join(unknown)}, which this repo's decision queue "
                       f"does not hold")
                if foreign_key:
                    warns.append(msg + f" — the row also names {', '.join(foreign_keys)}, so the "
                                       f"decision probably lives in that project's queue; "
                                       f"unresolvable from here")
                else:
                    errs.append(msg + " — a row justified by a decision that was never written "
                                      "is a row justified by nothing")
        if row["kind"] == "done" and row["tok_k"] is None:
            if d >= adopted:
                errs.append(f"line {n}: missing or malformed `tok ≈ N[k]` — token "
                            f"accounting is mandatory from {adopted.isoformat()} "
                            f"(one space each side of ≈)")
            else:
                warns.append(f"line {n} ({day}): missing `tok ≈` (grandfathered)")
    return errs, warns


def main() -> int:
    c = Ctx()
    log = c.path("pm") / "log.md"
    if not log.is_file():
        print(f"❌ log_check: {log} not found")
        return 1
    adopted = _parse_date(str(c.cfg("project.adopted")))
    raw_size = c.cfg("team.size", 1)
    try:
        team_size = int(raw_size)
    except (TypeError, ValueError):
        sys.exit(f"log_check: team.size {raw_size!r} is not an integer")
    errs, warns = check_text(log.read_text(encoding="utf-8"),
                             str(c.cfg("project.key")), adopted, c.root, team_size)
    for w in warns:
        print(f"⚠️  {w}")
    if errs:
        print(f"❌ log_check: {len(errs)} ledger rows failed")
        for e in errs:
            print(f"   - {e}")
        return 1
    print("✅ log_check: ledger well-formed, every row carries evidence")
    return 0


def _parse_date(s: str) -> date:
    m = re.match(r"^(\d{4})-(\d{2})-(\d{2})$", s)
    if not m:
        sys.exit(f"log_check: project.adopted {s!r} is not YYYY-MM-DD")
    return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))


def _selftest():
    head = "| Date | Lane | Item | Result | Link |\n|---|---|---|---|---|\n"
    good = head + ("| 2026-01-02 | DEV | PROJ-1 | done (workhorse) · tok ≈ 90k | PR #1 |\n"
                   "| 2026-01-03 | QA | PROJ-1 | blocked: Q2 open | PROJ-1 |\n")
    adopted = date(2026, 1, 1)
    errs, _ = check_text(good, "PROJ", adopted, None)
    assert not errs, errs
    mutations = {
        "bad result": good.replace("blocked: Q2 open", "in progress"),
        "empty link": good.replace("| PR #1 |", "|  |"),
        "no tok": good.replace(" · tok ≈ 90k", ""),
        # the H4 grammar rows — the gate must red exactly what ledger.py calls out
        "tok without the space rule": good.replace(" · tok ≈ 90k", " · tok≈90k"),
        "donezo is not done": good.replace("done (workhorse)", "donezo (workhorse)"),
        "bare blocked (no reason)": good.replace("blocked: Q2 open", "blocked"),
        "date regression": good.replace("2026-01-03", "2026-01-01"),
        "unrecognizable link": good.replace("PR #1", "somewhere"),
    }
    for name, text in mutations.items():
        errs, _ = check_text(text, "PROJ", adopted, None)
        assert errs, f"mutation {name!r} should have gone red"

    # ── the Actor column: team.size is a GATE consumer now, not decoration ──
    head6 = "| Date | Lane | Actor | Item | Result | Link |\n|---|---|---|---|---|---|\n"
    good6 = head6 + ("| 2026-01-02 | DEV | An | PROJ-1 | done (workhorse) · tok ≈ 90k | PR #1 |\n"
                     "| 2026-01-03 | QA | Binh | PROJ-1 | blocked: Q2 open | PROJ-1 |\n")
    errs, _ = check_text(good6, "PROJ", adopted, None, team_size=2)
    assert not errs, errs
    # legacy 5-col ledger stays green for a solo owner…
    errs, _ = check_text(good, "PROJ", adopted, None, team_size=1)
    assert not errs, errs
    # …and goes red the moment the team is real
    errs, _ = check_text(good, "PROJ", adopted, None, team_size=2)
    assert errs and "Actor column" in errs[0], errs
    # v2 mutations
    errs, _ = check_text(good6.replace("| An |", "|  |"), "PROJ", adopted, None, team_size=2)
    assert any("empty Actor" in e for e in errs), errs
    errs, _ = check_text(
        good6.replace("| 2026-01-03 | QA | Binh | PROJ-1 | blocked: Q2 open | PROJ-1 |",
                      "| 2026-01-03 | QA | PROJ-1 | blocked: Q2 open | PROJ-1 |"),
        "PROJ", adopted, None, team_size=2)
    assert any("5 columns under a 6-column header" in e for e in errs), errs
    print("log_check selftest: OK (green fixtures 5+6 col + 8 mutations red "
          "+ actor: legacy-red-at-size>1, empty-actor red, header-mismatch red)")


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        _selftest()
    else:
        sys.exit(main())
