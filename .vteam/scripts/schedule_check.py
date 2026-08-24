#!/usr/bin/env python3
"""schedule_check.py — "on schedule or off" must be a MACHINE-COMPUTED number.

Why: an audit found the project's most important metric (on/off schedule against
go-live) was the ONLY one with no gate — the acceptance dossier said "still on
time" by hand while unbudgeted work never entered the plan. The desk report MUST
paste this script's output instead of writing its own progress sentence.

Does:
  1. Parse the plan ({paths.pm}/plan.yaml — the structured contract; markdown
     views are generated, never parsed): current sprint, items + day-costs.
  2. Ask the tracker for each current-sprint item's status (+ count future-sprint
     items already Done = work done ahead).
  3. Compute: remaining day-cost vs remaining capacity (remaining workdays ×
     team.capacity_per_day) → ON SCHEDULE or OFF by +N person-days. OFF → exit 1
     (the desk report cannot go green with words).
  4. Scan the decision queue: 🔴 OPEN rows due ≤7 days or overdue → listed;
     deadlines written as WORDS ("asap", a sprint name) → warned — a deadline
     that isn't a date is invisible to every reminder machine.

plan.yaml shape (vteam YAML subset — items are "KEY days" strings):
    sprint-1:
      start: 2026-08-10
      end: 2026-08-21
      items:
        - "PROJ-1 1.5"
        - "PROJ-2 0.5"

Usage: schedule_check.py [--today YYYY-MM-DD]   · selftest: --selftest
"""
from __future__ import annotations

import argparse
import datetime as dt
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "lib"))
from ctx import Ctx, parse_config  # noqa: E402


def parse_cost(raw: str, hours_per_day: float) -> float:
    """A plan cost → person-days. Three spellings, one loud death:
    `1.5` / `1.5d` = days; `12h` = hours ÷ team.hours_per_day (a workday is
    hours_per_day hours — 8 by default — so estimates written in hours and
    estimates written in days land on the same scale)."""
    m = re.match(r"^([\d.]+)([dh]?)$", raw.strip(), re.I)
    if not m:
        raise SystemExit(f"schedule_check: cost {raw!r} is not <n>, <n>d or <n>h")
    n, unit = float(m.group(1)), m.group(2).lower()
    return n / hours_per_day if unit == "h" else n


def parse_plan(text: str, hours_per_day: float = 8.0) -> list[dict]:
    data = parse_config(text)
    sprints = []
    for name, s in data.items():
        m = re.match(r"^sprint-(\d+)$", name)
        if not m or not isinstance(s, dict):
            continue
        items = []
        for row in s.get("items", []) or []:
            im = re.match(r"^(\S+)\s+(\S+)$", str(row).strip())
            if not im:
                raise SystemExit(f"schedule_check: plan item {row!r} is not \"KEY <days|hours>\" "
                                 f"(e.g. \"PROJ-12 1.5d\" or \"PROJ-12 12h\")")
            items.append((im.group(1).upper(), parse_cost(im.group(2), hours_per_day)))
        sprints.append({
            "n": int(m.group(1)),
            "start": dt.date.fromisoformat(str(s["start"])),
            "end": dt.date.fromisoformat(str(s["end"])),
            "items": items,
        })
    return sorted(sprints, key=lambda s: s["n"])


def workdays(a: dt.date, b: dt.date) -> int:
    n, d = 0, a
    while d <= b:
        if d.weekday() < 5:
            n += 1
        d += dt.timedelta(days=1)
    return n


def decision_deadlines(text: str, today: dt.date) -> tuple[list[str], list[str]]:
    burning, textual = [], []
    for line in text.splitlines():
        if "🔴 OPEN" not in line or not line.startswith("|"):
            continue
        cols = [c.strip() for c in line.split("|")]
        ident = cols[1] if len(cols) > 1 else "?"
        due_cell = next((c for c in cols if re.search(r"\d{4}-\d{2}-\d{2}", c)), None)
        if due_cell:
            due = dt.date.fromisoformat(re.search(r"(\d{4}-\d{2}-\d{2})", due_cell).group(1))
            delta = (due - today).days
            if delta <= 7:
                burning.append(f"{ident} — due {due.isoformat()} "
                               f"({'OVERDUE' if delta < 0 else f'{delta} days left'})")
        else:
            cell = " ".join(cols[2:])[:60]
            if re.search(r"asap|soon|sprint|week", cell, re.I):
                textual.append(f"{ident} — deadline written as words: “{cell.strip()}” "
                               f"→ convert to YYYY-MM-DD")
    return burning, textual


