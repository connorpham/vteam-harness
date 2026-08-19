"""ledger.py — THE dispatch-ledger row grammar. One rule, one home.

The ledger table (`{paths.pm}/log.md`) has three readers that once carried
three private copies of this grammar and returned three different verdicts for
the same row (audit H4): log_check.py (the gate), perf_report.py (the desk
reader), and src/cli/board.mjs (the dashboard). The grammar now lives HERE;
log_check and perf_report import it, board.mjs mirrors it byte-for-byte and
proves conformance against `--fixtures` in its selftest.

Row shape:      | Date | Lane | Item | Result | Link |

Result kind — the gate's rule, word-boundary anchored:
    done\\b            'donezo' is NOT done
    blocked:\\s*\\S      a bare 'blocked' (no reason) is NOT blocked
    failed:\\s*\\S       same
  anything else is kind "other" — log_check reds it, the readers count it
  as neither done nor blocked nor failed.

Token accounting — the gate's space rule, exactly ONE space each side of ≈:
    tok ≈ N     N raw tokens        (tok ≈ 90   → 0.09 k-tokens)
    tok ≈ Nk    case-insensitive k  (tok ≈ 90K  → 90 k-tokens)
  'tok≈90k' (no space) and 'tok ≈ garbage' are MALFORMED → no accounting,
  which for a done row is a gate red.

Usage:
    python3 ledger.py --selftest    grammar proof over the 6 audit rows + edges
    python3 ledger.py --fixtures    the canonical fixture table as JSON —
                                    board.mjs asserts its mirror against this
"""
from __future__ import annotations

import re

HEADER_PAT = re.compile(r"^\|\s*Date\s*\|", re.I)
TOK_PAT = re.compile(r"tok ≈ (\d+(?:\.\d+)?)([kK])?\b")
_KINDS = (
    ("done", re.compile(r"^done\b")),
    ("blocked", re.compile(r"^blocked:\s*\S")),
    ("failed", re.compile(r"^failed:\s*\S")),
)

# The 6 rows the audit (H4) caught the three parsers disagreeing on, with the
# canonical answers. --selftest proves this file reproduces them; board.mjs's
# selftest proves its mirror does too. Do not edit casually — this table IS
# the cross-implementation contract.
FIXTURES = [
    {"result": "done (workhorse) · tok≈90k", "kind": "done", "tok_k": None, "tok": None},
    {"result": "done (workhorse) · tok ≈ 90", "kind": "done", "tok_k": 0.09, "tok": "90"},
    {"result": "done (workhorse) · tok ≈ 90K", "kind": "done", "tok_k": 90.0, "tok": "90K"},
    {"result": "donezo · tok ≈ 90k", "kind": "other", "tok_k": 90.0, "tok": "90k"},
    {"result": "blocked", "kind": "other", "tok_k": None, "tok": None},
    {"result": "blockedish reason", "kind": "other", "tok_k": None, "tok": None},
]


def result_kind(result: str) -> str:
    """done | blocked | failed | other — word-boundary, reason required after ':'."""
    r = str(result).strip()
    for kind, pat in _KINDS:
        if pat.match(r):
            return kind
    return "other"


def parse_tok(result: str) -> tuple[float | None, str | None]:
    """(k-tokens as float, display string) or (None, None) when absent/malformed."""
    m = TOK_PAT.search(result)
    if not m:
        return None, None
    n = float(m.group(1))
    suffix = m.group(2) or ""
    return (n if suffix else n / 1000), m.group(1) + suffix


def parse_row(line: str) -> dict | None:
    """One ledger TABLE line → a row dict, a malformed marker, or None.

    None — not a data line ('|---' separator or no leading '|'); detecting the
    `| Date |` header (HEADER_PAT) and table state stays the caller's job.
    {"malformed": True, "columns": n, "cells": [...]} — wrong column count.
    Otherwise: {date, lane, item, result, link, kind, tok_k, tok}.
    """
    if not line.startswith("|") or line.startswith("|---"):
        return None
    cells = [c.strip() for c in line.strip().strip("|").split("|")]
    if len(cells) != 5:
        return {"malformed": True, "columns": len(cells), "cells": cells}
    day, lane, item, result, link = cells
    tok_k, tok = parse_tok(result)
    return {"date": day, "lane": lane, "item": item, "result": result,
            "link": link, "kind": result_kind(result), "tok_k": tok_k, "tok": tok}


def _selftest():
    # the canonical table IS the contract — this implementation must reproduce it
    for f in FIXTURES:
        k, (tk, disp) = result_kind(f["result"]), parse_tok(f["result"])
        assert k == f["kind"], f"{f['result']!r}: kind {k} != {f['kind']}"
        assert tk == f["tok_k"] and disp == f["tok"], \
            f"{f['result']!r}: tok ({tk}, {disp}) != ({f['tok_k']}, {f['tok']})"
    # kind boundaries beyond the audit rows
    assert result_kind("done") == "done"
    assert result_kind("blocked: Q2 open") == "blocked"
    assert result_kind("failed: gate red at unit") == "failed"
    assert result_kind("blocked:") == "other", "blocked with no reason is not canonical"
    assert result_kind("failed:  ") == "other"
    assert result_kind("in progress") == "other"
    # tok grammar mutations — every one must stay red-able
    assert parse_tok("tok ≈ 90.5k") == (90.5, "90.5k")
    assert parse_tok("tok ≈  90k") == (None, None), "two spaces break the space rule"
    assert parse_tok("tok≈90k") == (None, None), "no space breaks the space rule"
    assert parse_tok("tok ≈ 90kb") == (None, None), "trailing junk is not a k suffix"
    assert parse_tok("tok ≈ garbage") == (None, None)
    # parse_row: separator / non-table / malformed / full row
    assert parse_row("|---|---|---|---|---|") is None
    assert parse_row("prose line") is None
    bad = parse_row("| a | b | c |")
    assert bad and bad["malformed"] and bad["columns"] == 3, bad
    row = parse_row("| 2026-01-02 | DEV | P-1 | done (workhorse) · tok ≈ 90k | PR #1 |")
    assert row == {"date": "2026-01-02", "lane": "DEV", "item": "P-1",
                   "result": "done (workhorse) · tok ≈ 90k", "link": "PR #1",
                   "kind": "done", "tok_k": 90.0, "tok": "90k"}, row
    print("ledger selftest: OK (6 audit rows + kind boundaries + 5 tok mutations + parse_row)")


if __name__ == "__main__":
    import sys
    if "--selftest" in sys.argv:
        _selftest()
    elif "--fixtures" in sys.argv:
        import json
        print(json.dumps(FIXTURES, ensure_ascii=False))
    else:
        print(__doc__)
