# VT-10 — /verify gate results (evidence)

Captured AFTER both review fix rounds, from one sequential run over the STAGED
tree — so this file covers every artifact in the commit, including
`REPORT.bdd.md` (a reviewer correctly noted the first capture predated it, and
that `bdd_report_check` had reded it while it was still a draft). Every line
below is verbatim tool output.

## The gates AC 7 names

```
### bash .vteam/scripts/gate.sh

E2E: GREEN — 164/164 checks passed
⚠️  skipped build: .vteam/build.sh absent — no project build entrypoint declared — create .vteam/build.sh if the project builds
GATE: GREEN (9 steps ran, 1 declared skips)

### node bin/vteam.mjs doctor
✅ config parses (version 1)
✅ manifest verified (115 framework-owned files intact)
✅ gate selftests green (32 discovered checks prove they can red)
PREFLIGHT: GREEN — the ticket→design→code→git chain runs end-to-end

### node tests/e2e.mjs

E2E: GREEN — 164/164 checks passed

### the three patched scripts own selftests — core AND the installed runtime copy
core/scripts/parallel_check.py --selftest
  parallel_check selftest: OK (parse + nest/equal/disjoint + `.`/`..`/`./` canonicalised + whole-repo scope collides with everyone; conflicts: disjoint green, overlap red, missing-scope red, over-cap comparison; bookkeeping homes ignored (home itself included, spelling-proof), real overlap still red, bookkeeping-only marked and named, root home not swallowing the repo; worktree: sibling tasksheet read from git, own branch read from the working tree, uncommitted one named; landed: merged branch — even '+'-decorated in a worktree — and squash-merged branch not in flight, while a NOT-YET-DIVERGED branch and post-squash work still are)
.vteam/scripts/parallel_check.py --selftest
  parallel_check selftest: OK (parse + nest/equal/disjoint + `.`/`..`/`./` canonicalised + whole-repo scope collides with everyone; conflicts: disjoint green, overlap red, missing-scope red, over-cap comparison; bookkeeping homes ignored (home itself included, spelling-proof), real overlap still red, bookkeeping-only marked and named, root home not swallowing the repo; worktree: sibling tasksheet read from git, own branch read from the working tree, uncommitted one named; landed: merged branch — even '+'-decorated in a worktree — and squash-merged branch not in flight, while a NOT-YET-DIVERGED branch and post-squash work still are)
core/scripts/coord_check.py --selftest
  coord_check selftest: OK (consistent green + unreflected/giver-keeps/over-budget/malformed red + dir-covers-file + no-trailing-pipe row caught + sibling scope read from git — newest branch beats an abandoned one, working tree beats git, VT-1 not matching VT-11, empty receiver scope still red)
.vteam/scripts/coord_check.py --selftest
  coord_check selftest: OK (consistent green + unreflected/giver-keeps/over-budget/malformed red + dir-covers-file + no-trailing-pipe row caught + sibling scope read from git — newest branch beats an abandoned one, working tree beats git, VT-1 not matching VT-11, empty receiver scope still red)
core/scripts/graph_check.py --selftest
  graph_check selftest: OK (coherent graph green + 7 reds: dangling, cycle, done-sans-verdict, done-with-FAIL, identical repeat, loop budget, out-of-scope commit — + loud skips: undeclared scope, remote tracker — + attribution, 17 positive / 12 negative: leading key attributed (bare/`type:`-prefixed/`feat(KEY):`/multi-scope `feat(a,KEY):`/`[KEY]`/`Revert "…"`), prose mention + longer key + merge-commit NOT, both directions proven end-to-end on the same out-of-scope directory)
.vteam/scripts/graph_check.py --selftest
  graph_check selftest: OK (coherent graph green + 7 reds: dangling, cycle, done-sans-verdict, done-with-FAIL, identical repeat, loop budget, out-of-scope commit — + loud skips: undeclared scope, remote tracker — + attribution, 17 positive / 12 negative: leading key attributed (bare/`type:`-prefixed/`feat(KEY):`/multi-scope `feat(a,KEY):`/`[KEY]`/`Revert "…"`), prose mention + longer key + merge-commit NOT, both directions proven end-to-end on the same out-of-scope directory)

### bash -n on the shell helper (the gate has no shell-lint step — see Notes)
  core/scripts/orca_team.sh: syntax OK
  .vteam/scripts/orca_team.sh: syntax OK
```

## AC 7's remaining clauses, checked explicitly

```
$ # "no unresolved {vars}" in the rendered outputs of `node bin/vteam.mjs update`
docs/team/parallel-transport.md:0
.claude/skills/team/SKILL.md:0
.claude/skills/dev/SKILL.md:0

$ # README counts unchanged (no new selftest-bearing scripts, no new e2e checks)
$ git diff origin/main --stat -- README.md
(empty = README untouched)
32 today
**164 checks**
  → doctor reported 32; tests/e2e.mjs reported 164. Both README numbers still true.

$ # core and the installed runtime copy are byte-identical after `update`
  parallel_check.py    core == .vteam
  coord_check.py       core == .vteam
  graph_check.py       core == .vteam
  orca_team.sh         core == .vteam

$ # reviewers read the index, so the index must BE the code under review.
$ # (Checked at commit time, not here: this file is itself written after the
$ #  check, so a count taken inside it could never read zero.)
$ git diff --cached -- core/scripts/parallel_check.py | grep -c 'first-parent'
2

$ python3 .vteam/scripts/review_check.py VT-10 --sha WORKTREE
✅ review_check: VT-10 — dossier complete (R1, R2; R3 (high-stakes) not required for this diff)
$ python3 .vteam/scripts/bdd_report_check.py
✅ bdd_report_check: 2 BDD report(s) readable, complete and concise
```

## Notes

- `GATE: GREEN (9 steps ran, 1 declared skips)` — the one skip is
  `.vteam/build.sh absent`, pre-existing and declared out loud (this repo is a
  CLI/framework with no build step). Unrelated to this change.
- The gate runs `tests/e2e.mjs` as its e2e step, which is why `E2E: GREEN —
  164/164` appears twice: once inside the gate, once standalone as AC 7 asks.
- `manifest verified (115 framework-owned files intact)` — unchanged count: this
  ticket edited existing core files and added no new framework-owned ones.
- Both `parallel_check` and `coord_check` are inert-green in THIS repo
  (`team.parallel: 1`), which is why the live three-worktree probe in
  `cmd_probe.md` exists — the gates' real behaviour cannot be observed here.
- **Side finding (not fixed, outside CODE-SCOPE):** the gate has no shell-lint
  step. During this ticket an apostrophe inside `orca_team.sh`'s embedded python
  heredoc silently broke the `trust` subcommand and every gate stayed green;
  only running the subcommand caught it. `bash -n` would have caught it
  instantly, and is run manually above. Worth its own ticket.
