# VT-3 task-sheet — competencies, the craft layer

CODE-SCOPE: core/doctrine/competencies/ core/scripts/competency_check.py core/scripts/gate.py core/workflows/dev.md src/cli/adapters.mjs profiles/ README.md docs/DESIGN.md docs/backlog/VT-3.md docs/pm/log.md docs/team/ .claude/skills/ .vteam/ evd/VT-3/

Competencies: dev-identity · dev-codebase-design · dev-testing-craft (the ticket
is doctrine + one Python gate + one renderer change; no data/API/stack rows match).

## Requirement

Give each role the craft it is expected to carry, in a form review can check
(Reviewer lens), routed by the lane from a one-page index, guarded by a gate
that reds the shapes that make craft uncheckable. DEV first, ten files.

## Research basis (evidence for the SHAPE, not decoration)

34 repos ranked by GitHub API stars (2026-08-28); ~20 skill files read in full.
Adopted: superpowers (iron law, rationalization table, red flags, "describe the
problem not the procedure"); mattpocock/skills (Decide-first craft, feedback loop
before hypothesis, deep modules, glossary); nodebestpractices (TL;DR + Otherwise);
OWASP cheat sheets, awesome-copilot security catalog; BMAD TEA (risk P0–P3, test
quality standards); goldbergyoni testing guide; bulletproof-react; ECC prisma /
migrations. Rejected: VoltAgent-style technique-name lists (the failure vteam
already had, inverted).

## AC → proof

| AC | Proof |
|---|---|
| 1 renders as doctrine + skills, no vars | cmd_verify.md (`update`, counts, grep none); skills visible in-session |
| 2 no Reviewer lens → exit 1 | cmd_probe.md §AC-2 |
| 3 procedural description → exit 1 | cmd_probe.md §AC-3 |
| 4 stale INDEX → exit 1 | cmd_probe.md §AC-4 |
| 5 /dev routes by INDEX; lens into briefs; DoD line | core/workflows/dev.md T1/T2/T3/T4b/DoD (rendered .claude/skills/dev/SKILL.md) |
| 6 selftest; every profile; doctor 23 | cmd_verify.md; profiles/*/gates.yaml `competencies:` step |

## Self-review (T4a)

- Word budget: 10 files, 783–901 words each, cap 1100 — deliberately under
  mattpocock/ECC sizes to protect the lane's context budget.
- `applies` grammar is checked by the gate but *matching* is done by the agent
  reading INDEX (prose routing) — stated in README; a machine loader is out of
  scope by design (the tool's skill discovery is the second path).
- gate.py BOOKKEEPING set extended so a competencies-only run still reports
  WEAK honestly.
- Pre-existing e2e Pillow reds untouched; README e2e count 141→142 fixed.

## Side findings

- SF-1 `evd_check`/`evd_ui_check` selftests red on this machine (python 3.9,
  no Pillow) — environment; consider `doctor` printing the interpreter path.
- SF-2 VT-2 (`/review` lane) parked in a named stash; branch
  `feat/VT-2-review-lane` still exists.
- SF-3 T4b two-agent review of THIS diff not yet run in this session.
