#!/usr/bin/env python3
"""comment_check.py — verify the 7-part report comment WAS REALLY POSTED (/dev T6).

Reads the ticket's latest comments back FROM the tracker and checks all 7 sentinel
markers — posting without read-back doesn't count as posted. The report comment
may not be the newest one (QA/bots interleave), so the latest 5 are scanned.

Markers are locale-neutral sentinels; the prose after each is localized freely:
  [R1] what was done · [R2] impact scope · [R3] technical · [R4] tested
  [R5] evidence · [R6] notes for QA · [R7] open issues

Usage: comment_check.py <TICKET>    · selftest: --selftest (mutation proof offline)
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "lib"))

MARKERS = ["[R1]", "[R2]", "[R3]", "[R4]", "[R5]", "[R6]", "[R7]"]


def check_body(body: str) -> list[str]:
    return [m for m in MARKERS if m not in body]


def selftest() -> int:
    good = "".join(f"{m} content\n" for m in MARKERS)
    fails = 0
    if check_body(good):
        print("✗ selftest: a complete comment reported missing markers")
        fails += 1
    else:
        print("✓ selftest: all 7 markers → green")
    for m in MARKERS:
        missing = check_body(good.replace(m, "[R0]"))
        if missing == [m]:
            print(f"✓ selftest: missing {m} → RED at the right marker")
        else:
            print(f"✗ selftest: missing {m} but gate reported {missing}")
            fails += 1
    return 1 if fails else 0


def main() -> int:
    if len(sys.argv) != 2:
        print(__doc__)
        return 1
    if sys.argv[1] == "--selftest":
        return selftest()
    from ctx import Ctx
    import tracker as trk
    ticket = sys.argv[1].upper()
    t = trk.load(Ctx())
    comments = t.get_issue(ticket).get("comments", [])
    if not comments:
        print(f"✗ {ticket}: no comments at all — the 7-part report is NOT posted")
        return 1
    best_missing: list[str] | None = None
    for body in comments[:5]:
        missing = check_body(body)
        if not missing:
            print(f"✓ {ticket}: the 7-part report comment is really on the tracker")
            return 0
        if best_missing is None or len(missing) < len(best_missing):
            best_missing = missing
    print(f"✗ {ticket}: none of the latest 5 comments carries all 7 markers; closest is missing:")
    for m in best_missing or []:
        print(f"  · {m}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
