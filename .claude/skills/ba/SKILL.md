---
name: ba
description: "BA pipeline — turns the upstream spec into a runnable backlog that /dev and /qa can execute. Reads the spec + schema + existing backlog → shards the spec into docs/specs/<feature>.md (index + per-feature files, the repo's citable oracle) → decomposes a feature into user stories with TESTABLE acceptance criteria (Given/When/Then, each tracing to a spec section) → flags every gap/contradiction as a question for the owner instead of inventing requirements → challenger review → creates the tickets per the B4 gate (owner approves the draft when present; in owner-absent sessions at full autonomy, challenger APPROVE suffices; dry-run always stops at the draft)."
argument-hint: "<feature|spec section|'all'> [epic=<epic key>] [dry-run]"
---

> **Model routing for this tool** (from `model-routing.data.yaml`, snapshot 2026-08-17):
> `frontier` → **fable** · `workhorse` → **opus** · `standard` → **sonnet** · `utility` → **haiku**
> Roles → tiers: ba-challenger: standard · ba-draft: standard · dev-r1: workhorse · dev-r2: standard (high-stakes: workhorse) · dev-r3: workhorse · explore: utility · qa-challenger: standard · sa-background: workhorse · sa-challenger: workhorse · sa-writer: workhorse
> Resolve at runtime: `python3 .vteam/scripts/model_route.py <role> --tool claude-code [--high-stakes]` — high-stakes diffs (review.high_stakes_*) bump dev-r2 to the workhorse tier.
> Spawning a subagent: pass the resolved name as the Agent tool's `model` parameter.


# /ba — from spec to runnable backlog (BA lane, no code)

**What this workflow is NOT:** it never writes product code, never invents
requirements the spec doesn't state, and never files tickets that skipped the B3
challenger gate. Its single output: a backlog where every ticket is EXECUTABLE by
/dev and VERIFIABLE by /qa without either having to re-open the whole spec.

**Immutable principles:**
1. **The spec is the source; the BA is a translator, not an author.** Every story
   and every AC cites its spec section (`spec §x.y`). Spec silent or
   self-contradictory → that's a QUESTION for the owner (collected in the gap
   list), never a guess. The schema is the second source — a story contradicting
   the schema gets flagged, not silently adapted.
2. **Acceptance criteria must be testable or they don't count.** Each AC is
   Given/When/Then with concrete values (role, input, expected output) —
   something /qa can turn into a TC mechanically. "The system must be friendly"
   is not an AC; "STAFF creates an order with 2 items → stock decremented by
   exactly 2, order PENDING" is.
3. **INVEST or split.** A story a dev can't finish in ≤2 days gets split. Every
   story states its dependencies (blocks/blocked-by) and what is OUT of scope.
4. **Dedup before create.** Check the existing backlog and
   `docs/qa/known-issues.md` before drafting — a story that already exists
   gets referenced, not duplicated.
5. **Outward actions are gated.** The backlog draft (table) is shown to the owner
   first; tickets are created after approval — with the ONE exception B4 defines
   for scheduled owner-absent sessions at `autonomy.level: full` (challenger B3
   APPROVE per `review-standard.md` suffices). `dry-run` always stops at the
   draft. Epic linking per the `epic=` argument.
6. **Visible, human-readable process.** Narrate each phase with a `▶ [B2/B5]`
   line; the deliverable leads with plain language — a non-technical PM reads the
   backlog table and understands what each ticket does, and why.

Tracker recipes: the configured tracker provider. UI tickets must carry the
design link for their screen — from the spec/design index or by ASKING; /dev will
stop without it.

---

## B0 — PREFLIGHT + ANNOUNCE

1. `bash .vteam/scripts/preflight.sh` — the tracker leg must be green at minimum
   (design/DB legs red only block the related steps). Fully RED → stop, present
   the unblock steps.
2. Resolve scope from the argument (feature / spec section / `all`). Announce:
   ```
   ▶ BA: analyzing <feature> — sources: <spec §…>
     existing backlog: <N related tickets> | epic: <key|none> | mode: <create|dry-run>
   ```

## B1 — READ THE SOURCES (spec + schema + backlog + KB)

- **Role playbook**: read `docs/team/roles/ba.md` first — the thinking floor
  (BACCM, the 9 ISO 29148 characteristics, declarative Gherkin, objective→story
  tracing, the data-review table, and "Living thinking": the user-day walk, the
  3-condition question bar, the summary bar, the pre-mortem) this lane is
  measured by.
- **KB preflight (index-only)**: `docs/qa/knowledge-base.md` §0 + INDEX, open
  lessons tagged `ba`/tracker/this feature's area; `docs/qa/known-issues.md`
  headings.
