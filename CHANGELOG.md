# Changelog

What changed in each released version, newest first. Dates are the npm publish date.

Every entry is derived from the commit that bumped `package.json` — not written from
memory. Two versions below were bumped in git but **never reached npm**; they are kept
here because the version numbers are spent and skipping them silently would be a lie.

The current version always has an entry: `tests/e2e.mjs` fails if the newest heading here
does not match `package.json`.

---

## 0.19.2 — 2026-09-18

Everything the BMAD benchmark taught, turned into code the same week (bumped 2026-09-18; the
date is corrected to the npm publish date on release). Seven gates that crashed, lied or went
vacuously green in the arm's repo; ceilings on review and challenger rounds; a stop state when a
session ends mid-ticket; per-worktree ports and databases for parallel lanes; a measurement of
what each lane really loads into context (no lane is near 40k tokens).

### Fixed: a merged branch is not work in flight (VT-38)

The planner shipped in VT-37 read `git branch` and called every local `feat|fix/<KEY>-*` branch
work in hand. Nobody deletes branches after a merge, so 32 of this repo's 33 were history and the
plan reported **21 tickets in flight when one was running** — a planner that miscounts capacity
tells the lane everything is busy, and the lane believes it. In flight now means an UNMERGED
branch, local or pushed (`-a --no-merged`), with a fall back to listing every branch when the
protected branch is absent, so a fresh clone over-reports rather than concluding nothing runs.

The other half of the same lie: a ticket saying In Progress with nothing running. The plan reports
those under STALE WORK IN PROGRESS and `graph_check` warns about them — a warning, never a failure,
because it is a fact about the board rather than about the change under review, and a ticket
waiting on something is blocked, not drifting. Nine such tickets in this repo were then corrected
against their evidence, and the tenth was not: VT-2 shipped with no dispatch row, and the only
retroactive row the ledger grammar accepts would have carried an invented token count, so the
question went to the decision queue instead.

### Added: the ledger's `tok ≈` is audited against measured usage (VT-39)

Every dispatch row ends `done · tok ≈ <N>k`, typed by the agent from memory — the one column of
testimony left in a framework whose argument is evidence over claims. `usage --sync` has been
publishing MEASURED session-log numbers into `{paths.pm}/usage/<actor>.md` all along, and nothing
put the two side by side. The new advisory gate step `cost` compares them PER DAY — a session log
knows the day and the model, never which ticket a token belonged to, so no per-ticket number is
derivable and none is produced. It warns past `ledger.cost_tolerance_factor` (default 10×) naming
the date, both numbers and the ratio, and — the louder finding — says when the measured record has
stopped being kept at all, past `ledger.usage_max_stale_days` (default 7). Advisory everywhere: an
estimate and a measurement differ by construction, and a gate that reds on that teaches people to
inflate the estimate. A divergence is a finding about the estimate; the doctrine says plainly that a
ledger row is never edited to match the measurement. A repo that has never synced gets one quiet
line and exit 0.

Run on this repo it found the thing it was written for: the measured record stopped on 2026-08-24
while the ledger ran to 2026-09-18, and on the only two days that were measured the estimates were
~13× low. The rows stay as written.

### Added: `graph --plan` — the dispatch order is computed, not reasoned (VT-37)

The graph knew the dependencies and printed them; then the PM lane worked out the order again in
prose, over every open ticket, every session. Ordering a DAG is Kahn's algorithm.
`vteam graph --plan` returns the waves (level 0 starts now), the batches inside each wave that are
already pairwise disjoint by `CODE-SCOPE` and capped at `team.parallel`, the lane each item is
owed (In Review routes to /qa, never a second /dev pass), what is in flight (a pushed
`feat|fix/<KEY>-*` branch is running, not dispatchable), what is blocked and by what — a cycle, a
decision row — the critical path by day-cost, and per item the upstream evidence to read first.
`/pm` P1 and `/team` consume it and adjudicate only what the plan prints as not its call. Measured
on this repo: the ordering input was 170,772 bytes ≈ 42,693 tokens of ticket files; the plan is
9,720 bytes ≈ 2,430 tokens, and it returns the same answer twice. The plan advises; every gate is
untouched and `graph` still exits 0 in every mode.

Three neighbouring claims were measured and did not survive, and are recorded in
`evd/VT-37/dev/proof.md` so they are not re-opened: reviewers already run in parallel, caching the
gate's bookkeeping steps would save 1.4 % of a 90.8 s run (the test suite is 98.6 % of it), and the
graph was never purely passive.

### Changed: the review shape follows the RISK of the diff, measured (VT-36)

Every change used to pay the same toll: two fresh reviewer agents, three "tried to break"
bullets each. On a one-line copy change there is nothing to try, so the bullets got invented —
and a card written to satisfy a counter has stopped being evidence. `change_class.py` now reads
the diff and returns `docs`, `surface`, `logic` or `high-stakes`; `review_check` picks the shape
from that class and prints it on every verdict. A diff where no executable file moved needs no
reviewer card. A diff where only string bodies, comments and JSX text moved, under
`review.surface_max_lines`, needs one card with one real bullet. Everything else is exactly the
fence that was there before, and every doubt — an added file, a renamed one, a config value, a
template literal, an unparsable file — resolves upward. The class comes from the diff: no agent
declares it and no dossier claims it. `review.proportional: false` restores the uniform fence in
one line. Measured on this repo's own history: 12 of the last 40 commits are `docs` class, and
none that touched code moved downward.

### Added: one worktree, one port, one database, one scratch dir (VT-35)

Benchmark finding E13: the DEV lane and three reviewers ran at once on ONE SQLite file, ONE dev
server and ONE scratch directory; fixture hooks raced, 19 phantom failures were reported and a
fabricated CONFIRMED was one tired reviewer away. Worktrees share `vteam.config.yaml`, so
`app.url` alone put every lane on one server. `lane_env.sh` now derives a lane's `PORT`,
`APP_URL`, `DATABASE_URL` (sqlite, under a per-lane scratch dir), `VTEAM_SCRATCH` and
`VTEAM_LANE` from the worktree it runs in — the same port scheme `init` writes, so a plain
checkout lands where init pointed — and leaves a marker; `app_check` honours `APP_URL`;
`parallel_check` reds two in-flight worktrees without a lane environment, or two lanes on one
port or one database. Reviewers run against the lane's own environment, never the author's.

