<!-- Reference detail for qa-requirement-smells. Moved out of the competency body so the
     lane spends its context on the ticket, not on the rulebook. The competency is
     the METHOD; this is the argument, the smell list and the worked case. -->

# qa-requirement-smells — rationalizations, red flags, example

> `/qa` opens this when a verdict is being argued, and at the challenger sign-
> off. Read the row that fits the change in front of you; never paste the whole
> file into a report.

## Rationalizations

| Excuse | Reality |
|---|---|
| "Everyone knows what 'valid email' means." | The product, the RFC and the login form disagree three ways. Which rule, written where? |
| "I'll test the clear parts first and ask later." | The unclear part decides the boundary case — you are testing around the requirement. |
| "Asking makes me look slow." | The ambiguity found after testing costs the day AND the retest, and looks slower. |

## Red flags

- Your verify sheet has zero questions on a ticket of any real size.
- An EXPECTED that paraphrases the ticket's own vague word ("shows an
  appropriate error").
- You inferred a rule from the code and wrote it as the expected value.
