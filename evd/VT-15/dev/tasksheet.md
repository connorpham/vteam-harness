# VT-15 — DEV tasksheet

CODE-SCOPE: core/doctrine/competencies/ profiles/ .claude/skills/

`.claude/skills/` is in the scope **deliberately, not by drift**: it is not hand-written, it is
what `adapters/claude-code.mjs` renders from `core/doctrine/` when `vteam update` runs, so a
doctrine ticket cannot avoid touching it. `graph_check` red-flagged the first commit here for
exactly that (MAST 2.3) and it was right to — the scope line was too narrow, so the widening is
recorded rather than the gate silenced.

Worth noting for the framework: `graph_check`'s ALWAYS_LEGAL list covers `docs/`, which quietly
includes the `docs/team/` doctrine mirror, but not `.claude/skills/` — the *other* mirror of the
same generated source. One deploy target is always legal and its twin is a scope violation. Raised
as a decision rather than patched here, because loosening scope enforcement is an owner's call.

Two homes only. The doctrine edit and the gate-manifest edit are declared together because
they came from one run and one lesson: the doctrine says what to look for, the manifest
decides whether the step that would have looked ever executes.

## Steps

- **T0** — prove the hole exists before writing anything: `grep -ril 'forced.colors|high
  contrast' core/doctrine/` → no files. Word-count the two target competencies → 1091 and
  1086 of a 1100 ceiling, i.e. any addition must be paid for.
- **T1** — decide where the knowledge lives. The measured detail (compiled-CSS lines, the
  `outline-none` vs `outline-hidden` difference, the measurement recipe) is reference
  material: needed once, when someone builds or verifies an indicator. The competencies
  carry only the *trigger* — one Decide row and one Rule each.
- **T2** — write `qa/reference/forced-colors.md` from the field evidence, then add the
  triggers and pay for them by moving each competency's `Rationalizations` table (a
  non-required section, wanted at rebuttal time rather than design time) into its 1:1
  reference file.
- **T3** — add the falsification question to both sides of the acceptance-criteria pair.
- **T4** — fix the gate manifests with the mechanism the driver already had, and prove it
  end to end on the testbed rather than by reading the YAML.
- **T5** — `competency_check`, `vteam update`, full gate.
