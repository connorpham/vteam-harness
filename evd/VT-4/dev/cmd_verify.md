# VT-4 — verification, real runs (branch feat/VT-4-qa-competencies, 2026-09-07)

```console
$ python3 core/scripts/competency_check.py --selftest      # VT-3 gate, unchanged
competency_check selftest: OK (valid file green + 7 mutations red + index missing/stale red)

$ node bin/vteam.mjs update
✓ doctrine refreshed in docs/team     ✓ claude-code workflows re-rendered

$ ls -d .claude/skills/qa-* | wc -l                        → 9   (reference/*.md NOT rendered as skills)
$ ls docs/team/competencies/qa/reference/                  → checklists heuristics hostile-inputs security-probes
$ grep -l '{(paths|project|team|review|git|stack|autonomy)\.[a-z_]*}' .claude/skills/qa-*/SKILL.md  → none

$ python3 .vteam/scripts/competency_check.py
✅ competency_check: 19 competencies well-formed and indexed under …/docs/team/competencies

$ python3 .vteam/scripts/competency_check.py --root <copy of dev only, qa deleted>   # AC-5: DEV set intact
✅ competency_check: 10 competencies well-formed and indexed

$ bash .vteam/scripts/gate.sh    (generic: docs-shrink·ledger·graph·verbatim·competencies·test)
▶ competencies: ✅ competency_check: 19 competencies well-formed and indexed
conformance: OK — 15 fixtures … ; ledger grammar 11 rows
E2E: 137/142  (5 reds = evd_check/evd_ui_check "Pillow missing", python 3.9, PRE-EXISTING — see cmd_probe/VT-3)

$ python3 .vteam/scripts/dor_check.py VT-4   → ✅   ;  log_check → ✅   ;  graph_check → ✅ (3 tickets)
```

Confirmation from inside this Claude Code session: after `update`, the nine
qa-* competencies appeared in the skill list by their "Use when…" descriptions
(qa-identity … qa-security-probes) — model-invoked path live, alongside the
lane-invoked INDEX routing in /qa.
