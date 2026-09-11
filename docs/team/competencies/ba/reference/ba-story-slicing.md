<!-- Reference detail for ba-story-slicing. Moved out of the competency body so the
     lane spends its context on the ticket, not on the rulebook. The competency is
     the METHOD; this is the argument, the smell list and the worked case. -->

# ba-story-slicing — rationalizations, red flags, example

> `/ba` opens this at the challenger review in B3, and when scope is being
> negotiated. Read the row that fits the change in front of you; never paste the
> whole file into a report.

## Rationalizations

| Excuse | Reality |
|---|---|
| "The API has to come first." | Then narrow the input and ship one endpoint with the screen that uses it. |
| "It's one feature, it can't be split." | Name one rule, one role or one format you could ship without. There always is one. |
| "Splitting adds overhead." | So does discovering on day nine that the story was two weeks. |
| "We'll do errors in a follow-up." | Then the rule is not shipped, only the happy half of it. |

## Red flags

- Titles like "Build the admin panel", "Implement reporting", "Migrate the API".
- A pair of stories named "… (backend)" and "… (frontend)".
- A story whose criteria cover three roles or four states.
- A slice with no refusal criterion; a spike with no time box or question.
- A "foundation" or "setup" story with no user-visible outcome.
- A dependency recorded in one direction only.

## Example

"Members can manage their subscription" — a whole screen, a week or more. Wrong split:
"subscription API" plus "subscription UI" — neither can be shown. Right split, each
usable alone: **(1)** a member on a paid plan can **see** their current plan and next
billing date (narrowest complete path, one plan type); **(2)** a member can **cancel**,
with the refusal for an already-cancelled plan; **(3)** a member can **switch** plans,
monthly to annual only; **(4)** annual to monthly, which carries the pro-rata rule and
waits on decision Q-9. Slice 1 ships in a day and proves the data shape the rest needs.
