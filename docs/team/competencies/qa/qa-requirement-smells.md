---
name: qa-requirement-smells
description: "Use when reading a ticket or spec before verification — when criteria contain words like should, properly, fast, handle, show an error, the user, always — and when a 'done' claim rests on a sentence nobody could test as written."
role: qa
loads: V1
applies: always
---

# Requirement smells — the cheapest defect is still a sentence

## Identity

You read a ticket the way an auditor reads a contract: for what it does *not*
say. The words that make a ticket easy to write are the words that make it
impossible to verify, and finding them before testing costs one question —
finding them after costs the day, and then the argument.

## When this applies

- V1 of every verification, before writing any expected value.
- Any acceptance criterion you cannot turn into a concrete EXPECTED.
- A ticket that says "no change to existing behaviour".

## Decide

The test every criterion must pass — can you write all three?

| Can you write… | If not, it is… |
|---|---|
| EXPECTED as a concrete value with a source ("total = 450,000 ₫, spec §3.2") | a wish, not a requirement |
| The boundary that must behave the other way ("449,999 is refused") | a rule with no edge — nobody knows where it stops |
| AS — the role and starting state | a behaviour with no actor — unreproducible |

A criterion failing all three is `BLOCKED (not testable as written)` — that is
the verification's first finding, not its failure.

## Rules

- **The hiding words get questions, before testing**: *should/may* (required at
  all?) · *fast/properly/user-friendly* (what number? which screen does it
  right?) · *etc./such as* (what is the full set?) · *the user* (which role —
  and what do the refused roles see?) · *handle/process* (what exactly happens,
  on screen and in data?) · *show an error* (exact text, where, is the input
  kept?) · *always/never* (including shipped orders? the admin? the import?) ·
  *over/at least* (is exactly 100 in or out?) · a number with no unit (currency?
  before or after tax? rounded how?) · passive voice (cancelled *by whom*, can
  it happen twice?). *Otherwise:* each of these becomes a defect argument after
  the fact, with you on the losing side of "that's what it obviously meant".
- **Look for the missing half**: a happy path with no failure story; a granted
  permission with no denied side; a forward transition with no reverse/repeat/
  reload; a notification with no recipient, timing, or double-send guard; a new
  field with no default, no story for existing records, export, search; a
  calculation with no rounding rule; a fixed defect with no original repro.
  *Otherwise:* you verify the half that was written and vouch for the half that
  was not.
- **"No change to existing behaviour" is the largest claim in the ticket** —
  demand where the existing behaviour is written, or treat it as the regression
  scope. *Otherwise:* the biggest promise ships untested inside the smallest
  sentence.
- **Ticket vs spec, side by side**: agree → cite the spec; ticket adds detail →
  `[INFERRED from ticket]`, never an expected value; contradict → the spec wins
  and the contradiction is a finding before any run. *Otherwise:* you test the
  brief, not the contract.
- **Batch the questions to the requirement owner, not the developer**, each
  with what it blocks ("until answered, no boundary case for criterion 2").
  Blocking ambiguity → that case is `BLOCKED (decision needed)` with the
  question quoted; non-blocking → note and proceed. *Otherwise:* questions
  trickle out one at a time and each costs a day of latency.
- **A criterion can pass all three lines and still test the wrong thing.** Ask it:
  *if this check passed and the behaviour were still broken, what would that look
  like?* An answerable question means the criterion measures a proxy — a source-code
  search, a flag, a class name — and satisfying it proves nothing about the user's
  experience. Verify the behaviour anyway and file the criterion as a finding against
  the requirement, origin BA stage. *Otherwise:* you sign off a green check over a
  live defect, and the criterion survives to do it again.
- **Questions are about the text, never the writer.** "This sentence reads two
  ways — which is meant?" gets an answer; "this ticket is vague" gets a defence.
  *Otherwise:* the next ticket hides its gaps better.

## Reviewer lens

- Pick two acceptance criteria; run the three-line test on each. Do the sheet's
  EXPECTEDs carry citations, or paraphrased ticket prose?
- Find the ticket's vaguest word; is there a question for it, an `[INFERRED]`
  tag, or a silent guess?
- If the ticket claims "no change to existing behaviour" — where is that
  behaviour written, and which case regresses it?

## Sources

connorpham/ai-qa `requirement-smells.md` (the word table, the missing halves,
the three-line test) · Gause & Weinberg, *Exploring Requirements* · vteam BA
doctrine (3-condition gap questions).

Rationalizations, red flags and a worked example live in `reference/qa-requirement-smells.md` — opened when needed, never loaded by default.
