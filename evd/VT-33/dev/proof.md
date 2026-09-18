# VT-33 · proof — commands run on 2026-09-18 with their real output

## 1. Selftest (the fixture that can go red)
```
$ python3 core/scripts/context_budget.py --selftest
context_budget selftest: OK (skill + role + INDEX + always-competency mandatory, missing file ignored, repeat counted once, on-demand listed apart, over-budget line at a tiny budget, json, unknown lane refused)
```

## 2. The measurement on this repo (the deliverable)
```
$ python3 core/scripts/context_budget.py --all
context_budget — doctrine each lane loads at start (≈tokens = bytes / 4)
── dev: .claude/skills/dev/SKILL.md
   MANDATORY (every run)                                        bytes   ≈tok
   .claude/skills/dev/SKILL.md                                  35722   8931   the lane skill
   docs/team/competencies/dev/dev-identity.md                    4258   1065   identity
   docs/team/roles/dev.md                                        3851    963   role playbook
   docs/team/competencies/dev/INDEX.md                           6854   1714   competency index
   docs/team/competencies/dev/dev-codebase-design.md             4005   1002   INDEX `always`, loads at T2
   docs/team/competencies/dev/dev-error-handling.md              3848    962   INDEX `always`, loads at T3
   docs/team/competencies/dev/dev-security-basics.md             4371   1093   INDEX `always`, loads at T3
   docs/team/competencies/dev/dev-testing-craft.md               4201   1051   INDEX `always`, loads at T2
   = mandatory total                                            67110  16778   budget 40000
   ON DEMAND (when the ticket matches)                          bytes   ≈tok
   .vteam/scripts/browser.mjs                                    7557   1890
   .vteam/scripts/app_check.sh                                   8348   2087
   .vteam/scripts/open_files.sh                                  5017   1255
   docs/qa/knowledge-base.md                                     3815    954
   docs/qa/known-issues.md                                        295     74
   docs/specs/changes.md                                          392     98
   docs/team/parallel-transport.md                               6684   1671
   docs/team/model-routing.md                                    4875   1219
   docs/team/review-standard.md                                  5258   1315
   docs/team/bdd-report.md                                       2342    586
   = on-demand total                                            44583  11146
── ba: .claude/skills/ba/SKILL.md
   MANDATORY (every run)                                        bytes   ≈tok
   .claude/skills/ba/SKILL.md                                   17195   4299   the lane skill
   docs/team/roles/ba.md                                        11902   2976   role playbook
   docs/team/competencies/ba/INDEX.md                            1169    293   competency index
   docs/team/competencies/ba/ba-acceptance-criteria.md           6098   1525   INDEX `always`, loads at B2
   docs/team/competencies/ba/ba-story-slicing.md                 4999   1250   INDEX `always`, loads at B2
   = mandatory total                                            41363  10341   budget 40000
   ON DEMAND (when the ticket matches)                          bytes   ≈tok
   docs/qa/known-issues.md                                        295     74
   docs/qa/knowledge-base.md                                     3815    954
   docs/specs/INDEX.md                                            309     78
   = on-demand total                                             4419   1105
── pm: .claude/skills/pm/SKILL.md
   MANDATORY (every run)                                        bytes   ≈tok
   .claude/skills/pm/SKILL.md                                   25062   6266   the lane skill
   docs/team/roles/pm.md                                         3075    769   role playbook
   docs/team/competencies/pm/INDEX.md                             789    198   competency index
   docs/team/roles/sa.md                                         3527    882   role playbook
   docs/team/competencies/pm/pm-prioritisation.md                5195   1299   INDEX `always`, loads at P1
   = mandatory total                                            37648   9412   budget 40000
   ON DEMAND (when the ticket matches)                          bytes   ≈tok
   docs/pm/decisions.md                                         21558   5390
   docs/pm/log.md                                               18590   4648
   docs/pm/plan.yaml                                              394     99
   docs/team/parallel-transport.md                               6684   1671
   docs/specs/changes.md                                          392     98
   docs/qa/knowledge-base.md                                     3815    954
   = on-demand total                                            51433  12859
── qa: .claude/skills/qa/SKILL.md
   MANDATORY (every run)                                        bytes   ≈tok
   .claude/skills/qa/SKILL.md                                   33974   8494   the lane skill
   docs/team/competencies/qa/qa-identity.md                      4473   1119   identity
   docs/team/roles/qa.md                                         5881   1471   role playbook
   docs/team/competencies/qa/INDEX.md                            4110   1028   competency index
   docs/team/competencies/qa/qa-case-writing.md                  4654   1164   INDEX `always`, loads at V2
   docs/team/competencies/qa/qa-heuristics.md                    4514   1129   INDEX `always`, loads at V2
   docs/team/competencies/qa/qa-hostile-inputs.md                3944    986   INDEX `always`, loads at V2
   docs/team/competencies/qa/qa-report-writing.md                3797    950   INDEX `always`, loads at V5
   docs/team/competencies/qa/qa-test-design.md                   4539   1135   INDEX `always`, loads at V2
   = mandatory total                                            69886  17472   budget 40000
   ON DEMAND (when the ticket matches)                          bytes   ≈tok
   .vteam/scripts/browser.mjs                                    7557   1890
   .vteam/scripts/app_check.sh                                   8348   2087
   .vteam/scripts/open_files.sh                                  5017   1255
   .vteam/scripts/annotate.py                                   15272   3818
   .vteam/scripts/evd_check.py                                  47919  11980
   docs/team/competencies/qa/qa-requirement-smells.md            5169   1293
   docs/qa/knowledge-base.md                                     3815    954
   docs/qa/known-issues.md                                        295     74
   docs/specs/changes.md                                          392     98
   docs/team/bdd-report.md                                       2342    586
   = on-demand total                                            96126  24032
── verify: .claude/skills/verify/SKILL.md
   MANDATORY (every run)                                        bytes   ≈tok
   .claude/skills/verify/SKILL.md                                7261   1816   the lane skill
   = mandatory total                                             7261   1816   budget 40000
   ON DEMAND (when the ticket matches)                          bytes   ≈tok
   .vteam/scripts/browser.mjs                                    7557   1890
   .vteam/scripts/app_check.sh                                   8348   2087
   .vteam/scripts/open_files.sh                                  5017   1255
   docs/qa/knowledge-base.md                                     3815    954
   = on-demand total                                            24737   6185
── team: .claude/skills/team/SKILL.md
   MANDATORY (every run)                                        bytes   ≈tok
   .claude/skills/team/SKILL.md                                 16896   4224   the lane skill
   = mandatory total                                            16896   4224   budget 40000
   ON DEMAND (when the ticket matches)                          bytes   ≈tok
   docs/team/parallel-transport.md                               6684   1671
   docs/qa/knowledge-base.md                                     3815    954
   = on-demand total                                            10499   2625
── plan: .claude/skills/plan/SKILL.md
   MANDATORY (every run)                                        bytes   ≈tok
   .claude/skills/plan/SKILL.md                                 11972   2993   the lane skill
   = mandatory total                                            11972   2993   budget 40000
   ON DEMAND (when the ticket matches)                          bytes   ≈tok
   docs/qa/knowledge-base.md                                     3815    954
   = on-demand total                                             3815    954
── docs: .claude/skills/docs/SKILL.md
   MANDATORY (every run)                                        bytes   ≈tok
   .claude/skills/docs/SKILL.md                                 18544   4636   the lane skill
   = mandatory total                                            18544   4636   budget 40000
   ON DEMAND (when the ticket matches)                          bytes   ≈tok
   docs/pm/decisions.md                                         21558   5390
   docs/specs/INDEX.md                                            309     78
   docs/qa/knowledge-base.md                                     3815    954
   docs/qa/known-issues.md                                        295     74
   = on-demand total                                            25977   6495
✅ context_budget: every lane within 40000 tokens at start (heaviest: qa ≈ 17472 tokens mandatory)
```