- **Close the QA→BA loop**: query the tracker for `qa-found`/`reopen` labels in
  this area — for every ticket whose REPORT.md marks **Origin: BA/spec stage**,
  the FIRST job of this lane is fixing the story/AC (+ a CH-nn row if the
  requirement changed) BEFORE writing new stories — a wrong AC left standing
  means the dev can fix code forever and still fail.
- Read the relevant spec sections. **Spec not in the repo yet → ask the owner for
  the file location once**, then shard what was read into
  `docs/specs/<feature>.md` (B2) — cite the in-repo file from then on.
  No spec exists ANYWHERE → stop and point at the right intake: `/plan`
  (greenfield) or `/docs` (undocumented codebase) — /ba shards truth, it never
  manufactures it.
- **Upstream and downstream spec disagree on the same requirement → read the
  spec's VERSION HISTORY section before concluding "undecided"** — parent–child
  contradictions are usually a stale parent, and the history records who changed
  what and why (provenance: a decided auth question was nearly reversed this
  way). Shards must include the version-history section, not just requirements.
- Read the schema for real models/fields/enums; skim existing code (which routes
  exist) to split new stories from change stories.
- Query the existing backlog for this feature (dedup — principle 4).

## B2 — SHARD THE SPEC (if not yet sharded) + DECOMPOSE INTO STORIES

- **Shard**: one file per feature in `docs/specs/<feature>.md` holding the
  requirements VERBATIM (no interpretation), section-numbered, plus one row in
  `docs/specs/INDEX.md` (feature | file | scope). This is the citable oracle
  of the other three lanes — a corrupted verbatim breaks the whole chain.
  - Extract table rows **BY REQUIREMENT CODE** (regex on the id column), **NEVER
    by line number**: an off-by-one line is a silent error — the wrongly-grabbed
    content is still a plausible sentence, so eyeballs won't catch it.
  - Only the "BA NOTES" section at the end of the file may interpret, clearly
    marked.
  - **Mandatory before leaving B2:** `python3 .vteam/scripts/verbatim_gate.py`
    must be GREEN. It byte-compares every coded row in the shards against the
    source documents.
- **The user-day walk before splitting** (top of the draft, ≤10 lines for the
  WHOLE feature): narrate one working day of 1–2 concrete people from this
  project's domain touching this feature — where they start, what they need to
  know, where the flow breaks without which screen/data. Every story below must
  point at the step of this walk where it stands; a story standing nowhere is a
  cut candidate (standard + examples: roles/ba.md "Living thinking" §1). The
  walk is BA interpretation — it lives in the draft, never in the shard (no
  verbatim-gate conflict).
- **Decompose** into stories per template (one block per story in the draft):
  ```markdown
  ### [<Feature>] <As — wants — so that>
  - **30-second summary** (MANDATORY, FIRST in the description): 2–4 plain
    sentences narrating what changes for the user — no requirement codes, no
    table names, no jargon. Bar: someone who knows neither code nor the project
    reads it and understands what this ticket does and why. Codes appear only
    from the Spec line down.
  - **Spec:** §x.y (docs/specs/<feature>.md)
  - **AC** (Given/When/Then, concrete values, ≥1 boundary pair):
    1. Given <role+data> / When <action> / Then <measurable outcome>
    2. (boundary) Given <adjacent wrong input> / When … / Then <how it's rejected>
  - **Schema:** models/fields involved (cited) — migration needed or not
  - **UI:** search the project's design source for the screen's frame → found:
    paste the node link here; no matching frame: add to the gap list (missing
    design oracle — owner to provide); no UI at all → write `no UI`
  - **Dependencies:** blocks/blocked-by <other story> | none
  - **Out of scope:** <explicit, so the dev doesn't self-expand>
  - **Pre-mortem (1 sentence):** "ships exactly as written and the user still
    suffers — why?" → patch with exactly 1 AC/note, or write "accepted, because
    <reason>". One sentence, no unlimited AC breeding.
  - **Priority:** Must/Should/Could (MoSCoW, per the roadmap)
  ```
- **Gap list** (mandatory, even when empty): every spot where the spec is silent
  / contradicts the schema / contradicts itself. **The 3-condition question bar —
  missing one means not sent:** (1) state where you ALREADY SEARCHED without
  finding the answer (spec, upstream spec + version history, schema, decision
  queue, change ledger); (2) a proposal with TWO-SIDED trade-offs + the cost of
  reversal; (3) which story it blocks, answer needed by when. A bare question
  ("what's the threshold?") outsources analysis to the owner — below the bar.

### Ticket taxonomy (applies to EVERY ticket created)

