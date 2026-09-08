# VT-6 — verification (branch feat/VT-6-agent-coordination, 2026-09-08)

```console
$ python3 core/scripts/coord_check.py --selftest    → OK (consistent green + unreflected/giver-keeps/over-budget/malformed red)
$ node bin/vteam.mjs update                          → runtime + doctrine + skills re-rendered
$ ls .vteam/scripts/coord_check.py                   → present ; grep coord: profiles → wired after parallel
$ grep -l '{(paths|...)\.[a-z_]*}' .claude/skills/*/SKILL.md → none
$ python3 .vteam/scripts/dor_check.py VT-6 / log_check.py → ✅ / ✅
$ bash .vteam/scripts/gate.sh  (…·competencies·parallel·coord·test)
▶ coord: ✅ coord_check: parallel mode off — nothing to check
  E2E: GREEN — 160/160
$ node bin/vteam.mjs doctor      → 28 discovered selftests (coord_check among them)
```

- coord_check integration probe: evd/VT-6/dev/cmd_probe.md (reflected→green, unreleased→red, over-budget→red).
- LIVE 2-agent chat smoke test: evd/VT-6/dev/chat_transcript.md — HONEST outcome:
  direct peer chat BLOCKED (ListAgents disabled in this session); artifact-based
  coordination succeeded; coordinator-mediated messaging available.
