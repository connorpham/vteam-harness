# VT-37 · dev tasksheet — the graph computes the execution plan
CODE-SCOPE: src/cli/graph.mjs core/workflows/ tests/e2e.mjs .vteam/ .claude/ docs/team/ README.md docs/GUIDE.md CHANGELOG.md evd/VT-37/ docs/pm/ docs/backlog/

Branch `feat/VT-37-graph-plan` from main 2f12b06.

| T | Task | State |
|---|---|---|
| T1 | Measure every claim in the critique before writing code — three of four are false for this repo | done — proof.md §1 |
| T2 | `buildPlan`: Kahn waves, scope-disjoint batches under `team.parallel`, lane per item, in-flight exclusion, blocked list with reasons, critical path, upstream `read first` pointers | done |
| T3 | `readScopes`, `scopesOverlap`, `inFlightKeys`, `renderPlan`; `--plan` and `--plan --json` on the CLI | done |
| T4 | 12 selftest assertions + 5 e2e checks on a fresh install | done — 232/232 |
| T5 | /pm P1 and /team consume the plan; the plan prints what it does NOT decide | done |
| T6 | Six code-only mutations, tests kept | done — mutations.md |
| T7 | Gate GREEN, npm test, PR | done — proof.md §4 |

## Two bugs the tests caught while writing this, recorded rather than quietly fixed
- `scopesOverlap` compared raw strings, so `src/` and `src/auth/a.ts` read as disjoint — the pair that collides most often. It normalises both sides itself now instead of trusting the caller.
- The planner read cycles as plain arrays; the real model carries `{path, display}`, so `--plan` threw on any repo with a cycle — and a ticket inside a cycle would have been dispatchable if the throw had been swallowed. Both shapes are read now (M5 proves it bites).
