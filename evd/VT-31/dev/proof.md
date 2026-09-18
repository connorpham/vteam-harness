# VT-31 · proof — commands run on 2026-09-18 in the worktree, with their real output

## 1. The finding, from the arm's own log
`~/Documents/vteam-vs-bmad/arm-a-vteam/RUNLOG.md` E2: "`app:` was empty in `vteam.config.yaml`, so `app_check.sh` printed `APP: SKIP` and the lanes had no app to drive." E7: "`app_check.sh` reported `APP: UP http://127.0.0.1:3000` before this arm had started anything … another process on this machine — plausibly the other benchmark arm — owns port 3000." E15: "A whole accessibility suite measured another process's server and reported 31 passes."

## 2. RED before, GREEN after (tests kept, code mutated)
```
$ sed -i '' 's/const nextApp = detectNextApp(root);/const nextApp = false \&\& detectNextApp(root);/' src/cli/init.mjs   # old behaviour
$ node tests/e2e.mjs
  ❌ Next repo: init prefills app.url with the port derived from the checkout path
  ❌ Next repo: app.start runs next on that same port and app.health probes /
  ❌ init tells the owner which port was pinned and why
E2E: RED — 201/204 checks passed
$ cp init.bak src/cli/init.mjs && node tests/e2e.mjs
E2E: GREEN — 204/204 checks passed
```
The two checks that stay green under the mutation ("three checkouts, three ports" and "a repo WITHOUT next keeps the empty block") test the function and the unchanged path; the three that go red are the behaviour this ticket adds.

## 3. Probes
```
$ node /tmp/vt31/probe-b.mjs
/var/tmp → 3297 · /private/var/tmp → 3297 · equal: true
fixed paths → 3660, 3717, 3698 · all in [3100,3900): true
$ node tests/conformance.mjs
conformance: OK — 17 fixtures, ctx.py == ctx.mjs (== ctx.sh on its scalar subset), error fixtures red in both.
conformance: OK — ledger grammar, 10 rows, lib/ledger.py == board.mjs parseLedger (kind/tok/actor/malformed).
```
The first GREEN attempt was RED on the same three checks because the test hashed `/var/folders/…` while init hashed `/private/var/folders/…`; `derivePort` now hashes the realpath (src/cli/init.mjs:479).

## 4. Repo checks
```
$ bash .vteam/scripts/gate.sh
GATE: GREEN (14 steps ran, 1 declared skips) — 1 ADVISORY FAILED: schedule   # advisory pre-exists this ticket (A3 overdue, D17 due)
$ npm test
conformance: OK — 17 fixtures, ctx.py == ctx.mjs (== ctx.sh on its scalar subset), error fixtures red in both.
conformance: OK — ledger grammar, 10 rows, lib/ledger.py == board.mjs parseLedger (kind/tok/actor/malformed).
  ✅ README's "204 checks" claim matches the suite (204)
E2E: GREEN — 204/204 checks passed
```
