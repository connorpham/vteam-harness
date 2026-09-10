# Changelog

What changed in each released version, newest first. Dates are the npm publish date.

Every entry is derived from the commit that bumped `package.json` — not written from
memory. Two versions below were bumped in git but **never reached npm**; they are kept
here because the version numbers are spent and skipping them silently would be a lie.

The current version always has an entry: `tests/e2e.mjs` fails if the newest heading here
does not match `package.json`.

---

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
**15 competency files ≈ 17,270 tokens**, and 5 of 9 dev ticket/lane pairs load at least
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
