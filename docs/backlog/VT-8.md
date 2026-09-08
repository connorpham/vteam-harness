# VT-8: BDD human report — AI reports in Given/When/Then anyone can read

- status: In Progress
- assignee: Connor Pham
- estimate: 0.5d
- labels: workflow, no UI

## Why

vteam already demands plain-language reports (/qa REPORT.md, /dev's 7-part
comment), but there is no STRUCTURED human format an agent can emit that a
non-programmer scans in seconds and a machine can check is honest. This adds a
BDD report: each thing the AI did/verified as a `Scenario` with Given/When/Then
in ordinary words — complete (every scenario ends in an observable outcome) but
not rambling (capped length, no code-speak in the human body). The gate makes
"readable, complete, concise" red-able instead of a style wish.

## Spec / oracle

Governing rule: spec §`qa` REPORT plain-language bar + `evd_check`'s banned-filler
discipline (an outcome may not be "works"/"OK"), and `comment_check`'s
"structured sections, machine-checked" pattern. BDD Given/When/Then mirrors the
Given/When/Then acceptance-criteria form `dor_check` already blesses.

## Acceptance criteria (testable)

0. **Given** a `*.bdd.md` report whose scenario has a `Then` that is only a
   banned filler word (e.g. "works"), or is missing `When`, or a step over the
   word cap, **When** `bdd_report_check.py` runs, **Then** it exits 1 naming the
   scenario + the problem; **and Given** a well-formed concise scenario, **Then**
   it exits 0.
1. New gate `bdd_report_check.py`: scans `{paths.evidence}/**/*.bdd.md`; inert-
   green when none exist. For each report it checks structure (≥1 `Scenario:`,
   each with Given+When+Then), plain language (no code-speak — function(),
   file.ext paths, HTTP verbs, SQL, selectors — in the human body), completeness
   (every Then is an observable outcome, no banned filler), and conciseness
   (per-step word cap + per-scenario line cap). `--selftest` proves each rule
   reds. Wired into every profile + doctor.
2. Doctrine `core/doctrine/bdd-report.md` + template
   `core/templates/docs/bdd-report.md` — how to write one (scenarios, the
   plain-language bar, the conciseness rule, a good vs bad example).
3. `/dev` and `/qa` workflows note the BDD report as the human-report option
   (an agent MAY emit `<report>.bdd.md`; the gate guards it); code details stay
   in the existing appendices, never in the scenarios.
4. `gate.sh` GREEN incl. the new gate; conformance/e2e green; no `{vars}`; a REAL
   sample BDD report + a rambling/jargon counter-example recorded in evidence.

## Out of scope

- Replacing the existing /qa REPORT.md or /dev 7-part comment (this is an
  additional, opt-in human format, not a replacement).
- Auto-generating the report from the ledger (agents write it; the gate checks it).
- Localization rules beyond "written in project.language" (keys/labels English).

## Comments

### 2026-09-08 Connor Pham
claimed 2026-09-08T17:00:00Z · branch feat/VT-8-bdd-report