### Fixed: seven gates that crashed, lied or went vacuously green in a real repo (VT-30)

The benchmark arm's RUNLOG listed 16 environment findings; eight were the framework's own
gates misbehaving in an ordinary Next.js repo. `preflight` no longer REDs a local-only repo
for having no origin (it names the local-merge rule instead). `verbatim_gate` recognises
unbolded and `AC-A01`-shaped codes and goes RED — never vacuously green — when sources are
configured but no coded row is found (the testbed's gate turned out to have been vacuous
all trial). `token_check` scans `git.code_paths` instead of a hardcoded `src/` and no longer
crashes on an App-Router layout. `app_check` looks up who listens on the port and reports a
stranger's server as `APP: FOREIGN` (a whole a11y suite was nearly claimed on one). `gate.sh`
tees its transcript to a file it names. `graph_check` requires a ledger row for every ticket
in review or done. `/verify` principle 6 says a red-proof against a built server needs a
build on both sides of the revert.

### Changed: `init` prefills `app:` for Next.js repos on a checkout-unique port (VT-31)

Benchmark findings E2/E7/E15: the vteam arm spent its first hour discovering that `app.*` was
empty (every browser step printed `APP: SKIP`), and two arms on one machine both sat on `:3000`,
so the gate reported the other arm's server as this one's. A repo whose `package.json` declares
`next` now gets `start: npx next dev -p <port>`, `url`, `health: /` at init, with the port derived
from the checkout's real path (3100–3899), and init prints which port it pinned. Non-Next repos
are untouched. e2e 199 → 204 checks.

### Changed: review rounds and BA challenger rounds have a ceiling (VT-32)

The 2026-09-03 benchmark arm spent three review rounds (~2.5 h) on one ticket and three
challenger rounds sharding a frozen, AC-coded spec; nothing said when to stop. `vteam init` now
writes `review.max_rounds: 1` and `ba.challenger_rounds: 1`, and `review_check.py` counts the
`## Round N` headings in the dossier against the knob (a `SECURITY`-tagged finding or a
high-stakes diff lifts it; `--ba <feature>` does the same for the challenger file, lifted by a
`SPEC` tag). The dev and BA lanes say what to do when the ceiling is hit — answer the finding in
the dossier, do not open another round — and a brief is now a prioritised attack list. Absent knob
= no ceiling, printed on the green line, so no existing repository goes red on upgrade.

### Added: the doctrine a lane loads at start is now measured, not argued (VT-33)

`context_budget.py --lane <lane>` / `--all` reads the rendered skill, resolves the files it
tells the agent to read before any ticket work (role playbook, identity, competency INDEX and
every competency the INDEX marks `always`) and prints bytes and ≈tokens (bytes/4) per file,
with everything else the skill names listed apart as on demand. Measured on this repo on
2026-09-18: dev ≈ 16.8k tokens mandatory (8.9k of it the skill itself, 4.1k the four `always`
competencies), qa ≈ 17.5k, ba ≈ 10.3k, pm ≈ 9.4k — no lane near the 40k default budget
(`team.context_budget_tokens`). The "31 competencies bloat the context" claim has a number now:
a lane loads four or five of them by default; the rest wait for a matching ticket. Runs as an
advisory gate step (`context-budget`) and never blocks.

### Added: a session that ends mid-ticket leaves a stop state behind (VT-34)

The benchmark arm stopped with 11 uncommitted files, a red unit suite and no closing entry;
two weeks later the stop had to be reconstructed from `git status`. `stop_state.sh` now writes
`{paths.evidence}/<KEY>/dev/STOP-STATE.md` (branch, HEAD, uncommitted files, last gate line)
whenever a session ends on a `feat|fix/<KEY>-…` branch with work in flight, and keeps exactly
one `- stop-state:` line on the task-sheet. Claude Code runs it from a `SessionEnd` hook the
adapter installs next to the SessionStart one (merged into `.claude/settings.json`, user hooks
untouched). The dev workflow gains "Stopping mid-ticket": WIP commit or dirty tree, but always
the stop state, and `Blocked` with a reason when it is not a hand-off. `graph_check` reds a
stop state older than 7 days on a ticket that is neither Done nor Blocked — silent
abandonment. 35 selftests, 207 e2e checks.

## 0.19.1 — 2026-09-18 (published 2026-09-18 from `870b64c`)

A patch on top of 0.19.0 (published 2026-09-17 from `ce2322b`): one gate defect found by
its own CI the same day, the benchmark result the README had promised, and the front page
that ships in the tarball.

### Fixed: the gate's first step made PR clones shallow (VT-29)

`docs_shrink_check` fetched the PR base with `--depth=1`. Into a full clone that writes
`.git/shallow` with the base tip as a boundary, so six steps later `graph_check` read the
base-tip commit as a root and flagged it for "touching" every file in the tree — a
deterministic false RED on every stacked ticket branch. The fetch no longer limits depth,
and the selftest now proves a full clone stays full through PR mode.

### Added: the first benchmark result — a loss (VT-27)

The vteam-vs-BMAD run from 2026-09-03 was finally judged. **BMAD 91/91, vteam 84/91 (92.3 %),
and three vteam "done" claims were contradicted by the held-out probes** (AC-A07, AC-D02,
AC-D07). Published as promised in `docs/BENCHMARK.md` with the scorecard, the five repairs the
judge needed before scoring (all applied to both arms, re-calibrated to 91/91 afterwards), and
the caveats: one sample, arm-a scored at its stop state, no token cost recorded. VT-28 is open
on why the arm's own e2e passed what the probes fail — the answer goes in the same page.

### Changed: the front page is a first-run page (VT-26)

The README that ships in this tarball went from 685 lines to 95: the ten-second `audit`
transcript first, install in two commands, a real-transcript demo, who it is for and not
for, and links out. The long form moved verbatim to `docs/GUIDE.md` in the repository.
`tests/e2e.mjs` still verifies every count the README claims. The audience question the
rewrite raises is filed as decision D17, not assumed.

