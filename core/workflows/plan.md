---
name: plan
command: /plan
description: Greenfield planning intake — for projects that have NEITHER code NOR documentation. Interviews the owner section by section (a five-field kernel: Why, Capabilities, Constraints, Non-goals, Success signal), with a one-round elicitation menu after every drafted section → writes a BRIEF, then a PRD whose requirement rows carry gate-compatible codes, then an optional architecture spine → registers the PRD as a SOURCE document (specs.sources) so the verbatim gate guards everything /ba later shards from it. Writes planning documents only — never product code, never tickets, never the config itself.
args: "[--update: revise an existing brief/PRD after answers changed]"
---

# /plan — from an idea to a gated source of truth (planning lane, no code)

**Why this exists:** every other vteam lane assumes an oracle already exists.
`/ba` shards a spec; `/docs` reverse-engineers one from code; `/dev` and `/qa`
cite it. A brand-new project has neither code nor documents — so before this
workflow, vteam was mute at the exact moment the most expensive decisions get
made. `/plan` is the intake: it turns the owner's head into documents the
gates can guard.

**Lane boundaries (pick the right door):**
- No code, no docs → **/plan** (this lane).
- Code exists, docs don't → **/docs** (read the code first, then ask).
- A spec document exists → **/ba** (shard it, build the backlog).

**What this workflow is NOT:** it never writes or edits product code, never
files tickets, never touches `vteam.config.yaml` (it PROPOSES the
`specs.sources` patch, the owner applies it), and never writes ADRs — it marks
ADR candidates for the SA lane.

**Immutable principles:**
1. **The owner is the only source.** There is no code to read and no spec to
   cite, so every requirement in the PRD must trace to an owner answer given in
   THIS lane. A sentence the owner never confirmed does not go in the PRD — it
   goes to the decision queue as an open question with a proposal. Inventing a
   requirement here poisons every gate downstream.
2. **Draft, then offer the menu — one round per section.** After drafting each
   section, present the elicitation menu (below) ONCE. The owner steers every
   section without reading a 20-page dump at the end; the lane never loops a
   section more than once (a second disagreement → a decision-queue row, move on).
3. **Outputs are SOURCE documents, and they live OUTSIDE `{paths.specs}/`.**
   The verbatim gate treats every `.md` in the shard directory as a shard —
   a PRD placed there would be byte-compared against itself. Planning documents
   go in the parent docs directory (`docs/BRIEF-<slug>.md`, `docs/PRD-<slug>.md`,
   `docs/ARCHITECTURE.md`); the PRD is then registered in `specs.sources`, which
   is what arms the verbatim gate the day /ba shards it.
4. **Requirement rows carry codes in the gate's shape.** Every functional
   requirement is a table row `| **FR-<AREA>-nn** | … |` (validation rules
   `VAL-nn`, messages `MSG-nn`, non-functionals `NFR-<AREA>-nn`) — exactly the
   row shape `verbatim_gate.py` extracts BY CODE. A PRD written as prose
   paragraphs produces shards no machine can guard; the codes are what make
   this document load-bearing instead of decorative.
5. **Scale-adaptive.** A small tool does not pay the full ceremony: the brief
   is always written; the PRD may collapse to one requirement table; P3
   (architecture spine) runs only when the answers reveal real structure
   (multiple services, external integrations, money/irreversible flows).
   Skipping a phase is DECLARED in the read-back, never silent.
6. **Token discipline.** The interview asks about the business; it never
   pastes long drafts into questions. Sections are drafted once, steered once.
7. **Visible, human-readable process.** One `▶ [P1/P3]` line per phase; every
   document leads with plain language a non-technical reader follows.

**The elicitation menu** (after each drafted section — answered with one digit;
credit: BMAD's advanced elicitation, held to vteam's one-round law):

```
1 accept as drafted
2 refine — one line on what to change
3 alternatives — I show 2 other ways to state/scope this section, you pick
4 challenge — I argue against my own draft (weakest assumption, what breaks)
5 defer — section ships marked ⚠ OPEN, a decision-queue row carries it
```

---

## P0 — SCOPE + THE RIGHT DOOR

1. Confirm this is really greenfield: product code in the repo → STOP, point at
   `/docs`; a spec document already exists → STOP, point at `/ba`. (`--update`:
   an existing `docs/BRIEF-*`/`PRD-*` from this lane → load it, revise only the
   sections whose answers changed, version-history the delta.)
2. Announce:
   ```
   ▶ PLAN: greenfield intake — <working name>
     door check: no code, no spec | mode: <new|update>
   ```

## P1 — THE BRIEF (the five-field kernel + the people)

Interview, then draft `docs/BRIEF-<slug>.md`, section by section, menu after
each. The kernel (five fields, one section each):

| Field | The question behind it |
|---|---|
| **Why** | What hurts today, for whom, and what does it cost them? |
| **Capabilities** | The 3–7 things the system must let people DO (verbs, not features) |
| **Constraints** | Hard walls: budget, deadline, compliance, stack the owner already owns, integrations that cannot change |
| **Non-goals** | What this project deliberately will NOT do — the section that saves the most money, written the earliest |
| **Success signal** | The observable number/event that says it worked (not "users are happy") |

Plus one section the kernel misses: **Users & roles** — who touches the
system, which roles are internal vs customer, and which actions are
irreversible or move money (the seed of `review.high_stakes_terms`).

