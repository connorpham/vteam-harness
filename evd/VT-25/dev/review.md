# Review dossier — VT-25 (the five untested tools)

**Provenance, stated plainly:** both cards were written by the implementing session, not by
spawned reviewers. The substance behind them is `evd/VT-25/dev/mutations.md` — nine code-only
mutations, each run against the new selftest, each RED, each restored — plus one defect the new
gate step found in a real consumer the same hour (below).

## R1 — implementation review (mutation probes)
APPROVE

Tried to break:
- mutated `0o600` → `0o644` for a created `~/.claude.json` in core/scripts/orca_team.sh: neighbourhood and ran `bash core/scripts/orca_team.sh --selftest` — RED (mode asserted with `stat`); mutated the backup-once guard to always copy — RED (the third run's backup no longer matched the first)
- dropped `redirect: "false"` from the credentials form in auth.mjs and ran `node profiles/nextjs-prisma/scripts/auth.mjs --selftest` — RED at profiles/nextjs-prisma/scripts/auth.mjs:40 (the form is asserted field by field)
- gave font-size the ±0.75px tolerance and let an off-list intent count as INTENDED in profiles/nextjs-prisma/scripts/ui_fidelity.mjs:72 neighbourhood — RED both times; the `DEVIATION: WRONG` marker evd_ui_check greps is asserted in the rendered fidelity.md
- made CI stop forcing headless and let a shot with no user through in profiles/nextjs-prisma/scripts/ui-evidence.mjs:57 neighbourhood — RED both times
- turned off the dirty-tree refusal and emptied the artifact filter in tools/prepublish-check.mjs:41 — RED both times; the fixture uses REAL git (a bare origin, ahead and behind states) and stubs only npm
- ran `bash .vteam/scripts/gate.sh` in the testbed after `vteam update` — RED at the new step on TB-7, a decision-closed ticket; added the `closed-by` rule at core/scripts/stale_verdict_check.py:172 with a green/red pair in its selftest

Traces: core/scripts/orca_team.sh:, tools/prepublish-check.mjs:41, profiles/nextjs-prisma/scripts/ui_fidelity.mjs:72, core/scripts/stale_verdict_check.py:172, `node tests/e2e.mjs` (199/199), `node bin/vteam.mjs doctor` (34 selftests discovered)

## R2 — adversarial read of the restructures (behaviour must not move)
APPROVE

Tried to break:
- diffed the runtime path of ui_fidelity.mjs and ui-evidence.mjs against HEAD by eye, statement by statement: the same config lookups, the same BASE/PASSWORD/EVD resolution, the same screenshot and fidelity.md strings; the only additions are `specProblem`/`shotsProblem` (fail fast on input the old code crashed on later — `<dir>/undefined` screenshots, "sign-in failed for undefined") and the lazy `import("playwright")` whose failure is a one-line install hint (proved in tests/e2e.mjs:902 — no stack trace)
- checked that the profile selftests do NOT pull playwright: e2e §20 runs `ui_fidelity --selftest` from an empty directory with no node_modules — green
- looked for a way the prepublish refactor changes the publish path: `prepublishOnly` still runs `node tools/prepublish-check.mjs` with no args → `check()` with the real spawnSync against ROOT, same five checks, same exit codes and closing lines; `packed === null` (unparseable pack JSON) is now a WARN instead of a crash — the one deliberate softening, named here
- tried `orca_team.sh --selftest` on Linux semantics: `ORCA_CLI_COMMAND=orca` is set for the fixture so the bare-`orca`-is-a-screen-reader guard cannot interfere; `stat -f` falls back to `stat -c`; HOME is a temp dir so the user's real `~/.claude.json` is never opened
- checked the `closed-by` rule cannot hide a real stale verdict: it applies only when `REPORT.md` is ABSENT; a ticket with a REPORT keeps every anchor rule, and a Done ticket with neither report nor field stays UNVERIFIABLE (both asserted)

Traces: profiles/nextjs-prisma/scripts/ui-evidence.mjs:57, profiles/nextjs-prisma/scripts/ui_fidelity.mjs:72, tools/prepublish-check.mjs:41, core/scripts/stale_verdict_check.py:172, `node profiles/nextjs-prisma/scripts/ui_fidelity.mjs --selftest` from an empty dir, `bash .vteam/scripts/gate.sh` in ~/Documents/testbed-base
