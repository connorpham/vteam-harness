# VT-38 · proof — commands run on 2026-09-18 with their real output

## 1. The miscount, measured on this repo
```
$ git branch --format="%(refname:short)" | grep -cE "^(feat|fix)/"       → 33
$ git branch --merged main --format="%(refname:short)" | grep -cE "^(feat|fix)/"  → 32
$ npx vteam-harness graph --plan   # before
15 schedulable · 21 in flight · 0 blocked · 1 wave(s)
$ npx vteam-harness graph --plan   # after
35 schedulable · 1 in flight · 1 blocked · 1 stale WIP · 2 wave(s)
```
One branch is genuinely unmerged (`feat/VT-5-team-room`). The other twenty were leftovers a
merge left behind, and the planner called every one of them work in hand.

## 2. What the plan says now
```
── IN FLIGHT (not re-dispatchable)
   VT-5  In Progress · branch pushed

── STALE WORK IN PROGRESS (status says one thing, the branches say another)
   VT-2  In Progress · no unmerged branch
   → these are counted as schedulable, not as running. Move each to the state it is in.

── BLOCKED
   VT-28  waits on decision D18

── CRITICAL PATH  0 day(s)  (INCOMPLETE — see warnings)
```

## 3. The nine drifted tickets, corrected against their evidence
```
$ python3 .vteam/scripts/graph_check.py
```
VT-3, VT-4, VT-6, VT-7, VT-8 and VT-9 each had a merged branch and a dispatch row → In Review
(Done stays QA's call). VT-14 is blocked by VT-13 → To Do. VT-28 waits on a decision → the
`blocked-by` field now says so. VT-2 shipped with NO dispatch row: it keeps In Progress, the
record gap is written into the ticket, and the grammar question went to the decision queue
rather than being settled by inventing a token count.

## 4. Tests and gate
```
$ node src/cli/graph.mjs --selftest
  graph selftest: OK (plan: chain→3 waves, done-dep flat, scope-disjoint batching, parallel ceiling, Q
  A lane split, in-flight excluded, cycle+decision blocked, critical path exact and honestly incomplet
  e; gate parity: graph_check.py reds on the same 3 findings, clean on the same 2 tickets; 6 nodes/5 e
  dges; ready set exactly {GRA-2}; dangling GRA-3→GHOST-9; cycle GRA-4→GRA-5→GRA-4; done_without_verdi
$ python3 core/scripts/graph_check.py --selftest
  graph_check selftest: OK (coherent graph green + 11 reds + 4 new greens: dangling, cycle, done-sans-
  verdict, done-with-FAIL, identical repeat, loop budget, out-of-scope commit, stale stop state by rec
  orded: line and by mtime (Blocked, In Review and a fresh stop state pass) + status drift reported an
$ npm test
E2E: GREEN — 234/234 checks passed
$ bash .vteam/scripts/gate.sh
GATE: GREEN (15 steps ran, 1 declared skips) — 1 ADVISORY FAILED: schedule
```

## 5. Mutations
mutations.md — four code-only mutations, tests kept, all RED.
