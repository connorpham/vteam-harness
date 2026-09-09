# VT-10 — live probe (evidence)

Everything below was RUN, not reasoned about. Three artefacts:

1. **A real two-worktree parallel-mode repo** — the layout that reded the gates in
   the live `/team` run: three git worktrees off one repo, each ticket's tasksheet
   committed only on its own branch, a merged-but-undeleted branch still checked
   out, and both agents listing the shared coordination log in CODE-SCOPE.
2. **The six mutation proofs** — each new rule reverted one at a time, to prove the
   new selftest assertions can actually go RED.
3. **The `trust` subcommand**, exercised against a sandboxed `HOME` (the real
   `~/.claude.json` was never touched — verified afterwards).

Reproduce artefact 1 with `probe.sh` (transcribed at the end of this file).

---

## 1. Two worktrees, sibling tasksheet only in git

Fixture: `project.key: VT`, `team.parallel: 2`, `team.coord_budget: 3`,
`git.protected_branch: main`, the PATCHED `.vteam/scripts` copied in.

- `feat/VT-19-landed` — work that ALREADY LANDED (merged `--no-ff` into main),
  branch not deleted, still checked out in `wt-landed`
- `feat/VT-20-alpha` — `CODE-SCOPE: src/alpha/ docs/pm/coordination.md`, tasksheet
  committed as its first commit
- `feat/VT-21-beta` — `CODE-SCOPE: src/beta/ src/shared/order.ts docs/pm/coordination.md`,
  same
- `docs/pm/coordination.md` on main carries the handoff row
  `| 1 | VT-20 | VT-21 | src/shared/order.ts | VT-21 owns the Order type |`

Three branches exist and the cap is 2 — the live run's exact over-cap trap.

```
───────────────────────────────────────────────────────────────────
LAYOUT — three worktrees, the merged branch among them:
<probe>            03c1cc7 [main]
<probe>/wt-alpha   f831599 [feat/VT-20-alpha]
<probe>/wt-beta    c4e36df [feat/VT-21-beta]
<probe>/wt-landed  560c00d [feat/VT-19-landed]

`git branch --merged main` — note the '+' decoration that fooled the live run:
+ feat/VT-19-landed
* main

From wt-beta (worker 2), the SIBLING's tasksheet is not on disk:
ls: wt-beta/evd/VT-20/dev/tasksheet.md: No such file or directory
…but it IS in the shared object store:
CODE-SCOPE: src/alpha/ docs/pm/coordination.md
───────────────────────────────────────────────────────────────────

### parallel_check, run from worker 2's worktree
   · VT-20: bookkeeping paths not counted as edit territory: docs/pm/coordination.md
   · VT-21: bookkeeping paths not counted as edit territory: docs/pm/coordination.md
✅ parallel_check: 2 unmerged in-flight DEV branch(es) ≤ 2, all code scopes disjoint
exit=0

### coord_check, run from worker 2's worktree
✅ coord_check: 1 peer handoff(s) all reflected in CODE-SCOPE, rounds ≤ 3
exit=0

### parallel_check, run from worker 1's worktree (mirror image)
   · VT-20: bookkeeping paths not counted as edit territory: docs/pm/coordination.md
   · VT-21: bookkeeping paths not counted as edit territory: docs/pm/coordination.md
✅ parallel_check: 2 unmerged in-flight DEV branch(es) ≤ 2, all code scopes disjoint
exit=0

### BOUNDARY — worker 2 has NOT committed its tasksheet yet
   · VT-20: bookkeeping paths not counted as edit territory: docs/pm/coordination.md
❌ parallel_check: 1 problems in the in-flight set
   - VT-21: no CODE-SCOPE readable — tasksheet missing on feat/VT-21-beta, not committed (commit evd/VT-21/dev/tasksheet.md on that branch so sibling worktrees' gates can read it via git)
exit=1

### BOUNDARY — a REAL overlap under code paths must still be RED
   · VT-20: bookkeeping paths not counted as edit territory: docs/pm/coordination.md
   · VT-21: bookkeeping paths not counted as edit territory: docs/pm/coordination.md
❌ parallel_check: 1 problems in the in-flight set
   - VT-20 and VT-21 share edit territory (src/alpha ∩ src/alpha/order.ts) — serialize them; parallel branches on one file merge blind
exit=1

───────────────────────────────────────────────────────────────────
### graph_check — a chore commit that only MENTIONS a key
in-scope commit → green:
✅ graph_check: work graph coherent (1 tickets, loop budget 4/day, scope armed where declared)
exit=0

now a PM chore commit that touches src/alpha (outside VT-22's scope) and merely NAMES VT-22:
  subject: chore: drop the leftover found by the VT-22 worker
✅ graph_check: work graph coherent (1 tickets, loop budget 4/day, scope armed where declared)
exit=0

### BOUNDARY — the SAME out-of-scope file under a LEADING key must RED:
  subject: feat(VT-22): sneak a change into alpha
❌ graph_check: 1 coherence violations
   - VT-22: commit 3cf356cf touches outside the declared CODE-SCOPE (src/gamma/): src/alpha/sneaky.ts (MAST 2.3: the task self-expanded — widen the declared scope in the tasksheet, deliberately, or split the ticket)
exit=1
───────────────────────────────────────────────────────────────────
```

