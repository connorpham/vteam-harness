# BDD report — the AI's account of its work, in words anyone can read

> Any lane MAY emit a `*.bdd.md` report under `evd/<TICKET>/`
> alongside its usual artifacts (the /dev 7-part comment, the /qa REPORT.md).
> `bdd_report_check` guards it. This is the human layer: a product owner reads it
> in a minute and knows exactly what happened, without a single line of code.

## The shape

One or more **Scenarios**, each a `Given / When / Then` in ordinary language:

```
## Scenario: <one plain sentence naming what this is about>
Given <the situation before — who, what state>
When <the single action taken>
Then <what a person can SEE afterwards — the observable outcome>
```

`And` / `But` continue the previous step. Keep code — file names, function calls,
SQL, routes — OUT of the scenarios; it lives in an appendix if it is needed at all.

## The two rules the gate holds

- **Complete.** Every scenario has all three of Given/When/Then, and the `Then`
  states something a person could watch happen — never "works", "OK", "passes",
  "as expected". If the only thing you can write is one of those, you have not
  said what actually happened.
- **Concise (đầy đủ nhưng không dài dòng).** A step is at most 30 words; a
  scenario is at most 15 lines. Longer means you are narrating, not reporting —
  split it or trim it. The report is scannable, not a wall of text.

## Good vs bad

**Bad** (rambling + code-speak + empty outcome):
```
## Scenario: discount
Given the user
When applyDiscount(cart) runs in src/checkout.ts and then the reducer updates and the API returns and a bunch of other things happen in sequence over several steps
Then it works
```

**Good** (a stranger understands it):
```
## Scenario: A member's code takes money off the total
Given a member has 500,000 ₫ of fruit in their cart
When they enter their discount code and press Pay
Then the total drops to 450,000 ₫ and the receipt shows a 50,000 ₫ saving
```

## Where the code goes

Selectors, queries, file paths, request/response bodies belong in an
`## Appendix (for technical readers)` section BELOW the scenarios, or in the
existing `cmd_verify.md` / `db_verify.md` — never inside a `Given/When/Then`.
The scenario is for the person deciding whether the work is done; the appendix is
for the engineer who has to reproduce it.
