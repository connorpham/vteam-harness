# VT-3: Competencies — the craft layer the roles were missing

- status: In Progress
- assignee: Connor Pham
- estimate: 1d
- labels: doctrine, no UI

## Why

The owner's review of 2026-08-28: "the framework has supervisors and an iron
rulebook, but no employees — who is the dev, what do they know?" Confirmed in
the files: `roles/dev.md` (66 lines) and `/dev` T3 are process standards (PR
size, branch hygiene, Figma mechanics); nothing says how a senior models data,
designs an API, handles errors, debugs, tests, or secures a handler. Gates
measure outcomes; nothing produces the competence that yields them.

Research (34 repos, stars from the GitHub API on 2026-08-28; ~20 skill files
read in full) found the shape that works: superpowers' iron-law + rationalization
table + red flags; mattpocock's decision-first craft (feedback loop before
hypothesis, deep modules, glossary discipline); nodebestpractices' TL;DR +
Otherwise; OWASP/TEA for security and test quality — and the shape that fails:
VoltAgent-style "list the technique names" personas.

## Spec / oracle

spec §`raci.md` §1 (DEV = R/A on code; REV = A on review) and
`review-standard.md` §1 (APPROVE must list what was tried) — the Reviewer lens
is how craft becomes something review can check. `docs/DESIGN.md` §1 layer
model (doctrine is rendered into paths.team). `red-flags.md` for the excuse
table form.

## Acceptance criteria (testable)

1. Given the package, When `vteam update` runs in an installed repo, Then
   `docs/team/competencies/dev/` holds ten competency files + `INDEX.md`, and
   each is also rendered as a skill (`.claude/skills/dev-identity/SKILL.md` …)
   with no unresolved `{vars}`.
2. Given a competency file missing its `## Reviewer lens`, When
   `competency_check.py` runs, Then it exits 1 naming the file and the section.
3. Given a competency whose description narrates a procedure ("then", "→"),
   When the gate runs, Then it exits 1 — the description must start with
   "Use when" and name the problem.
4. Given an `INDEX.md` that does not match the files present, When the gate
   runs, Then it exits 1 and names `--write-index`.
5. Given `/dev` T2, When a ticket carries `label: data`, Then the workflow text
   instructs loading `dev-data-modeling` from INDEX and pasting its Reviewer
   lens into the R1/R2 briefs; the DoD carries the **Competencies:** line.
6. `competency_check.py --selftest` proves every rule can go red; `gate.sh`
   runs it in every profile; `doctor` discovers it (23 selftests).

## Out of scope

- QA, BA, SA competencies (next tickets, same shape).
- Stack files beyond `nextjs-prisma`.
- Changing any card threshold in `review_check.py`.
- Auto-loading competencies by tooling — the lane loads them by INDEX; the
  agent tool's skill discovery is a second path, not a dependency.

## Comments

### 2026-08-28 Connor Pham
claimed 2026-08-28T10:30:00Z · branch feat/VT-3-competencies
