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
# a NEW worktree is a folder Claude has never seen → pre-trust it or the trust
# dialog eats the injected prompt (rule 3 below):
bash .vteam/scripts/orca_team.sh trust /abs/path/to/the/new/worktree
# the PM then blocks for lifecycle events (no sleep/poll loops):
bash .vteam/scripts/orca_team.sh wait "$RUN"          # → worker_done | escalation | question
```

Inside a worker, coordination is ordinary bus traffic:
- needs a contract another ticket owns → `orca orchestration ask --question "<what>"`
  (blocks for the PM/owner's answer) or `send --to run:$RUN`;
- hands a path off → append one row to `{paths.pm}/coordination.md`
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

## Three rules a split worktree makes non-negotiable

Learned in the first real two-worker run (2026-09-09): both workers hit the same
class of failure within minutes. In one working tree these rules are invisible; in
separate worktrees each one is the difference between a green run and a structural
red. The gates now enforce all three — this section says WHY, so nobody "fixes"
them back.

**1. In parallel mode the tasksheet is the FIRST commit.** A worker's own
`{paths.evidence}/<TICKET>/dev/tasksheet.md` lives in its own worktree, and a
sibling's worktree is a different directory on disk — so a sibling's gate cannot
see it as a file, no matter how correct it is. What worktrees DO share is one
object store, so `parallel_check` and `coord_check` read the sibling's
`CODE-SCOPE` with `git show <branch>:<path>`. That only works on a COMMITTED
sheet. Write the tasksheet, commit it before the first code edit, and every
sibling's gate can see your territory. Leave it uncommitted and the red says
`tasksheet missing on <branch>, not committed` — that message means "commit it",
not "add a CODE-SCOPE line".

**2. Bookkeeping paths are NEVER CODE-SCOPE.** `{paths.pm}` (the coordination log,
the ledger, the minutes), `{paths.evidence}` (every ticket's own evd/) and
`{paths.qa}` (the knowledge base, known-issues) are shared by design — this file
*orders* every agent that hands a path off to append a row to
`{paths.pm}/coordination.md`. Two agents that both obeyed and both declared that
log in CODE-SCOPE were reded for sharing edit territory on the protocol's own
log. `parallel_check` now discounts these homes (printing what it discounted) and
`graph_check` has always treated them as always-legal, so you never need them in
the line. Declare the CODE paths you edit; nothing else.

**3. A worktree Claude has never seen must be PRE-TRUSTED.**
`orca orchestration worker-start --worktree new-child` creates a brand-new
directory, so Claude Code opens its "Do you trust the files in this folder?"
dialog before reading anything — and the injected prompt is consumed by the
dialog. The worker then sits there and the run reports `agent_prompt_stalled`,
which looks like a transport failure and is not one. Mark the folder trusted
before dispatch:

```bash
bash .vteam/scripts/orca_team.sh trust /abs/path/to/new-worktree
```

The helper sets `projects["<abs path>"].hasTrustDialogAccepted = true` in
`~/.claude.json` (exactly that field — the same file Claude Code writes when a
human clicks "trust"). It is idempotent, backs the pre-existing config up once to
`~/.claude.json.vteam-bak`, writes via a temp file + rename so the config is never
torn, refuses a path that does not exist, and refuses a config it cannot parse
instead of replacing it. Trust the path, then `worker-start`.

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
