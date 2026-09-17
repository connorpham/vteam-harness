# Judge repairs before the 2026-09-17 scoring pass

The two arms were built on 2026-09-03/04 and never judged. Scoring on 2026-09-17 needed the
repairs below. Every repair is environmental or a probe defect, applied **before either arm was
scored**, and applied to both arms identically. None touches an arm's code.

| # | What was broken | Evidence | Repair |
|---|---|---|---|
| J1 | `arm-b-bmad/node_modules` had lost its packages (34 dirs, no `next`) | `npm run start` → `sh: next: command not found`, exit 127 | `npm ci` from arm-b's committed lockfile → 337 dirs, next 16.3.4 |
| J2 | `judge/node_modules` broken | `@playwright/test/cli.js` MODULE_NOT_FOUND | `npm ci` in `judge/`, Playwright 1.62.1 + chromium |
| J3 | Probe locator `getByLabel(/mật khẩu\|password/i)` is ambiguous when an arm ships an aria-labelled *show password* button (`aria-label="Hiện mật khẩu"`) — a legal, good-a11y control the spec does not forbid | arm-b: 8 of 12 a-core probes failed with `strict mode violation … resolved to 2 elements` (textbox + button) | field locators → `getByRole('textbox', { name: … })` in a-core, b3-hardening, c-reset, d-a11y (24 sites, email and password). Calibration rerun: see below |
| J4 | Generated Prisma client can be stale vs the schema being scored | arm-a seed: `P2022 User.failedAttempts does not exist` | `npx prisma generate` in each arm before its probes |
| J5 | `scaffold/` is iCloud-evicted (10 615 dataless files; `~/Documents` is under iCloud Drive with Optimize Mac Storage) — any content read hangs, so `calibrate.mjs` stalled in its first `rsync` for 10+ min with 5 files copied | `ls -lO scaffold/app/layout.tsx` → `compressed,dataless`; `brctl download` did not materialise it within the run | `scaffold/` rebuilt from the arms' shared baseline commit (`arm-b 8e0106b7`, identical file list plus the CLAIMS.md/RUNLOG.md templates); evicted tree kept at `scaffold.evicted-icloud/` for the owner |

## arm-a is scored at its stop state, not at HEAD

arm-a's last commit does not run: `schema.prisma` at HEAD lacks `failedAttempts`, while the
throttle migration and 10 other files were left uncommitted when the run stopped. Scoring the
committed state alone would score a tree that cannot even seed. arm-a is therefore scored as it
was left — working tree, 11 uncommitted files included. Both facts belong next to any number
from this run. arm-b's tree is clean.

## Cost

Token/time cost was to be read from each arm's RUNLOG.md/CLAIMS.md. Whatever `cost.mjs` can
recover from those files is reported as-is; nothing is estimated.

## Calibration after J3

(filled in below by the operator from `calibrate.log`)

`node judge/calibrate.mjs` on 2026-09-17, after J3 and J5, against the reference app built from the
rebuilt scaffold + `judge/reference`:

```
reference scores 91/91 = 100%
Every criterion is reachable. The suite can go green as well as red.
```

39 probes, 7 files, all pass (12 · 1 · 2 · 5 · 1 · 10 · 8). The 0 % side of the calibration
(empty scaffold) was proven on 2026-09-03 and is unaffected by J3: a role-based locator that finds
nothing fails exactly as the label-based one did.

## Side effect of the operator commit

arm-a's stop state was committed by the operator on 2026-09-17 (`356bfcc`, per PROTOCOL §3, no
content change). `truth.mjs` counts it: the scorecard's "Commits 28 / commitsSinceBaseline 26"
includes it, and `repo.lastCommitAt`/`elapsedMinutes` (20 636) are polluted by its date. The
headline uses neither; the arm's own commit span is 2026-09-03 12:28 → 2026-09-04 16:33.