## 0.19.0 — 2026-09-17 (bumped 2026-09-11, published after VT-24 and VT-25 landed)

Everything here came from running the lanes on a real second repo and then reviewing
the result. Nothing in it was designed from the armchair, and several entries are
corrections to things 0.18.0 shipped.

### Added before publish (2026-09-17): the line-by-line code review (VT-24)

0.19.0 was still waiting on the registry, so a full read of the framework's 64 files
(18,602 lines) went in first. Thirteen defects, every one with a test that was RED
before the fix (`evd/VT-24/dev/proof.md`, `mutations.md`):

- **`preflight.sh` ran the ENTIRE gate on every `/dev T0`, `/pm P0`, `/ba B0`.** Its
  "is the driver installed" probe was `gate.py --help`, and the driver read every
  argument as a tail name. `gate.py --help` now prints usage and runs nothing; an
  unknown `--flag` exits 2 instead of silently becoming a tail.
- **`stale_verdict_check` was named by five workflows and wired into zero profiles** —
  the same declared-but-unwired hole VT-17 closed for `evd_check`. All six profiles
  now run it as the `stale-verdict` step (declared skip on remote trackers, where it
  would be one network call per ticket).
- **A tracker or design provider switched after init was unreachable**: `update` only
  refreshed provider files already on disk, `tracker.py` said "run init", `init`
  refused because the config existed. `update` now installs whatever the CURRENT
  config names.
- **`update` never removed files the package stopped shipping** — a retired gate
  lingered in `.vteam/scripts` forever and dropped out of the manifest, where doctor
  could not see it. `ManifestGuard.prune()`: unmodified orphans are removed and named,
  modified ones kept and named, `owned` paths never touched. This repo's own
  `.vteam/profiles/generic/gates.yaml` mirror turned out to be six weeks behind its
  source (and a stray `.new` was committed) — both corrected by the same run.
- **Packaged agents and the SessionStart hook were written outside the manifest**, so
  an upstream change never reached a consumer, who was told "kept YOURS" about a file
  it never edited. Adapters' `pointers()` now write through the caller's
  manifest-guarded path (refreshed while unmodified, parked as `.new` once edited);
  each adapter declares `outputDirs` so prune knows its tree.
- **copilot and windsurf emitted invalid YAML frontmatter** — `plan.md`'s description
  carries `kernel: Why, …`, and an unquoted plain scalar with `: ` is "mapping values
  are not allowed here". Quoted, like the claude-code adapter always did.
- **Profile detection keyed on `prisma/` alone**, so an Express + Prisma repo got
  `nextjs-prisma` and its gate reddened on `npx next typegen`. Detection now asks
  `package.json` for `next`; the `typegen` step declares a skip when it is absent.
- `bdd_report_check.py --root <dir>` crashed (`IsADirectoryError`) — real argparse.
- `ctx.py` and `ctx.mjs` disagreed on `[a,,b]` (Python returned `['a','','b']`, Node
  threw), and both silently DROPPED every top-level key after a first key that sat at
  column 2. Both die loudly now with one message; two conformance fixtures (15 → 17).
- `--attach` (both evidence checkers) erased every section AFTER `## TRACKER
  ATTACHMENTS` to the end of the file on a re-run — `evdpack.replace_section` replaces
  exactly one section.
- `schedule_check` took the FIRST dated cell of a decision row as its deadline; a
  Question that quotes the day it was asked read as OVERDUE on the spot. The `Due`
  column (from the header) decides; last dated cell without one.
- `graph_check`'s always-legal homes, `log_check`'s path check and `route_check`'s
  tasksheet lookup hardcoded `evd/`; they follow `paths.*` now.
