<!-- Reference detail for qa-hostile-inputs. Moved out of the competency body so the
     lane spends its context on the ticket, not on the rulebook. The competency is
     the METHOD; this is the argument, the smell list and the worked case. -->

# qa-hostile-inputs — rationalizations, red flags, example

> `/qa` opens this when a verdict is being argued, and at the challenger sign-
> off. Read the row that fits the change in front of you; never paste the whole
> file into a report.

## Rationalizations

| Excuse | Reality |
|---|---|
| "Nobody types emoji in a name field." | Every phone keyboard offers it before the letter E. |
| "The framework validates that." | The framework validates what it was configured to validate. That is the question. |
| "I'll paste the whole table into the plan." | Sweeping is not choosing — thirty untargeted values crowd out the three aimed ones. |
| "That value is unrealistic." | It was copied from a real support ticket. They all were. |

## Red flags

- A boundary case whose input the spec accepts.
- A pack where every typed value is ASCII, positive, and in the developer's locale.
- A money ticket with no rounding case; a date ticket with no boundary-day case.
- The same coupon/action never tried twice anywhere.
