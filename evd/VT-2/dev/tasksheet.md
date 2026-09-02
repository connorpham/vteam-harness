# Task sheet — VT-2: watchable dev & QA sessions

CODE-SCOPE: core/ src/ profiles/ tests/ docs/ README.md evd/VT-2/ .claude/ .vteam/ .gitignore vteam.config.yaml package.json
<!-- scope widened deliberately (graph_check finding): editing core/workflows
     and core/scripts REQUIRES re-rendering this repo's own install via
     `vteam update` — .claude/skills + .vteam/scripts + manifest are the
     rendered mirror of the core change, not new scope. vteam.config.yaml
     carries the new `app:` block the feature reads; package.json is untouched
     content-wise beyond what main already carries. -->

## Requirement

Give both lanes a concrete, watchable environment: a config-declared app
(start command, URL, health), an env bring-up gate, a shared headed-Chrome
launcher for QA journeys, an editor-opening helper for /dev, and an
adapter-injected Environment block that tells each rendered workflow how to
use them. Close two known gaps: the dead `/verify --headed` flag and the
unchecked `verifysheet.md`.

Acceptance criteria: docs/backlog/VT-2.md (6 testable ACs).

## Spec check

- Schema house of record: docs/DESIGN.md §2 — gains the `app:` section.
- Workflow sources: core/workflows/{dev,qa,verify}.md (`.claude/skills/` are
  rendered artifacts; adapters.mjs:70-84 is the injection seam, mirrored on
  routingBlock at adapters.mjs:35-51).
- Parser subset: new config keys must be block-style scalars so ctx.sh's
  vteam_cfg can read them (ctx.sh:13-23); parity fenced by tests/conformance.mjs
  fixture "shipped vteam.config.example.yaml".

## Data model

None — no schema, no migration. Config contract only.

## Code map

- NEW core/scripts/app_check.sh · core/scripts/browser.mjs ·
  core/scripts/open_files.sh (ship to .vteam/scripts via update syncDir,
  update.mjs:44; selftests auto-discovered, doctor.mjs discoverSelftests)
- src/cli/adapters.mjs — envBlock() + injection for dev/qa/verify
- core/workflows/qa.md (V2b, V4, args, DoD) · dev.md (T3, T4.1) · verify.md (args)
- core/scripts/evd_check.py — verifysheet.md check + selftest mutation
- profiles/nextjs-prisma/scripts/{ui-evidence,ui_fidelity}.mjs — base-url
  fallback chain + headed mode
- core/templates/vteam.config.example.yaml · src/cli/init.mjs yaml template ·
  docs/DESIGN.md §2 · tests/{conformance,e2e}.mjs · README.md

## Impact

- Every target repo on next `vteam update`: 3 new scripts land in
  .vteam/scripts (manifest-tracked); dev/qa/verify skills re-render with the
  Environment block. Repos without an `app:` section degrade to today's
  behavior (SKIP paths, "not configured" block) — no gate can newly red except
  evd_check on QA dossiers missing verifysheet.md, which the workflow already
  mandated in prose.
- evd_check tightening affects only future QA runs; evd/VT-1 has no
  verifysheet.md but is a committed historical dossier — gate runs against
  dossiers under verification, not retroactively (nothing re-runs evd_check on
  VT-1; graph_check only requires REPORT.md PASS for Done tickets).
- Playwright stays a TARGET-repo dependency; browser.mjs errors loudly with
  the install command, selftest SKIPs (exit 0) when absent so doctor stays
  green on repos without web UIs.

## Self-review results

- Re-read the staged diff hunk by hunk; every hunk maps to an AC in
  docs/backlog/VT-2.md (no drive-by edits found; the dev.md/ui-evidence.mjs
  hunks were REBASED onto upstream 0.15.0's headed-by-default work rather than
  duplicating it).
- Caught and fixed 2 real bugs of my own before review:
  1. open_files.sh — a FORCED mode (`code`/`cursor`) with the CLI absent
     propagated exit 1 out of the case arm (`cmd && echo`), blocking the
     pipeline the script promises never to block. Fixed + a selftest case.
  2. app_check.sh — a non-numeric `--wait` made the retry loop's arithmetic
     test fail forever (infinite probe). Now validated up front, exit 1.
- Verify evidence: `node tests/conformance.mjs` OK (15 fixtures, new app.*
  keys in the sh subset) · `npm test` → `E2E: GREEN — 155/155 checks passed` ·
  `bash .vteam/scripts/gate.sh` → `GATE: GREEN (5 steps ran, 1 declared
  skips)` (one earlier gate run flaked at 152/155 in the e2e step; two full
  reruns are green and the failing lines were lost to a tail — noted honestly)
  · all four selftests green: app_check, open_files, browser (launch SKIPPED,
  playwright not installed here), evd_check (9 mutations red).
- Intentional deviations: `--headed` flag REMOVED from verify.md args (dead
  flag; headedness lives in `app.headed` + the lanes) · `.claude/skills/*`
  diffs are RENDERED artifacts of the core/workflows edits (vteam update), not
  hand edits.
