<!-- Reference detail for qa-user-mindset. Moved out of the competency body so the
     lane spends its context on the ticket, not on the rulebook. The competency is
     the METHOD; this is the argument, the smell list and the worked case. -->

# qa-user-mindset — rationalizations, red flags, example

> `/qa` opens this when a verdict is being argued, and at the challenger sign-
> off. Read the row that fits the change in front of you; never paste the whole
> file into a report.

## Rationalizations

| Excuse | Reality |
|---|---|
| "Double-click is user error." | It is the single most expensive defect class in commerce: two payments. |
| "Nobody leaves a form open overnight." | Everyone does. The session expiry path IS a main path. |
| "Autofill is the browser's problem." | The values landed in your fields. The wrong-field email is your bug report. |
| "I'll test the persona stuff if time remains." | It is not extra cases — it is one move inside the steps you already run. |

## Red flags

- Every STEPS line uses the mouse, in the intended order, with typed-perfect values.
- AFTER says only "toast appeared".
- No case presses Back, refreshes, or opens a second tab.
- The manifest has no PERSONA and no OBSERVATIONS anywhere in the pack.
