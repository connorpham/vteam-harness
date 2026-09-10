<!-- Reference detail for qa-case-writing. Moved out of the competency body so the
     lane spends its context on the ticket, not on the rulebook. The competency is
     the METHOD; this is the argument, the smell list and the worked case. -->

# qa-case-writing — rationalizations, red flags, example

> `/qa` opens this when a verdict is being argued, and at the challenger sign-
> off. Read the row that fits the change in front of you; never paste the whole
> file into a report.

## Rationalizations

| Excuse | Reality |
|---|---|
| "The screenshot shows everything." | In six months the screenshot shows a screen; the line says what mattered on it. |
| "Writing exact values is slow." | Arguing about an unreproducible FAIL is slower. |
| "The title is just a filename." | The title is the report row, the commit message, the sentence a manager quotes. |

## Red flags

- A title starting with "Test", "Check", "Verify".
- STEPS containing "verify that…" or "a valid value".
- EXPECTED without a citation; ACTUAL that says `failed`.
- Two different names for the same screen in one record.
