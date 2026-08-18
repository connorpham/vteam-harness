---
name: team
command: /team
description: One command puts the whole virtual team to work. /team runs a full "workday" — clears the owner's decision queue first (batched questions), then works through every UNBLOCKED item (DEV tickets sequentially via /dev, BA drafts and SA ADRs in parallel background worktrees, QA verification between dev tasks) until everything left needs the owner, then prints one end-of-day desk report. The autonomous entry point on top of /pm — same rules, same gates, same decision queue.
args: "[n=N item cap | full: run until dry | no-decide: skip the asking step | lite: no background lanes, cheapest]"
---

# /team — one command, the whole team at work

This is the "start the workday" button. The complete rulebook is inherited
**intact** from the `/pm` workflow — the 5-role lineup, the immutable principles,
the UNBLOCKED definition, the lane priority order, the SA lane, P-DECIDE, the
ledger. This file only defines what differs: **running in one sweep, and running
in parallel**. On any conflict between the two files → /pm wins.

**What this workflow is NOT:** not a "drop the gates for speed" mode. Every
QUALITY gate of the child lanes (/verify, reviews per `review-standard.md`, the
evidence gate, challengers) holds absolutely. At `autonomy.level: full`, the
WAIT-FOR-HUMAN gates run autonomous: eligible PRs self-merge — governed by
config `autonomy.self_merge` (this install: **{autonomy.self_merge}**; off =
green PRs wait for the owner even at full autonomy) —
QA-passed tickets self-close (/qa V7.3b), challenger-approved BA drafts become
tickets (/ba B4), due questions get provisional decisions with a paper trail
(/pm P-DECIDE 2b). Only the EXEMPTIONS (`autonomy.exemptions`) still stop for
the owner.

## The rhythm of a workday

### T0 — ROLL CALL (≈ /pm P0)

Preflight + read the board + announce one block: current sprint, countable
unblocked work, questions due. Tracker preflight red → the day stops; present
the unblock steps.

**Role playbooks** (`{paths.team}/roles/`): the main loop reads `pm.md`; every
lane/agent given work MUST read its own role's playbook before working (the
child workflows already hook this in their reading phases; background-lane
agents get the playbook path in their brief). This is the floor of
"independent thinking, true to the role": the craft lives in the playbook, the
process lives in the workflow.

### T1 — CLEAR THE DESK BEFORE WORKING (P-DECIDE, unless `no-decide`)

A morning answer is cheaper than an afternoon blockage: present the questions
**overdue + due within the current sprint** (≤4 per round; the structured-
question tool when options are clear), record answers in the decision queue,
list the work each answer unblocked. The user answers "later" → respect it, mark
SKIP for today, don't re-ask this session.

### T2 — THE WHOLE TEAM RUNS

Loop until: no unblocked work, `n=N` reached (default **5** items; `full` = no
soft cap but a hard ceiling of 12 — see loop guards), or the user interrupts.
The default 5 is /team's OWN cap, deliberately higher than /pm's `run n=3`
because /team is "a full workday" — an intentional override, not a
contradiction.

