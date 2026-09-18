# VT-29 · dev tasksheet — docs_shrink_check must not shallow the clone
CODE-SCOPE: core/scripts/docs_shrink_check.sh .vteam/ CHANGELOG.md evd/VT-29/ docs/pm/ docs/backlog/

Branch `fix/VT-29-shrink-shallow` from main ce2322b.

## Plan
| T | Task | State |
|---|---|---|
| T1 | Reproduce CI's RED locally: fetch `refs/pull/75/merge` as actions/checkout does, run the step with `GITHUB_BASE_REF`, observe `.git/shallow` and graph_check RED | done — proof.md §1 |
| T2 | Selftest case that fails on the current code (full clone + base fetch ⇒ `.git/shallow` must not appear) | done — RED, proof.md §2 |
| T3 | Fix: drop `--depth=1` from the base fetch; header comment explains why | done — GREEN, proof.md §2 |
| T4 | Same fixed step in the faithful PR clone: no shallow file, 12 files, graph coherent | done — proof.md §3 |
| T5 | Mirror synced (`vteam update`), gate GREEN (advisory `schedule` pre-existing), npm test 199/199, PR to main | done — proof.md §4 |

