# Operations runbook — running a virtual team continuously

> Goal: the virtual team keeps working while the owner is away, recovers by itself
> after usage-limit pauses, and the owner's daily touchpoint is ~15 minutes: read the
> desk report, answer queued decisions, accept finished work in batches.

## 1. State lives outside the session

The single most important operational property: **all state is external** — the
tracker (which column each ticket is in), git (branches/PRs), the dispatch ledger
(`{paths.pm}/log.md`), the decision queue (`{paths.pm}/decisions.md`). A session that
dies early (usage limit, crash, closed laptop) loses almost nothing; the next
scheduled session reads the board and continues exactly where work stopped. A
usage-limit pause is a break, not an incident — no special "resume" mechanism exists
or is needed.

**Duplicate-work guard:** every session opens by reading the ledger + tracker — work
already In Review or already carrying a PR is never picked up again; two overlapping
sessions therefore cannot do the same ticket twice. If duplication is *detected*
(two branches for one ticket), report it in the desk report; never auto-delete.

## 2. Scheduling and keep-awake

- Run the team on a schedule (typical: 4×/day). The machine must be awake when the
  schedule fires; missed runs execute late, they are not lost.
- Keep-awake is OS-specific — see `provenance.md` for the reference macOS setup
  (LaunchAgent + `caffeinate`). The invariants are portable: block system sleep, let
  the display sleep, auto-restart after reboot, and know that a closed laptop lid
  usually overrides everything.
- Locked screen ≠ sleeping machine. Locking keeps processes running; sleep stops
  agents and schedules. Only sleep needs handling.

## 3. Autonomy — a ladder, not a switch

`autonomy.level` in `vteam.config.yaml` controls only **wait-for-human** gates.
Quality gates (tests, reviews, evidence, challengers) never relax at any level.

| Level | Behavior |
|---|---|
| `off` | Every outward step waits: merge, ticket transition, ticket creation, decisions |
| `assisted` | Work proceeds; merge/close/create pause for a yes; due questions are asked, never provisionally decided |
| `full` | Eligible PRs self-merge (only if `autonomy.self_merge: true` — the per-project off switch); QA-passed tickets self-close; challenger-approved drafts become tickets; due questions get a **provisional decision** with a paper trail (🟡 marker, stated reversal cost, `pending-acceptance` label) |

**Exemptions (never auto-decided, at any level):** the `autonomy.exemptions` list —
by default real money / production payment config, legal, purchasing, credentials
and secrets, deletion of real data. These items sit untouched until the owner acts;
anything due shows up in session minutes and the desk report.

**Acceptance:** when the backlog drains, the owner reads ONE file —
`{paths.pm}/acceptance.md`: every machine-provisional decision, a demo checklist per
flow, an evidence index, and a sign-off log. Rejecting a provisional decision sends
the work that depended on it back to the backlog with the corrected answer.

## 4. Supersession law — changing a rule deletes the old sentence

When a decision CHANGES a written rule (a gate flips from user-gated to autonomous,
a threshold moves, a path changes): **delete or rewrite the old sentence in the SAME
commit, in EVERY file that repeats it** (frontmatter, principles, phase text,
Definition of Done, references). Never layer a dated annotation on top of a
still-standing old sentence — that is how a harness accumulates pairs of
self-contradicting rules that make its own DoD unsatisfiable (see provenance).

**One rule, one home.** Other files point to the home; they never restate it.

| Rule | House of record |
|---|---|
| Ticket status-transition rights + the In Progress claim protocol | `raci.md` §2 |
| Autonomy levels + exemption list | this file, §3 |
| Design oracle split (design source owns looks, spec owns behavior) | `roles/design.md` |
| Knowledge-base graduation | the KB's own §0 (`{paths.qa}/knowledge-base.md`) |
| Bug severity levels + SLA | `roles/qa.md` |
| Reviewer/challenger standard | `review-standard.md` |
| Model routing | `model-routing.md` |
| Per-OS 24/7 scheduling + keep-awake recipes | `ops-247.md` |

## 5. Git fence

All work reaches the protected branch (`git.protected_branch`) only through a PR
with CI green — code, docs, and framework changes alike. Where the hosting plan
provides real branch protection, use it (`git.hooks: external`); where it doesn't,
the managed pre-push hook is the only thing that can actually go red, and
`git config core.hooksPath .githooks` is a ONCE-PER-CLONE install step — every team
session verifies it at start, because a clone with silent hooks turns the rule into
prose, and prose rules get skipped. Escape hatches exist by design, are named
(`ALLOW_PUSH_MAIN=1`, `ALLOW_PUSH_NOREVIEW=1`), and every use is appended to
`{paths.pm}/hatch-log.md`. The secret scan runs before every hatch and has none.

## 6. Operating cadence — the virtual team's replacement for meetings

| Ritual | Virtual equivalent | Frequency | Required |
|---|---|---|---|
| Daily standup | Desk report ("Your desk") at end of every team session | Every session | Yes |
| Sprint planning | First day of each sprint: PM reconciles the plan (`{paths.pm}/plan.yaml`) with reality — velocity, open change requests, capacity — and logs the delta in session minutes; drift >1 person-day updates the plan | Sprint start | Yes |
| Backlog refinement | BA lane dispatched when the next sprint lacks ready tickets | Mid-sprint | Yes |
| Review / demo | Acceptance dossier (`{paths.pm}/acceptance.md` demo checklist + sign-off log) | When backlog drains | Yes |
| Retrospective | **Framework review**: survey the process itself with its own data (ledger, minutes, KB, git history) — hunt for gates that cannot go red and rules being skipped | Every 14 days; the PM lane checks the date of the latest review file and treats an overdue retro as priority UNBLOCKED work | Yes |

**Running this cadence unattended** (scheduled headless sessions, subscription usage
windows, per-OS scheduler + keep-awake recipes, and what still cannot relax at 03:00):
`ops-247.md`.

## 7. Token accounting & team performance

- Every ledger row closes with `· tok ≈ <N>k`, and DEV rows name the tier used
  (`done (workhorse) · tok ≈ 90k`) — rows from `project.adopted` onward;
  `log_check` enforces the format.
- **The reader is `perf_report.py`** — the accounting convention only pays off
  because a machine reads it: who did what per lane, tier usage vs the routing
  table (frontier without escalation, utility on DEV work, unrecorded tiers —
  all flagged), token outliers (>2× median = review-round eaters), monthly
  trend, and a rough cost band from `model-routing.data.yaml` prices.
- The desk report pastes the flags each session (pm P4.5); the full report is a
  mandatory input of the 14-day framework review — routing table changes are
  argued FROM this report, never from vibes.
- Read trends by WORK TYPE (schema groundwork vs screens vs docs), not per
  ticket — the biggest variable is the number of review rounds. After ~10
  tickets, the desk report starts estimating "a ticket this size ≈ Yk tokens"
  so the owner can budget.