def evaluate(sprints, statuses: dict[str, str], today: dt.date, cap_per_day: float,
             done_cats=("done",)) -> tuple[list[str], bool]:
    lines, red = [], False
    cur = next((s for s in sprints if s["start"] <= today <= s["end"]), None)
    if cur is None:
        return [f"⚠️  {today.isoformat()} falls in no sprint of the plan — plan stale?"], True
    remaining, detail, unknown = 0.0, [], 0
    for k, d in cur["items"]:
        st = statuses.get(k, "?")
        if st == "?":
            unknown += 1
        done = st in done_cats
        if not done:
            remaining += d
        detail.append(f"    {k} · {d} pd · {st}{'' if done else '  ← owed'}")
    if unknown:
        lines.append(f"⚠️  {unknown} items unqueryable on the tracker — every number "
                     f"below is a conservative guess (treated as NOT done)")
    cap = workdays(today, cur["end"]) * cap_per_day
    ahead = sum(d for s in sprints if s["n"] > cur["n"]
                for k, d in s["items"] if statuses.get(k) in done_cats)
    off = remaining - cap
    verdict = "ON SCHEDULE" if off <= 0 else f"OFF by +{off:.1f} person-days"
    lines.append(f"Sprint {cur['n']} ({cur['start']:%d/%m}–{cur['end']:%d/%m}): "
                 f"{remaining:.1f} pd owed · {cap:.1f} pd capacity left "
                 f"({workdays(today, cur['end'])} workdays × {cap_per_day}) → **{verdict}**")
    lines.extend(detail)
    if ahead:
        lines.append(f"    (+ {ahead:.1f} pd of future sprints already done — a "
                     f"go-live buffer, not this sprint's)")
    if off > 0:
        red = True
    return lines, red


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--today")
    args = ap.parse_args()
    today = dt.date.fromisoformat(args.today) if args.today else dt.date.today()

    c = Ctx()
    plan_file = c.path("pm") / "plan.yaml"
    if not plan_file.is_file():
        print(f"❌ schedule_check: {plan_file} missing — without a structured plan "
              f"nothing can be measured, and 'on time' may NOT be written by hand")
        return 1
    hours_per_day = float(c.cfg("team.hours_per_day", 8))
    if hours_per_day <= 0:
        raise SystemExit(f"schedule_check: team.hours_per_day must be > 0 (got {hours_per_day})")
    sprints = parse_plan(plan_file.read_text(encoding="utf-8"), hours_per_day)
    import tracker as trk
    t = trk.load(c)
    statuses: dict[str, str] = {}
    for s in sprints:
        for k, _ in s["items"]:
            if k not in statuses and k != "—":
                try:
                    statuses[k] = t.get_issue(k)["status_category"]
                except SystemExit:
                    statuses[k] = "?"
    lines, red = evaluate(sprints, statuses, today, float(c.cfg("team.capacity_per_day", 0.8)))

    dq = c.path("pm") / "decisions.md"
    if dq.is_file():
        burning, textual = decision_deadlines(dq.read_text(encoding="utf-8"), today)
        if burning:
            lines.append("Decision deadlines burning (≤7 days):")
            lines.extend(f"    🔥 {b}" for b in burning)
        lines.extend(f"    ⚠️  {t_}" for t_ in textual)

    print("\n".join(lines))
    if red:
        print("\n❌ schedule_check: OFF SCHEDULE or stale plan — the desk report must "
              "lead with this line plus a plan (cut scope / slip / add capacity).")
        return 1
    print("\n✅ schedule_check: on schedule by measurement — paste the block above "
          "into the desk report.")
    return 0


def _selftest():
    plan = ("sprint-1:\n  start: 2026-01-05\n  end: 2026-01-16\n  items:\n"
            "    - \"PROJ-1 2\"\n    - \"PROJ-2 6\"\n"
            "sprint-2:\n  start: 2026-01-19\n  end: 2026-01-30\n  items:\n"
            "    - \"PROJ-3 1\"\n")
    sprints = parse_plan(plan)
    assert len(sprints) == 2 and sprints[0]["items"][0] == ("PROJ-1", 2.0)
    today = dt.date(2026, 1, 5)  # 10 workdays left ⇒ cap 8.0
    lines, red = evaluate(sprints, {"PROJ-1": "done", "PROJ-2": "todo"}, today, 0.8)
    assert not red, lines  # 6 owed ≤ 8 cap
    lines, red = evaluate(sprints, {"PROJ-1": "todo", "PROJ-2": "todo"}, today, 0.5)
    assert red, lines      # 8 owed > 5 cap → OFF must red
    lines, red = evaluate(sprints, {}, dt.date(2027, 1, 1), 0.8)
    assert red, "date outside every sprint must red"
    b, t = decision_deadlines("| Q1 | question | 🔴 OPEN | 2026-01-07 |\n"
                              "| Q2 | question | 🔴 OPEN | asap |\n", today)
    assert b and t, (b, t)
    try:
        parse_plan("sprint-1:\n  start: 2026-01-05\n  end: 2026-01-16\n  items:\n    - \"PROJ-1\"\n")
        raise AssertionError("malformed item should exit")
    except SystemExit:
        pass
    # hour units: a workday is team.hours_per_day hours (default 8)
    hp = ("sprint-1:\n  start: 2026-01-05\n  end: 2026-01-16\n  items:\n"
          "    - \"PROJ-4 8h\"\n    - \"PROJ-5 4h\"\n    - \"PROJ-6 1.5d\"\n")
    items = parse_plan(hp, hours_per_day=8.0)[0]["items"]
    assert items == [("PROJ-4", 1.0), ("PROJ-5", 0.5), ("PROJ-6", 1.5)], items
    assert parse_plan(hp, hours_per_day=4.0)[0]["items"][0] == ("PROJ-4", 2.0), \
        "hours_per_day must rescale hour costs"
    try:
        parse_cost("2w", 8.0)
        raise AssertionError("unknown unit should exit")
    except SystemExit:
        pass
    print("schedule_check selftest: OK (on-schedule green + 3 reds + parser guard "
          "+ hour units at 8h/day, rescaled at 4h/day, unknown unit red)")


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        _selftest()
    else:
        sys.exit(main())
