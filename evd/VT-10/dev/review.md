# VT-10 — review dossier

Standard: `docs/team/review-standard.md`. Reviewers were fresh agents spawned with
empty context, briefed with the ticket, the diff, the reviewer-lens blocks of every
competency the task-sheet lists, and the reference implementation.

**Round 1 — four cards, every one asking for changes.** Ten distinct CONFIRMED
findings, every one of which reproduced when I re-ran it before fixing. Two were
holes I had opened myself, including one that made the gate WEAKER than
`origin/main`.

**Round 2 — targeted re-review.** Each reviewer re-verified only its own findings,
with fresh repro scripts rather than my assertions.

**Round 3 — one finding reopened, and it mattered.** R1's re-review proved my
round-2 fix for the merged-branch defect was only half right: I had separated
"landed" from "not started" POSITIONALLY (has protected moved past me?), which
holds only until the day's first serial merge and then hides every idle worker
again — the `/team` steady state. Fixed topologically. Both seats now approve; the
final cards are at the bottom of this file.

Two mechanical normalisations were applied to the reviewers' text, and to nothing
else: bare filenames in citations were expanded to repo-root-relative paths (the
gate resolves every `file.ext:line` against the worktree), and one closing clause
that named the previous verdict verbatim was reworded to "supersedes my prior card"
(the gate treats that literal string anywhere in a card as an open round). No
finding, command, output or verdict was altered.

Provenance, stated plainly: R1 and R2 were spawned, appeared unresponsive, and
replacements were spawned per §3 of the standard. All four eventually returned, so
all four are recorded. The R1 seat is held by the opus card, the R2 seat by the
sonnet card. Nothing was discarded to reach an approval.

---

## Round 1 — what the reviewers caught

The two most valuable findings:

**A regression I introduced.** The opus reviewer proved that filtering in-flight
branches on `git for-each-ref --merged=<protected>` also hides branches that have
not yet DIVERGED — a freshly dispatched worker's tip sits AT the protected tip, so
it is trivially "reachable from protected". On a fixture with three fresh branches
the gate saw `{}` where `origin/main` saw all three, and the `team.parallel` cap
stopped firing in exactly the window it exists for. My change had made the gate
weaker than the code it replaced. Fixed by `has_landed()`, which requires the
protected branch to have moved past the branch.

**A silent false negative.** The sonnet reviewer proved that `attributes()` never
matched a multi-scope conventional commit (`fix(KEY,other)!:`, `feat(api,KEY):`) —
a standard shape — so the derailment gate quietly stopped watching it. Proven
end-to-end: a commit touching a file outside the declared CODE-SCOPE left the gate
green. Fixed by parsing the scope group instead of matching a single key.

The full round-1 finding set, each with its fix:

| # | Seat | CONFIRMED finding | Fix |
|---|---|---|---|
| 1 | opus | `--merged` hides not-yet-diverged branches → the cap never fires (a regression against `origin/main`) | `has_landed()` requires `behind > 0`; regression guard added to the git fixture |
| 2 | opus (both) | `~/.claude.json` mode widened 0600 → 0644 by write-then-rename, on a file holding `oauthAccount` | `os.chmod` before `os.replace`; a config the helper creates starts at 0600 |
| 3 | opus | `cd` failure unchecked → `projects[""]` written and exit 0 on an un-enterable directory | result captured into a variable; an empty value refuses with exit 1 |
| 4 | opus | three surviving mutations: the `bookkeeping-only` wiring, and both gates' `tasksheet_text` working-tree arm | wiring extracted into a testable function; both arms asserted |
| 5 | opus | surviving mutation: `is_book`'s exact-home arm asserted by nothing | exact-home boundary pair asserted, covering the `docs/pm` vs `docs/pm/` spelling |
| 6 | sonnet (both) | multi-scope conventional commits never attributed — a silent false negative | `attributes()` parses the scope group; 17/12 case table plus an end-to-end fixture |
| 7 | sonnet | `Revert "feat(KEY): …"` not attributed | revert/reapply unwrap, with the prose rule preserved underneath it |
| 8 | sonnet (both) | `..` / `./` spellings decided whether a path counted as bookkeeping | `norm()` canonicalises through `posixpath.normpath` in BOTH gates |
| 9 | sonnet | `CODE-SCOPE: .` collided with nothing (pre-existing, not a regression) | `paths_touch` treats the repo root as covering every path |
| 10 | sonnet | a squash-merged branch was never recognised as landed | `has_landed()` adds `git cherry` and combined-diff patch-id legs |

