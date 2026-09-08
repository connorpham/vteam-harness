# VT-8 — bdd_report_check probes (real runs, 2026-09-08)
```console
$ python3 core/scripts/bdd_report_check.py --selftest
bdd_report_check selftest: OK (good green + 6 mutations red + And/But inheritance)

# GREEN — the committed sample report
$ python3 .vteam/scripts/bdd_report_check.py evd/VT-8/dev/REPORT.bdd.md
✅ bdd_report_check: 1 BDD report(s) readable, complete and concise

# RED — a rambling, code-speak, empty-outcome counter-example
$ python3 core/scripts/bdd_report_check.py <bad.bdd.md>
❌ bdd_report_check: /private/tmp/claude-501/-Users-connorpham-Documents-vteam/89054c28-407b-4e1f-a00c-494521cc47bb/scratchpad/bad.bdd.md — 2 problems
   - Scenario 'discount': Then says nothing observable ('it works') — state what a person would SEE, not 'it works'
   - Scenario 'discount': When contains a file path ('src/checkout.ts') — keep code out of the human scenario; put it in an appendix
```
