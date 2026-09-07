# VT-4 task-sheet — QA competencies distilled from ai-qa

CODE-SCOPE: core/doctrine/competencies/qa/ core/workflows/qa.md README.md docs/backlog/VT-4.md docs/pm/log.md docs/team/ .claude/skills/ .vteam/ evd/VT-4/

Competencies: qa-identity · qa-case-writing · qa-report-writing (this ticket is
doctrine + workflow wiring; no code, no gate change — VT-3's competency_check is
reused unchanged).

## Requirement

Give the QA role its craft (finding defects), in the VT-3 shape, sourced from the
owner's own ai-qa framework, so the same gate/INDEX/Reviewer-lens machinery holds.

## Source read (evidence for fidelity, not invention)

connorpham/ai-qa @ HEAD (2026-09-07), fetched via GitHub API tarball (git clone
blocked in sandbox). Read in full: roles-qa, test-design, user-mindset,
heuristics, hostile-inputs, security-probes, requirement-smells, case-writing,
checklists, severity, report-writing, evidence (3,180 lines). Each competency
distills one or two of these into the ≤1100-word Decide/Rules/Reviewer-lens
shape; the full tables are copied verbatim into reference/ with a credit header.

## AC → proof

| AC | Proof |
|---|---|
| 1 renders doctrine + skills, no vars | cmd_verify.md (`update`, 9 qa skills, reference present, grep none) |
| 2 no Reviewer lens → exit 1 | cmd_probe.md §AC-2 (reused VT-3 gate) |
| 3 "Use when" + no procedure + ≤1100 words; reference/ ignored | cmd_verify.md (gate green at 19; reference not counted) |
| 4 /qa V1 identity+smells, V2 INDEX route, V6 lens in brief, DoD line | core/workflows/qa.md diff (rendered .claude/skills/qa/SKILL.md) |
| 5 DEV set unchanged; selftest still red | cmd_verify.md (dev untouched; --selftest OK) |

## Self-review (T4a)

- Word budget: 9 files 737–920 words, cap 1100. Full tables deliberately NOT
  inlined — they live in reference/ (gate ignores subdirs), so the competency
  stays the METHOD and the DATA stays retrievable. This is the progressive-
  disclosure rule the gate's docstring names.
- qa-security-probes uses label:+term: routing (auth/session/role/payment/…);
  the always-set is the five design/writing files + identity + requirement-smells.
- Mapping to ai-qa is 1–2 sources per file, credited in Sources; nothing invented
  beyond the Decide tables and Reviewer lenses (the parts ai-qa states as prose).
- Reference files rendered into docs/team by the doctrine walk (recursive) but
  NOT as skills (adapter globs role/*.md only) — verified 9 skills, not 13.

## Side findings

- SF-1 `evd_check`/`evd_ui_check` selftests still red on this machine (python 3.9,
  no Pillow) — pre-existing environment issue, unrelated; CI installs pillow.
- SF-2 main has moved to 0.15.3 while VT-3/VT-4 sit on their branches; a rebase
  or merge decision is the owner's (noted out of scope).
- SF-3 VT-2 /review lane still parked in a named stash.
- SF-4 T4b two-agent review of THIS diff not yet run in this session.
