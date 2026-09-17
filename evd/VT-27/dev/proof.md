# VT-27 · proof — every claim below is a command that was run on 2026-09-17 and its real output

## 1. Judge calibration after the locator repair (J3) and the scaffold rebuild (J5)
```
$ node judge/calibrate.mjs
════ calibration ════
reference scores 91/91 = 100%

Every criterion is reachable. The suite can go green as well as red.

(reference app removed; pass --keep to inspect it)
```

## 2. Scoring run (both arms; arm-a at its committed stop state 356bfcc)
```
$ bash judge-run-3.sh   # prisma generate → run-probes → truth → cost per arm, then score
== judge run 3 started 2026-09-17T13:24:04Z ==
==== arm-b-bmad: prisma generate (client must match the schema being scored) ====
==== arm-b-bmad: run-probes (13:24:04) ====
  12 passed (6.5s)
  1 passed (4.4s)
  2 passed (3.6s)
  5 passed (4.5s)
  1 passed (4.1s)
  10 passed (2.0s)
  8 passed (6.0s)
run-probes exit 0
==== arm-b-bmad: truth (13:24:58) ====
  PASS  lint (exit 0)
  PASS  types (exit 0)
  PASS  unit (exit 0)
  PASS  build (exit 0)
truth exit 0
==== arm-b-bmad: cost (13:25:17) ====
cost exit 0
==== arm-a-vteam: prisma generate (client must match the schema being scored) ====
==== arm-a-vteam: run-probes (13:25:17) ====
  11 passed (11.7s)
  1 passed (4.7s)
  2 passed (3.7s)
  5 passed (4.5s)
  1 passed (4.1s)
  10 passed (2.0s)
  6 passed (11.6s)
run-probes exit 0
==== arm-a-vteam: truth (13:26:23) ====
  PASS  lint (exit 0)
  PASS  types (exit 0)
  FAIL  unit (exit 1)
  PASS  build (exit 0)
truth exit 0
==== arm-a-vteam: cost (13:27:40) ====
cost exit 0
==== score (13:27:40) ====
score exit 0
== done 2026-09-17T13:27:40Z ==
```

## 3. Scorecard headline (`results/2026-09-03/SCORECARD.md`, generated 2026-09-17T13:27:40Z)
```
## Headline

| Metric | arm-a-vteam | arm-b-bmad |
| --- | --- | --- |
| Spec integrity | identical | identical |
| Build | green | green |
| Verification all green | NO | yes |
| **AC coverage (weighted)** | **84/91 = 92.3%** | **91/91 = 100%** |
| Criteria passed | 36/39 | 39/39 |
| Overclaims | 3 | 0 |
| Claim accuracy | 92.1% | 100% |
| Mutation score (unit + types) | skipped | 4/5 = 80% |
| Human prompts | — | — |
| Active minutes | — | — |
| Output tokens | — | — |
| Billable input tokens | — | — |

```

## 4. arm-a stop-state commit (PROTOCOL §3 operator step)
```
$ git -C arm-a-vteam log -1 --format="%h %ci %s" ; git status --short | wc -l
356bfcc 2026-09-17 20:25:11 +0700 chore(operator): stop-state commit per PROTOCOL §3
0
```

## 5. This repo on the branch
```
$ bash .vteam/scripts/gate.sh
🟡 advisory schedule: FAILED — reported, not blocking; the condition is about the project, not about this change
GATE: GREEN (14 steps ran, 1 declared skips) — 1 ADVISORY FAILED: schedule
$ npm test
conformance: OK — 17 fixtures, ctx.py == ctx.mjs (== ctx.sh on its scalar subset), error fixtures red in both.
conformance: OK — ledger grammar, 10 rows, lib/ledger.py == board.mjs parseLedger (kind/tok/actor/malformed).
  ✅ README's "199 checks" claim matches the suite (199)
E2E: GREEN — 199/199 checks passed
```

The 0/0 SCORECARD written by the first attempt on 2026-09-17 (broken node_modules in arm-b and in the judge) was overwritten by this run and must not be cited.