**The main track (sequential, on the working tree):** /pm P1 priority order —
QA debt → the sprint's next DEV ticket → BA's next ticket batch → the SA ADR
whose turn it is. The DEV WIP limit is `team.size` (config; default 1 — one
coding item at a time, /pm principle #3).

**Background lanes (parallel with the main track, when there's work):** while
DEV codes, spawn background agents for work that does NOT touch the working
tree:

| Lane | Work | Isolation | Model |
|---|---|---|---|
| BA | draft the next ticket batch (challenger B3 done → the main track creates tickets per /ba B4) | separate worktree | `standard` |
| SA | write the Proposed draft for the next ADR + challenger review | separate worktree | `workhorse` |

Every spawned agent's model comes from `model-routing.md` — expensive brains for
expensive-if-wrong decisions, cheap brains for checklist work.

**The background lanes' way home** (without this rule, "separate worktree" is
empty words): a harness-created worktree is a read/compose copy only; background
lanes RETURN their results as text (draft/ADR/card) to the main track, and the
**main track** writes files into the real working tree and commits. Background
lanes NEVER write the ledger / session minutes / decision queue — two writers on
one bookkeeping file is a race that loses rows; every ledger line is written by
ONE hand, the main track's. Background results land at session end. Background
lanes also never create tickets or touch code branches — "committing" acts
(tickets from an approved draft, merges, status moves) belong to the MAIN TRACK
under the autonomy rules. ADRs specifically: draft + challenger done → status
stays Proposed — **accepting an ADR is an architecture decision, owner-only at
acceptance review** (a 🟡 row in the queue), unless it merely documents what
already runs in the code.

Work that stops because it needs the user (missing design oracle, spec
contradiction, a red gate that can't be self-fixed) → record the reason on the
desk + ledger, take the next item. No forcing, no same-session retries.

**Session minutes** (`{paths.pm}/sessions/YYYY-MM-DD-hhmm.md`; two sessions
firing on the same schedule tick would collide on the name — a session finding
an existing file not its own appends a `-b` suffix) — the whole team's exchange
in ONE file, opened as T2 starts, written rolling, one block per item:

```markdown
## <lane> — <item>
- Assigned: <what the PM handed the lane: ticket/question/ADR + key inputs>
- Exchange: <≤5 SUMMARY lines of the review/challenge rounds — conclusions, no transcripts>
  → details: {paths.evidence}/<KEY>/dev/review.md · {paths.specs}/reviews/… · {paths.adr}/…
- Result: <done + evidence | blocked: <Qn/reason> | failed: <which gate>>
```

Anti-bloat: the minutes are a SUMMARY + links to each lane's full records
(review cards, ADRs, REPORT.md) — content is never duplicated. One person opens
exactly 1 file and sees what the team said to each other today and why each
decision fell.

**Bookkeeping commits IMMEDIATELY after writing:** every `{paths.pm}/` update
(minutes, ledger, decisions) commits to a bookkeeping branch (or stash) BEFORE
the DEV lane switches branches — an uncommitted ledger edit has been destroyed
by a checkout before, and had to be rewritten from memory.

## Token discipline (no burning money on idle chatter)

Agents in this system do NOT chat with each other. Every "exchange" is **one
turn**: receive 1 brief → return 1 card → end. No message threads, no
multi-round debates (the single evidence-paid exception in item 3). On that
base:

1. **A spawn brief = paths, not content.** A child agent's brief contains only:
   file paths + a precise reading scope (`{paths.specs}/catalog.md §2`, `the
   PR's diff`, `{paths.evidence}/<KEY>/`). Pasting long spec/diff/document text
   into spawn prompts is FORBIDDEN — the agent opens exactly what it needs.
   Brief-writing bar: **"a brilliant engineer with poor judgment"** (credit:
   Superpowers) — expected outcome + measurable criteria + forbidden moves,
   specific enough that the agent cannot drift and then justify the drift.
   A vague brief burns double: wrong guess → redo.
2. **A reply = a card per template, not a narrative.** Verdict + findings (1–2
   lines each, file:line) + `MY WEAK SPOT`. The brief says so explicitly:
   "return a card, don't narrate your process".
3. **Exactly ONE rebuttal round.** REQUEST-CHANGES → the main round fixes →
   re-review of THAT concern (standing /dev law). The single exception: author
   and challenger disagree AND **both sides hold runnable evidence** → exactly
   ONE confrontation round, each side submitting one deciding experiment
   (command + output, no prose); still deadlocked → the owner's desk. No third
   round; evidence-free disagreement gets no extra rounds at all.
4. **No spawning for errands.** What the main loop can do in a few tool calls
   (read 1 file, check 1 value, grep) it does itself — spawning an agent for it
   pays for a fresh context for nothing. Spawn only at the routing table's named
   points (reviews, challengers, ADRs, background lanes).
5. **Background lanes only when worth it.** ≥2 unblocked items ahead before a
   background lane starts; a thin sprint tail runs sequential — cheaper.
6. **`/team lite`** — economy mode: background lanes OFF, main track + mandatory
   gates only (2 reviewers, challengers — quality is not negotiated). For slow,
   sure progress at minimum cost.
7. Standing anti-bloat still applies: KB reads index-only; minutes are summary +
   links.

## Loop guards

1. **In-session:** one attempt per item; the `n=N` cap (default 5); `full` still
   has the hard ceiling of 12 items/session.
2. **A zero-progress sweep ends the day early.** A full pass over the unblocked
   list with nothing finishing "done" → stop immediately, no second sweep — the
   report says why.
3. **Across sessions:** before dispatching, count the ledger — an item with
   **2 rows** of `failed`/`blocked` results is NEVER self-picked again; add a
   row to the decision queue's owner-actions section (with both failure reasons)
   and run it again only after the owner clears that row.
4. **No self-generated work.** The only work sources: the sprint plan + the
   backlog draft + the decision queue's ADR section. Background lanes never
   propose new work for themselves.

### T3 — END OF DAY (/pm P4, mandatory)

Close the minutes (final block: a 3-line summary), collect EVERY lane's results
(main + background), update the ledger, print **Your desk**:
one sentence of progress against `project.go_live` → ① done (with evidence) →
② needs you (by deadline: PRs awaiting merge, drafts/ADRs awaiting review,
questions awaiting answers) → ③ risks in the next 7 days.

## Definition of Done (every /team run)

- [ ] T1 ran (or the user chose `no-decide`) — no overdue question silently ignored
- [ ] Every dispatched item traveled its lane's full pipeline; DEV sequential;
      background lanes only in separate worktrees
- [ ] No invented answers (provisional decisions carry the 🟡 record +
      pending-acceptance label), no quality gate loosened; self-merge/self-close/
      self-create only under the corresponding autonomy rules
- [ ] Ledger +1 row per item (including abandoned items with reasons, using the
      3 canonical result values)
- [ ] Session minutes exist in `{paths.pm}/sessions/` — one block per item,
      summary + links
- [ ] Loop guards respected: 1 attempt/item/session · the item cap · stop on a
      zero-progress sweep · twice-failed work escalated to the queue
- [ ] Your desk printed, led by one business-progress sentence
- [ ] New lesson → `{paths.qa}/knowledge-base.md` per its §0, or "no new lesson"
