---
name: dev-debugging
description: "Use when a test, gate, build or user report says something is broken and the cause is not yet proven — especially under time pressure, when the fix 'looks obvious', or after a second attempt has already failed."
role: dev
loads: T3
applies: type:Bug, label:bug, label:reopen, term:regression, term:flaky
---

# Debugging — no fix without a reproduced root cause

## Identity

You do not guess. You build a feedback loop that shows the failure on demand,
you shrink the scenario until the cause is the only thing left, you form one
falsifiable hypothesis at a time, and you fix the cause — then you prove the
loop is green *and* that you understand why. Three failed fixes is a signal
that the problem is architectural, not a reason to try a fourth.

## When this applies

- A red test, gate, CI job or `--selftest`.
- A bug ticket or a `reopen` label from QA.
- "It works on my machine" in any form.
- Any fix you are about to apply without having watched the failure happen.

## Decide

| Signal | Do | Not |
|---|---|---|
| No reproduction yet | Build the loop first: failing unit test > script > curl > headed browser, in that order of preference | Read code and theorize |
| Flaky | Raise the reproduction rate (loop 50×, add load, fix the seed) until it is reliable | Re-run until green |
| Multiple components | Instrument each boundary; find the first one where data is wrong | Change the component you suspect |
| Fix "obviously" known | Write the failing test first, then the fix, watch it go green | Apply the fix, then look for a test |
| Two fixes failed | Stop. Question the architecture or the assumption; write it down; ask | Try variation three |
| Bug is in a dependency | Pin, patch or wrap with a test that proves the workaround | Upgrade and hope |

## Rules

- **Read the whole error.** Message, stack, the line above it, the first
  occurrence in the log — not the last. *Otherwise:* you fix the symptom the
  second error describes, not the cause the first one named.
- **Reproduce before you touch anything.** A red test that reds for the *right
  reason*, or a command with output. *Otherwise:* you cannot know your fix did
  anything.
- **Minimize.** Remove one element at a time until removing anything else makes
  it pass. *Otherwise:* the fix lands in the wrong layer and holds by accident.
- **Check what changed.** `git log -p` on the touched paths, dependency updates,
  config, data. *Otherwise:* you rediscover a change your teammate can name in
  ten seconds.
- **One hypothesis, one variable, one prediction**: "if X, then adding this log
  shows Y". Then test it. *Otherwise:* two changes at once and you cannot say
  which one mattered.
- **The regression test is written before the fix and fails before the fix.**
  *Otherwise:* a test written after passes trivially and proves nothing.
- **Fix the cause, not the site.** If the bad value came from three functions
  up, fix it there. *Otherwise:* the same bad value hits the next consumer.
- **Clean up instrumentation; keep the lesson.** Temporary logs out, test in,
  one line in the knowledge base if the lens was new. *Otherwise:* debug noise
  ships and the next engineer starts from zero.

## Rationalizations

| Excuse | Reality |
|---|---|
| "Quick fix now, investigate later." | Later never comes; the quick fix becomes load-bearing. |
| "Let me just try changing X." | Without a prediction you learn nothing whether it passes or fails. |
| "It's obviously the cache." | Obvious is a hypothesis. Show the stale value. |
| "The test is flaky, skip it." | Flaky is a bug with a low reproduction rate. Raise the rate. |
| "I've spent two hours, one more try." | Two hours of trying is the signal to stop and restate the problem. |

## Red flags

- You are editing code and no test or command is red.
- A fix that adds `try/catch`, a null check, or `?.` where a value was guaranteed.
- A fix that edits the assertion.
- A third attempt at the same area in one session.
- "Cannot reproduce, closing."

## Example

QA reopens: "balance wrong after two quick top-ups". Loop: a unit test firing
two `topUp` calls concurrently against one wallet — red (balance +10 instead of
+20). Minimize: one call → green; two sequential → green; two concurrent → red.
Hypothesis: read-modify-write outside a transaction. Instrument: log the read
value in each call → both read 0. Fix: `UPDATE … SET balance = balance + $1`
inside the transaction; test green; sequential and single still green.

## Reviewer lens

- Where is the failing test/command that reproduced the bug, and its red output?
- Does the fix change the cause or the symptom's neighborhood?
- Was anything else "tidied" in the same diff?

## Sources

obra/superpowers `systematic-debugging` (four phases, iron law, red flags) ·
mattpocock/skills `diagnosing-bugs` (feedback loop first, minimize, falsifiable
hypotheses) · Zeller, *Why Programs Fail* (delta debugging).
