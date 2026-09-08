# VT-5 — verification (branch feat/VT-5-parallel-team, 2026-09-08)

```console
$ python3 core/scripts/parallel_check.py --selftest       → OK (disjoint green + overlap/over-cap/missing-scope red)
$ node bin/vteam.mjs update                                → runtime + doctrine + skills re-rendered
$ ls .vteam/scripts/parallel_check.py                      → present
$ grep -c 'parallel:' .vteam/profiles/generic/gates.yaml   → 1 (wired after competencies)
$ grep -l '{(paths|project|team|review|git|stack|autonomy)\.[a-z_]*}' .claude/skills/*/SKILL.md → none
$ python3 .vteam/scripts/dor_check.py VT-5                 → ✅ ready
$ python3 .vteam/scripts/log_check.py / graph_check.py     → ✅ / ✅ (5 tickets)
$ bash .vteam/scripts/gate.sh   (generic: docs-shrink·ledger·graph·verbatim·competencies·parallel·test)
▶ parallel: ✅ parallel_check: parallel mode off (team.parallel=1) — nothing to check
  E2E: GREEN — see gate_vt5.log (README selftest count guard now 27)
$ node bin/vteam.mjs doctor      → 27 discovered selftests (parallel_check among them)
```

Config knob added in three homes (vteam.config.yaml · src/cli/init.mjs · core/templates/vteam.config.example.yaml)
and documented in DESIGN §2 + §7.
