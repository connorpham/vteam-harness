---
name: docs
command: /docs
description: Documentation bootstrapper for mature-but-undocumented repos — the "read then ask" lane. Reads the codebase FIRST (structure, manifests, routes/entrypoints/models/migrations, existing README, git-log themes) and drafts a "what this system appears to do" map where every inference is marked ⚠ UNVERIFIED → interviews the owner in ONE batched question table (each question carries what the code suggests, what is ambiguous, and a proposed answer acceptable in one word) → writes the standard oracle the other lanes assume exists: specs INDEX + per-area shards (DRAFT-FROM-CODE vs OWNER-CONFIRMED), decisions.md seeds, knowledge-base.md seeds, known-issues.md → proposes a vteam.config.yaml patch (high_stakes_terms/paths, specs.sources, docs.task_context) for the owner to apply. Writes documentation only — never product code, never the config itself.
args: "[area]"
---

# /docs — create the documented truth the gates assume (docs lane, no code)

**Why this exists:** every other vteam lane reads an oracle. /ba shards a spec,
/dev cites `{paths.specs}/<feature>.md`, /qa derives expected values from it, and
the review gate escalates on `review.high_stakes_terms`. A mature repo that grew
without documentation has none of that — so the gates either idle or fire on
nothing. This workflow CREATES that oracle from the only two sources that
actually hold it: **the codebase** and **the owner's head**. It does not require
documentation to pre-exist; it manufactures it, then says out loud which parts
are still guesses.

**What this workflow is NOT:** it never writes or edits product code, never
touches `vteam.config.yaml` (it PROPOSES a patch, the owner applies it), never
files tickets, and never turns an inference into a fact by rewording it.

**Lane boundaries:** this lane needs CODE to read. A project with neither code
nor docs → `/plan` (the greenfield interview); a spec document already in hand
→ `/ba` shards it directly.

**Immutable principles:**
1. **Read before asking.** D0 runs to completion before the first question. A
   question the code already answers wastes the owner's only scarce resource, and
   an interview conducted blind produces documentation that describes an
   imaginary system.
2. **Inference is never presented as fact.** Every sentence derived from code
   carries `⚠ UNVERIFIED` (D0) or the `DRAFT-FROM-CODE` marker (D2); every
   sentence the owner confirmed carries `OWNER-CONFIRMED`. **Never mix inference
   and confirmed truth in one sentence without its marker** — a mixed sentence is
   a lie with a citation attached.
3. **ONE interview round.** All questions go to the owner in a single batched
   table (decision-queue discipline, `{paths.pm}/decisions.md`). Follow-ups born
   from the answers do NOT reopen the interview — they become rows in the
   decision queue with a proposal, and the docs ship marked DRAFT for those
   spots. Never invent an answer.
4. **Every question is answerable in one word.** Each row states what the code
   suggests, what is ambiguous, and a concrete PROPOSED ANSWER — the owner types
   "yes" / "no" / a correction. A bare question ("what is the domain model?")
   outsources the reading this lane was hired to do.
5. **The config is the owner's.** `high_stakes_terms`, `high_stakes_paths`,
   `specs.sources`, `docs.task_context` are DERIVED here and SHOWN as a patch.
   Auto-applying them would silently change which diffs get a third reviewer.
6. **Token discipline.** Cite paths and line ranges, never paste file contents
   into the transcript or into the docs. Read manifests and entrypoints in full;
   sample everything else.
7. **Visible, human-readable process.** One `▶ [D1/D3]` line per phase. The
   deliverable leads with plain language — the owner reads the map and the
   question table without opening a single source file.

Tempted to skip the read and just interview? That excuse is in `red-flags.md`,
next to the reason the resulting docs describe a system nobody shipped.

---

## D0 — READ THE REPO (before a single question)

Scope from the argument: `[area]` narrows to one subsystem; no argument = the
whole repo. Announce:

```
▶ DOCS: reading <repo|area> before asking anything
  manifests: <N> | entrypoints: <N> | existing docs: <N files> | commits scanned: <N>
```

**Build the code map first** — `python3 .vteam/scripts/code_map.py build` (needs
`git.code_paths`; on a repo where that is still empty, build it right after step 1
names where code lives): it is the cheap index for every read below —
`code_map.py query <term>` answers with paths + line ranges instead of a tree walk.

