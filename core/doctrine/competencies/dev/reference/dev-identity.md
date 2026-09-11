<!-- Reference detail for dev-identity. Moved out of the competency body so the
     lane spends its context on the ticket, not on the rulebook. The competency is
     the METHOD; this is the argument, the smell list and the worked case. -->

# dev-identity — rationalizations, red flags, example

> `/dev` opens this at the review step, and whenever an excuse for skipping a
> rule appears. Read the row that fits the change in front of you; never paste
> the whole file into a report.

## Rationalizations

| Excuse | Reality |
|---|---|
| "It's a small change, I don't need the task-sheet." | Small changes ship most regressions; the sheet takes four minutes. |
| "I'll clean this up in a follow-up." | There is no follow-up ticket. Either it belongs here or it belongs in a side finding. |
| "The spec obviously means X." | Obvious to you is a guess to the gate. Ask. |
| "Tests slow me down on this one." | You are about to spend that time twice in review. |

## Red flags — stop and re-read this file

- You are typing a field, enum or route name without the schema open.
- The diff touches a file the task-sheet did not list.
- You wrote "should", "probably" or "seems to" about behavior you can run.
- You are explaining why a failing check is acceptable.
