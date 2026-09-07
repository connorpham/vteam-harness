# VT-4: QA competencies — distilled from ai-qa into the craft layer

- status: In Progress
- assignee: Connor Pham
- estimate: 1d
- labels: doctrine, no UI

## Why

VT-3 gave DEV its craft; QA still has only process (the /qa lane) and law
(evd_check). Meanwhile the owner built `github.com/connorpham/ai-qa` — a
standalone QA framework whose doctrine (test-design, user-mindset, heuristics,
hostile-inputs, security-probes, requirement-smells, case-writing, checklists,
severity — 3,180 lines read in full on 2026-09-07) is exactly the QA craft
vteam lacks. This ticket distills it into `competencies/qa/` in the VT-3 shape
so the same gate, the same INDEX routing and the same Reviewer-lens-into-brief
mechanism apply.

## Spec / oracle

spec §`raci.md` §1 (QA = R/A on test cases and verdicts) and §3 (QC finds
defects; the challenger is the adversarial seat) · `review-standard.md` (the
challenger contract the Reviewer lens feeds) · the VT-3 competency contract:
`competency_check.py` docstring is the house of record for shape and word
budget. Source texts: connorpham/ai-qa `core/doctrine/*` (verbatim reference
copies credited in each file).

## Acceptance criteria (testable)

1. Given the branch, When `vteam update` runs, Then `docs/team/competencies/qa/`
   holds nine competency files + INDEX.md + a `reference/` set, each competency
   also rendered as a skill with no unresolved `{vars}`.
2. Given any QA competency stripped of `## Reviewer lens`, When
   `competency_check.py` runs, Then exit 1 names the file and section.
3. Given the nine files, When the gate runs, Then every description starts
   "Use when", no description narrates a procedure, and every body ≤ 1100 words
   — full tables live under `reference/`, which the gate deliberately ignores.
4. Given `/qa` V1, When the lane starts, Then it reads `qa-identity` +
   `qa-requirement-smells` and routes the rest from INDEX by loads/applies;
   Given V6, Then the challenger brief carries the Reviewer lens of every
   loaded competency; the DoD carries the Competencies line.
5. Given the DEV set from VT-3, When this ticket lands, Then nothing in
   `competencies/dev/` changes and `competency_check.py --selftest` still
   proves red.

## Out of scope

- Changing evd_check.py fields or any gate threshold (PERSONA/KIND/HEURISTIC/
  OBSERVATIONS enter as prose in the workflow, optional in manifests).
- Importing ai-qa's scripts (browser.mjs, api_check.mjs, xlsx export) — tooling,
  not craft; separate ticket if wanted.
- BA/SA competencies.
- Merging VT-3/VT-4 into main or rebasing onto 0.15.3 (owner's call; noted
  that main has moved).

## Comments

### 2026-09-07 Connor Pham
claimed 2026-09-07T09:30:00Z · branch feat/VT-4-qa-competencies