Read, in this order — each line is a source, not a suggestion:

1. **Structure** — the directory tree to a sensible depth, with the generated /
   vendored / build directories excluded. Note where product code actually lives
   (candidate for `git.code_paths`).
2. **Package manifests** — `package.json`, `pyproject.toml`, `go.mod`, `Gemfile`,
   `pom.xml`, `Cargo.toml`, whatever exists. Read these IN FULL: dependencies name
   the stack, the scripts section names the real build/test/lint commands (they
   feed the `/verify` gate later), and the dependency list is the fastest honest
   read of what the system integrates with.
3. **Entrypoints and routes** — `main`/`index`/`app` files, route files, HTTP
   handlers, CLI commands, scheduled jobs, queue consumers. Enumerate them; do
   not read them all.
4. **Data model** — schema files, ORM models, and **the migration directory in
   chronological order** — migrations are the repo's only honest changelog of
   what the domain used to be and what it became.
5. **Existing docs** — README, `docs/`, ADRs, wiki exports, comment blocks at the
   top of core modules, `CONTRIBUTING`. Whatever is already true here gets
   REUSED, not rewritten (and its path is a candidate for `specs.sources`).
6. **Git-log themes** — `git log --oneline` over a meaningful window plus the
   most-churned files. What the team has been changing for months IS the system's
   center of gravity, and the churn list is the best first draft of
   `high_stakes_paths`.
7. **Vocabulary harvest** — collect the domain nouns that recur in model names,
   table names, enum values, and route segments. This is the raw material for
   `high_stakes_terms`; at D0 it is only a word list, not a risk judgment.

**Deliverable — the appearance map** (`{paths.specs}/DRAFT-system-map.md`, and
summarized in the transcript, ≤1 page):

```markdown
# What this system appears to do — DRAFT FROM CODE, <date>
⚠ Every line below is an INFERENCE from reading code. Nothing here is confirmed.

## Purpose (⚠ UNVERIFIED)
<2–4 plain sentences: what the system seems to be for, who seems to use it>

## Areas (⚠ UNVERIFIED per row)
| Area | Evidence (paths) | What it appears to do | Confidence |
|---|---|---|---|

## Domain vocabulary observed
| Term | Where it appears | Guessed meaning (⚠ UNVERIFIED) |

## Flows that touch money / external systems / irreversible state (⚠ UNVERIFIED)
| Flow | Entrypoint path | Why it looks high-stakes |

## Stack facts (VERIFIED — read from manifests, not inferred)
<language/framework/db/test runner + the real script names>

## What I could NOT determine from code
<the list that becomes the D1 questions>
```

The "Stack facts" section is the only unmarked section in the file: a dependency
read out of a manifest is a fact. Everything else is marked.

## D1 — INTERVIEW THE OWNER (one batched table, one round)

The core of this lane: **read, then ask.** The code told us how the system is
built; only the owner knows what it is FOR, what is dangerous, and where the
bodies are buried.

Present ONE table. Every row is answerable with one word because the proposal is
already written:

```markdown
| # | Question | What the code suggests | What's ambiguous | PROPOSED ANSWER (say "ok" to accept) |
|---|---|---|---|---|
| Q1 | … | <path>: … | … | … |
```

Cover all six categories — a category with nothing to ask says
`Q(n): nothing to ask, the code was unambiguous here`:

| # | Category | What the answer is FOR | Feeds |
|---|---|---|---|
| 1 | **System purpose + users** — what it is for, who the real roles are, which are internal vs customer | The one paragraph every spec shard opens with | specs INDEX, shard headers |
| 2 | **Domain vocabulary** — for each harvested term: does it mean what it looks like, and does it mean *money or irreversibility* in this business? | Turning a word list into a risk list | `review.high_stakes_terms` |
| 3 | **Money / irreversible flows** — which flows move money, delete real data, notify customers, or hit a partner that cannot be un-called | Which diffs deserve a third reviewer | `review.high_stakes_paths` |
| 4 | **Source-of-truth documents elsewhere** — the spec in a drive folder, the Notion page, the contract PDF, the sheet the rules actually live in | Stopping this lane from re-deriving requirements the owner already wrote down | `specs.sources` |
| 5 | **What "done" means here** — what must be true before a change ships: tests? staging? a person clicking? a release window? | The DoD the /verify and /qa gates enforce | `/verify` profile, DoD sections |
| 6 | **Known debt + landmines** — "never touch X on a Friday", the module everyone fears, the flaky suite, the manual step nobody automated | Warning the /dev lane before it steps on it | `known-issues.md` |

