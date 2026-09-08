# VT-8 task-sheet — BDD human report

CODE-SCOPE: core/scripts/bdd_report_check.py core/doctrine/bdd-report.md core/templates/docs/bdd-report.md core/workflows/dev.md core/workflows/qa.md profiles/ core/scripts/gate.py README.md docs/backlog/VT-8.md docs/pm/log.md docs/team/ .claude/skills/ .vteam/ evd/VT-8/

Competencies: dev-identity · dev-codebase-design · dev-testing-craft.

## Requirement

An opt-in BDD report format for AI agents — Given/When/Then in human language,
COMPLETE (every scenario ends in an observable outcome) but CONCISE (no rambling,
no code-speak). A gate makes those red-able, not a style wish.

## AC → proof

| AC | Proof |
|---|---|
| 0/1 gate: missing When / filler Then / over-cap step / code-speak red; well-formed green; inert when none | cmd_probe.md (selftest 6 mutations red; sample green; counter-example red) |
| 2 doctrine + template | core/doctrine/bdd-report.md, core/templates/docs/bdd-report.md |
| 3 /dev + /qa note the optional *.bdd.md | core/workflows/dev.md T6, core/workflows/qa.md V7 |
| 4 gate.sh GREEN; no {vars}; real sample + counter-example | cmd_verify.md + REPORT.bdd.md (itself a passing sample) |

## Self-review (T4a)

- Opt-in-safe: scans evd/**/*.bdd.md; no such file → inert green. Never reds a
  repo that doesn't use the format.
- FILLER reduction strips stopwords so "it works"/"the result is OK" reduce to
  the empty claim (fixed a first-cut miss where only exact-match filler caught).
  Verified legit short Thens ("the order is created", "the total reads 450,000 ₫")
  stay green — no false positives.
- CODE_SPEAK breaks on first hit per step (one clear finding, not a pile).
- REPORT.bdd.md is dogfood: this ticket's own account, and it passes its own gate.

## Side findings

- SF-1 the counter-example lives in scratch, not evd/, so the gate suite scans
  only the real (green) sample.
- SF-2 T4b two-agent review of THIS diff not yet run (per session pattern).
