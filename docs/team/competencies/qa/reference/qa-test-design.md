<!-- Reference detail for qa-test-design. Moved out of the competency body so the
     lane spends its context on the ticket, not on the rulebook. The competency is
     the METHOD; this is the argument, the smell list and the worked case. -->

# qa-test-design — rationalizations, red flags, example

> `/qa` opens this when a verdict is being argued, and at the challenger sign-
> off. Read the row that fits the change in front of you; never paste the whole
> file into a report.

## Rationalizations

| Excuse | Reality |
|---|---|
| "More cases = more coverage." | Ten valid emails test one thing ten times. Coverage is classes and consequences, not count. |
| "The dev already tested the boundary." | The dev's tests are part of the claim. Yours are the check on it. |
| "Exploratory is unstructured, skip it." | It is one named heuristic with a timebox and a written record — the only slot that can find the unknown unknown. |
| "This ticket doesn't touch money." | It touches the order form. Follow the total anyway; that is one case. |

## Red flags

- Five cases, five valid inputs.
- A "boundary" case whose input the spec accepts.
- A lifecycle ticket with no illegal-transition case.
- A pack for an auth/roles/money ticket with no ⑥.
- No case reads data back after a write.