Rules for this phase:
- **One round.** Ask everything at once. An answer that raises a new question →
  a row in `{paths.pm}/decisions.md` with a proposal and what it blocks, NOT a
  second interview.
- **Unanswered rows stay unanswered.** A question the owner skips leaves its
  documentation marked `DRAFT-FROM-CODE` + `⚠ OWNER QUESTION OPEN (Qn)`. Silence
  is never consent to the proposal here — that mechanism belongs to /pm's
  decision queue, and only for questions recorded there with a deadline.
- **Record the answers verbatim** into
  `{paths.specs}/DRAFT-system-map.md` under `## Owner answers <date>` before
  writing anything in D2 — the answers are the citation D2's OWNER-CONFIRMED
  markers point at.

## D2 — WRITE THE STANDARD DOCS (from D0 + D1, markers on every line)

Marker law, applied per sentence or per row — never per file:

| Marker | Means | Source |
|---|---|---|
| `OWNER-CONFIRMED` | The owner stated it in D1 | the answer log |
| `DRAFT-FROM-CODE` | Inferred from code, unconfirmed | cited path(s) |
| `⚠ OWNER QUESTION OPEN (Qn)` | Asked, not answered | the D1 table row |

Write:

1. **`{paths.specs}/INDEX.md`** — one row per area (area | file | scope | status
   `DRAFT-FROM-CODE`/`OWNER-CONFIRMED`/`MIXED`). This is the file /ba and /dev
   will look for; it exists after this phase or the lane failed.
2. **Per-area spec shards `{paths.specs}/<area>.md`** — for each area in the map:
   purpose (from Q1), the roles who use it, observed behavior as numbered
   `§x.y` sections so later lanes can cite them, the data it owns, and an
   explicit **`## NOT DOCUMENTED`** section listing what nobody could answer.
   Each `§` carries its marker and its evidence path. These shards are PROSE
   DESCRIPTION of observed behavior — they are **not** verbatim requirement rows
   copied from an upstream document, so they carry no coded requirement ids (see
   D3 on the verbatim gate).
3. **`{paths.pm}/decisions.md` seeds** — the architectural choices the code
   already made, recorded as decisions that were taken implicitly: the framework,
   the auth mechanism, the data store, the deploy target, the multi-tenancy
   model, whatever else the code committed to. One row each:
   `implicit decision · evidence path · when (first commit/migration) ·
   status: 🟢 IN FORCE (undocumented until now)`. Where a real trade-off is
   visible and load-bearing, note it as an **ADR candidate** for the SA lane —
   this lane does not write ADRs.
4. **`{paths.qa}/knowledge-base.md` seeds** — §0 + INDEX per the standard shape,
   seeded with the operational lessons the repo itself reveals: the real
   dev-server bring-up sequence, the env vars without which nothing runs, the
   seed/fixture path, the test command that actually passes. Tag each lesson so
   the /dev and /qa index-only preflights can match it.
5. **`{paths.qa}/known-issues.md`** — one heading per landmine from Q6, each with:
   what breaks, how to recognize it, the workaround, and whether it is a bug
   nobody filed (→ candidate for /ba) or accepted behavior.
6. **The proposed config patch — SHOWN, NEVER APPLIED.** Print it as a diff-ready
   block with a one-line justification per key, then state in plain language what
   each key will start doing once applied:

   ```yaml
   # PROPOSED — review, then paste into vteam.config.yaml yourself.
   # /docs does not write this file.
   specs:
     sources: [<the real source docs from Q4>]
   review:
     high_stakes_paths: [<paths from Q3 + the churn list>]
     high_stakes_terms: [<terms the owner confirmed mean money/irreversibility in Q2>]
   docs:
     task_context:
       always: [<what every ticket must read>]
       by_label:
         <label>: [<extra reading for that label/type>]
   ```

   `docs.task_context` is the payoff of this whole lane: it is how the /dev lane
   learns to read the right background for the right ticket without the owner
   repeating themselves (dev.md T1, "Task context"). A label with nothing worth
   reading is omitted, not filled with the README.

