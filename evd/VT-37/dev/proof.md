# VT-37 · proof — commands run on 2026-09-18 with their real output

## 1. The critique, measured before any code was written

| Claim | Verdict | Evidence |
|---|---|---|
| `/pm` derives the dispatch order in prose although the graph has the data | **TRUE** | pm.md P1 legs (a)–(g) + a priority list, reasoned over every open ticket each session |
| Reviewers R1/R2 run sequentially inside a ticket | **FALSE** | `core/workflows/dev.md` T4b: reviewers are "spawned in the SAME message — parallel, empty context, never forked" |
| Incremental gate caching would take the gate from 45 s to 2 s | **FALSE here** | measured below: the 14 bookkeeping steps cost 1.3 s of a 90.8 s gate; the test suite is 89.5 s = 98.6 % |
| The graph is a passive mirror that only prints | **PARTLY** | it already computed `ready` and cycles; what was missing is order, waves, batching and the critical path |

```
$ (timing every gate step, real run)
   89.46s  test
    0.70s  graph
    0.09s  stale-verdict
    0.05s  evd · schedule · evd-ui · bdd-report
    0.04s  competencies · docs-shrink · context-budget · doctrine-source · parallel · ledger
    0.03s  coord · verbatim
   90.76s  TOTAL (16 steps)
```
Caching the bookkeeping steps would save 1.4 % of the gate. The only expensive step is the test
suite, and skipping tests on a diff is the one saving this framework must not take.

## 2. What the plan replaces, measured
```
  today  — 35 open ticket files + plan.yaml + ledger + decisions = 170,772 bytes ≈ 42,693 tokens
  plan   — one JSON                                             =   9,720 bytes ≈  2,430 tokens
  ratio  — 17.6× less to read, and the ordering itself is not reasoned at all
```
The saving is not only the bytes: Kahn's algorithm returns the same answer twice, and an LLM
ordering 35 tickets against seven conditions does not.

## 3. The plan on this repo
```
$ npx vteam-harness graph --plan
EXECUTION PLAN  ·  commit 2f12b06a  ·  parallel 1
15 schedulable · 21 in flight · 0 blocked · 1 wave(s)

── WAVE 0  (start now)
   batch 1: VT-10
     VT-10  /qa  parallel-worktree mode — gates that read siblings fr   [no plan row]
   batch 2: VT-11
     VT-11  /dev  nextjs-prisma profile and init must work on a pnpm/t   [no CODE-SCOPE · no plan row]
   batch 3: VT-12
   …
   VT-2

⚠️  no sprint-plan row for VT-10, VT-11, VT-12, VT-13, VT-15, VT-16… — /pm leg (f): add the row WITH a day-cost before dispatching, or the capacity is spent off the books
⚠️  the critical path is INCOMPLETE: no day-cost for VT-2, VT-3, VT-4, VT-5, VT-6, VT-7 — the number below counts only the tickets that have one

This plan decides ORDER and BATCHES. It never relaxes a gate, and it does not decide:
   · priority overrides: an unanswered PR comment outranks the sprint (/pm P1 priority 0)
   · leg (b): whether a UI ticket's design link is a real oracle — a machine sees a URL, not a design
   · whether an off-plan item is worth a plan row at all
```

## 4. Tests and gate
```
$ node src/cli/graph.mjs --selftest
  graph selftest: OK (plan: chain→3 waves, done-dep flat, scope-disjoint batching, parallel ceiling, Q
  A lane split, in-flight excluded, cycle+decision blocked, critical path exact and honestly incomplet
  e; gate parity: graph_check.py reds on the same 3 findings, clean on the same 2 tickets; 6 nodes/5 e
  dges; ready set exactly {GRA-2}; dangling GRA-3→GHOST-9; cycle GRA-4→GRA-5→GRA-4; done_without_verdi
  ct GRA-6; plan 4h→0.5d; ledger actors An/Binh/Chi; --json byte-stable + sorted; --dot graphviz not i
  nstalled — syntax proven by construction + the assertions above; 9 mutations red — malformed ticket 
  + stray file warned, bad plan item/cost warned, self-block = 1-cycle, 60-node dense DAG proven cycle
  -free in 0ms, jira provider honest with 0 faked edges, bad config degraded, empty repo empty; exit 0
   in every mode)
$ npm test
conformance: OK — 17 fixtures, ctx.py == ctx.mjs (== ctx.sh on its scalar subset), error fixtures red in both.
conformance: OK — ledger grammar, 10 rows, lib/ledger.py == board.mjs parseLedger (kind/tok/actor/malformed).
E2E: GREEN — 232/232 checks passed
$ bash .vteam/scripts/gate.sh
GATE: GREEN (15 steps ran, 1 declared skips) — 1 ADVISORY FAILED: schedule
```

## 5. Mutations
mutations.md — six code-only mutations, tests kept, all RED.