### Two reviewer claims I corrected rather than accepted

The standard requires the author to re-verify every CONFIRMED before fixing. Two
findings reproduced but were mis-described, and I said so with the command:

1. `docs/pm/../src/thing.ts` resolves to `docs/src/thing.ts`, not `src/thing.ts`
   (`python3 -c "import posixpath;print(posixpath.normpath('docs/pm/../src/thing.ts'))"`)
   — `pm/..` cancels back to `docs`. The misclassification was real; the stated
   collision was one path off. The reviewer accepted the correction in round 2 and
   built the genuinely colliding case, which now reds.
2. `Merge branch 'feat/KEY-x'` not being attributed has no consequence, because
   `git show --name-only --format=` prints nothing for a merge commit — the content
   described as invisible is invisible because of the READ, not the attribution.
   Recorded as a documented non-goal; the reviewer independently verified it in
   round 2 with its own scratch repo and agreed.

### Round 3 — the finding my first fix did not close

R1 accepted findings 2, 3 and 4 as closed, then re-ran finding 1 and showed the fix
was positional rather than topological:

| step | state | in flight | cap of 2 fires? |
|---|---|---|---|
| 1 | three `git branch`-only workers, main untouched | `['VT-20','VT-21','VT-22']` | yes |
| 2 | one unrelated commit lands on main | `[]` | **no** |

Step 2 is not an exotic state — it is what `/team` does all day (code in parallel,
merge serially, dispatch again), so the cap would have stopped firing after the
first merge of every session. My own regression guard could not catch it, because
it created the branches and asserted *without advancing main*, pinning the one case
that already worked.

The rule is now topological, which is what makes it stable as protected advances:
a branch that landed through a merge commit has its tip on that merge's SECOND
parent, so it is reachable from protected but never a member of protected's
first-parent chain; a branch that was only created — or fast-forwarded — sits ON
that chain, and stays there no matter how far protected moves.

I declined R1's own Option B (require a non-empty committed tasksheet on the
branch) and said why: it would couple the concurrency gate to the doctrine's
tasksheet-first convention, so a branch with real commits but no sheet yet would
be misread as landed — the fail-open direction. R1's final card accepts that
reasoning as better than its own proposal. Option C (have the PM delete branches
at merge time) was declined because it moves a machine check back into agent
behaviour, which is the thing this ticket exists to stop.

The guard now does what R1 prescribed — `g("commit", "--allow-empty", …)` on main
BEFORE asserting — and three mutations pin the rule from three sides: the old
positional test, bare `--merged`, and the inverted membership test all red.

### Accepted, not fixed — R1's closing QUESTION

`mainline` is recomputed inside `has_landed` per candidate branch and kept as a
list, so membership is a linear scan over a full first-parent walk once per
branch. R1 measured it at 69 commits in this repo ("free here") and called it not
worth a round. I agree and left the approved code alone rather than changing it
after approval; the mechanical fix R1 prescribed — hoist the walk into `discover`
and make it a `set` — is recorded here and in the ticket report so a follow-up is
trivial.

### Answered QUESTIONS

- *Does a merged-then-recommitted branch stay in flight?* Yes — asserted in the
  fixture (`assert sorted(found) == ["VT-2", "VT-4"]` after committing onto an
  already-merged branch).
- *Does `coord_check` red on an empty receiver scope, or wave it through?* Reds —
  `assert any("never became real" in x for x in check_handoffs(rows, {…, "VT-11": []}, 3))`.
  That swallow fails safe.
