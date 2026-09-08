# VT-7 task-sheet — /team parallel uses Orca orchestration as transport

CODE-SCOPE: core/scripts/orca_team.sh core/scripts/parallel_check.py core/scripts/coord_check.py core/doctrine/parallel-transport.md core/workflows/team.md core/workflows/pm.md docs/backlog/VT-7.md docs/pm/log.md docs/team/ .claude/skills/ .vteam/ evd/VT-7/

> SCOPE widened deliberately (graph_check MAST 2.3): the combined VT-5+VT-6+VT-7
> review found 2 CONFIRMED defects in the VT-5/VT-6 gate files
> (`parallel_check.py`, `coord_check.py`); fixing them here is correct — the
> review covered all three tickets together — so those two paths are added to
> this ticket's scope rather than left as a stray cross-ticket edit.

Competencies: dev-identity · dev-codebase-design (a shell tool + doctrine + workflow wiring; no gate change).

## Requirement

Wire /team parallel to the transport that actually works (Orca orchestration
bus), off the disabled ListAgents/SendMessage path. Keep the guards (parallel_check,
coord_check) and the fallback for non-Orca tools.

## AC → proof

| AC | Proof |
|---|---|
| 0/1 orca_team.sh status/open-run/wait; degrades clean | cmd_verify.md — real runs: status reachable, open-run created run_f2216d7b3740 + ensured coordination.md |
| 2 parallel-transport.md doctrine (flow + fallback + CLI resolve + maps to gates) | core/doctrine/parallel-transport.md (rendered docs/team/) |
| 3 team.md + pm.md point at the transport, off ListAgents/SendMessage | core/workflows/team.md T2 + coord subsection; core/workflows/pm.md DEV dispatch |
| 4 gate.sh GREEN; no {vars}; real helper run recorded | cmd_verify.md |

## Self-review (T4a)

- orca_team.sh is a TOOL not a gate (no --selftest; not counted) — like
  annotate.py/code_map.py. Resolves the Orca CLI per the orchestration skill's
  rules (never bare `orca` on Linux). Degrades to the text-relay fallback and
  exit 0 when Orca is absent — never a hard crash on repos without Orca.
- No new gate: the transport is runtime; coord_check + parallel_check already
  arbitrate the OUTCOME (scopes + handoffs). Adding a transport gate would couple
  a gate to Orca being installed, which isn't true on every repo.
- Removed the test side-effect (docs/pm/coordination.md created by open-run) —
  the vteam repo runs parallel=1 so it wasn't needed here.
- Honest scope: this makes the transport NAMED, DOCUMENTED and RUNNABLE (helper
  tested live). It does NOT itself spawn two full worker agents end-to-end (that
  is a heavy live run; the bus primitive under it is proven — VT-6 + here).

## Side findings

- SF-1 leftover Orca test Runs (run_f2216d7b3740 + earlier) are inert empty
  namespaces; this Orca build exposes no run-delete. Harmless.
- SF-2 T4b two-agent review of THIS diff not yet run.
