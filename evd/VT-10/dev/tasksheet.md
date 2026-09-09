# VT-10 — task-sheet (DEV lane)

CODE-SCOPE: core/scripts/parallel_check.py core/scripts/coord_check.py core/scripts/graph_check.py core/scripts/orca_team.sh core/doctrine/parallel-transport.md core/workflows/dev.md core/workflows/team.md .claude/skills/dev/SKILL.md .claude/skills/team/SKILL.md

> `docs/`, `evd/`, `.vteam/` are graph_check's always-legal homes, so the rendered
> `docs/team/*` + `.vteam/scripts/*` outputs of `node bin/vteam.mjs update` and this
> evidence dir need no scope entry. `.claude/` is NOT always-legal — hence the two
> rendered SKILL.md files above.

## Requirement

The first live `/team` run with `team.parallel: 2` on a real Orca transport (two
opus workers in child worktrees, 2026-09-09) proved five defects in the
parallel-mode gates. All five share one root cause family: the gates assumed a
SINGLE working tree. In split-worktree mode a sibling ticket's `evd/` is not on
this disk, a shared bookkeeping file is not edit territory, a merged-but-undeleted
branch is not in flight, and a commit that merely says a ticket key in prose is
not that ticket's work. This ticket ports the fixes the PM already exercised live
(installed-runtime patches, gates GREEN afterwards) into `core/` **with their
selftests**, and writes the operating rules into doctrine so the next parallel run
does not re-learn them.

### Acceptance criteria (as the ticket states them)

1. Ticket B's tasksheet committed only on `feat/B-…` (not on disk) → `parallel_check`
   reads B's CODE-SCOPE from git, GREEN for disjoint scopes; no committed tasksheet →
   the red names it "tasksheet missing on `<branch>`, not committed", not a phantom
   empty scope. Off-disk git fixture in the selftest.
2. Same layout → `coord_check` finds the receiver's scope in git and calls the handoff
   "reflected" (GREEN); `VT-1` must not match a `VT-11` branch.
3. Two in-flight scopes both listing `docs/pm/coordination.md` (or anything under
   `paths.pm` / `paths.evidence` / `paths.qa`) → printed as "bookkeeping paths not
   counted as edit territory", no conflict; a real overlap under code paths still RED
   (boundary pair).
4. Local `feat/A-…` branches already merged into the protected branch (including one
   checked out in a worktree, `+`-decorated by `git branch`) → not counted toward
   `team.parallel`; the count line reports only unmerged branches.
5. Subject `chore: … found by the TB-5 worker` → NOT attributed to TB-5; subjects
   `TB-5 …`, `feat(TB-5): …`, `merge(TB-5): …`, `[TB-5] …` → ARE attributed. Selftest
   both directions; the existing 7 mutations stay red.
6. Doctrine: `core/doctrine/parallel-transport.md` + `core/workflows/dev.md` T1 state
   the committed-tasksheet rule, bookkeeping-never-CODE-SCOPE, and the pre-trust need
   for `orca worker-start` into a NEW worktree — `orca_team.sh` gains a `trust <path>`
   helper or the doctrine names the exact `~/.claude.json` field.
7. `gate.sh` GREEN, `doctor` 32 selftests green, `tests/e2e.mjs` green with README
   counts unchanged, no unresolved `{vars}`; evidence under `evd/VT-10/dev/` with the
   three selftests' output and a live two-worktree probe.

## Spec check — the governing sections, quoted

