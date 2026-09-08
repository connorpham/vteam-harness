# VT-6 — LIVE peer-chat smoke test: the real outcome (2026-09-08)

Two DEV agents spawned in parallel, each told to find the other via `ListAgents`
and coordinate the shared `Order` type via `SendMessage`. This records what
ACTUALLY happened — not a simulation.

## Result: direct peer-to-peer chat did NOT complete in this session

**Blocker — `ListAgents` is DISABLED in this session (subagents too).** Both
agents called it and got: *"No such tool available: ListAgents. ListAgents is
disabled for this session, in subagents as well as here."* With no roster,
neither could learn the other's addressable name.

**`SendMessage` IS available and functional** (it returns proper errors), but it
needs an exact reachable name/agentId that only `ListAgents` (or a spawn result)
provides. Every guessed name — `ORDERSVC-OWNER`, `ORDERSVC-CONSUMER`, `DEMO-1`,
`DEMO-2`, `owner`, `consumer`, … — returned *"No agent named '…' is reachable."*
So no message was delivered either direction; no reply arrived.

## What DID work: coordination through the committed artifact

The owner wrote the real `Order` type to the shared dir; the consumer, unable to
reach it by message, **read the shape from `src/order.ts`** and wrote a consumer
whose fields (`id`, `totalVnd`, `status: "OPEN"|"PAID"|"CANCELLED"`) match
exactly — never guessed. That is precisely the "decision becomes an artifact"
path VT-6's guardrail is built around, and it succeeded.

## Honest conclusion

- Direct sibling-to-sibling chat is **not exercisable in this session** — peer
  discovery (`ListAgents`) is turned off; spawned siblings have no address book.
- **Coordinator-mediated** messaging works: the main/PM session CAN `SendMessage`
  a spawned agent by its agentId. Relay-through-PM is the available channel.
- **Artifact-based** coordination works and is what the guardrail enforces.
- To make TRUE direct peer chat run, the environment must enable `ListAgents`
  for the sessions (or hand each agent the others' agentIds), or use the Orca
  `orchestration` skill, which is purpose-built for multi-agent addressing.

The VT-6 CODE is complete and gate-green regardless: `coord_check` is proven
(selftest + cmd_probe: reflected handoff green, unreleased/over-budget red), and
the workflow rules are in place. What the platform blocked here is the live
transport of the chat, not the guardrail.
