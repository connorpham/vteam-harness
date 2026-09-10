---
name: qa-combinatorial-design
description: "Use when a feature has several independent inputs and the honest combination count is too large to run — roles by plans by locales, payment method by currency by coupon, OS by browser by network by font scale. Also when deciding which tier a test belongs in, and when a suite is red often enough that people re-run it instead of reading it."
---



# Combinatorial design — choosing the case count, and defending the number

## Identity

You never answer "how many cases?" with the exhaustive count or a number you felt
like. You count the combinations, pick a strength you can justify, generate the set,
and have a machine prove it covers what you claimed. A test at the wrong tier is a
liability, and a suite that gets re-run rather than read has stopped being a test.

## When this applies

- Two or more inputs vary independently and their product is large.
- A platform or compatibility matrix must be tested on a budget.
- A decision has several boolean conditions and an outcome table.
- Someone proposes "test all combinations" or only the happy path.
- A test's tier has not been argued, or the suite fails intermittently.

## Decide

| Question | Choose | Because |
|---|---|---|
| Interaction strength | **2-way (pairwise)** by default; 3-way+ on paths that move money, grant access or delete data | NIST, verbatim: *"most failures were caused by one or two parameters, with progressively fewer by three or more"* |
| Upper bound to consider | **4-way to 6-way** | NIST, verbatim: in multiple case studies *"4-way to 6-way combination coverage was able to detect all faults found with exhaustive testing"* |
| Whether pairwise is "enough" | Never claim it is — state the strength and the escalated paths | The quoted "pairwise finds 80–93% of faults" figures are secondary and could not be confirmed in NIST primary sources |
| Ordered numeric or date range | Boundary values; say **2-value** or **3-value**, and match the increment to the data type (0.01 for money) | 2-value = boundary plus one outside (`99,100`); 3-value adds one inside (`99,100,101`) |
| Boolean conditions to outcomes | A **decision table**; collapse rules with identical actions using "don't care" | n conditions give 2ⁿ rules; collapsing is how 4 becomes 3 without losing a case |
| Which tier a test goes in | The **cheapest tier that can hold the assertion** | Fowler: *"Push your tests as far down the test pyramid as you can"* |
| Suite fails intermittently | Measure **your own** flake rate: run it **10×** with no code change | Published figures for large codebases are motivation; your number is the evidence |
| A flaky test blocking CI today | Quarantine to a non-blocking suite with a one-sprint deadline to fix or **delete** | A permanent quarantine is a deleted test that still costs time |

## Rules

- **Count the exhaustive product and write it down before choosing anything.**
  *Otherwise:* you cannot say what you cut, so nobody can judge the risk.
- **Name the coverage strength in the plan: "2-way, all pairs covered".**
  *Otherwise:* "we tested the combinations" is unfalsifiable.
- **Have a tool prove the coverage, not a person**, and exclude impossible
  combinations with an explicit constraint. *Otherwise:* a hand-built matrix silently
  misses pairs, or the generator spends cases on unreachable states.
- **Pairwise does not replace boundary analysis — run both.** Pairwise covers
  interaction; boundaries cover edges. *Otherwise:* you test 16 tidy combinations and
  never send `max+1`.
- **Escalate strength on paths that move money, grant access or delete data.**
  *Otherwise:* a partial technique met a total requirement.
- **Argue the tier for every new test in the PR.** *Otherwise:* the suite drifts into
  an ice-cream cone and every run costs minutes for coverage a unit test could hold.
- **Test observable behaviour, not internal calls.** *Otherwise:* the test breaks on
  every refactor and proves nothing.
- **Measure flake rate before debating it, and quote your number.** *Otherwise:* the
  argument is about vibes and the fix is "re-run".
- **Fix the non-determinism, not the symptom** — classify by root cause: timing,
  network, state pollution, order dependence, contention. *Otherwise:* you add a
  longer `sleep` and move on.

## Rationalizations

| Excuse | Reality |
|---|---|
| "We'll test all the combinations." | Five inputs of 3–4 values is 108–1024 runs. You will not, so decide deliberately. |
| "We'll just test the main flow." | That is 1-way coverage, and NIST puts most of the fault mass at two. |
| "It only fails sometimes." | In large suites most pass→fail transitions are flake, so intermittent red destroys your signal. |
| "Just re-run the pipeline." | You have replaced a test suite with a coin toss. |

## Red flags

- A case count with no stated strength; a matrix maintained by hand.
- Boundary cases absent from a plan that has combination cases, or the reverse.
- A decision table with 2ⁿ rules and no collapsing.
- "Re-run" appearing in a CI discussion more than once.
- A quarantine list with no dates; `sleep` as synchronization; new e2e tests for logic a unit test could assert.

## Example

Ticket: "role, plan and locale all affect the billing screen" — 4 × 4 × 4. Wrong: run
the three the developer mentioned, or ask for 64 runs. Right: state the exhaustive
count (64), choose 2-way, generate an all-pairs set and verify it — **16 cases covering
100% of the 48 required pairs**, machine-checked. A 3×3×3×2×2 payment form collapses to
13. Then add boundary cases for the amount (`0`, `0.01`, `max`, `max+0.01`) and
escalate "downgrade a paid plan" to 3-way because it moves money. The plan now names a
number, a strength and a proof.

## Reviewer lens

- What is the exhaustive combination count, and what strength was chosen?
- What proves the set covers that strength — a tool, or a person's word?
- Are impossible combinations excluded by an explicit constraint?
- Do boundary cases exist alongside the combination cases?
- Which paths were escalated above 2-way, and why those?
- For each new test: why this tier and not one lower?
- What is the current flake rate, and how was it measured?

## Sources

NIST CSRC "Interactions Involved in Software Failures" — two statements verified
verbatim against the primary page. The repeated "93% of NASA failures were 2-way" and
"pairwise finds ~80%" figures were checked in NIST primary sources and could **not**
be confirmed, so nothing here rests on them. Martin Fowler, *The Practical Test
Pyramid* — tier rules quoted verbatim. ISTQB definitions for equivalence partitioning,
2-value vs 3-value BVA and decision tables. Flake figures come from secondary
literature, hence the rule to measure your own. All-pairs generation implemented and
machine-verified. Complements `qa-test-design` and `qa-hostile-inputs`, which cover
boundaries and hostile values but not combinatorial strength, decision tables or
tier choice.
