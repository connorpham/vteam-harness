# VT-31 · dev tasksheet — init prefills app.* for Next repos on a checkout-unique port
CODE-SCOPE: src/cli/init.mjs tests/e2e.mjs README.md docs/GUIDE.md CHANGELOG.md evd/VT-31/ docs/pm/ docs/backlog/

Branch `feat/VT-31-init-app-port` from main d9b1e7e, in an isolated worktree.

## Plan
| T | Task | State |
|---|---|---|
| T1 | Read E2/E7/E15 in the arm's RUNLOG; read init's template, detectProfile, conformance's use of the documented block | done |
| T2 | Tests first: five checks in tests/e2e.mjs §5c (url+port, start+health, summary line, three paths → three ports, non-Next untouched) | done |
| T3 | `detectNextApp` + exported `derivePort` (fnv1a over the checkout's realpath → 3100 + h % 800) + prefilled template + summary line | done |
| T4 | RED proof by code-only mutation (detection forced off, tests kept): 3 RED; fix restored: 204/204 GREEN | done — proof.md §2 |
| T5 | README `**199 checks**` → 204; GUIDE `app:` bullet documents the prefill; documented config block unchanged (conformance OK) | done |
| T6 | Gate GREEN, npm test, PR | proof.md §4 |

## Decisions taken without the owner (reversible)
- Prefill keys on `next` in dependencies/devDependencies, not on the chosen profile: a Next app without Prisma is `node` by profile and just as runnable.
- Port = realpath-based, so `/var/…` and `/private/var/…` (macOS) agree; found because the first GREEN run disagreed with init by exactly that symlink.
