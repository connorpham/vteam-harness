# VT-2: watchable dev & QA sessions — app env config, headed Chrome, editor opening

- status: In Progress
- assignee: Connor Pham
- estimate: 1d
- labels: dx, qa-lane, dev-lane

## Why

The /qa workflow demands a "HEADED" browser run four times but never names a
mechanism — no browser tool, no env bring-up command, no app URL config; the
`base=` argument is read by nothing and /verify ships a dead `--headed` flag.
The /dev workflow has zero editor integration and hardcodes one profile's
headless capture script. The owner wants both lanes watchable: /dev opens the
files it edits in the owner's editor and sees the change running; /qa plans
first, then drives a REAL Chrome window through the journey like a human QA.

## Acceptance criteria (testable)

1. Given a repo with an `app:` section (start/url/health) in vteam.config.yaml,
   when `bash .vteam/scripts/app_check.sh --wait N` runs, then it prints
   `APP: UP <url> (HTTP <code>)` against a live server, `APP: DOWN … — start it
   with: <app.start>` (exit 1) against a dead one, and `APP: SKIP` (exit 0)
   when `app.url` is unset. Spec: docs/DESIGN.md §2 (app section).
2. Given Playwright is installed in the target repo, when a QA journey script
   imports `launch`/`shot` from `.vteam/scripts/browser.mjs`, then Chrome opens
   HEADED (`channel: "chrome", headless: false`) unless `app.headed: never` or
   `EVD_HEADED=0`, and `shot()` writes `NN_<name>.png` into the TC folder.
3. Given `app.open_files` is `auto|code|cursor`, when
   `bash .vteam/scripts/open_files.sh <file:line>` runs, then the file opens in
   the detected editor CLI; `none` or no CLI on PATH prints one line and exits 0.
4. Rendered dev/qa/verify skills carry an adapter-injected Environment block
   naming these commands; core workflows stay tool-neutral.
5. `evd_check.py` reds a QA dossier missing `verifysheet.md` (the V1/V2 plan)
   and its selftest proves the mutation.
6. `node tests/conformance.mjs` and `npm test` green; README check count matches.

## Out of scope

- No `.claude/launch.json` / Browser-pane path (owner chose real Chrome).
- Gates never start the dev server themselves.
- No QA-side `NN_*.png` naming gate (the `shot()` helper enforces it by construction).

## Comments

### 2026-09-01 Connor Pham
claimed 2026-09-01T00:00:00Z · branch feat/VT-2-live-dev-qa-env
