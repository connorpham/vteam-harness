# VT-40 · proof — commands run on 2026-09-18

## 1. What CI saw (PR #89, run 35329884243, Linux)
```
❌ doctor exits 0 — an honest unknown WARNS, it does not red
   ❌ selftest RED: lane_env.sh
   lane_env selftest: FAIL — reviewer lane R1 derived the author's port 3724
```
The e2e fixture builds its repo in a fresh `mktemp` directory, so the hashed path — and with
it the derived port — differs on every run. 3100..3899 is 800 buckets; two lanes of one
worktree collide with probability ~1/800 per pair, so main was green by luck, not by design.

## 2. After the fix
```
$ for i in 1 2 3 4 5; do bash .vteam/scripts/lane_env.sh --selftest; done
  lane_env selftest: OK (stable per worktree + distinct ports/dbs across worktrees and lanes + marker 
  written + parity with init.derivePort + non-sqlite hint + a planted collision stepped over and said 
  out loud)
  (five consecutive runs, none red)
```

## 3. Mutations (code-only, the tests kept)
```
$ port="$derived"   # no stepping
lane_env selftest: FAIL — a port another lane already claims must be stepped over, got 3648
exit 1

$ (a lane no longer skips its OWN marker)
lane_env selftest: FAIL — the same worktree must derive the same environment twice
exit 1
```
The second mutation is the one that matters: without the self-exclusion a lane would walk away
from its own port on every re-run, and nothing downstream would be stable.
