# VT-27 · dev tasksheet — publish the vteam-vs-BMAD scorecard
CODE-SCOPE: README.md CHANGELOG.md docs/ evd/VT-27/ docs/pm/ docs/backlog/

Branch `feat/VT-27-benchmark-scorecard` (stacked on `feat/VT-26-first-run`, which introduced the stub and the README line).

## Plan
| T | Task | State |
|---|---|---|
| T1 | Repair the judge environment (arm-b `npm ci`, judge `npm ci` + Playwright 1.62.1) | done — JUDGE-REPAIRS J1, J2 |
| T2 | Fix the ambiguous probe locator (strict-mode violation on arm-b's aria-labelled show-password button), re-calibrate | done — J3, calibration 91/91 |
| T3 | Work around the iCloud-evicted scaffold (10 615 dataless files hung `rsync`/`tar`) — rebuild from the arms' baseline commit | done — J5 |
| T4 | Commit arm-a's stop state per PROTOCOL §3 (operator step missed on 09-04) | done — `356bfcc`, no content change |
| T5 | Run probes → truth → cost → score for both arms | done — `results/2026-09-03/judge-run-3.log` |
| T6 | Publish: docs/BENCHMARK.md, docs/benchmark/2026-09-03/{SCORECARD,JUDGE-REPAIRS}.md, README line, VT-28 filed | done |
| T7 | Gate GREEN (14 steps, advisory `schedule` failed — project-level, pre-existing), npm test 199/199, PR opened stacked on #74 | done — proof.md §5 |


## Decisions taken without the owner (recorded, reversible)
- arm-a scored at stop state (working tree committed by the operator), because the 09-04 committed tree does not seed. Alternative — score the committed tree — would have scored a tree that cannot run.
- Judge repair J3 changed 24 locator call sites in four probe files. Guard: full re-calibration afterwards (91/91). The 0 % calibration from 09-03 is unaffected by construction.
- Cost row left empty; no estimate.
