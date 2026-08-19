# Model routing — the right brain for the job, no overpaying

> Every workflow that spawns an agent MUST consult the routing table before setting
> the `model` parameter. The main session's model is the user's to change; the desk
> report suggests next session's model based on the upcoming workload.

## 1. The principle

**Model cost follows the WORK, not prestige.** Work that must be redone if wrong
(architecture, migrations, money logic) makes the cheap model the most expensive
one. Work with a clear checklist (AC audits, extraction, lookup) makes the
expensive model pure waste.

vteam routes by **tier**, not by model name — model names and prices rot:

| Tier | Meaning | Economic role |
|---|---|---|
| `frontier` | The most capable (and priciest) model available | Genuine dead-ends only — never a default |
| `workhorse` | The strong daily driver | Hard code, architecture, first reviewer |
| `standard` | Near-workhorse quality at a fraction of the price | Checklist reviews, drafts, coordination |
| `utility` | Cheap and fast | Mechanical lookup/extraction subagents |

The tier → concrete-model mapping, the role → tier routing table, the
high-stakes overrides AND the per-tool model names all live in
[`model-routing.data.yaml`](model-routing.data.yaml) — a **data file with a
staleness date** and the MACHINE HOME of the mapping (one rule, one home:
edit values there; the table below is the annotated rationale). Resolution is
mechanical: `python3 .vteam/scripts/model_route.py <role> --tool <tool>
[--high-stakes]` — adapters embed the resolved table into every rendered
workflow, so no agent ever has to guess what "workhorse" means on its tool.
When providers change prices or release models, update the data file first;
only then reconsider the routing below.

## 2. Subagent routing (workflows apply this without asking)

| Agent | Tier | Why |
|---|---|---|
| DEV **R1 spec reviewer** | `workhorse` | The reviewer must not be weaker than the author; a bug that slips review costs many times the model fee |
| DEV **R2 challenger** | `standard` | The second reviewer needs a DIFFERENT LENS more than equal IQ |
| DEV **R3 architecture** (when the diff touches `review.high_stakes_paths` **or** matches `review.high_stakes_terms` — same triggers review_check enforces) | `workhorse` | "Option A vs B, will it scale" is expensive-if-wrong; skipped for routine screens |
| ⚠️ **High-stakes exception**: diff matches `review.high_stakes_terms` (money, irreversible state) | R1+R2 both `workhorse` | The project's highest risk class |
| BA **challenger** | `standard` | AC/INVEST/citation audit — clear checklist work |
| QA **challenger** | `standard` | Falsifying the verify-sheet — the evidence gate does the mechanical part |
| SA **ADR writer** | `workhorse` | Few in number, expensive to reverse |
| SA **ADR challenger** | `workhorse` | A weak challenge means the ADR was never challenged |
| Background BA draft lane | `standard` | Drafting from an already-structured spec shard |
| Background SA lane | `workhorse` | Same as ADR writer |
| Lookup/explore subagents | `utility` | Purely mechanical |
| `frontier` for any subagent | **never by default** | Only after the same work failed twice on `workhorse` AND the owner approved the spend (logged in the decision queue) |

## 3. Main-session suggestions (the user switches; the machine only suggests)

| Session workload | Suggest | Note |
|---|---|---|
| Routine team day (standard CRUD/UI tickets with clear spec + design oracle) | `standard` | |
| Hard tickets: large data-model/migration groundwork, money logic, deep refactors | `workhorse` | Wrong here breaks the whole chain behind it |
| Status, decisions, documentation, standup | `standard` | Coordination doesn't need peak intelligence |
| Dead-ends: a bug unsolved after 2 sessions, genuinely hard design | `frontier` | Drop back down immediately after |
| Any session | never `utility` for the main loop | Utility is a subagent brain, not a working brain |

## 4. Standing rules

1. **Never downgrade a tier at a quality gate to save money.** Reviewers/challengers
   may be CHEAPER when the table says so — never cheaper than the table.
2. **Controlled escalation:** work that failed twice (loop-guard law) escalates to
   the owner WITH the suggestion "retry on a higher tier?" — raising the tier is the
   owner's call, because it is their money.
3. **Record the model in the ledger:** DEV rows in `{paths.pm}/log.md` note the tier
   used (e.g. `done (workhorse)`) — so this table gets tuned with DATA, not vibes.
4. The data file is a snapshot — update it before touching §2/§3.
