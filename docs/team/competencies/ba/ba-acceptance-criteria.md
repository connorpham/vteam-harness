---
name: ba-acceptance-criteria
description: "Use when writing the acceptance criteria for a story, and when a criterion is about to say 'works correctly', 'handles errors', 'is fast' or 'the user can'. Also when a criterion describes clicks instead of outcomes, when one criterion carries three behaviours, and when nobody can name the value that proves it passed."
role: ba
loads: B2
applies: always
---


# Acceptance criteria — a criterion nobody can fail is not a criterion

## Identity

You write criteria the way a tester will read them: one behaviour, one observable
outcome, one concrete value, and a source you can point at. You know the difference
between describing *what the system must do* and *how a person clicks*, and you write
the first because the second breaks the moment the screen changes. A criterion you
cannot imagine failing is decoration, and you delete it rather than ship it.

## When this applies

- Writing or rewriting the criteria on any story, or a criterion contains "correctly", "properly", "handles", "fast".
- One criterion covers a happy path and its errors together.
- A criterion names buttons or screens; a non-functional requirement appears.
- The story is about a change, so what must **stay** true is also at stake.

## Decide

| Question | Choose | Because |
|---|---|---|
| Criterion shape | **Given / When / Then** — starting state including the role, one action, one observable outcome | It forces the three things a tester needs and exposes the ones you were guessing |
| Declarative or imperative | **Declarative**: state the intent ("when the member submits a valid order"), not the mechanics ("when they click the blue Submit button") | Imperative criteria are re-written by every UI change and test nothing durable |
| How many behaviours per criterion | Exactly one. A `Then` with "and" in it is two criteria | You cannot record a partial pass, so a compound criterion hides half its result |
| Values in the criterion | Concrete and typed — `total = 450,000 ₫`, `role = viewer`, `qty = 0` | "A valid amount" moves the decision to whoever runs the test |
| Outcome to assert | Something a person or an API response can **observe** | "The record is flagged internally" cannot be verified from outside the code |
| The failing side | Every rule gets its refusal: the value that must be **rejected**, and what the user is told | A rule with only its happy case is half specified, and the half missing is where users live |
| Non-functional criteria | A number, a measurement point and a condition — "p95 under 400 ms at 50 concurrent users" | "Fast" cannot pass or fail; a percentile at a load can |
| Where the criterion comes from | Cite the spec section or decision id; where none exists, raise a question rather than invent a plausible rule | An uncited criterion is the BA's invention, and inventions get built |
| Out of scope | Name what a reasonable reader would otherwise assume is included | Silence reads as inclusion, and the argument arrives at review |
| A change story | Add the criteria for what must **not** change | Regression is the failure mode of every change, and nobody writes it down |

## Rules

- **One behaviour per criterion; split on every "and" in the `Then`.** *Otherwise:*
  the result is "partly passed", which no report can carry.
- **Put a concrete, typed value in every criterion.** *Otherwise:* the tester picks
  the value, and they will pick the one that works.
- **Assert only what is observable from outside.** *Otherwise:* verification needs to
  read the code, and the oracle becomes the implementation.
- **Write the refusal for every rule you write.** *Otherwise:* the boundary is
  untested and the first bad input reaches the database.
- **Give every non-functional criterion a number, a unit and a measurement point.**
  *Otherwise:* it is a wish, and it will be dropped at the first deadline.
- **Cite the source on every criterion; raise a question instead of inventing.**
  *Otherwise:* the backlog quietly becomes the specification.
- **State what is out of scope in the words a reader would otherwise assume.**
  *Otherwise:* scope is negotiated during review, at the worst moment.
- **Keep mechanics out of `Given` and `When`.** *Otherwise:* a button rename fails a
  business rule.
- **Read each criterion back as a test: what would I do, what would I see?**
  *Otherwise:* you ship a sentence nobody can execute.

## Rationalizations

| Excuse | Reality |
|---|---|
| "The dev knows what I mean." | The tester does not, and neither will you in three weeks. |
| "It's obviously in scope." | Then write it down; obvious things are what teams argue about. |
| "The spec doesn't say, so I used the sensible rule." | You just authored a requirement nobody approved. |

## Red flags

- "correctly", "properly", "as expected", "handles", "fast", "user-friendly".
- A `Then` containing "and", or a criterion listing several outcomes.
- A criterion naming a button or screen; a rule with no rejected value and no message.
- A non-functional criterion with no number or no load.
- Any criterion with no spec reference on a story whose spec exists.

## Example

Weak: "The system handles invalid orders correctly." Nothing there can fail.
Strong, split into two: **(1)** *Given* a member with an empty cart, *When* they submit
the order, *Then* the order is refused and the response says "Add at least one item"
— spec §4.2. **(2)** *Given* a member whose cart total is 0 ₫ with one free item,
*When* they submit, *Then* the order is accepted with `total = 0 ₫` — spec §4.2, and
this is the boundary that must behave the other way. Out of scope: partial refunds
(no decision yet, Q-14).

## Reviewer lens

- Could each criterion fail? Name the input that would fail it.
- Does any `Then` contain "and"?
- Is every value concrete and typed, or does the tester have to choose?
- Is every asserted outcome observable from outside the system?
- For each rule: where is the rejected value and the message?
- Every non-functional criterion: number, unit, measurement point?
- Does each criterion cite a spec section or a decision id?
- Is "out of scope" written in the words a reader would assume are included?

## Sources

Field study of `nilbuild/developer-roadmap` @ `74a645b`: its `qa` roadmap spends 146
topics on testing and **zero** on writing a testable requirement. Measured gap here
before this file: `given/when/then`, `user story`, `traceab`, `non-functional` and
`out of scope` appeared in **zero** competencies. The `/ba` lane already requires
Given/When/Then and cites ISO 29148; this file supplies the craft it assumes.
Complements `qa-requirement-smells`, which **detects** an untestable criterion.
