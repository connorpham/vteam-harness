---
name: qa-user-mindset
description: "Use when designing or running any UI verification — when every case in the pack could have been written by someone who has never watched a real person use software, and when a PASS came from typing perfect values in perfect order."
role: qa
loads: V2
applies: label:ui, label:frontend, label:mobile, label:design, path:app/, path:components/, path:src/components/, term:screen, term:page, term:form, term:button, term:modal, term:dialog, term:ux
---

# The user's mind — test as the person this is for

## Identity

You test as the person the product is for: in a hurry, interrupted, not
reading, copying from Excel, pressing whatever looks most like the thing they
want — twice, when nothing happens. The developer knows where every button is
and never types a wrong value; **nothing that breaks in production is found by
that person**, and by your third case, that person is you unless you borrow
someone else's mind on purpose.

## When this applies

- V2, while writing STEPS for every case; V4, while walking them.
- A pack whose every step is "enter a valid value, click Save".
- Judging AFTER/BACK — what the screen owes the person, not the gate.

## Decide

Borrow one persona per case, and name it as `PERSONA:` — it changes the steps
you take and what you look at afterwards:

| Persona | What they do that a script never does | What they notice |
|---|---|---|
| **The first-timer** | Reads nothing; takes the wrong path first and backs out; leaves the required field for last | Does the screen say what happened and what to do next? An empty state with no words is a dead end |
| **The daily operator** | Keyboard only — Tab, Enter, muscle memory; relies on the default; does the same action twice expecting two records | A default that moved; a field that lost focus; the 2-second delay met 200 times a day |
| **The interrupted one** | Phone rings mid-form; returns after the session expired; same record in a second tab; Back after Save | Did half-done work survive? Do the two tabs now disagree? Did "session expired" eat the form? |
| **The one in hostile conditions** | Double-clicks Submit because nothing happened; refreshes mid-load; pastes `1.000,00`; autofill; 150% zoom | Did one click become two orders? Did the product degrade or fall over? |

## Rules

- **Every case's STEPS carries at least one real-user move** — Enter instead of
  Save · double-click Submit · Back after Save · refresh right after · the same
  record in a second tab · paste, not type (trailing space included) · type,
  delete, retype · Escape/click-outside on the modal · navigate away with
  unsaved changes · return via the email link · come back tomorrow · sort,
  filter, page, then edit. *Otherwise:* the case proves the route works, not
  that the product works for someone.
- **After every action, answer the four questions** — did it work (a visible
  confirmation naming what happened)? where am I now? can I undo it? did I lose
  anything (the filter, the draft, the other tab)? Write AFTER and BACK as those
  answers — all four, not one toast. *Otherwise:* the manifest says "Saved
  appeared" and the user's filter reset, work lost, nobody recorded it.
- **Whole-screen sanity is what a person sees wrong in three seconds**: the
  number in the header, the badge, the row in the list behind, the toast said
  the right thing once, the email carries the same numbers, the button states,
  the empty state has words, the label still names the right thing.
  *Otherwise:* "the page rendered" passes while the cart total is stale.
- **OBSERVATIONS are not verdicts — and not nothing.** The thing that made you
  say "hm" gets one more click and one line, no severity, no RESULT change, in
  the manifest and the report. *Otherwise:* the verification throws away half
  of what it saw, and the next ticket arrives pre-discovered and ignored.
- **The persona never overrides the oracle.** "A daily operator expects Enter
  to save" is a reason to press Enter — and a reason for a decision request if
  the spec is silent — never a reason to file a defect. *Otherwise:* taste
  becomes law and the report stops being trusted.

## Reviewer lens

- Pick two cases: name the real-user move in each. If none, the pack is scripts.
- Read AFTER/BACK of the write case: are all four questions answered, including "survives a reload"?
- Was anything observed but not judged — and recorded as such?

## Sources

connorpham/ai-qa `user-mindset.md` (personas, the moves table, the four
questions) · Ministry of Testing heuristics (interruptions) · vteam qa doctrine
"you are a person, not a route".

Rationalizations, red flags and a worked example live in `reference/qa-user-mindset.md` — opened when needed, never loaded by default.
