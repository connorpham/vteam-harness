---
name: qa-case-writing
description: "Use when writing a test case record or filling in its result — when a title names a topic instead of a behaviour, steps hide the typed value, EXPECTED says 'works correctly', or ACTUAL says 'failed'."
role: qa
loads: V2
applies: always
---

# Case writing — understood by a stranger in fifteen seconds

## Identity

You write for two readers: the one who runs the case must be unable to do it
wrong; the one who reads the result — a product owner, a developer, you in six
months — must know what was checked, what should have happened and what did,
without opening a screenshot or asking anyone.

## When this applies

- V2, the moment a case record is started; V4, when ACTUAL is filled in.
- Any record whose four key lines fail the fifteen-second test below.

## Decide

**The fifteen-second test:** cover everything except TITLE, RESULT, EXPECTED,
ACTUAL. A stranger reads those four. If they need STEPS to understand EXPECTED,
EXPECTED is too thin; if they need the screenshot to understand ACTUAL, ACTUAL
is too thin; if the title does not say *which behaviour*, it is a label.

| Field | Written well means |
|---|---|
| TITLE | A sentence about what the product does under a condition: `An order of exactly 499,999 gets no discount`. A product verb (gets, is refused, keeps, recalculates) — never test/check/verify. ≤12 words. No "and" (that is two cases). Folder = title in snake_case |
| AS | Account, role, persona: `staff@demo (STAFF) — the daily operator` |
| PRECONDITION | The state now, with ids, verified: `order #4102, Pending, 2 × item A à 150,000 (read-only check 10:02)` — not the history of how it got there |
| ENTRY | The click path in the screen's own labels: `signed in → Orders → filter "Pending" → row #4102 → "Edit"`; a URL only in brackets as the second path |
| STEPS | Numbered, one action each, imperative, the exact value as typed (trailing space included), the exact label pressed, ≤7 steps. No verification verbs — checking is EXPECTED's job |
| EXPECTED | An observable fact with the number/label the screen shows + citation: `"Total" reads 450,000 ₫ (spec §3.2 R1)` |
| ACTUAL | Same shape as EXPECTED so the eye compares lines: on PASS restate the value then "— as expected"; on FAIL the exact wrong value and what is missing, never a judgement |
| FINDING (FAIL) | `[where] what is wrong — under what condition`, readable alone; SEVERITY and ORIGIN one word each |

## Rules

- **One case, one claim.** "Also check that…" is the next case's title; an
  "and" in a title is two facts sharing one RESULT, and one half's PASS is lost
  when the other fails. (The whole-screen case is the deliberate exception: its
  one claim is "the screen is intact", its STEPS record which looks were taken.)
  *Otherwise:* the developer fixes one of the three assertions and closes the case.
- **The banned words** — as the whole of EXPECTED or ACTUAL: *works · fine ·
  correctly · as expected (alone) · properly · OK · success · passes · no
  errors*. If that is all you can write, you do not yet know what the product
  should show — back to the spec. *Otherwise:* the record is green and empty.
- **Numbers, dates, names carry their units and shapes**: `450,000 ₫`, never
  `450000`; `2026-09-04`, never `09/04`; `23:59 (Asia/Ho_Chi_Minh)`; `order
  #4102`; labels exactly as the screen spells them, in quotes, in the screen's
  language. *Otherwise:* the reader counts digits and guesses locales.
- **Words from the code stay out**: no selectors, routes, table names, HTTP
  verbs in a record a stranger reads — `press "Save"`, not `click #btn-save`;
  the SQL goes in `db_verify.md`, the request in the appendix. *Otherwise:* the
  one reader who could judge the business value cannot read the record.
- **Values in `project.language`, keys in English** (`RESULT:`, `EXPECTED:`) —
  the gate reads the keys, people read the values. *Otherwise:* the team needs
  English to know what their own total reads.

## Reviewer lens

- Run the fifteen-second test on two cases, cold. What could you not tell?
- Find a banned word standing alone in any EXPECTED/ACTUAL.
- Re-run one case using only the record — is any step ambiguous, any typed value missing?

## Sources

connorpham/ai-qa `case-writing.md` (the fifteen-second test, the field
standards, the banned words, before/after example) · goldbergyoni testing
(3-part naming) · vteam `evd_check.py` journey fields (AS/ENTRY/AFTER/BACK).

Rationalizations, red flags and a worked example live in `reference/qa-case-writing.md` — opened when needed, never loaded by default.