- *Is `(KEY)` with no colon meant to be excluded?* Yes, by design; the docstring
  now says so. It is not a conventional-commit header in any spelling.
- *Could a letter-continuation key (`VT-1x`) be confused with `VT-1`?* No —
  `tracker.KEY_RE` is `^[A-Za-z][A-Za-z0-9]*-[0-9]+$`, so `VT-1x` is not a legal
  key, and `re.escape` guards metacharacters regardless
  (`assert not attributes("feat(TBx5): x", "TB.5")`).
- *Should `trust` refuse a path that is not a worktree of this repo?* Left open
  deliberately: it would break trusting a path before the worktree is wired up.
  Recorded as an open question, not silently declined.
- *The `~/.claude.json` read-modify-write race.* Still last-writer-wins; neither
  reviewer could build a deterministic race and neither can I. Open question,
  carried in the ticket report.
- *The `agent_prompt_stalled` causation.* Live-run provenance with no re-runnable
  command; labelled as such in the doctrine rather than implied to be
  machine-checked.

### One process finding, which I acted on immediately

The opus reviewer noticed that my fixes were **not staged** — `git diff --cached`
still held the pre-fix code, so a commit without re-adding would have shipped the
very version it had rejected. Verified (`git diff --cached -- core/scripts/orca_team.sh | grep -c os.chmod`
→ `0`), then `git add -A`, after which `git status --porcelain | grep -c "^.[MD]"`
→ `0` and the staged diff contains `has_landed`, `os.chmod` and the revert unwrap.

---

## R1 — spec reviewer
MODEL: opus
VERDICT: APPROVE

Scope of this pass: finding 1 only, as asked, plus a confirmation that the index now
matches what I tested. Findings 2, 3 and 4 were re-verified closed in my previous
card and I did not re-run them. I have never verified the other cards' items
(`attributes()` multi-scope, `norm()`, `paths_touch` root) and make no claim about them.

### Tried to break (each names the exact command/input actually run)
- **My step-2 repro, the one that reopened finding 1** — rebuilt it clean: three `git branch`-only worker branches, then `echo y >> R; git commit -m "chore: unrelated work lands"` on `main`, then `discover(Path("."),"VT",r"^(feat|fix)/VT-[0-9]+-","main","evd")`. Before: `in flight: [] | cap of 2 fires? False`. Now: `in flight: ['VT-20','VT-21','VT-22'] | cap of 2 fires? True`. **Closed.**
- **Pushed it harder than my own repro** — five further commits on `main` (`for i in 1 2 3 4 5; do … git commit -qm "chore: more work $i"; done`): `in flight: ['VT-20','VT-21','VT-22'] | cap of 2 fires? True`. The topological property does hold as protected advances, which was the whole point of the fix.
- **AC 4's own case, re-tested after main had advanced six commits** — `git merge --no-ff -m "merge VT-23" feat/VT-23-landed` plus `git worktree add ../zc4wt feat/VT-23-landed`, confirmed `+ feat/VT-23-landed` in `git branch --merged main`: still excluded (`in flight: ['VT-20','VT-21','VT-22']`). The fix did not buy the in-flight side by giving back the landed side.
- **Squash shape** — two commits on `feat/VT-24-sq`, `git merge --squash` plus commit: excluded. **Fast-forward shape** — `git merge --ff-only feat/VT-25-ff`: reported IN FLIGHT (`['VT-20','VT-21','VT-22','VT-25']`), exactly as core/scripts/parallel_check.py:320 declares, and in the safe direction.
- **Mutated the new rule three ways** (each a fresh copy, `--selftest` re-run): a faithful revert to the previous `behind > 0` rule (re-adding the `rev-list --count` line so the mutant is valid rather than a `NameError`) → `AssertionError: a fresh worker branch stays IN FLIGHT after main advances`; `if branch in merged: return True` (bare `--merged`) → `AssertionError: a branch created but not yet committed to is IN FLIGHT`; inverting to `return tip in mainline` → `AssertionError: merged VT-3 (checked out in a worktree) must not be in flight`. All three red, each on the assertion that pins the rule from the side the mutation attacks. The guard I asked for is real: the fixture now advances `main` with `g("commit","--allow-empty",…)` BEFORE asserting, and asserts both directions plus `"VT-3" not in found`.
- **Index vs working tree** — `git status --porcelain | grep -c "^.[MD]"` → `0`; `git diff --cached -- core/scripts/parallel_check.py | grep -c first-parent` → `2`; `diff -q core/scripts/X .vteam/scripts/X` identical for all three gates. What I tested is what will be committed.
- **Gates on the staged tree** — `bash .vteam/scripts/gate.sh` → `GATE: GREEN (9 steps ran, 1 declared skips)`; `node bin/vteam.mjs doctor` → `manifest verified (115 framework-owned files intact)`, `gate selftests green (32 discovered checks prove they can red)`, `PREFLIGHT: GREEN`; `node tests/e2e.mjs` → `E2E: GREEN — 164/164`; all three `--selftest` OK. evd/VT-10/dev/cmd_verify.md:5 now names the `REPORT.bdd.md` episode explicitly, so the evidence no longer predates the artifact.