- Dead code removed (`util.copyDir`, an always-true assert in `evd_check`'s selftest).

`npm test` grew from 172 to 192 checks.

**VT-25 (same day):** the five tools that had no test of any kind now prove themselves.
`orca_team.sh --selftest` runs offline against a fake `orca` and a temp `HOME` (status,
open-run, wait, and every `trust` guard — 0600, idempotent, backup-once, mode kept, bad
path / bad JSON refused). `auth.mjs` drives the csrf → callback → session flow on a fake
Playwright context. `ui_fidelity.mjs` and `ui-evidence.mjs` export their rules (colour /
px / font comparison and the closed-list intent grammar; args, headed policy and the
shots.json contract) and import playwright lazily, so the rules are provable on a machine
with no browser and a real run without playwright refuses with the install command instead
of a stack trace. `tools/prepublish-check.mjs` became `check({root, run})` with an
injectable runner: all five refusals (dirty tree, HEAD ahead/behind, published version,
red suite, bytecode in the tarball) fire on a fixture repo with a stubbed npm — the guard
behind every publish had never been shown to refuse one. `npm test`: 192 → 198; doctor
discovers 34 selftests.



### The doctrine learned the thing two field tickets turned on

`grep -ril 'forced.colors|high contrast' core/doctrine/` returned **nothing** across
all 31 competencies, while two tickets on the field repo hinged on it. Chrome paints
no `box-shadow` under `forced-colors: active`, so a `ring`-only focus indicator
changes **zero pixels** in the mode whose users need it most and passes every
default-mode check on the way. `qa-accessibility-verification` and
`dev-frontend-craft` each gained one Decide row and one Rule; the measured detail —
compiled-CSS lines, the `outline-none` vs `outline-hidden` difference, the
measurement recipe, and what emulation cannot prove — is in
`competencies/qa/reference/forced-colors.md`. Both files were already at the 1,100-word
ceiling, so the additions were **paid for** by moving each file's `Rationalizations`
table into its `reference/` file. No rule was dropped.

### Three competencies no lane could reach

`/ba` and `/pm` contained the word "competency" **zero times**. Three competencies
declared `applies: always` — load on every session of that lane — and were written,
gated, indexed and deployed without one line ever reaching the lane that needed them.
Both lanes now load at their declared step, and `competency_check` validates the
**chain**: a lane whose workflow never mentions competencies is an error, and a
`loads:` value naming no step in that lane's workflow is an error.

### Gates that existed only in prose

- `evd_check` was named twelve times in `/qa`, including "must be green before V5",
  and **no gate ran it**. A verification pack shipped a report claiming ten test cases
  with zero case folders while the gate stayed green. `--sweep` now checks every pack
  carrying a REPORT, reading the expected count from each report's own `TC_<n>`
  citations so a report cannot out-claim its folder.
- `evd_ui_check` was named five times in `/dev` and ran nowhere. Same treatment.
- `gate e2e` died one step before the e2e it exists to reach, because the
  `integration` step ran a script that most repos do not have and carried no guard.
- `schedule_check` had nowhere honest to live, which produced a new step kind:
  **`advisory: true`**. The step runs and prints, and its failure is named on the
  closing banner instead of stopping the gate — for checks whose failure is a fact
  about the *project* ("the plan is stale", "a decision is overdue") rather than a
  defect in the change. Blocking a commit on those teaches people to bypass the gate.

### The graph and the ledger can reference the decision queue

A ticket blocked by a **decision** rather than by a ticket, and a ticket closed
**won't-fix** by an owner rather than by a verdict, both had to be written in prose,
which is invisible to a gate. `blocked-by:` now resolves against `decisions.md` (an
unanswered question prints `⏸` and exits 0 — a state, not a fault), and a terminal
ticket with no REPORT passes if it declares `closed-by:` against a `✅ DECIDED` row.
A ledger row citing a decision the queue does not hold is red.

### `owned` — a fork stops being a chore

A deliberately forked framework file got a `.new` parked on it on **every** update,
forever; worse, the parked file is where upstream improvements land, so a fork
silently stopped receiving them. `.vteam/manifest.json` now takes `owned: [paths]`:
a declared path is never clobbered and never parked, and update reports that upstream
moved.

### Routing, measured — and the measurement corrected four times

`route_check.py` (new) answers "which competencies does this ticket load, why, and
what does that cost". It found the real context cost is not the `always` set that
0.18.0's progressive-disclosure work attacked (measured: **−0.2%**) but the **routed**
set: the field repo's worst DEV ticket opens **fifteen** competency files. The
`type:` token was added so a Bug ticket routes on its own `type:` field rather than on
the word "bug" appearing in prose.

**The instrument was wrong three times before it was right**, and the arc is in the
evidence rather than tidied away: it first ignored two of six token kinds
(undercount), then matched `path:` against prose instead of CODE-SCOPE (overcount),
then matched `term:` as a *prefix* so `lock` hit "lockfile" (overcount again). Same
nine tickets, final reading: **94 files**. The conclusion never moved; the size of the
problem did.

### Two review rounds, and what they caught

Four reviewer agents across the two repos returned 30 findings. The ones worth naming
because they were defects *introduced* by this work, not found in old code: a fix that
made every text input flash a 2px box for 145ms on focus (caught by sampling at 40ms,
which the author's own scripts could not do because they wait 450ms for "settle"); a
sweep that enforced the literal status `done` while the config declared three; a
substring test where `UNDECIDED` read as `DECIDED`; a won't-fix closure that any
mention of "Q2" satisfied; and an `advisory` step that silently upgraded the
"ZERO verification" banner. All fixed, each with a selftest case that reds on the
exact bug.

### Honest limits

Forced-colors evidence is Chromium's emulation, not Windows High Contrast. A
same-pixel focused-vs-unfocused ratio is the shape of **SC 2.4.13 (AAA)**, not
SC 1.4.11 (AA) — a mislabel that reached a design document before a reviewer caught
it. And a gate can check that an evidence pack is complete and self-consistent; it
cannot check that the pack's claims are true. That is what the challenger step is for,
and it earned its cost twice in this release.

## 0.18.0 — 2026-09-10

Twelve new competencies — seven for DEV, two for QA, two for BA, one for PM — taking
the doctrine from 19 to 31, and giving the BA and PM lanes their first craft files.
From a field study of `nilbuild/developer-roadmap`: curriculum topics read in the
authors' own order across roadmaps covering frontend, mobile, QA and backend, with the
hard facts verified against primary sources rather than the roadmap's own summaries.

- **`dev-frontend-craft`** (T2, routed on `label:ui`/`path:app/`/`term:component`): the
  browser as a document platform used as an app platform — component states before
  code, server/client boundary, cascade layers over specificity, virtualization,
  minor-unit money. Specificity and cascade rules from MDN; WCAG thresholds verified
  verbatim against the `w3c/wcag` source; the JS semantics claims verified by execution.
- **`dev-mobile-craft`** (T2, routed on `label:mobile`/`term:lifecycle`): the OS owns
  your process. Rotation and OS-kill are **two** events, not one — `onDestroy` runs on
  the first and not the second, and a ViewModel survives the first but not the second.
  Secure stores, three permission branches, remote kill switch before the feature.
  Lifecycle order verified against developer.android.com, ARC against docs.swift.org.
- **`dev-content-pipelines`** (T3, routed on `label:content`/`term:corpus`): repositories
  whose asset is data. Count the corpus before reading the code, replay the round trip
  over the whole corpus, and make the detection predicate and the extraction expression
  the same expression. Derived from fourteen measured defects in the studied repo.
- **`qa-accessibility-verification`** (V2, routed on `label:ui`/`term:dialog`): the
  checks no role curriculum assigns. The `android` roadmap has **zero** accessibility
  topic nodes; `react` and `vue` have no accessibility chapter while `angular` does.
  Keyboard pass first, real screen reader, max font — and cite the criterion at the
  right level: 2.5.8 is **24×24 CSS px at AA**, satisfiable by spacing; 44×44 is 2.5.5
  at AAA.
- **`qa-combinatorial-design`** (V2, routed on `label:matrix`/`term:combination`): the
  case count, defended. Pairwise by default, 4-way to 6-way as the ceiling, both quoted
  verbatim from NIST; decision tables; tier choice from Fowler's push-down laws;
  measure your own flake rate. The widely-repeated "93% of NASA failures were 2-way"
  and "pairwise finds ~80%" figures were checked in NIST primary sources and **could
  not be confirmed**, so nothing in the file rests on them.


### Backend — four gaps that were measurable, not assumed

Before these files, a grep across all 24 competencies returned **zero** hits for
`isolation level`, `deadlock`, `race condition`, `n+1`, `tracing`, `metric`,
`background job`, `cron`, `rate limit` and `circuit breaker`. `dev-data-modeling`
owned the schema and `dev-error-handling` owned the single failure, so what was
missing was everything about **runtime behaviour under concurrency and load**.

- **`dev-concurrency-and-transactions`** (T3, routed on `label:payment`/`term:transaction`):
  name the isolation level or inherit its anomalies. PostgreSQL defaults to **Read
  Committed**, which permits nonrepeatable reads, phantom reads, serialization
  anomalies and lost updates in complex operations; its Repeatable Read is *stronger*
  than the SQL standard and leaves only serialization anomalies, at the price of
  `could not serialize access` errors the application **must** retry. Uniqueness is a
  constraint, never a check-then-insert. Isolation table and error semantics verified
  verbatim against the PostgreSQL documentation.
- **`dev-async-work`** (T3, routed on `label:queue`/`term:webhook`): at-least-once is
  the default, so an idempotency key backed by a unique constraint is not optional.
  Send ids, not state. Bounded retries with backoff **and jitter**, a dead-letter queue
  somebody alerts on, a timeout on every outbound call, circuit breaker plus throttle,
  and scheduled jobs that survive being run twice during a rolling deploy.
- **`dev-query-performance`** (T2, routed on `label:slow`/`term:pagination`): count the
  queries before timing them, because the usual cause is N+1 rather than a slow query.
  Read the plan before touching the schema; keyset pagination for anything deep; decide
  cache invalidation in the same change as the cache, and put the tenant in the key.
- **`dev-observability`** (T3, routed on `label:incident`/`term:tracing`): metrics
  answer "how much", traces answer "where", logs answer "what happened in this one
  case", and none substitutes for another. Correlation id across the queue boundary,
  low-cardinality labels, alerts on symptoms with a duration and a first action.

### What the gates prove, and what they do not

`competency_check` proves all **28** files carry the five required frontmatter fields,
the six required sections, routing tokens the lane can match, and a body inside the
1,100-word budget — it caught a description of mine that narrated a procedure and a
word count over budget, and both were fixed. Every one of the nine is **conditionally
routed**, so the `always` context budget is unchanged: DEV stays at 3,897 words and QA
at 6,367. What the gate does not prove is that any of them changes an output; the
before/after evaluation design ships with the study and the behavioural run has not
been done.

### BA and PM — the lanes that had no craft files at all

The step vocabulary lives in the **workflows**, not the role docs: `/ba` runs B0–B5 and
`/pm` runs P0–P4, so `loads` has an honest value for both. Both lanes already own the
*procedure* — `/ba` requires Given/When/Then and "INVEST or split", `/pm` defines
mechanically when an item is UNBLOCKED — and neither says how a senior actually does it.

- **`ba-acceptance-criteria`** (B2): one behaviour per criterion, declarative rather
  than imperative, a concrete typed value in every criterion, an observable outcome, a
  refusal for every rule, a number and a measurement point for every non-functional
  criterion, a cited source instead of an invented rule. Complements
  `qa-requirement-smells`, which **detects** an untestable criterion — this one writes
  a testable one. Measured gap: `given/when/then`, `user story`, `traceab`,
  `non-functional` and `out of scope` were in **zero** competencies.
- **`ba-story-slicing`** (B2): cut vertically, never into "backend story" and "frontend
  story". The test for a valid slice is the sentence "after this ships, a user can …";
  split by workflow step, by rule, by data shape or by role; narrow the **input**, not
  the layers; a spike is time-boxed and answers a question.
- **`pm-prioritisation`** (P1): finishing beats starting. Sweep the nearly-done before
  choosing anything new, order strictly with no ties, rank by cost of delay per unit of
  effort, cap work in flight below the number of people, never start a fifth thing to
  compensate for a blocker, escalate on elapsed time with a stated consequence, and
  report "nothing unblocked" as a real result.

**These three cost context, unlike the other nine.** All twelve pass the gate, but the
nine DEV/QA files are conditionally routed and added **zero** to the `always` budget,
while these three are `always` — deliberately, because writing criteria, slicing and
picking work are the acts those lanes exist to perform, and routing them conditionally
would mean sometimes omitting the craft for the lane's whole job. The cost is real and
new: BA goes from 0 to **2,155 words** (≈2,909 tokens) and PM from 0 to **1,076 words**
(≈1,452 tokens) on every session of those lanes.

### Progressive disclosure — the context the lane spends on the rulebook

The framework already had the mechanism (`competencies/qa/reference/`, loaded on
demand) and the new files were not using it. `Rationalizations`, `Red flags` and
`Example` are the three sections `competency_check` does **not** require, which is
what makes them movable: they are now in `competencies/<role>/reference/<name>.md`,
one reference file per competency so loading one does not pull the others, each with
a pointer from the competency's `Sources`. **2,459 words (~3,300 tokens)** left the
default load path across the 16 `always` files.

One `always` declaration also contradicted its own description and was fixed:
`qa-user-mindset` says "Use when designing or running **any UI verification**" — a
condition, not "always" — so it is now routed on `label:ui`/`path:components/`/
`term:form` and friends. On a UI ticket it loads exactly as before; on a backend
verification it does not load at all.

Measured effect on the `/qa` floor — lane file + role doc + INDEX + `always`
competencies + the skill catalogue, accumulated by the end of a task:

| | tokens |
|---|---|
| before | 21,169 |
| after moving the three sections | 19,873 (−1,296) |
| after routing `qa-user-mindset` | **18,869** (−2,300 total, **−10.9%**) |

Honest limits: the second saving applies only to **non-UI** verifications, and −11% is
not a fix. The two heaviest items are untouched — the lane file itself
(`qa/SKILL.md`, 6,844 tokens, 34% of the floor) and the 40-skill catalogue (3,498
tokens, loaded in every session regardless of lane, of which this release added
~1,050). Two other `always` competencies were examined and deliberately left alone:
`qa-heuristics` triggers on "the spec is silent", which is discovered mid-work and
cannot be matched from a ticket, and `qa-hostile-inputs` applies to every
verification that has an input.

### Roles still without competencies

Four of eight remain empty: `design`, `devops`, `sa`, `specialists`. Each is blocked on
the same thing — **no lane-step vocabulary**. `devops.md`, `design.md` and
`specialists.md` have no numbered steps and no workflow; `sa.md`'s only capital-letter
token is `C4`, the diagram model, not a step. `competency_check` does **not** validate
the value of `loads`, so a made-up step would pass the gate while guaranteeing the file
is never loaded — a green that lies. Naming those steps is a decision for the owner,
not something to invent.

---

### Written back from the field trial — VT-15, VT-16, VT-17

Three tickets that exist only because the lanes were run for real on a second repo,
and each records what the run measured rather than what seemed likely.

**The second rendering mode was missing from the whole doctrine.**
`grep -ril 'forced.colors|high contrast' core/doctrine/` returned nothing across all
31 competencies, while two field tickets turned on it and a third instance is still
live there. Chrome paints no `box-shadow` under `forced-colors: active`, so a
`ring`-only focus indicator changes **zero pixels** in the mode whose users need it
most — and passes every default-mode check on the way. `qa-accessibility-verification`
(verify) and `dev-frontend-craft` (build) each gained one Decide row and one Rule; the
measured detail lives in `competencies/qa/reference/forced-colors.md`. Both files sat
at 1,091 and 1,086 words against `competency_check`'s 1,100 ceiling, so the additions
were **paid for** by moving each file's `Rationalizations` table into its 1:1
`reference/` file — arguments you meet after a finding is filed, wanted at rebuttal
time rather than design time. No rule was dropped; the files end at 1,100 and 1,089.

**A criterion can be concrete, bounded, machine-checkable and still vacuous.** A field
ticket asked for a source-code search to come back empty; a build satisfying exactly
that criterion rendered identically to the broken one. `ba-acceptance-criteria` and
`qa-requirement-smells` now both carry the falsification question — *if this check
passed and the behaviour were still broken, what would that look like?* An answerable
question means the criterion measures a proxy. Writing the next ticket with it changed
two of seven criteria, and then caught a third on the second pass.

**Where the context cost actually is.** The progressive-disclosure work above moved
2,459 words off the `always` path and measured **−0.2%** on the DEV floor, because the
catalogue grew by as much as the `always` set shrank. `route_check.py` (new) explains
that: the cost is in a ticket's **routed** set. The field trial's worst DEV ticket opens
**15 competency files ≈ 17,459 tokens** (first published as 17,270 — the tool was
undercounting, see the correction note below), and 5 of 9 dev ticket/lane pairs load at least
one competency pulled in by a word appearing only in the ticket's prose — a CSS
focus-ring ticket loads `dev-mobile-craft` on the word "permission". The obvious fix was
run and **rejected on its own numbers**: matching `term:` only against title + labels +
summary cuts 17% overall and 38–42% on the worst tickets, and drops 3 false matches
together with **12 true ones**. So no `applies:` line was changed; the report exits 0 by
design and the four candidate fixes are D13, for the owner.

**The QA lane's own evidence gate now runs in the gate.** `workflows/qa.md` names
`evd_check.py` twelve times, including "must be green before V5", and `gate.sh` never
ran it — so a verification pack shipped a report claiming **ten test cases with zero
case folders** while the gate stayed green, and a challenger agent had to find it.
`evd_check.py --sweep` checks every pack that carries a `REPORT.md`, reads the expected
case count from each report's own `TC_<n>` citations so a report cannot out-claim its
folder, fails only on **closed** tickets, and reports rather than fails packs older than
the `KIND` standard — vteam's own VT-1 is Done with no `verifysheet.md` and had never
been noticed. An `evd` step was added to all six profiles. Proved by deleting a real
case folder and watching the gate go red, not by reading YAML.

Also fixed: the `integration` gate step ran a script with no guard, so `gate e2e` died
one step before the e2e it exists to reach and the end-to-end layer had never run on the
field repo. The driver already had `requires_cmd` + `skip_reason`; the manifest did not
use it. `gate e2e` there goes RED-at-integration (14 steps) → GREEN (15 steps).

**Correction (2026-09-11).** `route_check` shipped with two of the six `applies:` token
kinds — `profile:` and `path:` — unimplemented, and read the stack profile from the wrong
repo, so the figures above were a floor. Corrected twice: the first fix matched `path:` against prose
rather than the ticket's CODE-SCOPE and over-counted in turn. Best available reading
is **96 files / 105,403 tokens** for the nine field tickets — five measured against a
real CODE-SCOPE, four labelled estimates — against **84** first published. The saving
across the `type:` change is **−4.2%**, not −3.8%.
The conclusions hold; the problem is 21% larger than first published. Found by reviewing
the flow end to end, not by a gate — nothing checks that a measurement tool implements the
grammar it measures.

What none of this fixes, stated because the tempting summary is shorter than the truth:
a sweep can tell whether a pack is complete and self-consistent, never whether its
claims are **true**. The same pack the new gate would have caught also asserted that
four controls "show nothing at all" when they change 184–484 pixels. That took a
challenger who re-measured. Structure is gateable; honesty is not.

## 0.17.1 — 2026-09-10

The README describes what 0.17.0 ships — with pictures — and says out loud what the gates
cannot prove.

- **Parallel DEV has a section and a diagram** (`docs/assets/parallel.svg`): the PM, the
  Orca Run mailbox, two workers in their own worktrees, the serial three-command merge, and
  the four gates that refuse the shortcut. The `/team` paragraph no longer says "one coding
  item at a time, by design" — that is the default, not the ceiling — and `team.svg` says so
  too. `team.parallel` / `team.coord_budget` appear in the sample config and the knob list;
  Orca is listed as an optional requirement with its text-relay fallback.
- **The evidence pack has a section and a diagram** (`docs/assets/evidence-pack.svg`): the
  folder a stranger opens — case folders named for what they prove, `TITLE`/`KIND`,
  `COVERAGE`, the generated index, the exact-fit box with its caption below, the six-sheet
  workbook, the Given/When/Then report, the debate file — and the four scripts that hold
  it. One paragraph states what shape gates can and cannot prove, and names the three
  things truth actually rests on (the commit pin, the re-runnable measurement, the
  challenger) with what the challengers caught on the field run.
- **Known limits gained two honest rows:** parallel DEV is young (one live run; worker
  tokens measured by hand; a login expiry idles every agent silently — `VT-12`), and the
  `nextjs-prisma` profile assumes the app at the repo root (`VT-11`).
- **Status** records the field trial behind 0.17.0; **Security** no longer implies every
  version carries provenance — it tells you how to check (`dist.attestations`) and that a
  hand-published version has none. 0.17.0 itself was published by hand.
- No code change. Suite 164 → 164; the README's three guarded numbers are unchanged.

## 0.17.0 — 2026-09-09

Parallel DEV with real coordination, and a QA output layer a person can read. Field-tested
end to end on a pnpm/Turborepo Next 15 + Prisma monorepo before shipping (four tickets,
four QA runs, two Orca workers); the gaps that trial found are filed, not hidden (VT-11,
VT-12 in `docs/backlog/`).

- **`/team` parallel mode (VT-5).** `team.parallel: N` (default 1) lets the PM run up to N
  DEV agents at once, each in its own git worktree on a **disjoint `CODE-SCOPE`**, and merge
  their branches serially, re-gating between. New gate **`parallel_check.py`** reds two
  in-flight branches that share a file and any count past the cap; inert-green when
  parallel mode is off.
- **Peer coordination that leaves artifacts (VT-6).** Parallel DEV agents may split scope
  or hand off a shared contract, but every handoff is appended to
  `docs/pm/coordination.md` and both `CODE-SCOPE`s are updated. New gate
  **`coord_check.py`** reds a handoff not reflected in scope, an over-budget round
  (`team.parallel.coord_budget`, default 3) or a malformed row. Reviewers stay isolated;
  ledger and merges stay the PM's single hand.
- **A real transport for that coordination (VT-7).** `orca_team.sh` (`status` /
  `open-run` / `wait` / `trust`) drives the Orca orchestration Run mailbox — dispatch,
  heartbeats with a phase, blocking ask/reply, `worker_done` — and degrades to a text-relay
  fallback when no bus exists. Doctrine `parallel-transport.md` documents the tested flow.
- **BDD human report (VT-8).** Opt-in `*.bdd.md` reports in Given/When/Then. New gate
  **`bdd_report_check.py`** reds a scenario missing a step, a Then that says nothing
  observable, code-speak in the human body, or a step over the length cap. Doctrine
  `bdd-report.md` + template.
- **The /qa evidence layer, ported from [ai-qa](https://github.com/connorpham/ai-qa) (VT-9).**
  One vocabulary for the gate and the workbook (`lib/evdpack.py`); `xlsx_export.py` writes
  `<TICKET>_testcases.xlsx` — Summary / Test Cases / Defects / Traceability / Evidence /
  Images to ISO/IEC/IEEE 29119-3, never invents a value, `--strict` names what is undeclared;
  `evd_index.py` regenerates the folder's own index block and `--check` reds a stale one;
  `annotate.py` draws an exact-fit box with the caption **below** the image, coordinates
  intact; `evd_check` gains the v2 rules (a case names its `KIND`, its `COVERAGE`, what it
  proves — in words a reader can check). Doctrine `evidence.md`.
- **Gates that survive a split worktree (VT-10).** The first live parallel run broke five
  gate assumptions in minutes, all one family: a single working tree. Now `parallel_check`
  and `coord_check` read a sibling's tasksheet from git (`git show <branch>:<path>`), name
  an uncommitted one instead of reading it as empty, ignore the shared bookkeeping homes
  (`docs/pm`, `evd/`, `docs/qa`) as edit territory, and tell a **landed** branch from an
  in-flight one topologically (squash-merge aware). `graph_check` attributes a commit to a
  ticket only by a **leading** key (`VT-10 …`, `feat(VT-10):`, `[VT-10]`), never a prose
  mention. `orca_team.sh trust <path>` pre-accepts the agent's trust dialog for a new
  worktree, which used to eat the injected prompt.
- **Counts.** 15 → **18 gates**, 26 → **32 selftests**, suite 158 → **164 checks**; the
  README's three numbers are each guarded by the suite.
- **Known gaps, filed from the trial:** the `nextjs-prisma` profile assumes the app at the
  repo root (VT-11); Orca workers report no token usage, `usage --sync` is path-bound, a
  login expiry idles every agent silently, `graph_check`'s file listing can see a commit as
  parentless on CI, `schedule_check` reads the first date in a decision row (VT-12).

## 0.16.0

The competency layer — the framework had supervisors and an iron rulebook but no
craftspeople. Roles knew *when* things happen and nothing about *how* a senior does them.

- **DEV ships with ten competencies** (`competencies/dev/`): identity, domain-modeling,
  codebase-design, data-modeling, api-design, error-handling, debugging, testing-craft,
  security-basics, and a stack file per profile (`nextjs-prisma` first). Each is a short
  Decide/Rules/**Reviewer lens** file; `/dev` loads them from an `INDEX.md` by ticket
  label, path, profile or term, and pastes each loaded Reviewer lens into the R1/R2 briefs
  so the craft is checked by review.
- **QA ships with nine** (`competencies/qa/`), distilled from the standalone
  [ai-qa](https://github.com/connorpham/ai-qa) framework: identity, requirement-smells,
  test-design, user-mindset, case-writing, hostile-inputs, heuristics, report-writing and
  security-probes. Full hostile-input / heuristic / security / checklist tables live under
  `competencies/qa/reference/`, which the word-budget gate ignores. `/qa` loads them at
  V1/V2 and pastes their Reviewer lens into the V6 challenger brief.
- **A 15th gate: `competency_check.py`** — a craft file with no Reviewer lens, a
  description that narrates a procedure instead of naming the problem, a routing token with
  a typo, a body past the word budget, or a stale `INDEX.md` goes red. Ships its
  `--selftest`, bringing the discovered battery to 26.

---

## 0.15.4 — unreleased

The README finally describes what the last three releases actually shipped.

- **The specialists have a section.** The seven deep-skill subagents from 0.14.0 were
  installed by `init` and mentioned nowhere in the README — zero occurrences of the word
  "specialist". They now have their own section with a diagram
  (`docs/assets/specialists.svg`), a dispatch table, and the rule that matters: they work
  inside the same `/dev` pipeline, the same evidence rules, the same gates. Specialists
  advise; the lane decides.
- **Watchable dev and QA sessions have a section.** The `app:` capabilities from 0.15.0
  and 0.15.2 — `APP: UP` bring-up proof, a real headed Chrome window per QA journey,
  `/dev` opening the files it edits — were one dense line inside a config table. They are
  now described where someone deciding whether to adopt vteam will actually read them.
- **This changelog exists.** 22 versions shipped before it did.
- Two more guards: the README's selftest count must equal what `doctor` discovers (it
  said 25 in two places and 22 in four *at the same time*), and the newest entry here must
  be the shipping version. Suite total 156 → 157.

## 0.15.3 — 2026-09-03

The README npm actually serves, and a guard on the count that drifted.

- Nine relative links (`LICENSE`, `docs/TUTORIAL.md`, `docs/DESIGN.md`, `SECURITY.md`, …)
  only resolved on GitHub. On npmjs.com and in any `node_modules` copy they pointed
  nowhere. All are absolute now — the README is one file serving two surfaces.
- The selftest count said **22** in four places; `doctor` discovers and runs **25**. Fixed
  in the prose, the pasted `doctor` transcript and both text layers of `commands.svg`.
- The transcript is a real captured run again, which also corrected `55`→`59`
  framework-owned files, `1`→`2` tickets, and removed a duplicated line left by an old
  elision.
- New machine check: the README's selftest count must equal what discovery finds. The
  suite already guarded its own `N checks` claim for the same reason; this number had no
  guard and drifted the same way. Suite total 155 → 156.

## 0.15.2 — 2026-09-02

Watchable dev & QA sessions (VT-2).

- App environment config, headed Chrome by default, and editor opening — so a `/dev` or
  `/qa` session is something a human can sit and watch rather than infer from logs.

## 0.15.1 — 2026-09-02

Maintenance release.

## 0.15.0 — 2026-08-30

Ship the headed-by-default UI evidence to npm installs.

## 0.14.0 — 2026-08-30

Ship the specialist subagents to npm installs.

- The backend, frontend/mobile, DevOps, data, AI/data, QA-automation and security
  specialist agents now land in a fresh install instead of living only in this repo.

## 0.13.1 — 2026-08-24

Ship the command-reference README to npm.

## 0.13.0 — 2026-08-24

Close the 2026-08-24 review holes.

- A TTL knob for verdict expiry, a ledger fence, and the first README truth guard — the
  suite began machine-checking a number the README states about itself.

## 0.12.0 — 2026-08-24

`resume` is a READER, not a store.

- Checkpoint-resume reworked per ops doctrine: it derives the furthest proven stage from
  claim, branch, tasksheet, review dossier, QA verdict and ledger. It stores nothing, so
  nothing can go stale or lie.

## 0.11.0 — never published

`vteam usage` — measured AI-usage history per person, model and day. The version was
bumped in git (`e5066e86`) but no tarball was published under it.

## 0.10.1 — 2026-08-21

Ship the explanatory README and its three diagrams to npm.

## 0.10.0 — 2026-08-21

Evidence a stranger can read, and a tester who behaves like a person.

- QA evidence gained the journey fields (`AS:`, `PRECONDITION:`, `ENTRY:`, `AFTER:`,
  `BACK:`), named screenshots and the boxed verdict shot. An `ENTRY:` that is only a URL
  is refused: typing an address proves the address, not the product.

## 0.9.2 — 2026-08-21

Ship the visuals to npm, and stop the stale-README trap.

## 0.9.1 — 2026-08-21

Ship the reshaped README to npm.

## 0.9.0 — 2026-08-21

The graph round — the work graph made visible, and the four MAST holes closed.

- `vteam graph` renders READY/BLOCKED work and findings; `graph_check` is its gate twin,
  catching dangling edges, dependency cycles, Done tickets without a PASS verdict,
  repeated dispatches and commits straying outside a ticket's declared scope. Each check
  names the MAST failure mode it closes (arXiv 2503.13657).

## 0.8.0 — never published

The scale round — 8h workdays, 24/7 shifts, cross-model review, code map, conflict-free
knowledge files. Bumped in git (`1f687fde`) but no tarball was published under it.

## 0.7.0 — 2026-08-19

Team accountability — the Actor column makes `team.size` real.

- Every ledger row names the human whose session dispatched it. With `team.size > 1` the
  column is machine-mandatory: `log_check` reds a legacy header and any empty Actor cell.

## 0.6.1 — 2026-08-19

One rule, one home — the consistency round.

## 0.6.0 — 2026-08-18

Field-trial findings #17–#20, plus the 15-minute tour.

- Finding #17 is why `code_paths` is derived from the repo's real layout at init: a
  hardcoded `[src/, prisma/]` default silently lost the review fence on repos whose code
  lives elsewhere.

## 0.5.0 — 2026-08-18

The greenfield intake release — `/plan`.

- Interviews the owner section by section, writes a BRIEF then a PRD whose requirement
  rows carry gate-compatible codes, and registers the PRD as a source document so the
  verbatim gate guards everything sharded from it.

## 0.4.1 — 2026-08-18

Ship the rewritten README to npm.

## 0.4.0 — 2026-08-18

Per-project customization; record the compatibility debt.

## 0.3.0 — 2026-08-18

The proof-of-done release.

## 0.2.0 — 2026-08-18

The audit-hardening release.

## 0.1.0 — 2026-08-17

First published version — LICENSE, repository metadata, packaging manifest.

---

## A note on provenance

`release.yml` publishes with npm provenance (Sigstore) when a GitHub release is drafted on
the version tag. Versions from 0.13.0 onward were published from a workstation instead, so
they carry npm's registry signature but **no provenance attestation**. Publishing through
the release workflow is what makes the README's provenance claim true.
