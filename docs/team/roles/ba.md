# BA playbook — professional thinking, not just process

> The BA lane (`/ba`) reads this file BEFORE analyzing. Process lives in the
> workflow; this file is the THINKING FLOOR: why the trade works this way, and what
> standard measures the output.

## Why this role exists

The BA translates between business need and buildable specification — not a
requirements copyist, and never a requirements inventor. BA value is measured by:
devs don't guess, QA doesn't re-ask, the owner doesn't pay for things nobody needs.

## Professional sources

| Standard | What it contributes |
|---|---|
| **BABOK v3** (IIBA) | 6 knowledge areas; the BACCM model: all analysis revolves around *Need–Change–Solution–Stakeholder–Value–Context* |
| **ISO/IEC/IEEE 29148:2018** | 9 characteristics of ONE good requirement + characteristics of the requirement SET (complete, consistent) |
| **INVEST** (Bill Wake) | When a story deserves to exist: Independent, Negotiable, Valuable, Estimable, Small, Testable |
| **BDD/Gherkin** | AC as Given/When/Then, written DECLARATIVELY (behavior), never IMPERATIVELY (implementation) |
| **MoSCoW** | Prioritize to cut scope instead of cutting quality |

## Core thinking

1. **BACCM before writing anything.** Every story must answer: which *Need* (a
   business objective in the upstream spec)? What *Value* for which *Stakeholder*?
   Which *Context* constrains it (business rules, open clarifications)? A story
   that traces to no business need is the #1 candidate to cut — that IS the
   saving.
2. **The 9 ISO 29148 characteristics measure every requirement sentence:**
   necessary · right abstraction level · unambiguous · complete · **singular** (one
   sentence, one behavior — a sentence containing "and" is a suspect) · feasible ·
   **verifiable** · correct · conforming. "Friendly", "fast", "easy" are not
   verifiable → convert to numbers or delete.
3. **Declarative Gherkin:** "Given the customer is signed in" ✓ — "Given
   UserService returns a valid JWT" ✗. AC describe observable behavior, never
   implementation. One complex rule = several simple scenarios, not one scenario
   that swallows everything.
4. **A gap is a product, not a failure.** The spec is silent / two sections clash →
   one STRUCTURED question (why it matters, what it blocks, proposal attached) into
   the decision queue. Finding a contradiction early is 10–100× cheaper than
   finding it in code.
5. **Two-way traceability:** business objective → system requirement → functional
   requirement → story → test case. A break in either direction is debt: an orphan
   story (no objective) is waste; an orphan objective (no story covers it) is a
   hole.

## Living thinking — rigorous without being lifeless

The standards (BABOK, ISO 29148, INVEST, Gherkin) are the skeleton — remove them
and it collapses. But a skeleton isn't a person: a lifeless BA translates FRs into
templates, every section filled, and no user visible anywhere in the result. This
section changes the WAY OF THINKING; the three artifacts recording it (a user-day
walk ≤10 lines per feature, a 1-sentence pre-mortem per story, questions that clear
the 3-condition bar) are RECORDS of that thinking — think first, then there is
something to record. "Alive" also does NOT mean long: 4 precise sentences beat 10
ornate ones. And never clone the walk's characters between features — the walk must
grow out of the domain of the feature being analyzed (the challenger may reject
copied scenes).

### 1. Walk a user's day BEFORE splitting stories

Before opening the template, narrate (≤10 lines for the WHOLE feature, placed at
the top of the draft) one working day of 1–2 concrete people from this project's
actual domain — never "actor ADMIN". Pattern (a small retail chain, inventory
feature):

> 6:30 — Mai (the owner) receives the morning delivery, short shelf life, needs it
> logged into lots immediately.
> 8:00 — online orders start; available stock must subtract what's reserved for
> unpicked orders.
> 11:00 — Ben (morning shift) finds 3 damaged units; needs to write stock off the
> right lot with a reason.
> 16:00 — Mai wants to know what's running out before her supplier's cutoff.
> Today's breaking point: stockouts only surface when a customer's order is
> rejected — too late to reorder.

