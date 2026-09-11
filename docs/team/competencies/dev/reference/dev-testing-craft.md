<!-- Reference detail for dev-testing-craft. Moved out of the competency body so the
     lane spends its context on the ticket, not on the rulebook. The competency is
     the METHOD; this is the argument, the smell list and the worked case. -->

# dev-testing-craft — rationalizations, red flags, example

> `/dev` opens this at the review step, and whenever an excuse for skipping a
> rule appears. Read the row that fits the change in front of you; never paste
> the whole file into a report.

## Rationalizations

| Excuse | Reality |
|---|---|
| "Too simple to test." | Simple code breaks; the test takes 40 seconds. |
| "I tested it manually." | Unrepeatable and unrecorded; gone with the session. |
| "I'll write the tests after." | They will pass immediately and prove nothing. |
| "Mocking the repository is easier." | You are testing that the mock returns what you told it to. |
| "Coverage is 90%." | Coverage measures execution, not assertion. Mutate a line; did anything red? |

## Red flags

- `expect(result).toBeTruthy()` / `toBeDefined()` as the only assertion.
- A test with `sleep`, `setTimeout`, or `Date.now()`.
- A test file that mirrors the implementation's structure line for line.
- Green on the first run of a new test.
- A boundary tested on one side only.

## Example

```ts
describe("Wallet.topUp", () => {
  it("when amount equals the daily limit, accepts and balance increases by amount (spec §4.1)", …);
  it("when amount exceeds the daily limit by 1, rejects LIMIT_EXCEEDED and balance is unchanged (spec §4.1)", …);
  it("when two top-ups run concurrently, balance reflects both (spec §4.3 atomicity)", …);
});
```
