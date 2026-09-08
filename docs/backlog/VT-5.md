# VT-5: `/team` parallel mode — PM coordinates N DEV agents in Orca worktrees

- status: In Progress
- assignee: Connor Pham
- estimate: 1d
- labels: workflow, no UI

## Why

Owner review 2026-09-08: `team.size=3` today does NOT fan out to 3 coders. Its
only real effects are the WIP-number prose, the board's per-person rollup, and
log_check's Actor column — while `pm.md` principle #3 hard-caps DEV at "one
coding item at a time — never 2 in parallel." Config implies a parallelism the
execution model forbids. The platform now ships the primitives that make true
fan-out honest: `Agent(isolation:"worktree")`, the `orchestration` skill, and
`EnterWorktree`. This ticket turns `/team` into a PM that runs up to
`team.parallel` DEV agents concurrently — each in its own worktree/branch on a
DISJOINT code scope — while keeping the two laws that make it safe:
**coding is parallel, integration is serialized, and the ledger + merges are the
PM's single hand.**

## Spec / oracle

`pm.md` principle #3 + #5 (one coding item / single-writer ledger),
`team.md` T2 (main track vs background lanes, the "way home" worktree rule),
`raci.md` §2 (transition rights), `graph_check.py` (CODE-SCOPE tracking, MAST
loop budget). Governing rule: spec §`pm.md` principle #3 (coding concurrency) and
#5 (single-writer ledger); the ledger law (`ops-247.md` §7) is preserved, not relaxed.

## Acceptance criteria (testable)

0. **Given** `team.parallel > 1` and two in-flight DEV branches whose CODE-SCOPE
   share a path, **When** `parallel_check.py` runs, **Then** it exits 1 naming
   the overlapping pair; **and Given** disjoint scopes, **Then** it exits 0.

1. **A new gate `parallel_check.py`** exists, wired into every stack profile and
   discovered by `doctor`. Given `team.parallel <= 1`, it is inert-green (the
   feature is opt-in). Given `team.parallel > 1` and two in-flight DEV branches
   whose CODE-SCOPE overlap, it exits 1 naming the pair; disjoint scopes and an
   over-cap count also red. `--selftest` proves each rule can go red.
2. **`pm.md` principle #3 rewritten**: DEV may run up to `team.parallel` agents
   concurrently, each in its own worktree on a disjoint CODE-SCOPE; INTEGRATION
   is serialized (one merge at a time, re-gate between); merges and the ledger
   stay the PM's single hand. The old "never 2 DEV in parallel" absolute is gone;
   the P1 UNBLOCKED test gains a "scope disjoint from every in-flight branch" leg.
3. **`team.md` T2 rewritten**: the main track becomes a coordinator that
   partitions unblocked tickets by disjoint scope, spawns `min(team.parallel,
   disjoint-tickets)` DEV worktree agents (Orca `isolation: worktree`), collects
   their PRs, merges serially re-gating between, and writes every ledger row
   itself. Background BA/SA lanes unchanged.
4. **Config knob `team.parallel`** (default 1) in the example config + `init`
   default + DESIGN §2 schema; `conformance`/`e2e` stay green; no unresolved
   `{vars}` in rendered workflows.
5. `gate.sh` GREEN end to end (incl. the new gate), `doctor` discovers the new
   selftest.

## Out of scope

- Auto-merging PRs without the owner at `autonomy < full` (unchanged policy).
- A tracker-side "assignee per agent" — actors stay per `VTEAM_ACTOR`.
- Changing review_check / evd_check thresholds.
- Implementing an Orca-specific driver; the workflow names the primitive, the
  agent tool provides it.

## Comments

### 2026-09-08 Connor Pham
claimed 2026-09-08T09:00:00Z · branch feat/VT-5-parallel-team
