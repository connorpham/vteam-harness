#!/usr/bin/env python3
"""coord_check.py — when parallel DEV agents coordinate by talking, the DECISIONS
they reach must become real, auditable scope — not vanish into chat.

Why: peer chat lets agents split work and hand off contracts, which closes the
FUNCTIONAL-conflict hole `parallel_check` can't see (two files, one hidden type).
But a chat is ephemeral; vteam's thesis is evidence-in-files. So every scope or
contract handoff agreed in chat is appended to {paths.pm}/coordination.md, and
THIS gate proves the log is real: each handoff moved the territory it claims to
(the receiver's CODE-SCOPE now covers the path, the giver's no longer does), the
rounds stayed under budget, and no row is malformed. A handoff that "was agreed"
but never changed a scope is exactly the ephemeral failure — and it goes red.

OPT-IN: inert-green when `team.parallel <= 1`, or when no coordination log exists
(no coordination happened — fine).

Log format ({paths.pm}/coordination.md), a markdown table, append-only:
  | Round | From | To | Path/Contract | What/why |
  | 1 | XOAI-10 | XOAI-11 | src/lib/order.ts | XOAI-11 consumes the Order type |

Usage: coord_check.py [--root <dir>]
Exit 0 = coordination is honest (or off); 1 = exactly which agreement didn't land.
Selftest: --selftest (consistent handoff green + unreflected/over-budget/malformed red).
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "lib"))

def norm(p: str) -> str:
    return p.strip().rstrip("/")


def paths_touch(a: str, b: str) -> bool:
    a, b = norm(a), norm(b)
    return a == b or b.startswith(a + "/") or a.startswith(b + "/")


def covered(path: str, scope: list[str]) -> bool:
    return any(paths_touch(path, s) for s in scope)


def parse_log(text: str) -> list[dict]:
    """Table rows → [{round, frm, to, path}]. Skips the header + separator rows.
    A row that can't yield those four fields is returned with an `error`."""
    rows: list[dict] = []
    for line in text.splitlines():
        s = line.strip()
        if not s.startswith("|"):
            continue  # a table row starts with `|`; prose does not
        inner = s[1:]
        if inner.endswith("|"):
            inner = inner[:-1]  # the trailing outer pipe is optional (GFM); don't require it
        cells = [c.strip() for c in inner.split("|")]
        low = [c.lower() for c in cells]
        if "round" in low and "from" in low and "to" in low:
            continue  # header
        if set("".join(cells)) <= set("-: "):
            continue  # separator
        if len(cells) < 4:
            rows.append({"error": f"malformed row (needs Round|From|To|Path): {line.strip()}"})
            continue
        rnd, frm, to, path = cells[0], cells[1], cells[2], cells[3]
        if not (rnd.isdigit() and frm and to and path):
            rows.append({"error": f"malformed row (round not a number, or empty From/To/Path): {line.strip()}"})
            continue
        rows.append({"round": int(rnd), "frm": frm.upper(), "to": to.upper(), "path": norm(path)})
    return rows


def check_handoffs(rows: list[dict], scope_map: dict[str, list[str]], budget: int) -> list[str]:
    """Every well-formed handoff must be reflected in the two tasksheets' scopes,
    and stay within the round budget."""
    errs: list[str] = []
    for r in rows:
        if "error" in r:
            errs.append(r["error"])
            continue
        if r["round"] > budget:
            errs.append(f"round {r['round']} > team.coord_budget {budget} — bounded coordination, not endless chat "
                        f"({r['frm']}→{r['to']} {r['path']})")
        to_scope = scope_map.get(r["to"], [])
        frm_scope = scope_map.get(r["frm"], [])
        if not covered(r["path"], to_scope):
            errs.append(f"handoff {r['frm']}→{r['to']} of {r['path']} not reflected: "
                        f"{r['to']}'s CODE-SCOPE does not cover it — the chat agreement never became real")
        if covered(r["path"], frm_scope):
            errs.append(f"handoff {r['frm']}→{r['to']} of {r['path']} not reflected: "
                        f"{r['frm']} STILL owns it — the giver never let go")
    return errs


def sh(root, *a):
    import subprocess
    r = subprocess.run(a, cwd=root, capture_output=True, text=True)
    return r.stdout if r.returncode == 0 else ""


