# VT-38 · dev tasksheet — a merged branch is not work in flight
CODE-SCOPE: src/cli/graph.mjs core/scripts/graph_check.py tests/e2e.mjs .vteam/ README.md docs/GUIDE.md CHANGELOG.md evd/VT-38/ docs/pm/ docs/backlog/

Branch `feat/VT-38-in-flight-truth` from main d53eeb8.

| T | Task | State |
|---|---|---|
| T1 | Prove the miscount: 33 local branches, 32 merged, plan says 21 in flight | done — proof.md §1 |
| T2 | `inFlightKeys` reads `git branch -a --no-merged <protected>`, falls back to all branches when the protected branch is absent | done |
| T3 | In Progress with no unmerged branch → `stale_wip` in the plan, still schedulable, with the reason | done |
| T4 | `graph_check` warns on the same condition; a blocked ticket is exempt | done |
| T5 | 3 plan selftest assertions, 2 graph_check selftest cases, 2 e2e checks | done — 234/234 |
| T6 | Four code-only mutations, tests kept | done — mutations.md |
| T7 | Correct the nine drifted tickets against their evidence, and refuse to fabricate the tenth | done — proof.md §3 |

## The data fixes, one line of evidence each
| Ticket | Was | Now | Evidence |
|---|---|---|---|
| VT-3, VT-4, VT-6, VT-7, VT-8, VT-9 | In Progress | In Review | merged branch + a dispatch row each; Done stays QA's call |
| VT-14 | In Progress | To Do | blocked-by VT-13, which is In Review — nobody could have been working on it |
| VT-28 | In Progress | In Progress + `blocked-by: D18` | its closure waits on that decision; now the graph shows it instead of the plan guessing |
| VT-2 | In Progress | **unchanged** | it shipped as PR #55 with no dispatch row. Moving it to In Review would red the rule that says work in review must appear in the ledger, and a retroactive row cannot be written honestly — the grammar demands `tok ≈ N[k]` and nobody measured it. The gap went to the decision queue; the ticket keeps the state its record supports and stays in the drift list until the owner decides. |
