<!-- Reference detail for qa-report-writing. Moved out of the competency body so the
     lane spends its context on the ticket, not on the rulebook. The competency is
     the METHOD; this is the argument, the smell list and the worked case. -->

# qa-report-writing — rationalizations, red flags, example

> `/qa` opens this when a verdict is being argued, and at the challenger sign-
> off. Read the row that fits the change in front of you; never paste the whole
> file into a report.

## Rationalizations

| Excuse | Reality |
|---|---|
| "The evidence folder speaks for itself." | Only if every file is named and the verdict shot is boxed. Otherwise it is a pile of screens. |
| "I'll note what I skipped if asked." | Unstated gaps are read as coverage; the gap becomes production's problem. |
| "PASS needs no evidence." | A PASS is worth the folder behind it. An unboxed full-page shot proves the address, not the product. |
| "The developer will understand the stack trace." | The product owner deciding whether to ship will not. Write for them. |

## Red flags

- A verdict stated in code terms ("null pointer in totals").
- A claim in the report with no file named behind it.
- Screenshots named `01.png`, `02.png`; a full-page shot with nothing boxed.
- No "what I could not check" section on a real verification.
