#!/usr/bin/env python3
"""cost_check.py — the ledger's `tok ≈` is an ESTIMATE; the session logs are the measurement.

Why this exists: every ledger row ends `done · tok ≈ <N>k`, and that number is typed by
the agent from memory. `lib/ledger.py` parses it and nothing ever checked it — the one
column of testimony left in a framework whose whole argument is "evidence, not claims".
`npx vteam-harness usage --sync` already publishes the MEASURED numbers per day and
model into `{paths.pm}/usage/<actor>.md`; this step reads both and says when they
disagree, and — louder — when the measured record stopped being kept at all.

WHAT IS COMPARED, and what cannot be:

  · Per DAY, never per ticket. A session log knows the day, the model and the token
    counts; it does not know which ticket a token belonged to. Any per-ticket number
    here would be an invention, so the check refuses to produce one and says so.
  · Measured "new spend" = input + cache-write + output.
      - cache-read is EXCLUDED: re-reading context already paid for is not new work,
        and it dwarfs everything else (938M against 3.3M of output in this repo), so
        including it would make every comparison meaningless.
      - cache-write IS included: the first read of a file is real ingestion.
      - input is included because it is new spend too; under caching it is a rounding
        error (12k against 938M here), so the figure is in practice output+cache-write.
  · An estimate and a measurement differ by construction. The tolerance is a FACTOR
    (`ledger.cost_tolerance_factor`, default 10), not a percentage, and crossing it is a
    finding about the ESTIMATE — never a number to edit afterwards so the check goes
    quiet. Editing the estimate to match the measurement is the one response that
    destroys the signal.

SEVERITY — advisory everywhere, and the gate manifest carries `advisory: true`:

  · staleness (the loud one): ledger rows newer than the newest measured row by more
    than `ledger.usage_max_stale_days` (default 7) means the measured record silently
    stopped. That is the finding this check was written for — a divergence you can see,
    a record nobody keeps you cannot.
  · divergence past the tolerance factor: named with the date, both numbers, the ratio.
  · dates with ledger rows and no measured row: ONE compact line, never a wall. Most
    repos never run `usage --sync`, and a check that shouts at them is a check people
    turn off.
  · no usage directory at all: one quiet line, exit 0. Nothing has been claimed about
    a measurement that was never taken.

Exit 0 when clean or unmeasurable; exit 1 on staleness or divergence — which the gate
reports as `🟡 advisory cost: FAILED`, exactly like `schedule`. It never blocks a commit.

  python3 cost_check.py [--selftest]
"""
from __future__ import annotations

import datetime as _dt
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "lib"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import ledger  # noqa: E402 — the one dispatch-row grammar, imported not re-written

DATE_RE = _dt.date.fromisoformat


def measured_by_day(measured: list[dict]) -> dict[str, float]:
    """date → measured new spend in k-tokens, summed across every actor and model.

    New spend = input + cache-write + output (see the header for why cache-read is out)."""
    out: dict[str, float] = {}
    for person in measured:
        for r in person.get("rows", []):
            spend = r.get("input", 0) + r.get("cache_write", 0) + r.get("output", 0)
            out[r["date"]] = out.get(r["date"], 0.0) + spend / 1000
    return out


def claimed_by_day(rows: list[dict]) -> dict[str, float]:
    """date → claimed k-tokens, summed over the ledger rows that carry a `tok ≈`."""
    out: dict[str, float] = {}
    for r in rows:
        if r.get("malformed") or not r.get("tok_k"):
            continue
        out[r["date"]] = out.get(r["date"], 0.0) + float(r["tok_k"])
    return out


def newest(dates) -> str | None:
    """The newest parseable ISO date, or None. A hand-edited junk date is skipped
    rather than crashing the step — this is a reporter, not a parser gate."""
    best = None
    for d in dates:
        try:
            DATE_RE(d)
        except (ValueError, TypeError):
            continue
        if best is None or d > best:
            best = d
    return best


def audit(claimed: dict[str, float], measured: dict[str, float],
          has_usage_files: bool, factor: float = 10.0,
          stale_days: int = 7) -> tuple[list[str], bool]:
    """(lines to print, any_finding). Pure — the selftest drives it directly."""
    lines: list[str] = []
    finding = False

    if not has_usage_files:
        lines.append("ℹ️  no measured record to audit against — nobody has run "
                     "`npx vteam-harness usage --sync` here. The ledger's `tok ≈` stays an "
                     "unaudited estimate, which is honest as long as it is not quoted as a "
                     "measurement.")
        return lines, False

    both = sorted(set(claimed) & set(measured))
    for day in both:
        c, m = claimed[day], measured[day]
        if c <= 0 or m <= 0:
            continue
        ratio = max(c, m) / min(c, m)
        if ratio > factor:
            finding = True
            lines.append(
                f"⚠️  {day}: the ledger claims ≈{c:,.0f}k, the session logs measured "
                f"≈{m:,.0f}k — {ratio:.0f}× apart (tolerance {factor:g}×). A finding about "
                f"the ESTIMATE: say what the day actually cost next time, never edit the "
                f"row to match the measurement.")

    unmeasured = sorted(set(claimed) - set(measured))
    if unmeasured:
        head = ", ".join(unmeasured[:3])
        more = f" … +{len(unmeasured) - 3} more" if len(unmeasured) > 3 else ""
        lines.append(f"ℹ️  {len(unmeasured)} day(s) with ledger rows and no measured row "
                     f"({head}{more}) — not audited, not a fault.")

    newest_claim, newest_measure = newest(claimed), newest(measured)
    if newest_claim and newest_measure:
        gap = (DATE_RE(newest_claim) - DATE_RE(newest_measure)).days
        if gap > stale_days:
            finding = True
            lines.append(
                f"⚠️  the measured record STOPPED: newest ledger row {newest_claim}, newest "
                f"measured row {newest_measure} — {gap} days apart (limit {stale_days}). "
                f"Run `npx vteam-harness usage --sync` and commit the file; until then every "
                f"cost number in this repo is self-reported.")
    elif newest_claim and not newest_measure:
        finding = True
        lines.append(f"⚠️  usage file(s) exist but carry no parseable measured row, while the "
                     f"ledger runs to {newest_claim} — re-run `npx vteam-harness usage --sync`.")

    if not finding:
        n = len(both)
        lines.append(f"✅ cost_check: {n} day(s) audited within {factor:g}×, measured record "
                     f"current" if n else
                     f"✅ cost_check: nothing to audit yet — no day has both a ledger row and a "
                     f"measured row")
    lines.append("   (per DAY only: a session log knows the day and the model, never which "
                 "ticket a token belonged to)")
    return lines, finding