## 3. Mutations — code-only, selftest kept (KB-R1)
```
M1  core/scripts/context_budget.py:104  is_file guard removed → a missing file is "loaded"
$ python3 core/scripts/context_budget.py --selftest
FileNotFoundError: [Errno 2] No such file or directory: '…/docs/team/competencies/dev/dev-identity.md'
exit 1
M2  core/scripts/context_budget.py:136  over_budget forced False
$ python3 core/scripts/context_budget.py --selftest
✅ context_budget: every lane within 10 tokens at start (heaviest: dev ≈ 258 tokens mandatory)
AssertionError: a tiny budget must print the over-budget line and still exit 0
exit 1
M3  core/scripts/context_budget.py:87  INDEX `always` rows ignored
$ python3 core/scripts/context_budget.py --selftest
AssertionError: ['.claude/skills/dev/SKILL.md', 'docs/team/roles/dev.md', 'docs/team/competencies/dev/INDEX.md']
exit 1
```
Restored after each probe (`cmp` against the saved copy: identical); selftest OK again.

## 4. Repo checks
(appended below after the final gate run)
```
$ npm test
conformance: OK — 17 fixtures, ctx.py == ctx.mjs (== ctx.sh on its scalar subset), error fixtures red in both.
conformance: OK — ledger grammar, 10 rows, lib/ledger.py == board.mjs parseLedger (kind/tok/actor/malformed).
E2E: GREEN — 216/216 checks passed
$ python3 .vteam/scripts/gate.py
GATE: GREEN (15 steps ran, 1 declared skips) — 1 ADVISORY FAILED: schedule
$ node bin/vteam.mjs doctor
✅ manifest verified (174 framework-owned files intact)
✅ gate selftests green (36 discovered checks prove they can red)
```
