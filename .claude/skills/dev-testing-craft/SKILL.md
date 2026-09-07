---
name: dev-testing-craft
description: "Use when deciding which tests to write for a change, how to name and structure them, what data they use, and how deep to go — and when an existing test is flaky, asserts nothing meaningful, or breaks on every refactor."
---


# Testing craft — tests are the executable spec, written to fail first

## Identity

You write tests that a stranger can read as requirements, that fail for exactly
one reason, that never pass by accident, and that survive a refactor of the
implementation. You test behavior through the interface with realistic data;
you put the effort where a failure hurts most; you write the boundary pair for
every rule. A test that has never been red has proven nothing.

## When this applies

- Before implementing any behavior change (the test comes first).
- Choosing between unit, integration and end-to-end for a given check.
- Writing test names, fixtures, assertions.
- A test is flaky, slow, or asserts `toBeTruthy`.

## Decide

| Question | Choose | Because |
|---|---|---|
| Which level? | Unit for logic; integration (real DB/HTTP in-process) for wiring; e2e only for the few lifeline journeys | Cost rises 10× per level; confidence per test does not |
| How many, how deep? | Risk = probability × impact; P0 (money, auth, data loss) gets the boundary table and an e2e; P3 gets a smoke | Equal effort everywhere means too little where it matters |
| What to assert? | The observable outcome the spec names, with its exact value cited (`spec §3.2`, `schema Lot.status`) | Asserting internals couples the test to the implementation |
| Test data | Realistic values, generated per test, unique | `"foo"` never hits the length limit; shared fixtures couple tests |
| Boundary | Both sides: the last valid and the first invalid (`limit`, `limit+1`; `0`, `-1`; empty, one, many) | Off-by-one lives exactly there |
| Doubles | Fake at the seam (in-memory adapter); mock only what you cannot own (payment provider, clock) | Mocks of your own code test the mock |
| Flaky | Fix the nondeterminism (time, order, shared state, network) — never retry-until-green | Retries hide the bug the test found |

## Rules

- **Name = unit · scenario · expected**: *"topUp — when amount exceeds daily
  limit — rejects with LIMIT_EXCEEDED and leaves balance unchanged"*.
  *Otherwise:* a red CI says "test 14 failed" and nobody knows what broke.
- **AAA, visibly**: Arrange, Act, Assert; one act per test; assertions in the
  test body, not hidden in a helper. *Otherwise:* the reader cannot tell what is
  being claimed.
- **Red first, for the right reason.** Run it; read the failure; only then make
  it green. *Otherwise:* a test that passed immediately may be testing nothing.
- **Black-box through the public interface.** *Otherwise:* every refactor
  breaks tests that were never about behavior.
- **Every rule gets its boundary pair; every write gets a read-back**, ideally
  through a different path (API write, DB read). *Otherwise:* the write "succeeds"
  and persists nothing.
- **Determinism**: no sleeps, no wall clock, no test-order dependence, no
  conditionals in the test body. *Otherwise:* the suite becomes a coin flip and
  gets ignored.
- **Isolation**: each test creates what it needs and cleans up; parallel-safe.
  *Otherwise:* a green suite locally is red in CI, or vice versa.
- **Don't test the framework or the mock.** *Otherwise:* thousands of lines of
  false confidence.

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

## Reviewer lens

- For each rule in the spec touched by the diff: where is the pair (last valid, first invalid)?
- Flip one condition in the implementation; which test reds? None → say so.
- Any assertion that would pass for a wrong answer? Any test that never ran red?

## Sources

goldbergyoni/javascript-testing-best-practices (3-part names, AAA, black-box,
realistic data) · BMAD TEA test-quality standards (determinism, isolation,
explicit assertions) and risk-based P0–P3 · obra/superpowers
`test-driven-development` (red first, rationalizations).
