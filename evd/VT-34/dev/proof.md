# VT-34 · proof — every line below is a command run on 2026-09-18 in the worktree and its real output

## 1. `stop_state.sh --selftest` (six cases)

```
$ bash core/scripts/stop_state.sh --selftest
stop_state selftest: OK (dirty ticket branch recorded + fields · idempotent tasksheet line · ahead-only recorded · clean+level skips · keyless skips · VTEAM_TICKET override)
```

Two fixture defects were found by the selftest itself while writing it and fixed in the fixture,
not the script: (a) deleting the tracked STOP-STATE.md after the WIP commit made the tree dirty
again ("clean tree count 0" FAIL), (b) the second run rewrites the file so `git checkout main`
needs `git checkout -- .` first.

## 2. `graph_check` stale-stop-state rule — RED before, GREEN after

Fixture first (PROJ-11 "In Progress" + `STOP-STATE.md` recorded 2026-01-01), rule absent:
```
$ python3 core/scripts/graph_check.py --selftest
AssertionError: a 7-day-old stop state on an open ticket must red:
✅ graph_check: work graph coherent (4 tickets, loop budget 4/day, scope armed where declared)
exit 1
```
Rule added (`check_stop_states`, wired in `main` for the markdown tracker):
```
$ python3 core/scripts/graph_check.py --selftest
graph_check selftest: OK (coherent graph green + 11 reds + 4 new greens: … stale stop state by recorded: line and by mtime (Blocked and a fresh stop state pass) …)
exit 0
```

## 3. Install path: hook, settings, manifest, e2e

```
$ node bin/vteam.mjs update
✓ .vteam runtime refreshed
✓ doctrine refreshed in docs/team
✓ claude-code workflows re-rendered
$ git status --short        # what update touched in this repo
 M .claude/settings.json           (SessionEnd entry merged)
 M .claude/skills/dev/SKILL.md     (Stopping mid-ticket)
 M .vteam/manifest.json
?? .claude/hooks/vteam-session-end.sh
?? .vteam/scripts/stop_state.sh
$ node bin/vteam.mjs doctor
✅ manifest verified (173 framework-owned files intact)
✅ gate selftests green (35 discovered checks prove they can red)
❌ core.hooksPath is /Users/connorpham/Documents/vteam/.githooks — (worktree artefact: the shared
   repo config points at the main checkout's hooks dir; not introduced by this change)
```
First e2e run, before the README numbers were touched — every new check green, only the count stale:
```
$ npm test
  ✅ README's selftest count matches discovery (35)
  ❌ README claims "199" but the suite ran 207 — fix README.md's number
E2E: RED — 206/207 checks passed
```
After `README.md`: 34 → 35 selftests (two places), 199 → 207 checks:
```
$ npm test
conformance: OK — 17 fixtures … · conformance: OK — ledger grammar, 10 rows …
  ✅ README's selftest count matches discovery (35)
  ✅ README's "207 checks" claim matches the suite (207)
E2E: GREEN — 207/207 checks passed
```

## 4. Mutation probes — code-only, the new tests kept, source restored byte-identical after each

```
$ bash scratchpad/vt34/mutations.sh
── M1 graph_check: STOP_STATE_MAX_DAYS 7 → 7000 (the rule can no longer fire)
exit 1   AssertionError: a 7-day-old stop state on an open ticket must red:
── M2 graph_check: Blocked no longer exempt
exit 1   AssertionError: Blocked (with the stop state as the reason) must pass:
── M3 stop_state: tasksheet line appended without removing the old one (idempotency lost)
exit 1   stop_state selftest: FAIL — second run must not duplicate the tasksheet line
── M4 stop_state: the 'ahead of base' leg dropped (only a dirty tree records)
exit 1   stop_state selftest: FAIL — ahead-of-base must record (+1)
sources byte-identical to pre-mutation
both selftests GREEN again
$ bash scratchpad/vt34/m5.sh    # adapter stops wiring SessionEnd (HOOK_EVENTS loses the entry)
e2e exit 1
  ❌ t1 settings.json carries the SessionEnd entry
  ❌ SessionEnd entry merged alongside the user's hooks too
E2E: RED — 205/207 checks passed
adapter restored byte-identical
```
M5 is also the RED-before for the two settings checks; the "hook script exists" and "records the
stop state" checks stay green under M5 because the script install and the settings merge are
separate steps — which is why both are checked.

## 5. Gate on the finished branch

```
$ bash .vteam/scripts/gate.sh
GATE: GREEN (14 steps ran, 1 declared skips) — 1 ADVISORY FAILED: schedule   (pre-existing: A3 overdue, D17 due, plan has no current sprint)
$ npm test
E2E: GREEN — 207/207 checks passed
```
