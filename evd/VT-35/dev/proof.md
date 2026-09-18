# VT-35 · proof — commands run on 2026-09-18 in the worktree, with their real output

## 1. RED before: the parallel selftest case was written first, against no implementation
```
$ python3 core/scripts/parallel_check.py --selftest
  File ".../core/scripts/parallel_check.py", line 642, in _selftest
    wts = worktree_branches(r)
NameError: name 'worktree_branches' is not defined
```

## 2. GREEN after: the three selftests carrying the new cases
```
$ bash core/scripts/lane_env.sh --selftest
lane_env selftest: OK (stable per worktree + distinct ports/dbs across worktrees and lanes + marker written + parity with init.derivePort + non-sqlite hint)
$ bash core/scripts/app_check.sh --selftest
app_check selftest: OK (SKIP on unset url + UP on a live server + health path joined + DOWN red naming app.start + FOREIGN red on a stranger's server + APP_URL from lane_env honoured over config + trailing flag refused)
$ python3 core/scripts/parallel_check.py --selftest
parallel_check selftest: OK (… lane isolation: two in-flight worktrees without lane_env markers red, each with its own env green, one shared port red, a single worktree exempt)
```
The lane_env selftest's parity case runs `derivePort()` from `src/cli/init.mjs` on the same
temp checkout and asserts the helper's `PORT` equals it — the two writers cannot drift silently.

## 3. Mutations — code-only, tests kept (KB-R1), each restored from a byte copy afterwards
```
M1  parallel_check: check_lane_envs returns [] before looking at any worktree
$ python3 core/scripts/parallel_check.py --selftest
AssertionError: two in-flight worktrees without lane_env markers must both red:
[]                                                                    → RED, exit 1

M2  parallel_check: the duplicate-port branch disabled (`if False:`)
$ python3 core/scripts/parallel_check.py --selftest
AssertionError: two lanes on one port must red:
[]                                                                    → RED, exit 1

M3  lane_env: the lane name no longer enters the hash (key = path)
$ bash core/scripts/lane_env.sh --selftest
lane_env selftest: FAIL — reviewer lane R1 derived the author's port 3885   → RED, exit 1

M4  app_check: APP_URL ignored again (URL="${URL_OVERRIDE:-$(vteam_cfg app.url "")}")
$ bash core/scripts/app_check.sh --selftest
app_check selftest: FAIL (APP_URL pointing at a closed port must red, got: APP: SKIP — app.url not set …)   → RED, exit 1
```
After each restore the three selftests were re-run and read OK (section 2); `git status` lists
only the intended files.

## 4. Mirrors, suite, gate
```
$ node bin/vteam.mjs update
✓ .vteam runtime refreshed · ✓ doctrine refreshed in docs/team · ✓ claude-code workflows re-rendered
$ node bin/vteam.mjs doctor
✅ manifest verified (174 framework-owned files intact)
✅ gate selftests green (36 discovered checks prove they can red)
❌ core.hooksPath is /Users/…/vteam/.githooks   ← the shared repo config's absolute path, a worktree
                                                  artefact seen by every fork today; not this change
$ npm test        (first run, before the README counts were updated)
  ❌ README's selftest count matches discovery (36)   README claims [35], discovery found 36
  ❌ README claims "214" but the suite ran 219
E2E: RED — 217/219 checks passed
```
```
$ npm test        (README says 36 selftests / 219 checks)
conformance: OK — 17 fixtures, ctx.py == ctx.mjs (== ctx.sh on its scalar subset), error fixtures red in both.
conformance: OK — ledger grammar, 10 rows, lib/ledger.py == board.mjs parseLedger (kind/tok/actor/malformed).
E2E: GREEN — 219/219 checks passed
$ bash .vteam/scripts/gate.sh
GATE: GREEN (14 steps ran, 1 declared skips) — 1 ADVISORY FAILED: schedule   ← pre-existing (A3 overdue, D17 due)
```