| Type | When | Convention |
|---|---|---|
| **Epic** | A complete requirement group of the spec, living across sprints | Description = requirement scope + oracle link + "held back, not yet ticketed" list + deferred section. Parent of every child Story/Task. |
| **Story** | Observable USER value — "As… I want… so that…" writes itself | Full story template (above). Always has a parent Epic. |
| **Task** | Technical/docs/infra work with no direct user value (docs sync, groundwork migration, CI setup) | Replace "user story" with a *Context* section; still carries AC/spec/out-of-scope. Parent Epic. |
| **Bug** | /ba does NOT create — that's /qa's lane on a NEW-BUG verdict | — |
| **Subtask** | /ba does NOT create — the dev splits their own work in /dev if needed | — |

Field conventions (non-negotiable):
- **Summary ≤70 chars**, shaped `[<Area>] <main behavior>` — longer gets clipped
  on the board.
- **Priority maps from MoSCoW** and MUST match the "Priority" line in the
  description: Must → **High** (go-live blocker → **Highest**) · Should →
  **Medium** · Could → **Low**.
- **Labels**: `ba-generated` + `<area>` for EVERY ticket **including Epics** —
  an area filter must catch the complete set.
- **Dependencies** = real tracker links with the correct direction; never
  dependencies recorded only as prose.
- **Original estimate is mandatory at creation**, from the draft/sprint plan
  (1d = 8h). A ticket without an estimate is a ticket not yet created — /dev's
  DoR gate will block it at T0; don't push the debt downstream.

## B3 — CHALLENGER REVIEW (1 fresh agent)

Spawn 1 fresh agent (model `standard` per model-routing) with the draft + spec
shard + schema + the decision queue (+ the change ledger) — without the decision
queue, the question bar's "already searched" condition can't be falsified.
Mission: FALSIFY —
which AC is unmeasurable? which story too big (INVEST)? which spec citation not
verbatim? missing boundary? reversed dependency? which summary reads like a
translated requirement — no concrete user situation (bars: roles/ba.md §4/§6)?
does the draft open with the ≤10-line walk — which story can't point at its step?
which pre-mortem is absent or toothless (leads to no patched AC and no "accepted,
because…")? which gap question misses one of the 3 conditions? Card per
`review-standard.md` (APPROVE carries the tried-to-break list — the 2-card quota
is not an excuse to invent findings).
**QC lens (shift-left — early testing is cheaper):** for the draft's riskiest
story, the challenger must SKETCH ONE TC in its card (account + steps + expected
per the AC) — an AC no TC can be sketched from mechanically is a failed AC,
return it. Record both cards in `docs/specs/reviews/<feature>-backlog.md`.
Fix the draft per real findings; disagreement → the owner.

## B4 — CREATE TICKETS (full autonomy; `dry-run` still stops at the draft)

1. Summary backlog table (1 row/story) + gap list written into the draft file.
   Owner present in the session → show the table and wait, as always. **Owner
   absent (scheduled session, `autonomy.level: full`):** challenger B3 APPROVE
   per `review-standard.md` is sufficient — don't wait.
2. Create tickets via the provider: description = the full story block, label
   `ba-generated` (+ `pending-acceptance` when the story rests on a 🟡
   provisional decision), epic link, dependency links. **Dependency links: after
   creating, READ ONE BACK and print the link type's direction fields to confirm
   orientation** (provenance: an entire batch of links once shipped reversed
   because the sent parameters were trusted). A gap on the exemption list (never
   auto-decided) → the dependent story is NOT created; stays in the draft with a
   note.
3. Print the created keys + URLs into the session minutes.

## B5 — CLOSE THE LOOP

- Plain-language summary: this feature now has N runnable tickets; which gaps
  still wait on the owner.
- Learning loop: new lesson (+1 INDEX line) into `docs/qa/knowledge-base.md`
  or "no new lesson"; prefer GRADUATION per §0.

## Definition of Done
- [ ] Preflight ran; scope announced
- [ ] Verbatim spec shard lives in `docs/specs/` + INDEX updated (if new)
- [ ] `verbatim_gate.py` GREEN — printed the number of rows compared
- [ ] Every story: measurable G/W/T AC + ≥1 boundary + spec § citation + schema
      check + out-of-scope + 1-sentence pre-mortem; draft opens with the ≤10-line
      user-day walk
- [ ] UI stories have a design link or sit in the gap list — no design-blind UI story
- [ ] EVERY created ticket has an original estimate
- [ ] Gap list delivered (even if empty — say "no gaps"); every question clears
      the 3-condition bar
- [ ] Challenger review really ran; 2 cards recorded
- [ ] Tickets created per the B4 gate (owner approves when present; challenger
      APPROVE when absent at full autonomy; dry-run stops at draft); keys + URLs
      printed
- [ ] No product code touched; no requirements invented beyond the spec
- [ ] ▶ narration per phase; lesson recorded/declared at B5
