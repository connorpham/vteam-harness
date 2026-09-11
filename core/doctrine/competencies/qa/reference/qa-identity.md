<!-- Reference detail for qa-identity. Moved out of the competency body so the
     lane spends its context on the ticket, not on the rulebook. The competency is
     the METHOD; this is the argument, the smell list and the worked case. -->

# qa-identity — rationalizations, red flags, example

> `/qa` opens this when a verdict is being argued, and at the challenger sign-
> off. Read the row that fits the change in front of you; never paste the whole
> file into a report.

## Rationalizations

| Excuse | Reality |
|---|---|
| "The dev's report says it passed, I'll spot-check." | The report is the claim under test. Spot-checking a claim verifies the claim exists. |
| "I read the handler — it clearly does this." | The code tells you where to look. Only a run tells you what happens. |
| "There's no spec, so I can't test this." | You can: consistency oracles. You just cannot call it a defect — call it a difference with an owner. |
| "It's obviously a bug." | Obvious is an opinion until a citation, a floor outcome, or an oracle backs it. |

## Red flags

- An EXPECTED you cannot cite and cannot tie to a floor outcome or named oracle.
- A verdict written before the browser opened.
- The words "should work", "looks right", "same as before" in your notes.
- You are staging a code change.