`docs/specs/` holds only `INDEX.md` + `changes.md` in this repo (it is the framework's
own repo; the framework's spec of record is the workflow + doctrine text itself, and
the ticket's "Spec / oracle" section names exactly that). The oracles I read and
quote below are therefore the workflow/doctrine/docstring text the ticket names.

**`core/workflows/team.md` §T2, parallel branch (lines 67-91) — verbatim:**

> **Parallel (`team.parallel: N > 1`) — fan out the coding, serialize the
> integration:** the PM picks up to **N** unblocked tickets whose `CODE-SCOPE`
> are **pairwise disjoint** (/pm P1 leg (g)) and dispatches each as a DEV agent
> in its **own git worktree** …
> 3. **Collision is a gate, not a hope.** `parallel_check` reds two in-flight
>    branches that share a file and any count past N; the PM never dispatches an
>    overlapping pair — it serializes them.

The spec's own words are "its **own git worktree**" and "in-flight". Both defects
1/2 and defect 4 are the gates contradicting this spec: a gate that reads a sibling
scope from the local filesystem cannot work in "its own git worktree", and a merged
branch is not "in flight". So the fixes restore spec conformance; they do not add
new requirements.

**`core/scripts/parallel_check.py` docstring (house of record for what it reds) —
verbatim:**

> When on, the IN-FLIGHT set = local branches matching `git.branch_pattern`
> (feat|fix/<KEY>-nn-*), minus the protected branch. For each, the ticket key →
> its `CODE-SCOPE:` line in {paths.evidence}/<TICKET>/dev/tasksheet.md (the
> committed tasksheet /dev T1 already requires).

The docstring already says **committed** tasksheet — the code read the working tree.
The docstring was right and the implementation was wrong; the fix makes the code
match its own contract, and the docstring gains the worktree sentence.

**`core/scripts/coord_check.py` docstring — verbatim:**

> every scope or contract handoff agreed in chat is appended to
> {paths.pm}/coordination.md, and THIS gate proves the log is real

Note the gate's own design **requires** every coordinating agent to write
`{paths.pm}/coordination.md`. Defect 3 is therefore a contradiction inside the
framework: `coord_check` orders both agents to write one shared file, and
`parallel_check` reds them for sharing it. Bookkeeping homes must be excluded, or
the two gates cannot both be green.

**`core/scripts/graph_check.py` docstring §5 — verbatim:**

> 5. SCOPE DERAILMENT (MAST 2.3, task derailment): if a ticket's tasksheet
>    declares `CODE-SCOPE: <path> <path>…` …, commits **naming that ticket** may
>    only touch files under the declared paths

"naming that ticket" is the ambiguity defect 5 exploited. The fix pins the meaning
to *the key LEADS the subject*, which is what the ticket's AC 5 asks for.

### Assumptions to confirm — none blocking

- A CODE-SCOPE that lists **only** bookkeeping paths is not covered by any AC. The
  reference implementation would report it as "no CODE-SCOPE in its tasksheet",
  which is a misleading red (the line exists). I add one distinct message for it —
  see "Deliberate deltas from the reference" below.

## Change ledger

`docs/specs/changes.md` has a header and zero `CH-nn` rows — no requirement deltas
touch this ticket's area. No new spec contradiction found: defects 1/2/4/5 are the
implementation disagreeing with its own docstring (code wrong, text right), and
defect 3 is a cross-gate contradiction that this ticket RESOLVES rather than
discovers as an open question. No `proposed` CH row needed.

## KB preflight

`docs/qa/knowledge-base.md` §0 read; its INDEX table has **zero rows** (no lessons
in transit) — nothing matches this ticket's tags. `docs/qa/known-issues.md` has only
its `# Known issues — KI-nnn registry` heading, no KI entries. Nothing to answer.
Under the §0 cleanup thresholds (INDEX > 25 rows / file > 250 lines) — no
consolidation pass due.

## Task context

`docs.task_context.always` is `[]` and `by_label` is `{}` in `vteam.config.yaml` —
nothing mapped, nothing missing.

## Code map

`python3 .vteam/scripts/code_map.py query VT-10 parallel worktree tasksheet attribution`
(map rebuilt first — it printed `NO CODE MAP`) returned:

- `core/doctrine/parallel-transport.md` — the doctrine to extend (AC 6)
- `core/workflows/team.md:185` — § "Parallel DEV coordination", the T2 rule to point
- `core/scripts/parallel_check.py` — defects 1, 3, 4
- `core/workflows/dev.md` — cites `{paths.evidence}/<TICKET>/dev/tasksheet.md`, the T1
  rule to extend (AC 6)
- 1-hop: `core/scripts/lib/ctx.py` (config reader used by all three gates),
  `core/doctrine/review-standard.md`, `core/scripts/review_check.py`

**code map MISSED: `core/scripts/coord_check.py` — defect 2 lives here** (`scope_of`
reads the sibling tasksheet from disk). The map ranked it out even though the query
carried "tasksheet"; its scan roots (`git.code_paths` = `src/, core/, bin/`) do
include it, so this is a ranking miss, not a root miss.
**code map MISSED: `core/scripts/graph_check.py` — defect 5 lives here** (commit
attribution). Same cause: neither file's text carries the query terms densely.
Both were read anyway.

Also read (not returned by the map, found by reading the ticket): `core/scripts/orca_team.sh`
(AC 6's `trust` helper), `.vteam/scripts/lib/tracker.py` (claim/comment API),
`README.md` (the "32 today" / "164 checks" counts AC 7 pins).

### What exists vs what is new

| File | Exists | This ticket |
|---|---|---|
| `core/scripts/parallel_check.py` | `discover`, `find_conflicts`, `parse_scope`, `paths_touch`, `sh` | + `tasksheet_text`, + `split_bookkeeping`; `discover` gains `with_sources` + merged-branch filter; `find_conflicts` gains `sources` |
| `core/scripts/coord_check.py` | `scope_of` reads disk | + `tasksheet_text`; `scope_of` delegates to it |
| `core/scripts/graph_check.py` | `check_scope` attributes by `\b<key>\b` anywhere in the subject | + `attributes()` (leading-key rule); `check_scope` calls it |
| `core/scripts/orca_team.sh` | `status`, `open-run`, `wait` | + `trust <path>` |
| `core/doctrine/parallel-transport.md` | transport + serial integration | + "Rules the gates enforce" section |
| `core/workflows/dev.md` T1 | CODE-SCOPE bullet | + parallel-mode commit-first + bookkeeping rule |
| `core/workflows/team.md` T2 | 3 integration rules | + one sentence pointing at the rule |

## Data model

No database, no schema, no migration — this repo is a CLI/framework (`app.start` is
`""`, `stack.profile: generic`). The only "schema" touched is the config key set the
gates read, all of which already exist in `vteam.config.yaml`: `team.parallel`,
`team.coord_budget`, `git.protected_branch`, `git.branch_pattern`, `project.key`,
`paths.evidence`, `paths.pm`, `paths.qa`. **`paths.qa` is newly read by
`parallel_check`** — it is present in this repo's config (`docs/qa`) and
`split_bookkeeping` defaults it, so an older config without the key still works.

## Impact — who else uses what I change

Searched every symbol I touch (`grep -rn` over `core/ bin/ src/ tests/ .githooks/`):

- `parallel_check.discover(…)` — called only from `parallel_check.main()`. The new
  `with_sources` parameter defaults to `False`, so the 5-arg call shape is unchanged
  for any external caller. **No other caller exists in the repo.**
- `parallel_check.find_conflicts(…)` — called from `main()` and its own selftest. The
  new `sources` parameter defaults to `None`; every existing selftest call stays
  valid. This is why I extended rather than replaced the signature.
- `coord_check.scope_of(…)` — called only from `coord_check.main()`. Signature
  unchanged; only its body changes.
- `graph_check.check_scope(…)` — called only from `graph_check.main()`. Signature
  unchanged.
- `gate.sh` / `gate.py` run all three as steps; `doctor` discovers their `--selftest`.
  Both call them as processes, so no signature coupling.
- `orca_team.sh` — called from `core/workflows/team.md` + `core/doctrine/parallel-transport.md`
  (documented invocations `status` / `open-run` / `wait`). Adding a 4th subcommand
  cannot break the existing three; the `*)` usage line is updated with it.
- **`~/.claude.json` is user state OUTSIDE the repo.** `trust` writes it. That is the
  only thing in this diff that touches anything outside the working tree, which is
  why it backs the file up before writing and is idempotent (see security note).

Auth/role implications: none (no request handling, no sessions). External sandbox:
none. The `trust` helper touches the user's Claude Code config — treated as the
security-sensitive edit of this diff.

## Competencies

`dev-identity` (T1, always) · `dev-codebase-design` (T2, always) ·
`dev-testing-craft` (T2, always) · `dev-error-handling` (T3, always) ·
`dev-security-basics` (T3, always).
Not loaded, and why: `dev-data-modeling` / `dev-domain-modeling` (no `label:data`,
no `path:prisma|migrations|db`, no schema in this repo), `dev-api-design` (no
endpoint), `dev-stack-nextjs-prisma` (`stack.profile: generic`), `dev-debugging`
(no red to chase; would load the moment one appeared — none did).

Rows followed where the choice was non-obvious:
- `dev-codebase-design` → "a function used by two callers with the same intent gets
  ONE home": `tasksheet_text` is needed by both `parallel_check` and `coord_check`.
  Decision below in "Deliberate deltas".
- `dev-testing-craft` → "for each rule in the spec touched by the diff, where is the
  pair (last valid, first invalid)": every new behavior below ships a boundary PAIR,
  not a single happy assertion — bookkeeping-ignored **vs** real-overlap-still-red;
  read-from-git **vs** not-committed-named; `VT-11` branch **vs** `VT-1` key;
  leading key **vs** prose mention.
- `dev-security-basics` → the `trust` subcommand writes a file in `$HOME`. It is the
  one place in this diff where a path from the caller reaches a write, so it
  validates the path, refuses to create it, and never interpolates it into a shell
  string (python `json` does the write).

## Plan — minimal, file by file

1. `core/scripts/parallel_check.py` — (a) `tasksheet_text(root, ev, ticket, branch)`
   returning `(text, source)`, order: own working tree → `git show <branch>:<path>` →
   working-tree fallback → `("", "missing on <branch>")`; (b) `discover` filters
   branches reachable from the protected branch via
   `for-each-ref --merged=<protected>` (plain names, no `+`/`*` decoration) and
   returns `(scope_map, sources)` under `with_sources`; (c) `split_bookkeeping` moves
   `paths.pm` / `paths.evidence` / `paths.qa` paths out of edit territory and prints
   them; (d) `find_conflicts(scope_map, sources)` names an uncommitted tasksheet
   distinctly; (e) docstring updated to describe all of it.
2. `core/scripts/coord_check.py` — `tasksheet_text(root, ticket, ev)` (working tree,
   else the committed sheet on any in-flight branch naming the ticket, with a
   `VT-1`-must-not-match-`VT-11` key boundary); `scope_of` delegates.
3. `core/scripts/graph_check.py` — `attributes(subject, key)`: the key must LEAD the
   subject (bare / `word:`-prefixed / `word(KEY):` / `[KEY]`); `check_scope` uses it.
4. `core/scripts/orca_team.sh` — `trust <path>` subcommand.
5. Doctrine + workflows per AC 6; then `node bin/vteam.mjs update` to re-render
   `docs/team/*`, `.claude/skills/*`, `.vteam/scripts/*`.

Migration: **no**. New dependency: **no** (stdlib `json`/`re`/`subprocess`/`tempfile`
only).

### Test plan — which test proves which AC

| AC | Test | Expected value cites |
|---|---|---|
| 1 | `parallel_check --selftest`: off-disk git fixture, `tasksheet_text` returns `["src/other"]` with source `git …`; a branch with no sheet returns `("", "missing on …")` and `find_conflicts` says "not committed" | AC 1 text; the gate's own docstring ("the committed tasksheet") |
| 2 | `coord_check --selftest`: off-disk git fixture, `scope_of(r,"VT-11")==["src/lib/order.ts","src/ui"]`; `scope_of(r,"VT-1")==[]` | AC 2 text |
| 3 | `parallel_check --selftest`: bookkeeping pair — `find_conflicts(code)==[]` for two scopes sharing `docs/pm/coordination.md`, **and** `"share edit territory"` still raised for two scopes sharing `src/a` | AC 3 boundary pair |
| 4 | `parallel_check --selftest`: git fixture with a merged branch → `discover` omits it, unmerged one kept | AC 4 text |
| 5 | `graph_check --selftest`: `attributes()` table (4 positive forms, 3 negative) **and** an end-to-end fixture commit whose subject only mentions the key touching an out-of-scope file → gate stays GREEN | AC 5 text |
| 6 | `orca_team.sh trust` run on a temp path, twice (idempotent), read back from `~/.claude.json`; doctrine text read back | AC 6 text |
| 7 | `gate.sh`, `doctor`, `tests/e2e.mjs`, three `--selftest`s | AC 7 text |

### Out of scope (explicitly)

Everything the ticket's own "Out of scope" lists: the `nextjs-prisma` profile's
monorepo blindness (VT-11), per-worktree port/DB isolation, Orca worker token
accounting, `docs/backlog/attachments/` not being git-ignored, `browser.mjs`
needing `playwright`. Also out: any change to `parallel_check`'s overlap ALGORITHM
(`paths_touch` is untouched) and any new gate.

## Deliberate deltas from the reference implementation

The reference was exercised live and green; I ported every hunk but did not port it
blindly. Three deliberate differences, each with a reason:

1. **`graph_check`: the attribution regex became a named function `attributes(subject, key)`.**
   The reference inlines the compiled regex inside `check_scope`'s per-ticket loop.
   A rule that AC 5 states as seven cases needs seven cheap assertions, and
   `graph_check`'s selftest is an end-to-end git-fixture harness where each case
   costs a commit. `dev-testing-craft`'s "make the rule directly assertable" applies:
   extracting the predicate lets the selftest state all seven cases as one table AND
   still prove the end-to-end negative with one fixture commit. Behavior is identical.
2. **`parallel_check`: a CODE-SCOPE of only bookkeeping paths gets its own message.**
   With the reference's ordering, such a ticket falls into the "no CODE-SCOPE in its
   tasksheet" branch — a red whose remedy sentence ("add CODE-SCOPE at /dev T1")
   is wrong, because the line is there. `dev-error-handling`'s "an error message
   names the actual remedy" applies. One extra `sources` marker, one extra branch,
   one selftest assertion.
3. **`tasksheet_text` is NOT shared between the two gates.** `dev-codebase-design`
   would normally push two same-named functions into one home
   (`core/scripts/lib/`). I kept them separate on purpose: they solve DIFFERENT
   problems. `parallel_check` already knows the branch (it is iterating branches) and
   must report WHERE it read from; `coord_check` knows only a ticket key and must
   SEARCH the branches for it (hence the `VT-1`/`VT-11` boundary, which
   `parallel_check` does not need — its key comes pre-extracted from the branch
   name). A shared helper would need both a branch-or-None parameter and a
   return-the-source flag, i.e. two behaviors behind one name. **Option A (as
   built): two 12-line functions, each doing one thing, each with its own boundary
   selftest. Option B: one `lib/tasksheet.py` with `branch: str | None` and
   `with_source: bool`.** B removes ~10 duplicated lines and adds a parameter matrix
   of 4 combinations of which 2 are unused, plus a third file in the gate's import
   graph (each gate is currently self-contained apart from `lib/ctx`). I took A and
   record the trade here so a future reader does not "fix" it by accident. If a
   third caller appears, B becomes correct — that is the trigger to revisit.

## Side findings (NOT fixed here)

- `.vteam/scripts/lib/tracker.py` `comment()` writes `### <YYYY-MM-DD HH:MM UTC>`
  while every hand-written comment in `docs/backlog/*.md` uses `### <date> <Actor>`.
  The two formats coexist and `get_issue` parses both, but the actor is lost on
  machine-written comments. Not this ticket's file; noted for a follow-up.
- `docs/backlog/VT-10.md` was UNTRACKED at branch time (the PM wrote the ticket
  without committing it). It is committed on this branch, since `dor_check` and
  `graph_check` both read it from disk and a sibling worktree could not.
- The code map ranked both `coord_check.py` and `graph_check.py` out of a query that
  named their exact subject matter (see Code map above) — the map's lexical ranking
  under-weights python files whose relevant text lives in a docstring far from the
  matched term.

## /verify gate results

Verbatim in `evd/VT-10/dev/cmd_verify.md` (written only after seeing green). Closing lines:

- `GATE: GREEN (9 steps ran, 1 declared skips)` — the skip is the pre-existing
  `.vteam/build.sh absent` (no build step in a CLI repo), declared out loud
- `✅ gate selftests green (32 discovered checks prove they can red)`
- `✅ manifest verified (115 framework-owned files intact)` — same count as before
- `E2E: GREEN — 164/164 checks passed`
- all three patched scripts' `--selftest` OK, run in BOTH `core/scripts/` and the
  installed `.vteam/scripts/` copy (they are byte-identical after `update`)
- README's "32 today" and "**164 checks**" both still true; README untouched
- zero unresolved `{vars}` in the three rendered outputs

## Self-review (T4a) results — what I caught before the reviewers did

Re-read `git diff --cached` hunk by hunk, every hunk asked "which AC?". Four
findings, all mine, all fixed in this branch before any reviewer saw it:

1. **`{team.parallel}` in my own new dev.md bullet rendered to the literal config
   value** — `node bin/vteam.mjs update` produced "In parallel mode (`1` > 1)
   COMMIT the tasksheet FIRST", which is nonsense. Caught by READING the rendered
   `.claude/skills/dev/SKILL.md` instead of trusting the source. Fixed to the
   literal `` `team.parallel` ``. Lesson: in core markdown, a config var used as a
   *name* must not be written as a *template*.
2. **`find_conflicts` hardcoded `evd/` in the "not committed" remedy** — a project
   with `paths.evidence: evidence/` would be told to commit a path that does not
   exist. Added an `ev` parameter (defaulted, so no existing call broke) and a
   selftest asserting the message follows the configured dir.
3. **`coord_check`'s branch search had no defined order** — a ticket that was
   retried keeps its abandoned branch, an abandoned branch holds a stale
   CODE-SCOPE, and `for-each-ref`'s default order could let the stale one shadow
   the live one *non-reproducibly*. Now `--sort=-committerdate` (newest first),
   with a two-branch fixture and mutation M7 proving it.
4. **`trust` would have re-indented the user's `~/.claude.json`** — that file is
   often megabytes of history; rewriting a compact file with `indent=2` balloons
   it and noises up any diff the owner takes of their own settings. Now the
   original's style is detected and preserved (verified both directions).

Also swept for: dead code (none), debug prints (none), forgotten TODOs (none),
scope creep (every hunk traces to AC 1-7 or to `update`'s rendering).

**Deliberately NOT done** (so reviewers don't re-dig it): `tasksheet_text` is
duplicated across `parallel_check` and `coord_check` rather than shared — the
A-vs-B trade is written out under "Deliberate deltas from the reference", with the
trigger that would make sharing correct.

**The mutation discipline, done rather than claimed:** all seven new rules were
reverted one at a time in scratch copies and each intended assertion fired.
Table + verbatim messages in `cmd_probe.md` §2. M5/M6 are the pair that pins the
attribution rule from both sides — too loose attributes the prose mention, too
tight stops attributing `feat(KEY):`.

## T4b review — what the reviewers changed about this diff

Four fresh agents reviewed it (R1/R2 plus replacements after the first pair went
quiet; all four eventually reported, and all four cards are in `review.md`).
**Round 1 was four REQUEST-CHANGES cards with ten CONFIRMED findings**, every one
of which reproduced when I re-ran it. Round 3 reopened one of them. Final: both
seats APPROVE.

The two findings worth remembering:

1. **I made the gate weaker than the code I replaced.** My merged-branch filter
   (`--merged=<protected>`) also hid branches that had not yet DIVERGED, because a
   freshly dispatched worker's tip sits AT the protected tip. Three fresh branches
   → the gate saw none, and the `team.parallel` cap stopped firing in exactly the
   window it exists for. My first fix (`behind > 0`) was only half right and a
   reviewer broke it in one commit: it holds until the day's first serial merge,
   then hides every idle worker again. The rule is now TOPOLOGICAL — a branch that
   landed through a merge commit is never on protected's first-parent chain, a
   merely-created one always is — which is stable however far protected moves.
2. **A silent false negative in the attribution rule I wrote.** `attributes()`
   never matched a multi-scope conventional commit (`fix(KEY,other)!:`,
   `feat(api,KEY):`), so the derailment gate quietly stopped watching a standard
   commit shape — proven end-to-end with an out-of-scope file left green. The
   dangerous direction: a gate that stops looking says nothing.

Also fixed from their cards: `~/.claude.json` mode widened 0600 → 0644 by
write-then-rename (a file holding `oauthAccount`); `cd` failure unchecked so an
un-enterable directory wrote `projects[""]` and exited 0; `..`/`./` spellings
deciding whether a path counted as bookkeeping; `CODE-SCOPE: .` colliding with
nothing; squash-merged branches never recognised as landed; and five assertion
gaps their mutation sweeps found in MY selftests.

Two reviewer claims I corrected rather than accepted, each with the command:
`docs/pm/../src/thing.ts` resolves to `docs/src/thing.ts`, not `src/thing.ts`; and
`Merge branch …` non-attribution has no consequence because
`git show --name-only --format=` prints nothing for a merge commit. Both reviewers
accepted the corrections. Details and the answered QUESTIONS are in `review.md`.

**Accepted, not fixed** (R1's closing non-blocking QUESTION): `mainline` inside
`has_landed` is a per-branch linear scan over a first-parent walk, kept as a list.
Measured at 69 commits in this repo. The mechanical fix — hoist into `discover`,
make it a `set` — is recorded for a follow-up rather than applied after approval.

Final mutation discipline: **14 mutations, 14 reds**, table in `cmd_probe.md` §2.
Five of those rows exist because a reviewer's sweep found my suite could not see
the rule at all.
