# VT-1: vteam adopts vteam — the framework runs under its own gates

- status: Done
- assignee: Connor Pham
- estimate: 0.5d
- labels: dogfood

## Why

The 2026-08-24 framework review found the biggest credibility hole was not in
the code: the repo that ships accountability machinery scored 62/C on its own
`audit` — no ledger, no evidence tree, no commit-anchored verdicts for its own
releases. A framework about proof-of-done must be an adopter of itself.

## Acceptance criteria (testable)

1. `vteam init` runs against this repo without clobbering the existing
   pre-push fence or hooksPath, and `doctor` is GREEN end to end.
2. The generic gate profile runs the repo's REAL suite: `.vteam/test.sh`
   executes `npm test` and `gate.sh` finishes green.
3. The dispatch ledger carries the release history with real dates, actor,
   tiers and `tok ≈` accounting, and `log_check` + `graph_check` are green.
4. `npx vteam-harness audit` on this repo scores ≥ 85 (was 62).

## Comments

### 2026-08-24 Connor Pham
claimed 2026-08-24T04:20:00Z · branch chore/self-install
