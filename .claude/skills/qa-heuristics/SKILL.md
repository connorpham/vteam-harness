---
name: qa-heuristics
description: "Use when the spec is silent and you need a defensible finding anyway, when choosing the exploratory case, or when a boundary needs a sharper edge — consistency oracles, coverage walks, data shapes, interruptions, tours."
---


# Heuristics — the working toolbox when the script runs out

## Identity

Scripted cases confirm what someone already thought of; heuristics find what
nobody did. A heuristic is a fallible rule of thumb — it tells you *where to
look and what to try*, never what the right answer is. You name it, timebox it,
and record what you tried even when you found nothing, because a heuristic run
and not written down was a hunch, not a test.

## When this applies

- The exploratory case (V2), and any time the spec is silent on an area.
- A boundary case that needs a sharper edge.
- The whole-screen case, when "does it look right" needs to become specific looks.

## Decide

**No spec? Reach for consistency oracles — HICCUPPS.** You cannot call it a
defect against a spec; you can report it is *inconsistent with something it
should be consistent with*, name which, and send a decision request with an owner.

| Consistent with… | Example finding |
|---|---|
| **H**istory (prior release) | the list used to keep its filter after an edit; now it does not |
| **I**mage (org's reputation) | a stack trace on a bank's checkout |
| **C**omparable products | Enter deletes the row where every spreadsheet commits it |
| **C**laims (tooltip, help, ticket) | button says "Save draft"; the record is published |
| **U**ser expectations | a 30-second wait with no spinner |
| **P**roduct (itself, next screen) | `dd/mm` on the list, `mm/dd` on the detail |
| **P**urpose | a search that finds "Nguyen" but not "Nguyễn" in a Vietnamese product |
| **S**tatutes/standards | VAT rounded per line where the law requires rounding on the total |

Two need no decision request — a crash, a raw error, silent data loss, or one
role seeing another's data violates all eight; report as a defect.

## Rules

- **Report a consistency finding as**: *"Inconsistent with `<oracle>`: `<the two
  things that disagree>`. No written spec decides which is correct. Decision
  requested from `<owner>`."* Severity by consequence, ORIGIN `SPEC`.
  *Otherwise:* it reads as a personal opinion and gets waved off.
- **Coverage when unsure you looked everywhere — SFDIPOT**: Structure, Function,
  Data, Interfaces, Platform, Operations, Time. One question, one sheet line
  each. *Otherwise:* the nightly job, the export's old field name, the
  first-of-the-month bug go unlooked-at.
- **Data shapes for the boundary**: Zero/One/Many · Goldilocks (min−1, max+1,
  exactly the limit) · Some/None/All · First/Last/Middle · Before/During/After ·
  CRUD then read-back · Same-again. *Otherwise:* Many breaks at page-size+1 and
  nobody visited it.
- **Interruptions — pick two per journey**, at the step where interruption hurts
  most (between "pressed the button" and "confirmation appeared"): cancel, back,
  refresh, close tab, session expiry, logout in another tab, network drop,
  return in 40 minutes, record changed by someone else. *Otherwise:* the
  double-submit and the race ship.
- **Follow the data**: enter a value once, find *every* place it appears — list,
  detail, header total, badge, search, export, report, email, audit log, API,
  PDF — and check they agree. *Otherwise:* the fix-one-place defect hides on the
  screen nobody's happy path visits.
- **Tours as a way into a new screen**: Money, Landmark, Back-alley,
  Bad-neighbourhood, Garbage-collector, Couch-potato, Obsessive-compulsive,
  Supermodel, Intellectual — one, for its timebox, one paragraph written.
- **RCRCRC to choose what to regress**: Recent, Core, Risky,
  Configuration-sensitive, Repaired, Chronic.

## Reviewer lens

- For any silent-spec finding: which oracle, both disagreeing things named, owner attached?
- Does the exploratory case name its heuristic and timebox, and record what was tried even if empty?
- Pick a value the pack wrote; was it followed to a second screen, or verified once?

## Sources

connorpham/ai-qa `heuristics.md` — the full HICCUPPS/SFDIPOT/tours/RCRCRC tables
at `reference/heuristics.md` · Bach, Heuristic Test Strategy Model · Hendrickson,
*Explore It!*

Rationalizations, red flags and a worked example live in `reference/qa-heuristics.md` — opened when needed, never loaded by default.