def scope_of(root: Path, ticket: str, ev: str) -> list[str]:
    ts = root / ev / ticket / "dev" / "tasksheet.md"
    if not ts.is_file():
        return []
    m = re.search(r"^\s*CODE-SCOPE:\s*(.+)$", ts.read_text(encoding="utf-8", errors="replace"), re.M)
    return [norm(p) for p in m.group(1).split()] if m else []


def main() -> int:
    from ctx import Ctx  # noqa: E402
    c = Ctx()
    try:
        parallel = int(str(c.cfg("team.parallel", 1)))
        budget = int(str(c.cfg("team.coord_budget", 3)))
    except ValueError:
        print("❌ coord_check: team.parallel / team.coord_budget is not a number")
        return 1
    if parallel <= 1:
        print(f"✅ coord_check: parallel mode off (team.parallel={parallel}) — nothing to check")
        return 0

    pm = str(c.cfg("paths.pm", "docs/pm"))
    ev = str(c.cfg("paths.evidence", "evd"))
    log = c.root / pm / "coordination.md"
    if not log.is_file():
        print(f"✅ coord_check: no coordination log at {pm}/coordination.md — no peer handoffs to verify")
        return 0

    rows = parse_log(log.read_text(encoding="utf-8", errors="replace"))
    tickets = {t for r in rows if "error" not in r for t in (r["frm"], r["to"])}
    scope_map = {t: scope_of(c.root, t, ev) for t in tickets}
    errs = check_handoffs(rows, scope_map, budget)

    if errs:
        print(f"❌ coord_check: {len(errs)} coordination problems in {pm}/coordination.md")
        for e in errs:
            print(f"   - {e}")
        return 1
    n = sum(1 for r in rows if "error" not in r)
    print(f"✅ coord_check: {n} peer handoff(s) all reflected in CODE-SCOPE, rounds ≤ {budget}")
    return 0


def _selftest() -> None:
    # a consistent handoff: VT-10 gave src/lib/order.ts to VT-11
    rows = parse_log(
        "| Round | From | To | Path/Contract | What |\n"
        "|---|---|---|---|---|\n"
        "| 1 | VT-10 | VT-11 | src/lib/order.ts | VT-11 consumes Order |\n")
    assert len(rows) == 1 and "error" not in rows[0], rows
    good_scopes = {"VT-10": ["src/lib/wallet.ts"], "VT-11": ["src/lib/order.ts", "src/ui/"]}
    assert check_handoffs(rows, good_scopes, 3) == [], "consistent handoff must be green"
    # receiver's scope does NOT cover the path → red
    bad_to = {"VT-10": ["src/lib/wallet.ts"], "VT-11": ["src/ui/"]}
    e = check_handoffs(rows, bad_to, 3)
    assert any("never became real" in x for x in e), e
    # giver STILL owns the path → red
    bad_from = {"VT-10": ["src/lib/order.ts"], "VT-11": ["src/lib/order.ts"]}
    e = check_handoffs(rows, bad_from, 3)
    assert any("STILL owns" in x for x in e), e
    # round over budget → red
    e = check_handoffs(rows, good_scopes, 0)
    assert any("bounded coordination" in x for x in e), e
    # malformed row → red
    mal = parse_log("| 1 | VT-10 |\n")
    e = check_handoffs(mal, {}, 3)
    assert any("malformed" in x for x in e), e
    # nesting: a dir handoff covered by a broader dir scope
    rows2 = parse_log("| Round | From | To | Path |\n|-|-|-|-|\n| 2 | VT-1 | VT-2 | src/featB/x.ts | y |\n")
    assert check_handoffs(rows2, {"VT-1": ["src/featA/"], "VT-2": ["src/featB/"]}, 3) == [], "dir covers file"
    # C2 regression: a handoff row WITHOUT the trailing outer pipe must still be
    # parsed and checked, not silently dropped (was a false green).
    no_pipe = parse_log("| Round | From | To | Path |\n|-|-|-|-|\n| 1 | VT-10 | VT-11 | src/lib/order.ts | h\n")
    assert len(no_pipe) == 1 and "error" not in no_pipe[0], no_pipe
    e = check_handoffs(no_pipe, {"VT-10": ["src/lib/order.ts"], "VT-11": ["src/ui/"]}, 3)
    assert any("never became real" in x or "STILL owns" in x for x in e), ("trailing-pipe-less row must be checked", e)
    print("coord_check selftest: OK (consistent green + unreflected/giver-keeps/over-budget/malformed red + dir-covers-file + no-trailing-pipe row caught)")


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        _selftest()
    else:
        sys.exit(main())
