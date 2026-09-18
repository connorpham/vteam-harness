# VT-30 · dev tasksheet — gates that crashed, lied or went vacuously green in a real repo
CODE-SCOPE: core/scripts/ profiles/nextjs-prisma/scripts/ core/workflows/verify.md .vteam/ .claude/ docs/team/ tests/e2e.mjs README.md docs/GUIDE.md CHANGELOG.md evd/VT-30/ docs/pm/ docs/backlog/

Branch `fix/VT-30-gates-in-a-real-repo` from main d9b1e7e.

| T | Finding | Change | Test | State |
|---|---|---|---|---|
| T1 | E1 preflight RED on no origin | ⚠️ line + local-merge rule; hosting-CLI leg skipped without a remote | e2e §5b: no-origin repo → GREEN | done |
| T2 | E4 verbatim_gate: bold-only, digits-only codes; vacuous pass | ROW accepts `\| CODE \|` and `AC-A01`; configured-but-zero-rows → RED | selftest: 4 regex cases + temp-repo RED | done |
| T3 | E5 token_check ENOENT on App Router | `pickRoots(git.code_paths)` skips missing dirs; message names the dirs | selftest: app/-only layout | done |
| T4 | E7/E15 stranger's server = UP | `owner_check`: listener pid → cwd vs repo/worktrees → `APP: FOREIGN` exit 1 | selftest: same server, foreign root | done |
| T5 | E10 gate blocks on an undrained pipe | gate.sh tees to `$TMPDIR/vteam-gate-<repo>.log`, names it | e2e §5b: transcript line + file | done |
| T6 | E14 ledger row announced, never written | graph_check: In Review/Done needs a row naming the key (`closed-by:` exempt) | selftest m0 | done |
| T7 | E16 stale build red-proof | /verify principle 6 sentence | doctrine | done |
| T8 | Mutations M1–M7 (code-only, tests kept) | see mutations.md | all RED | done |
| T9 | Gate GREEN, npm test 201/201, mirrors synced, PR | see proof.md §3 | done |


Testbed dry run (2026-09-18): graph_check coherent; **verbatim_gate now RED there** — its two REQ documents carry no coded rows, so the trial's verbatim gate had passed vacuously since day one (E4 in the wild). Left for the testbed to fix (code the rows or unset `specs.sources`); recorded, not hidden.
