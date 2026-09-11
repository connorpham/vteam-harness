<!-- Reference detail for ba-acceptance-criteria. Moved out of the competency body so the
     lane spends its context on the ticket, not on the rulebook. The competency is
     the METHOD; this is the argument, the smell list and the worked case. -->

# ba-acceptance-criteria — rationalizations, red flags, example

> `/ba` opens this at the challenger review in B3, and when scope is being
> negotiated. Read the row that fits the change in front of you; never paste the
> whole file into a report.

## Rationalizations

| Excuse | Reality |
|---|---|
| "The dev knows what I mean." | The tester does not, and neither will you in three weeks. |
| "It's obviously in scope." | Then write it down; obvious things are what teams argue about. |
| "The spec doesn't say, so I used the sensible rule." | You just authored a requirement nobody approved. |

## Red flags

- "correctly", "properly", "as expected", "handles", "fast", "user-friendly".
- A `Then` containing "and", or a criterion listing several outcomes.
- A criterion naming a button or screen; a rule with no rejected value and no message.
- A non-functional criterion with no number or no load.
- Any criterion with no spec reference on a story whose spec exists.

## Example

Weak: "The system handles invalid orders correctly." Nothing there can fail.
Strong, split into two: **(1)** *Given* a member with an empty cart, *When* they submit
the order, *Then* the order is refused and the response says "Add at least one item"
— spec §4.2. **(2)** *Given* a member whose cart total is 0 ₫ with one free item,
*When* they submit, *Then* the order is accepted with `total = 0 ₫` — spec §4.2, and
this is the boundary that must behave the other way. Out of scope: partial refunds
(no decision yet, Q-14).
