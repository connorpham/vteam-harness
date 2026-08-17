# RACI — who executes, who is finally accountable

> The ONLY home of decision rights in the virtual team (supersession law, `ops.md`
> §4). Workflows and playbooks POINT here; they never restate it. Any lane unsure
> "who decides this" reads this file.

**R** = executes · **A** = finally accountable (exactly ONE A per row) · **C** =
consulted · **I** = informed. Roles ≠ people: one session may run several lanes,
but each activity has one A.

Roles: **OWNER** = project owner (PO/customer — the only human) · **PM** = `/pm`,
`/team` · **BA** = `/ba` · **SA** = the SA lane of /pm (ADRs) · **DESIGN** = the
design lane (design oracle + UI quality rules) · **DEV** = `/dev` · **REV** =
reviewers R1/R2/R3 (`review-standard.md`) · **QA** = `/qa` · **OPS** = the DevOps
role (`roles/devops.md` — CI + gates; deploy once hosting is decided).

## 1. Activity matrix

| Activity | OWNER | PM | BA | SA | DESIGN | DEV | REV | QA | OPS |
|---|---|---|---|---|---|---|---|---|---|
| Elicit & finalize business requirements | **A** | C | R | C | – | I | – | C | – |
| Write spec shards / stories / AC | C | I | **R/A** | C | C | I | C (challenger) | C | – |
| Architecture decisions (ADR) | **A** (approves) | I | C | R | – | C | C (challenger) | I | C |
| UI design (design oracle) | **A** (provides it) | I | C | – | R | I | – | I | – |
| Estimation & sprint planning | I | **A** | C | C | – | R (per-ticket estimate) | – | C | – |
| Code + unit tests + self-review + evidence | I | I | C | C | C | **R/A** | – | I | – |
| Code review | I | I | – | C | – | R (fixes) | **A** (APPROVE/veto) | – | – |
| Write & run QA test cases | I | I | C | – | – | I | C (challenger) | **R/A** | – |
| Pass/fail verdict on a ticket | I | I | C (business arbitration) | – | – | I | – | **R/A** | – |
| Fix bugs | I | I | C | C | – | **R/A** | – | C (retest) | – |
| Arbitrate "bug or intended behavior" | A (when the spec is silent) | I | **R** (per spec) | – | – | C | – | C | – |
| CI / gate scripts / hooks | I | I | – | C | – | C | – | C | **R/A** |
| Environments / production release | **A** (until hosting decided) | R (coordinates) | I | C | – | I | – | C (smoke) | R |
| Change requests (CH-nn) | **A** (decides) | R (schedule/cost) | R (business impact) | C (technical impact) | C | I | – | C (test impact) | – |
| Acceptance (UAT, sign-off log) | **A** | R (prepares dossier) | C | I | I | I | – | C | I |
| Close ticket (Closed after acceptance) | **A** | R | I | – | – | I | – | I | – |

## 2. Ticket status-transition rights — who may touch which column

Root law: **no lane moves a ticket into a state another lane controls.**

| Transition to | Who | Condition |
|---|---|---|
| To Do (create) | BA | Story passes DoR (G/W/T AC + estimate + design link if UI + dependencies) |
| In Progress | DEV | On pickup, **with a claim comment `claimed <timestamp> · <branch>`** — In Progress is a CLAIM: other sessions seeing a claim under the claim TTL keep off; a claim past TTL with no remote branch/worklog is orphaned and handled by the PM recovery lane |
| In Review | DEV | Code done + gate green + reviews APPROVE + PR merged + full report comment |
| Done | QA | Verdict PASS + PR merged + CI green |
| To Do + `reopen` label | QA | Verdict FAIL / NEW-BUG — the `reopen` label distinguishes returned work from new work |
| In Review (unchanged) | QA | BLOCKED / UNCLEAR |
| In Review (reverted from Done) | PM | Only via the stale-verdict gate (a verdict expires when the code it judged changed afterward) |
| Closed | OWNER (PM operates on their behalf) | After a row exists in the acceptance sign-off log |

Outside the stale-verdict exception the PM **does not merge and does not transition
tickets** — those belong to the child lanes.

## 3. QA vs QC — two jobs, named correctly

- **QC (product control — finding defects):** the `/qa` lane + `roles/qa.md`.
  Test cases, execution, evidence, verdicts.
- **QA (process assurance — preventing defects):** the **gate suite + the learning
  loop** — review/evidence/ledger/DoR/stale-verdict gates, the pre-push hook, CI —
  plus the **periodic framework review** (`ops.md` §6) that audits the process
  itself. OPS owns keeping these gates runnable and ABLE TO GO RED (a gate that
  cannot go red is not a gate; every gate ships with mutation proof).

A bug caused by misread requirements is a BA/spec-stage defect, not a DEV defect.
Record the true origin stage in the QA report to improve the process — never to
assign blame.