Rules: every section drafted from the owner's answers, menu once, then on.
Deferred sections carry `⚠ OPEN (Qn)` and a decision-queue row with a proposal
and what it blocks.

## P2 — THE PRD (a source document with teeth)

Transform the brief into `docs/PRD-<slug>.md` — drafted area by area (one area
per Capability, typically), menu after each area. Fixed shape:

```markdown
# PRD — <name>
## Version history
| Date | Change | Why |            ← /ba is REQUIRED to read this section later
## 1. Purpose (plain language, from the brief's Why)
## 2. Users & roles
## 3. Functional requirements — <AREA>
| Code | Requirement | Priority |
|---|---|---|
| **FR-<AREA>-01** | <one behavior, one sentence, verifiable> | Must |
## 4. Validation rules
| **VAL-01** | <rule with concrete values/boundaries> |
## 5. Messages
| **MSG-01** | <exact user-facing text> |
## 6. Non-functional requirements
| **NFR-<AREA>-01** | <number, not adjective: p95 < 300ms, not "fast"> |
## 7. Non-goals (verbatim from the brief, plus per-area exclusions)
## 8. Open questions
| Qn | question | proposal | blocks |   ← mirrors the decision queue, never resolved silently
```

Row discipline (this is where the BMAD-style comfort meets vteam's teeth):
- **One row, one behavior**, ISO-29148 singular — a row with "and" is split.
- Every Must row is **verifiable as written**: a QA who has read nothing else
  can turn it into a test case. "Friendly", "fast", "easy" are returned to the
  interview, not written down.
- Codes are permanent: rows are never renumbered on edit — superseded rows are
  struck through in place and the version history says why (the verbatim gate
  will hold shards byte-identical to THESE rows; churn here is churn everywhere).

**P2b — challenger pass (one fresh agent, `ba-challenger` tier).** Brief: the
PRD + the brief + `review-standard.md`. Falsify: which Must row is not
verifiable as written? which two rows contradict? which Capability from the
brief has NO covering row (and which row serves no Capability)? is any
non-goal violated by a requirement? Card per the review standard; fix real
findings; disagreement → the owner, via the menu's challenge option, one round.

## P3 — ARCHITECTURE SPINE (only when the answers earned it)

Trigger: multiple deployable parts, external integrations, or money/
irreversible flows surfaced in P1/P2. Otherwise: SKIP, declared in the
read-back ("single-container CRUD — spine deferred until it hurts").

Draft `docs/ARCHITECTURE.md` — a SPINE that hydrates later, not a novel:
context (who/what talks to the system) → containers (the deployable parts and
why that many) → data (the entities that matter and who owns each) →
cross-cutting (auth, money handling, audit). Menu after each layer.

Every expensive-to-reverse choice visible here is recorded as an
**ADR candidate** row (`decision · why it's expensive to reverse · options
seen`) — the SA lane writes the ADRs; this lane never does.

## P4 — WIRE THE GATES + HAND OVER

1. **Propose the config patch — SHOWN, NEVER APPLIED:**
   ```yaml
   # PROPOSED — review, then paste into vteam.config.yaml yourself.
   specs:
     sources: [docs/PRD-<slug>.md]
   review:
     high_stakes_terms: [<terms the owner marked money/irreversible in P1>]
   ```
2. **Prove the wiring:** with the patch applied (owner's call), run
   `python3 .vteam/scripts/verbatim_gate.py` — it reports the PRD's coded rows
   as available truth; it starts actually guarding the day `/ba` shards them.
   State this out loud — the gate is armed, not yet firing.
3. **Read-back list** — every file written (path → sections → open-question
   count) and every phase deliberately skipped, with the reason.
4. **Closing line + the handover:**
   ```
   ▶ PLAN done. The idea is now a gated source of truth:
     · docs/PRD-<slug>.md — <N> coded rows, <M> open questions (decision queue)
     · next: apply the config patch, then /ba <first area> shards it and builds
       the backlog — from here the standard pipeline takes over
   ```
5. **Close the learning loop** — a lesson (+1 INDEX line) into
   `{paths.qa}/knowledge-base.md`, or "no new lesson".

## Definition of Done
- [ ] Door check ran: no code (else /docs), no existing spec (else /ba)
- [ ] Brief exists with all five kernel fields + users/roles; every section got
      exactly ONE elicitation-menu round; deferred sections carry ⚠ OPEN + a
      decision-queue row with a proposal
- [ ] PRD rows are coded (`FR/VAL/MSG/NFR`), singular, verifiable-as-written;
      Must rows pass the "a stranger can write the test" bar; codes never
      renumbered; version-history section present
- [ ] Every requirement traces to an owner answer from THIS lane — zero
      invented rows; open items live in §8 + the decision queue, not in silence
- [ ] P2b challenger ran (one fresh agent, one round); card recorded; real
      findings fixed
- [ ] P3 ran or its skip is declared with a reason; ADR candidates listed, no
      ADR written
- [ ] Planning docs live OUTSIDE `{paths.specs}/` (the shard dir belongs to the
      verbatim gate); config patch SHOWN with `specs.sources`, config UNTOUCHED
- [ ] Read-back list printed; closing line names the /ba handover
- [ ] No product code, no tickets, no config writes
- [ ] ▶ narration per phase; lesson recorded/declared at P4