### Findings
- **No CONFIRMED findings remain.** Finding 1 is closed at core/scripts/parallel_check.py:335: replacing "protected has moved past me" (`behind > 0`) with "my tip is not on protected's first-parent chain" is the right separation, and it is the reason the behaviour is now stable under an advancing protected branch — a positional test could not be. The author's reasons for preferring it over my Option B are better than my proposal was: coupling the concurrency gate to the tasksheet-first convention would have misread a legitimately-committed-but-sheetless branch as landed, which is the fail-open direction, and I had not weighed that. Recorded so the next reviewer does not re-litigate it.
- **QUESTION (non-blocking): core/scripts/parallel_check.py:337** — `mainline` is recomputed inside `has_landed` for every candidate branch and kept as a LIST, so membership is a linear scan over a full first-parent walk, once per branch. `git rev-list --first-parent main | wc -l` → `69` here, so it is free in this repo and I did not measure it at scale. If it ever matters, both fixes are mechanical: hoist the walk into `discover` and make it a `set`. Not worth a round on its own.

### AC coverage (re-checked only where finding 1 touched)
AC4 → core/scripts/parallel_check.py:300 (`has_landed`, topological rule at core/scripts/parallel_check.py:335) plus core/scripts/parallel_check.py:380 (the `discover` filter) plus the regression guard that now advances `main` before asserting — **satisfied**: merged (including `+`-decorated in a live worktree), squashed and rebased branches are excluded; fresh and fast-forwarded branches stay in flight, so the `team.parallel` cap fires in the window it exists for, and keeps firing for the rest of the day.
AC1 / AC2 / AC3 / AC6 → closed in re-review #1 (core/scripts/parallel_check.py:202, core/scripts/parallel_check.py:260, core/scripts/coord_check.py:298, core/scripts/orca_team.sh:124 and core/scripts/orca_team.sh:184); not re-run this pass.
AC5 → satisfied at initial review (core/scripts/graph_check.py:67, core/scripts/graph_check.py:207); the multi-scope and `Revert "…"` extensions landed after my pass and were verified by the other reviewers, NOT by me.
AC7 → `GATE: GREEN`, `32 discovered checks`, `E2E: GREEN — 164/164`, `115 framework-owned files intact`, core equivalent to `.vteam` for all rendered scripts, evidence re-captured — **satisfied on the staged tree**.


## R2 — challenger
MODEL: sonnet
VERDICT: APPROVE

