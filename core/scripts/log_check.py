#!/usr/bin/env python3
"""log_check.py — the ledger must not contain fabricated reports.

Why: the PM workflow declares the ledger's Result column "machine-countable", and
a rule no machine counts gets eroded (measured in the source project: rows outside
the value set, token accounting on 7/20 rows). This gate makes it red-able.

Checks, for every data row of the table in {paths.pm}/log.md:
  1. Exactly 5 columns; date is ISO YYYY-MM-DD (a range "2026-08-07/08" allowed).
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


def check_text(text: str, key: str, adopted: date, root: Path | None) -> tuple[list, list]:
    errs, warns = [], []
    in_table, prev_date = False, None
    # project.key is config-supplied text, not a regex — escape it (audit M15;
    # review_check and stale_verdict_check already do)
    link_pat = re.compile(rf"PR #\d+|{re.escape(key)}-\d+|https?://|[\w./-]+/[\w./-]+")
    for n, line in enumerate(text.splitlines(), 1):
        if ledger.HEADER_PAT.match(line):
            in_table = True
            continue
        if not in_table:
            continue
        row = ledger.parse_row(line)
        if row is None:
            continue
        if row.get("malformed"):
            errs.append(f"line {n}: {row['columns']} columns (need 5)")
            continue
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
    errs, warns = check_text(log.read_text(encoding="utf-8"),
                             str(c.cfg("project.key")), adopted, c.root)
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
    print("log_check selftest: OK (green fixture + 8 mutations red)")


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        _selftest()
    else:
        sys.exit(main())