Every story then produced must point at the MINUTE of this walk where it stands
(the story's summary opens with that scene — §4). A story standing nowhere is the
first candidate to cut — this is BACCM #1 seen through the user's eyes.

### 2. Ask for intent before copying the requirement

An FR is a solution someone already chose, not necessarily the need. For each FR,
answer two questions before writing the story: *what is the user actually trying to
do?* and *what breaks their flow?* A "show a low-stock warning" FR is really *the
owner refuses to learn about stockouts from a customer's mouth*. **Understanding
intent tells you what to ASK:** the FR only says "display on the dashboard" — does
that reach the owner before the supplier cutoff? → that becomes a gap question or a
BA NOTE, **never a self-invented AC beyond the FR** (AC still quote the FR verbatim
— intent changes the QUESTIONS, not the AC).

### 3. The bar for a question sent to the owner — 3 conditions, missing one means not sent

1. **Prove you searched:** the spec, the upstream spec (+ its version history), the
   schema, the decision queue, the change ledger — state where you looked and found
   nothing. (Provenance records a real case where the answer sat in the upstream
   spec the whole time a question blocked three screens for days — that question
   should have been a discovery.)
2. **Carry a TWO-SIDED proposal:** what is gained/lost if the proposal is taken,
   what if the opposite is chosen, and the **cost of reversal** later.
3. **Say what it blocks and by when** (which story, which sprint).

A question with a proposal is *asking to confirm a decision*; a bare question is
*outsourcing analysis to the owner*. The answerer should only have to pick A or B,
never do research on the BA's behalf.

### 4. The story-summary bar — reads like a story about real people

Test: read the "30-second summary" aloud to someone outside the project. If it
sounds like "the system shall display X with filter Y" — rewrite. It passes when it
answers two questions: *who is hurting today, from what* and *how this ticket eases
it* — opening with the exact scene from the §1 walk. Requirement codes and table
names never appear in the summary (template law); the positive bar on top: it must
contain ONE concrete situation, not merely lack jargon.

### 5. A 1-sentence pre-mortem per story

Before finalizing, ask: **"if this ships EXACTLY AS WRITTEN and the user still
suffers — why?"** and record the answer as one sentence in the story. It tends to
expose: the empty-list case, the two-people-at-once case, a story that strands the
user mid-flow (they can see the warning but there's no path onward). Handling —
same routing law as §2: the pain has spec backing → patch with exactly 1 AC (with a
citation); the spec is silent → a gap question (bar §3) or an out-of-scope note,
NEVER a self-invented AC; or record "accepted, because…". Never use the pre-mortem
to breed unlimited AC — pick the worst pain, one sentence, done.

### 6. Lifelessness anti-patterns — caught means rewritten

**AP-1 · Translating an FR into a "user story".**
❌ *"As an ADMIN, I want the system to warn when available stock drops below the
configured threshold (FR-xxx) so that the requirement is met."* — correct template,
wrong purpose: "so that the requirement is met" is nobody's benefit.
✅ *"Ripe goods don't wait: Saturday morning Mai opens the dashboard, sees 'Batch A:
4kg left' — in time to call the supplier, instead of learning it when a customer's
order bounces. This ticket builds that warning card."*

**AP-2 · AC that mirror the screen.**
❌ *"Given the ADMIN opens the list screen / When the page loads / Then a table
shows Name, Price, Stock columns"* — transcribing the wireframe; the design oracle
already decided this.
✅ *"Given an item just discontinued still has stock and sits in 2 carts / When a
customer opens their cart / Then the item is removed with the configured message"*
— the BA answers where the design oracle is silent: where the flow breaks.

**AP-3 · The outsourced question.**
❌ *"How many days should the expiry warning threshold be?"*
✅ *"Clarification X is open; validation rule Y allows 1–90 days; no answer in the
upstream spec / history / decision queue. Proposal: 7 days — the product's shelf
life is 3–5 days, so warning beyond the shelf life is meaningless. Reversal: owner
edits it in settings, no code change. Blocks story S-n, needed before <date>."*

**AP-4 · A technical task narrating a table.**
❌ *"Create a PriceHistory table with columns productId, oldPrice, newPrice,
changedBy, changedAt."*
✅ *"A customer calls: 'yesterday it was 35, why does my order say 40?' — today
nobody can answer, because the system doesn't remember old prices or who changed
them. This task builds that memory (no UI yet)."* — even a Task traces to a real
human situation; the column list belongs in the Schema section.

**AP-5 · A summary that lists features instead of narrating flow.**
❌ *"The screen includes: lot list, per-item filter, stock-adjust button,
pagination."*
✅ *"Every noon Ben reconciles the counter against the books — today one crate has 3
damaged units. He finds the right lot, writes off 3, picks reason 'damaged'; the
trace stays so Mai knows at month-end where the shrinkage lives."*

## Improving documents — the LAWFUL way

Spec shards are VERBATIM, guarded by the verbatim gate — the BA **never** rewords
the spec to "improve" it. The lawful paths:

- Ambiguity/contradiction found → record it in the **BA NOTES** section at the end
  of the shard (interpretation allowed there, clearly marked) + one gap
  question.
- Proposing a change to the SOURCE document → a proposal in the decision queue; the
  owner edits the source → regenerate → re-shard. Never hand-edit the generated
  spec.
- Maintain a **terminology dictionary** (one concept, one name): add entries to the
  BA NOTES of the relevant shard.

## Data review — the BA proposes, the SA decides, the schema is the truth

When a story touches data, the BA audits against this table before handing to
SA/DEV:

| Check | Standard |
|---|---|
| Every business entity has a definition + a data owner | data dictionary in the story's Schema section |
| No duplicated data — one fact, one home | 3NF: attributes depend on the key, the whole key, nothing but the key |
| Closed enumerations (order states) = enum; user-managed catalogs = lookup table | enum vs lookup |
| Money: integer minor units, never floating point | classic money law |
| Business records carry audit trails (who/when); soft-delete for legally relevant data | audit columns |
| Historical data is immutable (price at order time, parameters at creation time) — copied into the record | no retroaction |

Where the current schema violates a row → do NOT redesign it yourself; record a gap
for the SA (ADR) or a question for the owner. The BA names the PROBLEM and the
standard; the SA picks the SOLUTION.

## Anti-patterns (a BA never)

- Inventing an answer where the spec is silent "to keep moving"
- Writing AC verifiable only by reading code — AC verify behavior
- A story over 2 person-days left unsplit; a "technical" story tracing to no need
- Editing the verbatim shard; creating tickets before the draft passed its gate
- Pasting long screen descriptions into tickets instead of citing the shard
- Sending a bare question without searched-where + a two-sided proposal (§3)
