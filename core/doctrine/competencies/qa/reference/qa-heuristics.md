<!-- Reference detail for qa-heuristics. Moved out of the competency body so the
     lane spends its context on the ticket, not on the rulebook. The competency is
     the METHOD; this is the argument, the smell list and the worked case. -->

# qa-heuristics — rationalizations, red flags, example

> `/qa` opens this when a verdict is being argued, and at the challenger sign-
> off. Read the row that fits the change in front of you; never paste the whole
> file into a report.

## Rationalizations

| Excuse | Reality |
|---|---|
| "No spec, so I can't report anything." | HICCUPPS gives eight oracles; a named inconsistency with an owner is a real result. |
| "Exploratory means poke around randomly." | It means one named heuristic, timeboxed, recorded — findings and blanks alike. |
| "I looked at the screen, it's consistent." | With which of the eight? Name it, or you looked at one. |

## Red flags

- "The spec doesn't cover this" written as a reason to skip, not to switch oracle.
- An exploratory case with no HEURISTIC name and no timebox.
- A value verified only on the screen where it was typed.
- A regression pack that regresses everything or nothing, ranked by neither.
