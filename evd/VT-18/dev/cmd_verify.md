# VT-18 — command verification

## AC1-AC5, AC7 — graph_check selftest carries the new branches
```
$ python3 core/scripts/graph_check.py --selftest
graph_check selftest: OK (coherent graph green + 9 reds + 2 new greens: dangling, cycle, done-sans-verdict, done-with-FAIL, identical repeat, loop budget, out-of-scope commit — + loud skips: undeclared scope, remote tracker — + attribution, 17 positive / 12 negative: leading key attributed (bare/`type:`-prefixed/`feat(KEY):`/multi-scope `feat(a,KEY):`/`[KEY]`/`Revert "…"`), prose mention + longer key + merge-commit NOT, both directions proven end-to-end on the same out-of-scope directory)
```

The four cases added (m1b-m1d in the fixture): an edge onto an OPEN decision passes and prints
`blocked by decision Q1`; an edge onto a ghost key still reds; a terminal ticket citing a
DECIDED row passes; the same ticket citing the OPEN row reds with "cannot be closed by a question".

## AC1 + AC3 on the real field repo
```
$ python3 .vteam/scripts/graph_check.py    # testbed, TB-7 closed won"'t-fix citing Q6 (DECIDED)
✅ graph_check: work graph coherent (9 tickets, loop budget 4/day, scope armed where declared)
```

Before this ticket the same repo printed:
```
TB-7: judged done with NO evd/TB-7/REPORT.md — only QA closes (raci §2), and QA's act IS
      the verdict (MAST 1.2: a lane closed outside its rights)
GATE: RED at graph
```

## AC6 — a ledger row cannot cite a decision that was never written

Run against a throwaway repo whose queue holds only Q1, so the outcome is not read off the
project's own ledger:
```
cites Q1 (exists)        green
cites D13 (absent)       RED   line 3: cites D13, which the decision queue does not hold —
                               a row justified by a decision that was never written is a row
                               justified by nothing
```

## What this does not do

It does not move a ticket when its decision is answered. The `⏸` line simply stops printing.
Rewriting someone else's status is not a gate's job, and a released edge still needs a human to
decide the ticket is next.
