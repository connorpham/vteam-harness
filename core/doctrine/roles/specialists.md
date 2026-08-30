# Specialist roster — deep-skill dev agents the lanes can dispatch

> The DEV lane (`/dev`) and the PM lane (`/pm`) consult this roster when a ticket
> clearly belongs to one domain. Specialists are defined as subagents in
> `.claude/agents/` and are spawned via the Agent tool (`subagent_type`), with the
> model resolved from `model-routing.data.yaml` like any other role.

## Why this roster exists

A generalist dev agent guesses at domain trade-offs; a specialist names them.
Deep tickets (a migration strategy, a rendering stall, a flaky pipeline, a RAG
quality drop) get better first-pass answers from an agent whose prompt already
carries the domain's failure modes. Specialists do NOT bypass anything: they work
inside the same /dev pipeline, the same evidence rules, the same gates.

## The roster

| Subagent | Domain depth | Dispatch when the ticket is about |
|---|---|---|
| `backend-specialist` | API contracts, data modeling, transactions, concurrency, query performance | Endpoints, schema/migrations, background jobs, caching, backend bugs/slowness |
| `frontend-mobile-specialist` | Component architecture, state, rendering perf, design fidelity, accessibility, mobile | Screens from a design source, UI bugs, layout/interaction, web vitals |
| `devops-cloud-specialist` | CI/CD, containers/K8s, IaC, observability, deploy safety | Pipeline failures, Dockerfiles, deploy config, secrets handling, "works locally not in CI" |
| `ai-data-specialist` | LLM integration, agents/RAG, evals, AI feature data prep | Model API features, prompt/tool design, retrieval quality, eval/embedding data prep |
| `data-engineer-specialist` | Warehouse/lakehouse modeling, ELT (dbt/orchestrators), streaming, data quality contracts, analytical cost/perf | Data pipelines, warehouse schemas, ingestion/backfills, slow or expensive analytical queries, data quality incidents |
| `security-specialist` | Threat modeling, authn/authz, injection classes, crypto usage, supply chain (defensive scope) | Security review of a diff/PR, auth flows, untrusted-input handling, hardening tickets, dependency audits |
| `qa-automation-specialist` | Test strategy, E2E frameworks, flaky-test forensics, test data, CI test infra | Writing/restructuring automated tests, flaky-test hunts, slow suites, test harness work (dev-lane; /qa stays verify-only) |

## Dispatch rules

1. **One domain, one specialist.** If a ticket clearly lives in one row above,
   spawn that specialist for the implementation or diagnosis step instead of a
   generic agent. Cross-domain tickets stay with the generalist /dev flow, which
   may consult a specialist for its slice.
2. **Same gates, no exceptions.** A specialist's output obeys every /dev
   invariant: spec is the oracle, minimal diff, evidence under `evd/<ticket>/`,
   `gate.sh` green before done. A specialist claim without recorded output is
   not a claim.
3. **Model routing applies.** Resolve the tier for the work (implementation →
   `dev-r1`'s tier; consultation → `standard`) via
   `python3 .vteam/scripts/model_route.py` and pass it as the Agent tool's
   `model` parameter.
4. **Specialists advise, the lane decides.** A specialist recommendation that
   expands scope or touches an exemption (real-money, credentials, …) goes to
   the decision queue like anything else.
