# VT-40 · dev tasksheet — a derived port is a starting point, not a promise
CODE-SCOPE: core/scripts/lane_env.sh .vteam/ CHANGELOG.md evd/VT-40/ docs/pm/ docs/backlog/

Branch `fix/VT-40-lane-port-collision` from main 381cda1.

| T | Task | State |
|---|---|---|
| T1 | Reproduce CI's failure and name the cause: 800 buckets, random fixture path, R1 drew the author's port | done — proof.md §1 |
| T2 | `free_port`: step forward from the derived port over ports other lanes' markers claim; a lane never steps over its own | done |
| T3 | Say it out loud in the emitted environment when a step happened | done |
| T4 | Selftest: a PLANTED collision must be stepped over, and the step must be printed; block runs last so its marker cannot confuse the earlier marker assertions | done |
| T5 | Two code-only mutations, tests kept | done — proof.md §3 |
| T6 | Five consecutive runs green (the failure was random before) | done — proof.md §2 |
