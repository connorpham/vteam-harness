---
name: pm
command: /pm
description: PM+SA orchestration lane — one command runs the whole virtual team so the owner only watches results. Reads the tracker + the sprint plan + the decision queue → picks the highest-value UNBLOCKED work → dispatches to the right lane (/ba for backlog, /dev for code, /qa for verification, the SA lane for ADRs) with every child gate intact → ends each session with the "your desk" report: done / needs-you / upcoming deadlines. Blocked work stays blocked — open business questions are collected for the owner, never answered by the machine.
args: "[status | next | run [n=N] | decide | sa <ADR topic>]"
---

# /pm — orchestrate the team; the owner keeps only the decision desk

**What this workflow is NOT:** it never answers an open business question itself
(the documented 🟡 PROVISIONAL mechanism in P-DECIDE 2b is the sole exception,
and only at `autonomy.level: full`), never bypasses a child lane's QUALITY gate
(/dev's verify + reviewers, /ba's challenger, /qa's evidence gate + challenger),
and never merges/transitions ANYTHING itself — merging PRs and moving statuses
belong to the child lanes under their own autonomy rules. Its single output: work
flowing through the right lane, and ONE table of things only the owner can do.

**The lineup** — 5 roles; three have their own workflows; /pm plays the other two
and keeps the beat:

| Role | Lane | Runner |
|---|---|---|
| **PM** | orchestration, work selection, unblocking, reporting | /pm (main loop) |
| **BA** | spec → backlog/tickets, gap updates after each answer | invoke `/ba` |
| **SA** | architecture decisions → ADRs in `{paths.adr}/` | the SA lane below (agent + challenger) |
| **DEV** | ticket → code + PR + tracker report | invoke `/dev` |
| **QA** | verify tickets the dev reports done | invoke `/qa` |
| **DESIGN** | UI tickets missing a design oracle | the DESIGN lane below — step 0 searches the project's design source for a matching frame and attaches the link; an HTML mockup is only the FALLBACK when no frame matches |

**Immutable principles:**
1. **Blocked is blocked.** Work blocked by a 🔴 OPEN row in the decision queue is
   NOT dispatched, even with an empty queue. No lane invents answers for the
   owner — /ba's principle #1 raised to project level. *Sole exception:* the
   documented 🟡 PROVISIONAL mechanism in P-DECIDE 2b — "provisionally decide +
   record + label for acceptance" differs in kind from "invent": reversible,
   traceable, always in the acceptance dossier.
2. **Child-lane gates stay intact.** /pm schedules and forwards; it never
   loosens a child gate "in the name of automation".
3. **One coding item at a time.** /dev needs a branch + gate on the working tree
   — never 2 DEV items in parallel. Non-code lanes (BA/SA/QA read-only) may
   interleave while waiting.
4. **Everything needing the owner funnels to ONE place:** the decision queue
   (`{paths.pm}/decisions.md`) + the "Your desk" table at session end. The owner
   never has to read the tracker/PRs/logs to know what they must do.
5. **The ledger:** every dispatched item writes 1 row to `{paths.pm}/log.md`
   (`date | lane | item | result | link`) — progress reports come from the books,
   not memory. The result column accepts EXACTLY 3 machine-countable values:
   `done` · `blocked: <Qn/reason>` · `failed: <which gate went red>` — DEV rows
   append the model tier used, e.g. `done (workhorse)`, to tune routing with data.
6. **Visible process** (framework-wide): one `▶` line per phase; the final report
   leads with plain language.
7. **Tokens are the owner's money.** Agents spawn only at the points the routing
   table names; briefs are paths, never pasted long content; answers are cards,
   not essays; one rebuttal round. What the main loop can do in a few tool calls
   is not delegated.

## Modes

> Want ONE command for the whole team? Use `/team` — it wraps `decide` + `run`
> into a full workday, inheriting every rule in this file.

| Command | Runs | Stops at |
|---|---|---|
| `/pm` · `status` | P0 → P1 → P4 | report + suggestion, no work done |
| `/pm next` | P0 → P1 → P2 (1 item, user confirms first) → P4 | after 1 item |
| `/pm run [n=N]` | autonomous loop: up to N items (default 3) | a gate needing the user, N reached, or no unblocked work |
| `/pm decide` | P-DECIDE only | after recording answers + listing unblocked work |
| `/pm sa <topic>` | the SA lane for 1 ADR | user reviews the ADR |

## P0 — PREFLIGHT + READ THE BOARD

1. `bash .vteam/scripts/preflight.sh` — the tracker leg must be green at minimum.
1a. **Git fence:** `git config core.hooksPath` must return the managed hooks dir
   (when `git.hooks: managed`) — empty/other → set it NOW and write one line into
   the session minutes (a clone once ran for days with silent hooks — every
   pre-push gate mute).
   **Retro cadence (ops.md §6):** the newest framework-review file older than 14
   days → "framework review" is UNBLOCKED work, slotted right after pending QA.
1c. **Recovery lane (a dead session must not orphan work):** scan for
   (i) In Progress tickets whose claim is past TTL with no remote branch/new
   worklog, (ii) local `feat|fix/*` branches with no upstream. Each is ONE piece
   of unfinished work: take it over (prefer resuming the old branch) or return
   the ticket to To Do + clear the claim; always write a `failed: previous
   session died mid-work` ledger row — so loop guards count crashed sessions.
1d. `python3 .vteam/scripts/schedule_check.py` — on/off-schedule numbers are
   MACHINE-computed (plan ↔ tracker ↔ today). Paste the output VERBATIM into the
   P4 desk report; OFF-SCHEDULE → the desk report's first line must be a plan
   (cut scope / slip / add capacity) — hand-writing "still on time" is forbidden.
1b. `python3 .vteam/scripts/stale_verdict_check.py` — catches tickets judged Done
   whose code changed afterward (preferred anchor: the COMMIT sha pinned in
   REPORT.md — more precise than the tracker changelog and catches pre-merge
   verdicts). Hits → run `--fix` to return them to In Review with an explanatory
   comment, and put that QA work at the head of the queue. **A verdict is valid
   only for the code it examined.**
2. **Role playbook:** read `{paths.team}/roles/pm.md` — the thinking floor
   (empiricism, low WIP, unblock before adding, quality is not an adjustment
   variable) this loop is measured by.
3. Read: the decision queue · the sprint plan (`{paths.pm}/plan.yaml`) · the
   ledger tail · `git status` + current branch · open PRs · **scan for human
   comments**: open PRs + PRs merged in the last 7 days — any unanswered human
   comment → priority-0 work (P1).
4. Query the tracker for the full project state by status + sprint label.
5. Announce one block: today → which sprint per the plan; tickets To Do / In
   Progress / Done; questions overdue / due within 7 days; PRs waiting.

## P1 — PICK THE WORK

An item is **UNBLOCKED** when all 6 hold: (a) no 🔴 OPEN question/action blocks
it; (b) if it's a UI ticket, its **design oracle** exists — a real design link on
the ticket (missing → dispatch the DESIGN lane first; the dev ticket queues right
after); (c) no blocked-by ticket still un-Done; (d) it belongs to the current
sprint or earlier; (e) **nobody holds it** — no In Progress claim within TTL and
no `feat|fix/<KEY>-*` branch being pushed; (f) **it is a row in the sprint plan**
— including harness/process work: work without a day-cost in the plan consumes
capacity off the books (a real week lost 4 days to exactly this without the desk
report noticing). Worthwhile ad-hoc harness work → add the plan row FIRST (with a
day-cost), then dispatch.

Dispatch priority (top down, first match wins):

0. **PR FEEDBACK** — any PR (open OR merged) carrying an unanswered comment/review
   from a REAL PERSON (P0 scanned for these; pipeline-authored comments filtered
   out). The owner's input is the most valuable input there is; handle before
   everything else, by protocol:
   - **Every comment gets a response, never silence.** Either ① FIX: check out
     the branch (merged PR → a new fix branch), change per the comment, re-run
     the /verify gate, re-review if code was touched, reply "fixed in <sha>:
     <what>"; or ② PUSH BACK: only with evidence the comment is mistaken — reply
     per `review-standard.md` (file:line citations, spec §, real test output;
     respectful tone, no empty argument).
   - Push-back met with the owner restating their position → do it their way
     (they own the product), unless doing so violates the spec/safety → a new
     decision-queue row, work paused.
   - A comment on a merged PR that asks for behavior change → a follow-up ticket
     (label `pr-feedback`), dispatched as normal DEV work.
1. **QA** — a ticket the dev reported done (PR merged / report posted) but not
   yet verified. Verification debt is quality debt; pay it first.
2. **DEV** — the next unblocked item, in sprint-plan order (the order means
   something).
3. **BA** — the current sprint has ≤1 item left and the next sprint lacks
   tickets → /ba creates the next batch from the existing draft.
4. **SA** — an ADR in the decision queue whose underlying question is answered
   but the ADR is unwritten/unreviewed.
5. **Nothing unblocked** → go straight to P-DECIDE: unblocking IS the most
   valuable work now, and only the owner can do it.

`next`: state the pick + one sentence why, wait for OK. `run`: proceed in the
order above.

## P2 — DISPATCH

- **DEV** → invoke `/dev <KEY>` — its whole pipeline (task-sheet, branch, verify
  gate, reviewers, push + PR, tracker report).
- **QA** → invoke `/qa <KEY>` — verify-only, evidence + REPORT.md.
- **BA** → invoke `/ba <feature> [epic=…]` — at full autonomy: draft through
  challenger B3, then tickets; undecided gaps go through P-DECIDE 2b.
- **SA** → the SA lane below.
- **Light path (scale-adaptive — credit: BMAD):** docs/chore work touching NO
  product code (docs, workflow updates, CI config) takes the light path — branch
  + PR + green CI is enough; no full /dev pipeline (reviewers, design, evidence).
  Touching product code paths ends the discount — full path, no negotiation.
- Work stopped mid-lane because it needs the user (missing design, ticket
  contradicts spec, a red gate that can't be self-fixed…) → record the reason on
  the desk + ledger, then (in `run` mode) take the next unblocked item. Never
  force a gate, never retry the same item in the same session.
- **Escalate instead of looping:** an item with 2 `failed`/`blocked` ledger rows
  (any sessions) → never self-dispatched again; add a row to the decision
  queue's owner-actions section with both failure reasons.

## The SA lane — ADRs

1. Spawn 1 fresh agent (model `workhorse`; the challenger too) reading:
   **`{paths.team}/roles/sa.md` (mandatory)** + the originating question (full
   text from the backlog draft) + the relevant spec shard + the schema + the
   owner's answer if one exists → writes `{paths.adr}/ADR-nnn-<slug>.md`:

   ```markdown
   # ADR-nnn: <decision name>
   Status: Proposed | Accepted <date> | Superseded by ADR-mmm
   ## Context — the problem, citing spec §/gaps/queue questions
   ## Decision — ONE sentence
   ## Options considered — 2–3, why chosen / why rejected
   ## Consequences — which migration, which tickets affected, accepted trade-offs
   ```

2. Spawn 1 challenger to FALSIFY: which consequence is unpriced? which
   spec/schema contradiction? does the migration path exist? Fix per real
   findings, and record the exchange in the ADR itself under `## Challenge`
   (finding + how fixed / why rejected) — an ADR without a Challenge section
   hasn't been challenged.
3. Present the Proposed ADR → the owner accepts → Status = Accepted, update the
   decision queue and related gaps. **An unaccepted ADR is code law for no one.**
   (Accepting an ADR is an architecture decision — it belongs to acceptance
   review, unless the ADR merely documents what already runs in the code.)

## The DESIGN lane — design oracles for UI tickets

Activates when a UI ticket is business-unblocked but has no design oracle.

**Step 0 — SEARCH THE PROJECT'S DESIGN SOURCE FIRST** (when `design.provider` is
configured): match frames against the screen code/name; a match → attach the
link to the ticket and this lane is DONE (the real design is the oracle — no
mockup generated). Multiple ambiguous matches → pick the closest name, record
the choice in the minutes. NO matching frame (or no design provider) → mockup
fallback below (design APIs are read-only — the machine cannot create frames):

0b. **Learn the design language before drawing**: refresh/verify
   `{paths.design}/design-language.md` (palette/type-scale/radii/components
   generated from the project's own design source). No design source at all →
   use the latest design-language file if one exists; none → the UI quality
   rules decide alone (record "no design source to learn from" in the minutes).
1. Spawn 1 fresh agent (`standard`): reads the screen's spec shard + the
   design-language file (**mandatory to follow — deviations only for a11y**) +
   the UI quality rules (for what the design language doesn't specify: layout
   patterns, states, UX flow) + existing screens in the codebase for system
   consistency → builds a **self-contained static HTML mockup** (1 file, inline
   CSS, display text VERBATIM from the spec's message/label catalog) at
   `{paths.design}/mockups/<Screen>-<slug>.html`, plus a 5-line note: which
   tokens came from the design language, what the UI rules decided and why.
2. The main track renders it at the right viewport (desktop/mobile per screen
   type), captures a PNG, sanity-checks against the UI quality checklist
   (contrast, touch targets, labels) — misses → one fix round with the agent.
3. Attach the PNG to the ticket + comment `Design oracle: attached mockup — dev
   builds to this image; the spec still rules behavior.` → the ticket becomes
   UNBLOCKED for DEV. The mockup commits via the light path.
4. The owner later adds a real design frame for that screen → the real design
   WINS over the mockup; QA compares against it from then on.

## P-DECIDE — unblocking (the heart of the workflow)

1. Filter the decision queue: overdue first, then nearest deadline. **Expected-
   value exception:** a question whose recorded savings/risk is **≥2 person-days**
   joins EVERY asking round regardless of deadline — a question due in three
   months that decides ten days of work is asked now, or the savings it priced
   are lost. Each round asks **≤4 questions** — no carpet-bombing.
2. Each question presented with: full text from the backlog draft + the BA's
   ready proposal + one line "unanswered past <date> → <what slips>". Clear
   options → use the structured-question tool, the BA's proposal first.
2b. **PROVISIONAL DECISIONS in the owner's absence (only at `autonomy.level:
   full`):** a question DUE in a session with no user response (scheduled run,
   owner away) → the machine provisionally adopts the BA's proposal (no proposal
   → the LEAST RISKY and MOST REVERSIBLE option). Record in the queue:
   `🟡 PROVISIONAL (machine) <date> — pending acceptance` + one-line reason + the
   reversal path if rejected. Tickets built on it carry `pending-acceptance`.
   Work unblocks and proceeds.
   **EXEMPT — never provisionally decided; dependent work waits:** everything in
   `autonomy.exemptions` (real money/production payment config, legal,
   purchasing, credentials/secrets, deletion of real data), and anything an ADR
   marked owner-only.
3. Answers are recorded in the queue (`✅ DECIDED <date>` + content; rows are
   never deleted), then: list the tickets just unblocked; an answer that changes
   requirements → the BA lane updates the gaps + comments on affected tickets.
4. **The change ledger (credit: OpenSpec):** an answer that CHANGES or ADDS a
   requirement (not merely picks between readings of the spec) → one CH-nn row
   in `{paths.specs}/changes.md`: source (question id), the requirement delta in
   1–2 sentences, status `decided` → `reflected` once shards/tickets updated.
   Shards stay verbatim (the verbatim gate) — this ledger is the bridge until
   the owner updates the source document and regenerates.
4b. **Impact assessment is part of every CH row** — the Impact column is NEVER
   empty, three parts before dependent work dispatches:
   - **Business (BA):** which stories/AC/TCs must be rewritten.
   - **Technical (SA):** CH touches schema/architecture/money flows → one
     assessment line from the SA lane (breaks the current design? needs an
     ADR?); display-only CH writes "no architectural impact".
   - **Schedule & cost (PM):** delta in person-days + affected sprints; delta >
     0.5 person-day → update the sprint plan in the SAME session — a CH that
     moves the schedule while the plan stands still makes the books lie.
   An exemption-listed CH → impact still recorded, work still waits for the owner.

## P4 — YOUR DESK (the closing report, mandatory in every mode)

Open with the VERBATIM output of `schedule_check.py` (from P0.1d) — on/off
schedule against `project.go_live` is a machine number, not a hand-written
sentence; a red script makes the first line a plan (cut scope / slip / add
capacity). Then exactly 3 sections, plain language:

1. **Done this session** — one line per item + LIVE evidence: merged PR #,
   COMMITTED file, ticket key. Evidence that exists only in the session
   (scratchpad, narration) does not count — a "done" row pointing nowhere is a
   fabricated report, and the ledger gate will red it.
2. **Needs you** — at full autonomy this usually reduces to: exemption-listed
   items and 🟡 PROVISIONAL decisions awaiting acceptance. Green PRs self-merge,
   QA-passed tickets self-close — no longer waiting on you.
2b. **The acceptance dossier:** when the current sprint's backlog DRAINS (every
   ticket Done or exemption-blocked) → write/update `{paths.pm}/acceptance.md`:
   (a) every 🟡 row + its `pending-acceptance` tickets, (b) a demo checklist per
   flow from the spec, (c) the evidence index, (d) work held by exemptions. The
   one document the owner reads at acceptance time.
3. **Risks & deadlines, next 7 days** — from the decision queue + sprint plan.
4. **Next session's model** — look at the next unblocked work, suggest
   `/model <tier>` per `model-routing.md` §3 (the machine suggests; the user
   types the command).
5. **Team performance** — when this session added ledger rows, run
   `python3 .vteam/scripts/perf_report.py --since <sprint start>` and paste its
   "Routing & accounting flags" section (who ran on which tier, was it per the
   routing table, where the tokens went). Any 🚩 flag is a desk-report line, not
   a footnote. The FULL report (`perf_report.py` with no filter) is a mandatory
   input of the 14-day framework review (`ops.md` §6).

Before printing: update the ledger (+1 row per dispatched item). **Token
accounting:** each row closes with `· tok ≈ <N>k` (main-loop estimate + subagent
totals from task notifications). After ~10 tickets the desk report can say
"a ticket this size ≈ Yk tokens" — trend per work type, never per single ticket.

## Definition of Done (every /pm session)

- [ ] Preflight ran; the board announced (sprint, tickets, due questions)
- [ ] No blocked item dispatched; no machine-invented answers
- [ ] Every dispatched item traveled its lane's whole pipeline — gates intact
- [ ] Ledger +1 row per item; decision queue updated on any new answer/ADR
- [ ] Your desk printed — even when empty ("nothing needs you today")
- [ ] New lesson → `{paths.qa}/knowledge-base.md` per its §0, or "no new lesson"