## D3 — VERIFY THE DOCS, READ BACK, HAND OVER

1. **Gate the generated docs against the gates that will now judge them:**
   - `python3 .vteam/scripts/verbatim_gate.py` — **must stay GREEN, and if
     `specs.sources` is still empty it has nothing to compare and says so.** State
     this explicitly to the owner: **the shards this lane writes are PROSE
     DESCRIPTIONS of observed behavior, not verbatim requirement rows, so they
     carry no coded ids for the gate to byte-compare.** The verbatim gate starts
     guarding real requirement text only when /ba later shards an actual source
     document listed in `specs.sources`. A shard from this lane that DID paste
     coded rows out of a source document is a /docs bug — move those rows to /ba.
   - `bash .vteam/scripts/preflight.sh` — confirms the paths this lane just
     created are where the config says they are.
   - Marker audit: every `§` in every shard carries exactly one marker; grep for
     unmarked sections and fix them. An unmarked sentence is the one failure mode
     this whole workflow exists to prevent.
2. **Read-back list — every file written, one line each** (path → what it
   contains → marker mix), plus the files deliberately NOT written and why:
   ```
   WROTE  docs/specs/INDEX.md            — 6 areas (2 OWNER-CONFIRMED, 4 DRAFT)
   WROTE  docs/specs/billing.md          — §1–§7, DRAFT-FROM-CODE, 2 open questions
   …
   NOT WRITTEN  docs/adr/               — ADR candidates listed, SA lane's call
   NOT WRITTEN  vteam.config.yaml       — patch proposed above, yours to apply
   ```
3. **Closing line — which gates now guard what.** Plain language, one line per
   gate, naming what became enforceable that was not enforceable an hour ago:
   ```
   ▶ DOCS done. From now on:
     · /dev cites docs/specs/<area>.md instead of guessing — dor_check will demand it
     · <N> tickets' worth of background is auto-read via docs.task_context (once you apply the patch)
     · reviews escalate to a 3rd reviewer on <terms> and <paths> (once applied)
     · /qa derives expected values from the shards; the NOT DOCUMENTED sections
       are where it will still say BLOCKED and send the question to /ba
     · verbatim_gate guards nothing yet — it starts the day /ba shards <source doc>
   ```
4. **State the debt honestly.** Count and name what is still `DRAFT-FROM-CODE`
   and every `⚠ OWNER QUESTION OPEN` — the docs are a starting oracle, not a
   finished one, and the next lane must know which sentences it may not lean on.
5. **Close the learning loop** — append a lesson (+1 INDEX line) to
   `{paths.qa}/knowledge-base.md` or state "no new lesson".

## Definition of Done
- [ ] D0 ran to completion BEFORE the first question; the appearance map exists
      with `⚠ UNVERIFIED` on every inferred line
- [ ] Stack facts read from real manifests (not inferred), including the real
      build/test/lint script names
- [ ] D1 was ONE batched table covering all six categories; every row carried
      what-the-code-suggests + what's-ambiguous + a one-word-acceptable proposal
- [ ] Owner answers recorded verbatim before any doc was written; follow-ups went
      to `{paths.pm}/decisions.md`, not to a second interview round
- [ ] `{paths.specs}/INDEX.md` + one shard per area exist; every `§` carries
      exactly one marker; no sentence mixes inference with confirmed truth
- [ ] `decisions.md` seeds recorded for the choices already made in code; ADR
      candidates listed, not written
- [ ] `knowledge-base.md` seeded (§0 + INDEX + tagged lessons);
      `known-issues.md` written from the landmines question (or "none reported")
- [ ] Config patch SHOWN with per-key justification; `vteam.config.yaml`
      UNTOUCHED by this lane
- [ ] `verbatim_gate.py` GREEN, and the prose-not-verbatim reason stated out loud
- [ ] Read-back list printed: every file written + every file deliberately not
      written
- [ ] Closing line delivered: which gate now guards what; remaining DRAFT and
      open-question count named
- [ ] No product code touched; no requirement invented; no config auto-applied
- [ ] ▶ narration per phase; lesson recorded/declared at D3
