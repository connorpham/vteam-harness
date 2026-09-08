# VT-7: /team parallel uses Orca orchestration as the real coordination transport

- status: In Progress
- assignee: Connor Pham
- estimate: 0.5d
- labels: workflow, no UI

## Why

VT-5/VT-6 gave `/team` parallel mode the RULES and the GATES (parallel_check,
coord_check) but named `SendMessage`/`ListAgents` as the transport — which is
DISABLED for spawned subagents in practice (proven 2026-09-08: agents got
"ListAgents disabled … no agent reachable"). The Orca `orchestration` bus was
tested and WORKS (run/task/send/check/ack — a real persistent, addressable
mailbox). This ticket wires the parallel path to that real transport: the PM
creates a Run, launches each DEV agent as an Orca worker bound to it, agents
coordinate through the Run mailbox, and the PM waits on `worker_done`. The two
guards stay: parallel_check (disjoint file scope) and coord_check (handoffs
become real scope). Tool-neutral fallback preserved for tools without a bus.

## Spec / oracle

Governing rule: spec §`team.md` parallel-DEV section (VT-5/VT-6) + the Orca
orchestration guide (`orca skills get orchestration`) as the transport reference.
`coord_check`/`parallel_check` are unchanged and remain the arbiters; the ledger
+ merges stay the PM's single hand (`pm.md` #5).

## Acceptance criteria (testable)

0. **Given** a repo with Orca running, **When** `bash .vteam/scripts/orca_team.sh status`
   runs, **Then** it reports the transport reachable and exits 0; **and Given**
   Orca absent, **Then** it prints the neutral fallback (agents return text to the
   PM) and exits 0 — never a hard crash.
1. `orca_team.sh` helper: resolves the Orca CLI per the skill rules; `status`
   (transport up?), `open-run <objective>` (create Run + ensure coordination.md),
   `wait <run>` (wrap `check --wait` for worker_done/ask). Degrades cleanly when
   Orca is absent. It is a TOOL, not a gate (no selftest, not counted).
2. `core/doctrine/parallel-transport.md` documents the tested flow (CLI resolve →
   run-create → per-agent worker-start bound to the Run → check --wait → reply →
   worker_done → serial merge) + the non-Orca fallback + how it maps to
   coord_check/parallel_check.
3. `team.md` + `pm.md` parallel-DEV text points at the transport doctrine and the
   Run-mailbox model instead of the disabled ListAgents/SendMessage path.
4. `gate.sh` GREEN; conformance/e2e green; no unresolved `{vars}`; a REAL run of
   `orca_team.sh status` + `open-run` recorded in evidence.

## Out of scope

- New gate (transport is runtime; coord_check/parallel_check already arbitrate).
- Forcing Orca on non-Claude tools — the fallback stays.
- Auto-merge policy / review thresholds.

## Comments

### 2026-09-08 Connor Pham
claimed 2026-09-08T15:30:00Z · branch feat/VT-7-orca-transport
