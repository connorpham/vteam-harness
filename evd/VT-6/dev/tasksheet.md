# VT-6 task-sheet — peer coordination (agents chat, decisions become artifacts)

CODE-SCOPE: core/scripts/coord_check.py core/workflows/team.md core/workflows/pm.md profiles/ core/scripts/gate.py vteam.config.yaml core/templates/vteam.config.example.yaml src/cli/init.mjs docs/DESIGN.md README.md docs/backlog/VT-6.md docs/pm/log.md docs/team/ .claude/skills/ .vteam/ evd/VT-6/

Competencies: dev-identity · dev-codebase-design · dev-testing-craft.

## Requirement

Owner's call: let parallel DEV agents talk directly to split/hand off work and
kill functional (contract) conflicts that disjoint-file scope can't see. Add the
guardrail that keeps peer chat from becoming the ephemeral, unauditable failure
vteam exists to prevent: chat DECISIONS become committed scope, verified by a gate.

## Design (why this shape, given the owner chose direct peer chat)

I recommended contract-first+escalate; the owner chose direct peer chat. Built
peer chat WITH four guardrails so it stays honest: (1) every scope/contract
decision is appended to docs/pm/coordination.md and both tasksheets' CODE-SCOPE
updated; (2) coord_check reds a handoff not reflected in scope, an over-budget
round, or a malformed row; (3) reviewers stay fresh/isolated (chat is DEV-only);
(4) ledger + merges stay the PM's single hand. Chat is the means; the gate is the
check — same as everywhere in vteam.

## AC → proof

| AC | Proof |
|---|---|
| 0/1 coord_check reds unreflected handoff/over-budget/malformed; inert off | cmd_probe.md (A green, B red "giver never let go", C red over-budget); selftest |
| 2 team.md peer-coordination subsection (chat, artifact, reviewer-isolation, bounded, PM books) | core/workflows/team.md §"Parallel DEV coordination" |
| 2b pm.md dispatch hands handles+coord path, re-gates after handoff | core/workflows/pm.md DEV dispatch line |
| 3 coord_budget knob (config+init+example+DESIGN); conformance/e2e green; no {vars} | cmd_verify.md |
| 4 gate.sh GREEN incl. coord; LIVE 2-agent chat smoke test | cmd_verify.md + chat_transcript.md |

## Self-review (T4a)

- coord_check core (parse_log/check_handoffs/covered) pure + selftested; reuses
  the same path-nesting rule as parallel_check (a dir covers a file under it).
- Fixed a selftest bug (fake header "R|F|T|P" not recognized → used the real
  "Round|From|To|Path" header) before finalizing.
- gate.py BOOKKEEPING extended with "coord".
- The "agents do NOT chat" line kept for the default + reviewers; only parallel
  DEV coordination is the carve-out.

## Side findings

- SF-1 a genuinely-live peer chat depends on the platform delivering
  sibling-to-sibling SendMessage; the smoke test records the REAL outcome
  (chat_transcript.md), not a simulation.
- SF-2 T4b two-agent review of THIS diff not yet run.
