# VT-33 · dev tasksheet — measure the doctrine a lane loads at start
CODE-SCOPE: core/scripts/context_budget.py core/scripts/gate.py profiles/ .vteam/ tests/e2e.mjs README.md docs/GUIDE.md CHANGELOG.md evd/VT-33/ docs/pm/ docs/backlog/

Branch `feat/VT-33-context-budget` from main d58433e.

## Plan
| T | Task | State |
|---|---|---|
| T1 | `core/scripts/context_budget.py`: resolve the lane skill, classify referenced files (mandatory: skill, role, identity, INDEX, INDEX `always` rows; on demand: the rest), bytes + ≈tokens, budget compare, `--json`, exit 0 | done |
| T2 | `--selftest`: temp repo with a fake skill (existing + missing file, INDEX with one `always` and one conditional row, repeat reference), tiny budget → over-budget line, json, unknown lane → exit 2 | done |
| T3 | Advisory step `context-budget` after `competencies` in all six `profiles/*/gates.yaml`; `gate.py` BOOKKEEPING gains it | done |
| T4 | e2e §5b: the step RAN on a fresh install and printed a lane total; README 35 → 36 selftests, 214 → 216 checks | done |
| T5 | Measure this repo, paste the table into the ticket and proof | done — docs/backlog/VT-33.md "Measured 2026-09-18" |
| T6 | Mutations M1–M3 (code-only, test kept) | see proof.md §3 |
| T7 | `vteam update` (mirror + manifest), doctor 36 selftests, gate GREEN, npm test, PR | see proof.md §4 |

## Competencies
dev-testing-craft (a measurement tool needs a fixture that can go red), dev-codebase-design (one
script, one home under core/scripts, mirrored like its siblings).

## Decisions taken without the owner (recorded, reversible)
- "Mandatory" is defined structurally (role / identity / INDEX / INDEX `always`), not by parsing
  prose like "read … first" — deterministic and explainable; pm's `roles/sa.md` therefore counts as
  mandatory although the skill reads it only at the SA step. Stated in the docstring.
- Tokens ≈ bytes / 4, the same rule for every lane; the tool says so on every run.
- The SessionStart hook output is not counted (a few lines; stated in the docstring).