### What each block proves

| Block | Defect | Verdict |
|---|---|---|
| `parallel_check` from `wt-beta` and from `wt-alpha` | 1 (sibling sheet off disk) + 4 (merged branch counted) | GREEN — the sibling's CODE-SCOPE was read out of the object store, and `feat/VT-19-landed` (`+`-decorated, worktree-checked-out, merged) did not count toward the cap of 2 |
| the two `bookkeeping paths not counted` lines | 3 (shared coordination log) | both agents listed `docs/pm/coordination.md`; it is printed as discounted and causes no conflict |
| `coord_check` from `wt-beta` | 2 (receiver's scope looked empty) | GREEN — "1 peer handoff(s) all reflected in CODE-SCOPE" |
| BOUNDARY "not committed yet" | 1's failure mode | RED, and the message says `tasksheet missing on feat/VT-21-beta, not committed` — the remedy, not a phantom empty scope |
| BOUNDARY "real overlap" | 3's boundary | RED — `src/alpha ∩ src/alpha/order.ts`. Discounting bookkeeping did NOT disarm the gate |
| `graph_check` on `chore: drop the leftover found by the VT-22 worker` | 5 (prose mention attributed) | GREEN — the commit touched `src/alpha/leftover.ts`, well outside VT-22's `src/gamma/`, and was correctly judged as another lane's work |
| BOUNDARY `feat(VT-22): sneak a change into alpha` | 5's boundary | RED on `src/alpha/sneaky.ts` — the SAME out-of-scope directory, this time under a leading key. The pair is what makes the rule a rule |

---

## 2. Mutation proofs — every new rule can go RED

Each rule was reverted in a scratch copy, one at a time, and the script's own
`--selftest` re-run. **All 14 die on the intended assertion.**

The first four are the ones that SURVIVED the reviewers' own sweeps in round 1 —
real holes in my test suite, found by them, and closed here. M12 restores the
original defect the whole ticket exists to fix.

| # | Mutation (one rule reverted) | Result |
|---|---|---|
| M1 | `parallel_check.py` — mark_bookkeeping_only made a no-op | RED — `["VT-1: no CODE-SCOPE in its tasksheet — can't prove it is disjoint from the others (add CODE-SCOPE at /dev T1` |
| M2 | `parallel_check.py` — tasksheet_text drops the working-tree arm | RED — `my own branch must be read from disk, not from git: ('CODE-SCOPE: src/other/
', 'git feat/VT-2-other')` |
| M3 | `coord_check.py` — tasksheet_text drops the working-tree arm | RED — `the working tree must win over git: ['src/lib/order.ts', 'src/ui']` |
| M4 | `parallel_check.py` — is_book loses the exact-home arm | RED — `{'VT-1': ['docs/pm'], 'VT-2': ['docs/pm']}` |
| M5 | `parallel_check.py` — norm stops resolving . and .. | RED — `docs/pm/../src/x.ts` |
| M6 | `coord_check.py` — norm stops resolving . and .. | RED — `docs/pm/../src/x.ts` |
| M7 | `parallel_check.py` — paths_touch loses the repo-root rule | RED — `AssertionError` |
| M8 | `parallel_check.py` — has_landed back to bare --merged | RED — `a branch created but not yet committed to is IN FLIGHT: {'VT-2': ['src/other'], 'VT-4': []}` |
| M9 | `parallel_check.py` — has_landed loses squash detection | RED — `a squash-merged branch has landed: {'VT-2': ['src/other'], 'VT-4': [], 'VT-7': []}` |
| M10 | `graph_check.py` — attributes loses multi-scope parsing | RED — `must be attributed: 'feat(api,TB-5): x'` |
| M11 | `graph_check.py` — attributes loses the revert unwrap | RED — `must be attributed: 'Revert "feat(TB-5): fix the thing"'` |
| M12 | `graph_check.py` — attributes back to KEY anywhere (the original bug) | RED — `must NOT be attributed: 'chore: drop the leftover found by the TB-5 worker'` |
| M13 | `core/scripts/parallel_check.py` — has_landed reverted to the positional test (`behind > 0`) | RED — `a fresh worker branch stays IN FLIGHT after main advances: {'VT-2': ['src/other'], 'VT-4': []}` |
| M14 | `core/scripts/parallel_check.py` — has_landed reverted to bare `--merged` membership | RED — `a branch created but not yet committed to is IN FLIGHT: {'VT-2': ['src/other'], 'VT-4': []}` |

M13/M14 are the second round: a reviewer proved that my first fix for the
merged-branch defect was POSITIONAL ("has protected moved past me?"), which
holds only until the day's first serial merge and then hides every idle worker
again. The rule is now topological — a branch that landed through a merge commit
is never on protected's first-parent chain, a merely-created one always is — and
M13 is the guard that the old rule cannot pass.

M10/M12 pin the attribution rule from both sides: too loose and a prose mention
is judged (M12, the original bug); too tight and a real `feat(a,KEY):` commit
stops being watched (M10, the more dangerous direction — a gate that quietly
stops looking).

---

## 3. `orca_team.sh trust <path>` (AC 6)

Run against a sandboxed `HOME`. Afterwards `ls ~/.claude.json.vteam-bak
~/.claude.json.vteam-tmp` → "No such file or directory" for both, i.e. the real
config was never touched by these tests.

```
### 1. a pre-existing config with other keys and another project
$ HOME=<sandbox> bash .vteam/scripts/orca_team.sh trust <sandbox>/wt-child
   backed up <sandbox>/home/.claude.json -> <sandbox>/home/.claude.json.vteam-bak
trusted: set projects['<sandbox>/wt-child'].hasTrustDialogAccepted = true in <sandbox>/home/.claude.json
   a worker dispatched into this worktree now gets its prompt, not a dialog
exit=0
--- the resulting config (other keys + the other project intact) ---
{
  "numStartups": 42,
  "projects": {
    "/Users/x/other": {
      "hasTrustDialogAccepted": true,
      "history": [
        "a"
      ]
    },
    "<sandbox>/wt-child": {
      "hasTrustDialogAccepted": true
    }
  }
}
### 2. idempotent: a second run writes nothing and backs nothing up again
already trusted: projects['<sandbox>/wt-child'].hasTrustDialogAccepted = true in <sandbox>/home/.claude.json
exit=0
--- the backup still holds the ORIGINAL, not our own output ---
{"numStartups": 42, "projects": {"/Users/x/other": {"hasTrustDialogAccepted": true, "history": ["a"]}}}

### 3. a path that does not exist is refused (trusting a typo leaves the real worktree untrusted)
❌ trust: '<sandbox>/nope' is not an existing directory (create the worktree first)
exit=1

### 4. a config we cannot parse is refused, never "repaired"
trust: cannot read <sandbox>/home/.claude.json (Expecting property name enclosed in double quotes: line 1 column 2 (char 1)) - fix or move it, then retry
exit=1
the file is untouched: {not json

### 5. usage line names the new subcommand
usage: orca_team.sh {status | open-run <objective> | wait <run_id> | trust <path>}
exit=2
```

The field is exactly the one Claude Code writes when a human clicks "trust":
`projects["<abs path>"].hasTrustDialogAccepted = true`.

---

## Appendix — probe.sh

```bash
#!/usr/bin/env bash
# VT-10 LIVE probe — reproduce the live parallel-mode layout that reded the gates,
# on the PATCHED scripts. Two real git worktrees, sibling tasksheet only in git.
set -uo pipefail
VT=/Users/connorpham/Documents/vteam
P="${1:?usage: probe.sh <empty dir>}"
rm -rf "$P"; mkdir -p "$P"
cd "$P"

g() { git "$@" >/dev/null 2>&1 || { echo "git $* FAILED"; exit 1; }; }

# ── a repo shaped like a real vteam project, parallel mode ON ────────────────
g init -q -b main
g config user.email probe@t.t
g config user.name probe
cat > vteam.config.yaml <<'Y'
version: 1
project:
  name: 'probe'
  key: VT
  adopted: 2026-01-01
paths:
  specs: docs/specs
  pm: docs/pm
  qa: docs/qa
  evidence: evd
  backlog: docs/backlog
  team: docs/team
git:
  protected_branch: main
  branch_pattern: "^(feat|fix)/{key}-[0-9]+-"
  code_paths: [src/]
tracker:
  provider: markdown
  done_statuses: [Done]
  review_status: In Review
team:
  parallel: 2
  coord_budget: 3
  loop_budget_per_day: 4
Y
mkdir -p docs/pm docs/qa docs/backlog src/alpha src/beta src/shared
# the worker worktrees live inside this dir for tidiness — they are not content
printf 'wt-*\n.vteam/map.json\n' > .gitignore
cp -R "$VT/.vteam" .vteam                      # the PATCHED runtime under test
rm -f .vteam/map.json
# the PM's coordination log: VT-20 handed the Order contract to VT-21
cat > docs/pm/coordination.md <<'M'
# Coordination log — peer handoffs between parallel DEV agents

| Round | From | To | Path/Contract | What/why |
|---|---|---|---|---|
| 1 | VT-20 | VT-21 | src/shared/order.ts | VT-21 owns the Order type |
M
g add -A
g commit -qm "init probe repo"

# ── defect 4: a branch that ALREADY LANDED, still checked out in a worktree ──
g checkout -qb feat/VT-19-landed
echo landed > src/alpha/landed.ts
g add -A
g commit -qm "VT-19 landed work"
g checkout -q main
g merge -q --no-ff -m "merge VT-19" feat/VT-19-landed

# ── two in-flight tickets, each with its tasksheet COMMITTED on its branch ──
g checkout -qb feat/VT-20-alpha main
mkdir -p evd/VT-20/dev
printf 'CODE-SCOPE: src/alpha/ docs/pm/coordination.md\n' > evd/VT-20/dev/tasksheet.md
g add -A
g commit -qm "docs(VT-20): tasksheet first (parallel mode)"

g checkout -qb feat/VT-21-beta main
mkdir -p evd/VT-21/dev
printf 'CODE-SCOPE: src/beta/ src/shared/order.ts docs/pm/coordination.md\n' > evd/VT-21/dev/tasksheet.md
g add -A
g commit -qm "docs(VT-21): tasksheet first (parallel mode)"
g checkout -q main

# ── the real thing: separate worktrees, one per worker ───────────────────────
g worktree add -q wt-alpha feat/VT-20-alpha
g worktree add -q wt-beta  feat/VT-21-beta
g worktree add -q wt-landed feat/VT-19-landed

echo "───────────────────────────────────────────────────────────────────"
echo "LAYOUT — three worktrees, the merged branch among them:"
git worktree list | sed "s#$P#<probe>#g"
echo
echo "\`git branch --merged main\` — note the '+' decoration that fooled the live run:"
git branch --merged main
echo
echo "From wt-beta (worker 2), the SIBLING's tasksheet is not on disk:"
ls wt-beta/evd/VT-20/dev/tasksheet.md 2>&1 | sed "s#$P#<probe>#g"
echo "…but it IS in the shared object store:"
git -C wt-beta show feat/VT-20-alpha:evd/VT-20/dev/tasksheet.md
echo "───────────────────────────────────────────────────────────────────"
echo
echo "### parallel_check, run from worker 2's worktree"
( cd wt-beta && python3 .vteam/scripts/parallel_check.py ); echo "exit=$?"
echo
echo "### coord_check, run from worker 2's worktree"
( cd wt-beta && python3 .vteam/scripts/coord_check.py ); echo "exit=$?"
echo
echo "### parallel_check, run from worker 1's worktree (mirror image)"
( cd wt-alpha && python3 .vteam/scripts/parallel_check.py ); echo "exit=$?"
echo
echo "### BOUNDARY — worker 2 has NOT committed its tasksheet yet"
( cd wt-beta && git rm -q --cached evd/VT-21/dev/tasksheet.md && git commit -qm "docs(VT-21): uncommit the sheet" && cd ../wt-alpha && python3 .vteam/scripts/parallel_check.py ); echo "exit=$?"
( cd wt-beta && git revert -q --no-edit HEAD >/dev/null 2>&1 )
echo
echo "### BOUNDARY — a REAL overlap under code paths must still be RED"
( cd wt-beta && printf 'CODE-SCOPE: src/alpha/order.ts docs/pm/coordination.md\n' > evd/VT-21/dev/tasksheet.md \
  && git add -A && git commit -qm "docs(VT-21): overlap alpha" \
  && cd ../wt-alpha && python3 .vteam/scripts/parallel_check.py ); echo "exit=$?"
( cd wt-beta && printf 'CODE-SCOPE: src/beta/ src/shared/order.ts docs/pm/coordination.md\n' > evd/VT-21/dev/tasksheet.md && git add -A && git commit -qm "docs(VT-21): restore scope" >/dev/null 2>&1 )
echo
echo "───────────────────────────────────────────────────────────────────"
echo "### graph_check — a chore commit that only MENTIONS a key"
cd "$P"
cat > docs/backlog/VT-22.md <<'T'
# VT-22: gamma work
- status: To Do

body
T
mkdir -p evd/VT-22/dev src/gamma
printf 'CODE-SCOPE: src/gamma/\n' > evd/VT-22/dev/tasksheet.md
echo in > src/gamma/g.ts
g add -A
g commit -qm "VT-22 gamma work"
echo "in-scope commit → green:"
python3 .vteam/scripts/graph_check.py; echo "exit=$?"
echo
echo "now a PM chore commit that touches src/alpha (outside VT-22's scope) and merely NAMES VT-22:"
echo cleanup > src/alpha/leftover.ts
g add -A
g commit -qm "chore: drop the leftover found by the VT-22 worker"
git log -1 --format='  subject: %s'
python3 .vteam/scripts/graph_check.py; echo "exit=$?"
echo
echo "### BOUNDARY — the SAME out-of-scope file under a LEADING key must RED:"
echo more > src/alpha/sneaky.ts
g add -A
g commit -qm "feat(VT-22): sneak a change into alpha"
git log -1 --format='  subject: %s'
python3 .vteam/scripts/graph_check.py; echo "exit=$?"
echo "───────────────────────────────────────────────────────────────────"
```