def _selftest() -> None:
    # 1. a matching day is green and says nothing alarming
    lines, finding = audit({"2026-09-18": 100.0}, {"2026-09-18": 120_000 / 1000}, True)
    assert not finding, lines
    assert any("audited within" in x for x in lines), lines

    # 2. a 40× divergence is named, with both numbers and the ratio
    lines, finding = audit({"2026-09-18": 5.0}, {"2026-09-18": 200.0}, True)
    assert finding, lines
    hit = [x for x in lines if "40×" in x]
    assert hit and "5k" in hit[0] and "200k" in hit[0], lines
    assert any("never edit the row to match" in x for x in lines), lines
    # …and inside the tolerance it stays quiet
    _, finding = audit({"2026-09-18": 25.0}, {"2026-09-18": 200.0}, True)
    assert not finding, "8× is inside the default 10× tolerance"

    # 3. a stale measured record is the loud finding, naming both dates
    lines, finding = audit({"2026-09-18": 100.0, "2026-08-24": 10.0},
                           {"2026-08-24": 10.0}, True)
    assert finding, lines
    stale = [x for x in lines if "STOPPED" in x]
    assert stale and "2026-09-18" in stale[0] and "2026-08-24" in stale[0] and "25 days" in stale[0], lines
    # …and a 3-day gap is not stale
    _, finding = audit({"2026-09-18": 10.0, "2026-09-15": 10.0}, {"2026-09-15": 10.0}, True)
    assert not finding, "a 3-day gap is inside the default 7-day limit"

    # 4. no usage directory at all: quiet, no finding, and it says what that means
    lines, finding = audit({"2026-09-18": 100.0}, {}, False)
    # exactly one line: when there is nothing to audit, even the per-day caveat is noise
    assert not finding and len(lines) == 1 and "unaudited estimate" in lines[0], lines

    # unmeasured days are one compact line, never one per day
    lines, _ = audit({f"2026-09-{d:02d}": 1.0 for d in range(1, 12)},
                     {"2026-09-01": 1.0}, True)
    compact = [x for x in lines if "no measured row" in x]
    assert len(compact) == 1 and "+7 more" in compact[0], lines

    # the column choice: cache-read is excluded, cache-write and output are not
    got = measured_by_day([{"rows": [{"date": "2026-09-18", "input": 1000,
                                      "cache_read": 900_000_000, "cache_write": 4000,
                                      "output": 5000}]}])
    assert got == {"2026-09-18": 10.0}, got

    # a junk date is skipped, not fatal
    assert newest(["2026-09-18", "not-a-date", "2026-09-01"]) == "2026-09-18"
    assert newest(["nope"]) is None

    # the ledger grammar is IMPORTED, not re-derived: a malformed `tok≈90k` contributes 0
    rows = [ledger.parse_row("| 2026-09-18 | dev | An | VT-1 | done · tok≈90k | PR #1 |"),
            ledger.parse_row("| 2026-09-18 | dev | An | VT-2 | done · tok ≈ 12k | PR #2 |")]
    assert claimed_by_day(rows) == {"2026-09-18": 12.0}, claimed_by_day(rows)

    print("cost_check selftest: OK (match green + 40× divergence named + staleness names both "
          "dates + no-usage-dir quiet + unmeasured days compact + cache-read excluded + "
          "malformed tok ignored via lib/ledger)")


def main() -> int:
    if "--selftest" in sys.argv:
        _selftest()
        return 0
    from ctx import Ctx  # noqa: E402 — the selftest must run without a config
    import perf_report   # noqa: E402 — parse_usage_dir: one home for the usage grammar

    c = Ctx()
    pm = c.path("pm")

    def knob(key, default, cast):
        raw = c.cfg(key, default)
        try:
            return cast(str(raw))
        except (TypeError, ValueError):
            print(f"❌ cost_check: {key} {raw!r} is not a number")
            sys.exit(2)

    factor = knob("ledger.cost_tolerance_factor", 10, float)
    stale_days = knob("ledger.usage_max_stale_days", 7, int)

    log = pm / "log.md"
    rows = []
    if log.is_file():
        for line in log.read_text(encoding="utf-8", errors="replace").splitlines():
            r = ledger.parse_row(line)
            if r and not r.get("malformed"):
                rows.append(r)

    measured = perf_report.parse_usage_dir(pm)
    lines, finding = audit(claimed_by_day(rows), measured_by_day(measured),
                           bool(measured), factor, stale_days)
    for line in lines:
        print(line)
    return 1 if finding else 0


if __name__ == "__main__":
    sys.exit(main())
