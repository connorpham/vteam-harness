# Review dossier — VT-24 (fix the 13 defects of the 2026-09-17 code review)

**Provenance, stated plainly:** both cards below were written by the implementing session,
not by spawned reviewer agents. What makes them more than testimony is
`evd/VT-24/dev/mutations.md`: 13 code-only or whole-file reverts, each run against the
suite, each RED, each restored — the "tried to break" bullets cite those runs. The owner
may still want an independent R2 before merge; nothing here pretends to be one.

## R1 — implementation review (mutation probes)
APPROVE

Tried to break:
- reverted `core/scripts/gate.py` `--help` handling to `if False and …` at core/scripts/gate.py:101 and ran `python3 core/scripts/gate.py --selftest` — RED on the "--help must print usage and run no step" fixture; same for the unknown-flag branch
- reverted `core/scripts/lib/ctx.py` to HEAD and ran `node tests/conformance.mjs` — RED: the two new fixtures (`x: [a,,b]`, first key indented) at tests/conformance.mjs:227 die in mjs but not in py, so parity is now fenced
- reverted `src/cli/manifest.mjs` and `src/cli/update.mjs` (one at a time) to HEAD and ran `node tests/e2e.mjs` — 5b RED both times (orphans not pruned / github provider not installed), tests/e2e.mjs:244
- mutated `legal = always_legal(c)` → `legal = ALWAYS_LEGAL` at core/scripts/graph_check.py:69 neighbourhood and ran the selftest — RED on the `paths.evidence: proof` fixture
- mutated `cell = dated[-1]` → `dated[0]` in core/scripts/schedule_check.py:106 neighbourhood — GREEN on the first attempt, because the headerless fixture carried ONE date; added the two-date row `Q6`, re-ran: RED. A test that was not biting is now biting.
- mutated `if a.files:` → `if a.files or a.root:` in core/scripts/bdd_report_check.py:138 neighbourhood (the old bug's shape) — RED on the new `--root <tmpdir>` subprocess check
- ran `bash .vteam/scripts/gate.sh` on a fresh `init` repo inside e2e (tests/e2e.mjs:244) — GREEN, and the transcript carries `▶ stale-verdict:` for the first time in any profile

Traces: core/scripts/gate.py:101, core/scripts/preflight.sh:85, src/cli/update.mjs:57, src/cli/manifest.mjs:160, `node tests/e2e.mjs` (192/192), `node bin/vteam.mjs doctor` (33 selftests green, manifest 171 files intact), `bash .vteam/scripts/gate.sh` (GREEN, 14 steps ran, stale-verdict among them)

## R2 — adversarial read of the diff (what the probes cannot see)
APPROVE

Tried to break:
- looked for a way `prune()` could delete a user's own file: it iterates the OLD manifest only (src/cli/manifest.mjs:160), so a `.claude/skills/<theirs>/SKILL.md` the framework never recorded is never a candidate; `owned` paths short-circuit before the hash test; a modified orphan is kept. Ran e2e 5b's three planted orphans (unmodified / modified / owned) — removed / kept / untouched.
- looked for a prefix escape: `prunable` is built from the trees update actually refreshed (src/cli/update.mjs:57 neighbourhood — `.vteam/scripts/`, `.vteam/profiles/<profile>/`, `<paths.team>/`, provider dir, and each RE-RENDERED tool's `outputDirs`). A tool whose marker is gone contributes no prefix, so a stale manifest cannot sweep its files. Confirmed by reading; not fixture-tested — noted.
- checked the one behaviour change with no test: on a FRESH `init`, a pre-existing `.claude/agents/<vteam name>.md` is now force-written like every other framework file (adapters/claude-code.mjs:43 → init's `guard.force`), where it used to be kept with a warning. `update` never clobbers it (sync parks `.new`). Accepted because init already owned `.claude/skills/` the same way and refuses to run twice; called out in the PR so the owner can veto.
- tried the YAML scalar path for the new `requires_cmd` in profiles/generic/gates.yaml:51: the value begins with `t`, carries no ` #`, so `_parse_scalar` returns it raw; the gate ran it on this repo and on the e2e fixture (declared skip path exercised by reading only — no remote-tracker fixture exists; the probe's `|| echo markdown` fallback means a missing key still runs the step, which is the strict direction)
- tried to make `replace_section` (core/scripts/lib/evdpack.py:193) eat a following section: heading prefix + `\b`, lazy `.*?` up to `^## ` — a third re-run keeps `## Notes for QA` (asserted in evd_check's selftest); a manifest with NO heading gets the block appended after one blank line
- read the copilot/windsurf quoting (adapters/copilot.mjs:15, adapters/windsurf.mjs:13): `"` inside the description becomes `'`, the slice happens BEFORE quoting so a cut description cannot end mid-escape; a description with a backslash would still be a YAML escape — none of the 40 workflow/competency descriptions carries one (`grep -c '\\\\' core/workflows/*.md` = 0)
- `src/cli/init.mjs:444`: an unparseable `package.json` yields `deps = {}` → `node`, never a crash; a Next app with `next` only in `devDependencies` still detects (both maps merged)

Traces: src/cli/manifest.mjs:160, src/cli/update.mjs:57, adapters/claude-code.mjs:43, core/scripts/lib/evdpack.py:193, src/cli/init.mjs:444, `python3 .vteam/scripts/review_check.py VT-24 --sha WORKTREE`, `grep -c '\\\\' core/workflows/*.md`

## Not fixed here, filed
- VT-25: `orca_team.sh`, `ui-evidence.mjs`, `ui_fidelity.mjs`, `auth.mjs`, `prepublish-check.mjs` have no test of any kind.
- The remote-tracker skip branch of the `stale-verdict` step has no fixture (needs a jira/github-configured repo in e2e).
