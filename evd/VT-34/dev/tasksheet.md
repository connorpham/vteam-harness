# VT-34 · dev tasksheet — record the stop state when a session ends mid-ticket
CODE-SCOPE: core/scripts/stop_state.sh core/scripts/graph_check.py core/templates/hooks/ adapters/claude-code.mjs core/workflows/dev.md tests/e2e.mjs README.md CHANGELOG.md .vteam/ .claude/ evd/VT-34/ docs/pm/ docs/backlog/

Branch `feat/VT-34-stop-state` from main d9b1e7e. Spec: docs/BENCHMARK.md ("How the two runs
went"), core/workflows/dev.md T5/T6, adapters/claude-code.mjs (hook install), graph_check rules.

## Plan
| T | Task | State |
|---|---|---|
| T1 | `core/scripts/stop_state.sh` — writes `{evd}/<KEY>/dev/STOP-STATE.md` when dirty or ahead of base on a `feat|fix/<KEY>-…` branch (or `VTEAM_TICKET`), replaces one `- stop-state:` tasksheet line, exit 0 always, never commits; `--selftest` with 6 cases | done — proof.md §1 |
| T2 | `core/templates/hooks/session-end` + adapter installs it and merges a `SessionEnd` entry into `.claude/settings.json` (same manifest-guarded `write`; file untouched when both entries are present) | done — proof.md §3 |
| T3 | `graph_check.py`: `check_stop_states` — STOP-STATE.md older than 7 days on a ticket neither Done nor Blocked is a coherence violation; `recorded:` line dates it, mtime otherwise. Fixture FIRST (RED), rule after (GREEN) | done — proof.md §2 |
| T4 | core/workflows/dev.md "Stopping mid-ticket" (WIP commit or dirty tree, ALWAYS the stop state; Blocked + reason when not a hand-off); `vteam update` re-rendered the skill, mirror, hook, settings, manifest | done |
| T5 | tests/e2e.mjs §5b manifest + §14: hook script, settings entry, merge alongside user hooks, script installed, hook records a ticket in flight, records nothing on a clean protected branch; README counts 34→35 selftests, 199→207 checks | done — proof.md §3 |
| T6 | Mutation probes (code-only, tests kept), gate GREEN, npm test GREEN, review dossier, PR | proof.md §4–5 |

## Decisions taken without the owner (recorded, reversible)
- The hook never changes ticket status and never commits: a status is a claim the lane makes on purpose; the doctrine tells the lane to set `Blocked`, the gate reds the silence after 7 days.
- 7 days is a constant (`STOP_STATE_MAX_DAYS`), not config — one number, one meaning; make it a knob when a second project needs a different one.
- Other adapters get the doctrine rule only; they have no session-end event to hook.
