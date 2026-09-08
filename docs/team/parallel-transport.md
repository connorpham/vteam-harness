# Parallel-DEV coordination transport — how the agents actually talk

> `/team` and `/pm` read this when `team.parallel > 1`. It names the REAL channel
> the parallel DEV agents coordinate on, and the fallback when there isn't one.
> The rules that make parallel safe live in `team.md` (coding parallel /
> integration serial) and in two gates — `parallel_check` (disjoint file scope)
> and `coord_check` (a chat handoff must become real `CODE-SCOPE`). This file is
> only the wire; those gates are the arbiters, and the ledger + merges stay the
> PM's single hand.

## Why a named transport at all

The obvious channel — a spawned subagent messaging a sibling — does **not** work
in practice: `ListAgents` is disabled for spawned agents, so they can't discover
each other's address, and `SendMessage` then has no reachable target (verified
2026-09-08). So the transport is named explicitly, and it degrades to a text
relay when absent — never a silent half-working chat.

## The transport, in priority order

**1. Orca orchestration (Claude Code) — the real bus.** A persistent, addressable
mailbox with `send` / `check` / `ask` / `reply` / `worker_done`. Tested working:
a Run holds messages until read + acked, each carrying from/to/subject/body/seq.
The PM coordinator drives it; the helper `.vteam/scripts/orca_team.sh` wraps the
flow:

```bash
bash .vteam/scripts/orca_team.sh status              # is the bus reachable?
RUN=$(bash .vteam/scripts/orca_team.sh open-run "<sprint> parallel DEV" | sed -n 's/^RUN=//p')
# for each unblocked, scope-disjoint ticket, launch a worker bound to the Run:
orca orchestration task-create --spec "<ticket + CODE-SCOPE + the contracts it OWNS vs CONSUMES>" --json
orca orchestration worker-start --task <task_id> --agent claude --worktree new-child --run "$RUN" --json
# the PM then blocks for lifecycle events (no sleep/poll loops):
bash .vteam/scripts/orca_team.sh wait "$RUN"          # → worker_done | escalation | question
```

Inside a worker, coordination is ordinary bus traffic:
- needs a contract another ticket owns → `orca orchestration ask --question "<what>"`
  (blocks for the PM/owner's answer) or `send --to run:$RUN`;
- hands a path off → append one row to `docs/pm/coordination.md`
  (`| Round | From | To | Path/Contract | What/why |`) **and** update both
  tasksheets' `CODE-SCOPE`, so `coord_check` stays green;
- done → `orca orchestration worker_done` (settles its task; the PM never
  hand-writes that status).

Everything routes through the Run (the hub); the PM relays, decides, and is the
only writer of the ledger and the only hand on the merges. Reviewers are never on
this channel — a reviewer is always fresh and isolated.

**2. Fallback — text relay (any tool, or Orca absent).** `orca_team.sh status`
prints this when the bus is down. Each worktree DEV agent returns its result —
ledger row, report, any contract it produced — as TEXT to the PM. The PM writes
`coordination.md` + the ledger and merges serially. Same guards, slower channel,
no live ask/reply.

## Serial integration, re-gated (unchanged from VT-5)

However the agents coordinated, the PM merges their PRs **one at a time**, runs
the /verify gate between each (a green PR expires when a sibling lands beneath
it — `stale_verdict_check`), and re-runs `parallel_check` + `coord_check` after
any handoff. Coding fans out; integration never does.

## CLI resolution

`orca_team.sh` resolves the Orca executable the way the orchestration skill
prescribes: `ORCA_CLI_COMMAND` if set, else `orca-dev` in a dev checkout, else
`orca-ide` on Linux outside an Orca terminal (never bare `orca` there — it is the
GNOME screen reader), else `orca`.
