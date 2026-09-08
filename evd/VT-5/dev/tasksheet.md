# VT-5 task-sheet — /team parallel mode

CODE-SCOPE: core/scripts/parallel_check.py core/workflows/pm.md core/workflows/team.md profiles/ core/scripts/gate.py vteam.config.yaml core/templates/vteam.config.example.yaml src/cli/init.mjs docs/DESIGN.md README.md docs/backlog/VT-5.md docs/pm/log.md docs/team/ .claude/skills/ .vteam/ evd/VT-5/

Competencies: dev-identity · dev-codebase-design · dev-testing-craft (workflow/doctrine + one Python gate; no data/API/stack rows match).

## Requirement

Make `team.parallel > 1` fan out to N DEV agents in their own worktrees on
DISJOINT scopes, PM-coordinated, integration serialized — without breaking the
single-writer ledger or the sequential gates. Close the config-vs-execution
contradiction the owner found (size=3 didn't fan out).

## Design (why this shape)

The two laws that make parallel safe: (1) code in parallel worktrees, (2)
serialize the MERGE + ledger under the PM's single hand. `parallel_check` is the
new machine that makes "disjoint scope" red-able — it reuses the CODE-SCOPE line
/dev already writes (graph_check reads it too) as the collision oracle. The gate
is opt-in-safe: inert-green at `team.parallel: 1` so it never spuriously reds a
sequential repo (this one included).

## AC → proof

| AC | Proof |
|---|---|
| 0/1 overlap→exit1, disjoint→exit0, inert when off | cmd_probe.md (selftest + live: off=green, parallel=2 with 4 real branches → red naming pairs + over-cap + missing-scope) |
| 2 pm.md principle #3 rewritten + P1 leg (g) | core/workflows/pm.md diff (rendered .claude/skills/pm) |
| 3 team.md T2 coordinator + serialized integration | core/workflows/team.md diff (rendered .claude/skills/team) |
| 4 team.parallel knob (config+init+example+DESIGN §2); conformance/e2e green; no {vars} | cmd_verify.md |
| 5 gate.sh GREEN incl. new gate; doctor discovers 27 | cmd_verify.md |

## Self-review (T4a)

- parallel_check core (parse/paths_touch/scopes_overlap/find_conflicts) is pure
  and selftested; discovery (git branches + tasksheet CODE-SCOPE) is best-effort
  and only runs when parallel>1. Removed a dead duplicate discovery function
  (deletion test) before finalizing.
- gate.py BOOKKEEPING set extended with "parallel" so a bookkeeping-only run
  still reports WEAK honestly.
- DESIGN §7 "Still prose, not gates" corrected — parallel is now a gate; the TTL
  and self-merge-review lines stay prose (accurate).
- team.size KEPT as headcount for actor accounting; team.parallel is the new
  concurrency knob — decoupled on purpose (surprising to overload size).

## Side findings

- SF-1 README intro said "14 machine gates" while the table said 15 — pre-existing
  drift from the 0.16.0 competency merge; fixed to 16 here.
- SF-2 the Orca `isolation:"worktree"` / orchestration primitives are named in the
  workflow but no Orca-specific driver is shipped (out of scope, by AC).
- SF-3 T4b two-agent review of THIS diff not yet run in this session.
