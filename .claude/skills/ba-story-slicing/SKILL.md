---
name: ba-story-slicing
description: "Use when a story is too big for one developer to finish in about two days, when it contains the word 'and', or when it names a whole screen, module or role. Also when a split has produced a 'backend story' and a 'frontend story', and when nobody can say what a user could do after the first slice ships."
---



# Story slicing — every slice ships something a user can do

## Identity

You slice work the way it will be demonstrated, not the way it will be built. A slice
that produces a table with no screen, or a screen with no data, is a task pretending
to be a story: it cannot be tested from outside and cannot be shown to anyone. So you
cut through the layers rather than along them, and you accept a narrow, ugly, complete
path over a wide, elegant, unusable one.

## When this applies

- A story looks larger than about two days for one developer.
- The title or criteria contain "and", or a list of roles, states or formats.
- A story names a whole screen, module, report or integration.
- A proposed split has produced layer-shaped pieces (API story, UI story).
- The work is exploratory and the size cannot be known yet.

## Decide

| Question | Choose | Because |
|---|---|---|
| Direction of the cut | **Vertical** — through every layer, so the slice is usable alone | A horizontal slice cannot be verified from outside or demonstrated to anyone |
| The test for a valid slice | Name what a user can **do** after it ships, in one sentence | If the sentence needs "once the other story lands", it is not a slice |
| Story is a workflow | Split by **step**: the first step end-to-end, then the next | Step one delivers value and de-risks the shape of the rest |
| Story has many rules or cases | Split by **rule**: the common case first, each variation after | The common case is most of the value and all of the learning |
| Story has many data shapes or formats | Split by **shape**: one format complete, others after | The second format is cheap once the first one works |
| Story covers several roles | Split by **role**: the role with the most users first | Roles rarely share criteria as much as the title suggests |
| Story is happy path plus errors | Keep the happy path with its **refusals**; split only elaborate recovery | A story with no refusal is half a rule, not a slice |
| Size is unknown | A **spike** with a time box and a question to answer — never an open story | A spike's output is a decision, not software; sizing it as a story hides the risk |
| A slice must go first for technical reasons | Say so as a dependency, and keep it user-visible anyway | "Foundation" stories accumulate until nothing has shipped |
| The slice is still too big | Narrow the **input**, not the layers — one currency, one region, one plan | Narrowing scope keeps the slice whole; removing layers breaks it |

## Rules

- **Write, for every slice, the sentence "after this ships, a user can …".**
  *Otherwise:* you have created a task and lost the ability to demonstrate progress.
- **Never split into layer stories.** *Otherwise:* neither half can be verified, and
  both are "done" while nothing works.
- **Split on every "and" in the title, then re-read the criteria.** *Otherwise:* the
  estimate covers one half and the review discovers the other.
- **Keep each slice's refusals with it.** *Otherwise:* the rule ships without its
  boundary and QA has nothing to fail.
- **Record dependencies in both directions — blocks and blocked-by.** *Otherwise:*
  the board looks parallel and the work is serial.
- **Say what each slice leaves out, in the reader's words.** *Otherwise:* the missing
  part is discovered at review as a defect rather than as scope.
- **Time-box a spike and state the question it answers.** *Otherwise:* research runs
  until someone notices.
- **Stop splitting when a slice can no longer be demonstrated.** *Otherwise:* you have
  traded one oversized story for six meaningless ones.

## Reviewer lens

- For each slice: what can a user do after it ships? Read the sentence aloud.
- Is any slice layer-shaped rather than end-to-end?
- Does any title still contain "and", or cover several roles or formats?
- Does each slice carry its own refusals?
- Are dependencies recorded in both directions?
- Does each slice say what it leaves out?
- Any spike: time box and question stated?
- Is any slice too small to demonstrate?

## Sources

The `/ba` lane requires "INVEST or split" and a ≤2-day size but does not say **how**
to cut; this file supplies the cut. Measured gap in this doctrine before it:
`user story`, `vertical slice`, `definition of ready` and `out of scope` appeared in
**zero** competencies. Complements `ba-acceptance-criteria` (the criteria inside a
slice) and `dev-codebase-design` (where the resulting code lives).

Rationalizations, red flags and a worked example live in `reference/ba-story-slicing.md` — opened when needed, never loaded by default.
