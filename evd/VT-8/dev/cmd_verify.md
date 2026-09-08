# VT-8 — verification (branch feat/VT-8-bdd-report, 2026-09-08)

```console
$ python3 core/scripts/bdd_report_check.py --selftest   → OK (good green + 6 mutations red + And/But inheritance)
$ node bin/vteam.mjs update                              → gate synced to .vteam, doctrine → docs/team, template rendered
$ python3 .vteam/scripts/bdd_report_check.py evd/VT-8/dev/REPORT.bdd.md → GREEN (the sample passes its own gate)
$ python3 core/scripts/bdd_report_check.py <rambling+jargon+filler>     → RED (2 problems named)
$ grep -l '{(paths|…)\.[a-z_]*}' .claude/skills/*/SKILL.md → none
$ python3 .vteam/scripts/dor_check.py VT-8 / log_check.py → ✅ / ✅
$ bash .vteam/scripts/gate.sh   (…·coord·bdd-report·test) → GREEN ; e2e GREEN
$ node bin/vteam.mjs doctor      → 29 discovered selftests (bdd_report_check among them)
```