### Tried to break (re-verification only, per instruction — fresh repro scripts, not a re-run of the author's own assertions)
- Ran my original `attributes()` unit probes against the current core/scripts/graph_check.py:67 (`fix(TB-5,other)!:`, `feat(api,TB-5):`, `merge(TB-5,TB-9):`, `Revert "feat(TB-5): x"`) — all now return `True`.
- Re-ran my original end-to-end git fixture (`repro_multiscope.py`, independent of the diff's own selftest) committing `fix(PROJ-2,billing)!: sneaky billing change` outside `CODE-SCOPE: src/auth/` — `graph_check.py` now exits 1 with `PROJ-2: commit … touches outside the declared CODE-SCOPE … src/billing/b.js`.
- Generalization check with cases in NEITHER party's test tables: `fix(TB-5, api, ui)!:`, `chore(TB-5):`, `feat(TB-50,TB-5):` (longer key co-present) all correctly attributed; `feat(TB-59):` and `docs(other,TB-5x):` correctly NOT — the fix is a real parse, not special-cased to the literal strings in either test suite.
- Re-ran my `..`-traversal repro: `split_bookkeeping()` on `docs/pm/../src/billing/x.ts` now resolves through `posixpath.normpath` to `docs/src/billing/x.ts` and is correctly classified as CODE, not bookkeeping (`ignored: {}`). This is a correction to my own original card — `docs/pm/..` cancels back to `docs/`, not to the repo root, so my claimed collision with `src/billing/x.ts` was never real; the underlying bug (spelling-dependent misclassification) is what is fixed. Built the actual colliding case (both tickets naming the same resolved file via different spellings) — now correctly reds: `VT-1 and VT-2 share edit territory (docs/src/x.ts ∩ docs/src/x.ts)`.
- Re-ran my repo-root-scope repro: `paths_touch(".", "src/anything")` → `True`, `scopes_overlap(["."], ["src/anything/x.ts"])` → `'. ∩ src/anything/x.ts'` (previously `False` / `None`).
- Built a fresh (not copy-pasted) squash-merge fixture from scratch against the current `discover()`: init repo → branch with committed tasksheet → `git merge --squash` plus commit on `main` → `discover()` now returns `{}` (was `{'VT-3': [...]}`).
- Independently tested the merge-commit non-goal: `git init`, commit on a feature branch, `git merge --no-ff`, then `git show --name-only --format= HEAD` → zero files printed, confirming that attributing merge commits would change no verdict.
- Ran all three gates' selftests directly: `python3 core/scripts/graph_check.py --selftest`, `python3 core/scripts/parallel_check.py --selftest`, `python3 core/scripts/coord_check.py --selftest` — all green.

### Findings
All four of my original CONFIRMED findings reproduce as FIXED under independent re-test:
1. core/scripts/graph_check.py:67 (`attributes()`) — multi-scope conventional commits and `Revert "…"` / `Reapply "…"` now correctly attributed. The prior silent false negative (the gate staying green on a genuinely out-of-scope multi-scope commit) is closed.
2. core/scripts/parallel_check.py:68 (`norm()`) — `..` and `./` spellings are canonicalised before any prefix test, so classification no longer depends on how a path was typed.
3. core/scripts/parallel_check.py:95 (`paths_touch`) — a CODE-SCOPE of `.` now collides with every other scope instead of nothing.
4. core/scripts/parallel_check.py:300 (`has_landed`) — a squash-merged branch is now excluded from the in-flight set. Verified this does not overcorrect: a fresh not-yet-diverged branch and new work added after a squash both still count as in-flight (these two sub-cases I checked via the selftest output rather than re-deriving from scratch — flagging that as the one part I did not re-derive).
- ADDRESSED, not a bug: merge-commit non-attribution left unchanged, with the reason now documented at core/scripts/graph_check.py:95 and independently verified above. The finding was real (the function does return `False`) but the consequence I flagged does not exist, because `check_scope`'s file reader cannot see merge-commit files either way. Correctly deferred as a documented non-goal rather than silently ignored.

### Lens answers
(a) The new `sh()` swallows in `tasksheet_text` (both gates) and `discover()`'s `--merged` filter all fail SAFE (stricter), not open — confirmed again by fixtures now covering the empty-scope and empty-merged-set paths.
(b) No pre-existing selftest assertion was deleted or weakened (checked against `origin/main` in round 1); this round only added coverage.
(c) `find_conflicts` and `discover` gained defaulted parameters — every caller either passes them explicitly or relies on the safe default; no broken caller exists.

No new findings raised; this card supersedes my prior card.
