---
name: dev-domain-modeling
description: "Use when a ticket introduces or reuses business nouns (order, wallet, lot, member, tier…), when two names seem to mean the same thing, when a name in the spec differs from the name in the code, or before modeling any data — the vocabulary is decided before the table is."
role: dev
loads: T2
applies: label:data, label:domain, term:model, term:entity
---

# Domain modeling — the words are the design

## Identity

You treat the project's vocabulary as a contract. A concept has one canonical
name, one definition, and clear edges; every table, type, route and message
uses that name. When language is fuzzy you sharpen it *before* writing code,
because a fuzzy noun becomes a nullable column, then a special case, then a
bug nobody can name.

## When this applies

- The ticket or spec uses a noun the code does not yet have.
- Two words are used for what looks like one thing (`customer`/`user`,
  `plan`/`tier`, `item`/`line`).
- A concept has "kinds" (`status`, `type`) whose behavior differs.
- You are about to add a table, a type, or an enum.

## Decide

| Signal | Decision | Why |
|---|---|---|
| Spec and code use different words for one concept | Code adopts the spec's word; record the alias in the glossary | The spec is the oracle; a rename is cheaper than a permanent translation layer |
| One word, two behaviors (a `Member` who can and cannot buy) | Two concepts, or one concept with an explicit state — never a boolean pile | Booleans multiply into invalid combinations |
| A "type" column drives branching in ≥3 places | Model the variants explicitly (enum + per-variant rules, or separate types) | Repeated switches are shotgun surgery waiting to happen |
| A relationship is "usually one, sometimes many" | Ask which; model the real cardinality | "Sometimes many" becomes a JSON column nobody can query |
| A concept exists only for one screen | Keep it a view model, not a domain entity | Entities are forever; screens are not |

## Rules

- **Glossary first, code second.** Before modeling, list the concepts the ticket
  touches with a one-line definition each; put them in the task-sheet under
  *Domain*. *Otherwise:* you discover the definition disagreement in review,
  after the migration.
- **One concept, one name, everywhere.** Table, type, DTO, route segment, UI
  label share the canonical noun. *Otherwise:* every layer needs a mapping and
  every mapping is a place to be wrong.
- **Stress the model with concrete scenarios.** "A member's tier expires
  mid-order — which tier applies?" Write three such cases; the model must answer
  each without a shrug. *Otherwise:* the edge case arrives as a production
  incident with real money attached.
- **Make invalid states unrepresentable where cheap.** Enum over string,
  required over nullable, a state column over three booleans, a constraint over
  a comment. *Otherwise:* the code must defend against combinations that should
  not exist, in every place it reads the row.
- **Decisions that are hard to reverse get a record.** Money type, identity
  strategy, soft-delete policy, time zone rule → an ADR candidate for the SA lane
  (three tests: hard to reverse, surprising without context, a real trade-off).
  *Otherwise:* the fourth developer relitigates the decision and half-migrates
  away from it.

## Rationalizations

| Excuse | Reality |
|---|---|
| "It's just a status string for now." | Strings accept anything; "for now" is the schema in two years. |
| "The name in the code is close enough." | Close enough is a translation layer forever. Rename or alias explicitly. |
| "We can add the relation later." | Later means backfilling a foreign key against live data. |

## Red flags

- A `type`/`kind` column with behavior spread across the codebase.
- Three booleans on one row (`isActive`, `isSuspended`, `isDeleted`).
- A JSON column called `meta`, `extra` or `data`.
- Your task-sheet's *Domain* section is empty on a data ticket.

## Example

Spec says *"a Lot belongs to one Warehouse; a Lot is quarantined when its
inspection fails"*. Model: `Lot.warehouseId` required FK; `Lot.status` enum
`{AVAILABLE, QUARANTINED, CONSUMED}` — not `isQuarantined: Boolean`, because a
consumed lot cannot also be quarantined and the enum says so.

## Reviewer lens

- List the nouns the diff introduces; does each have one name across schema, types, routes and UI?
- Find a boolean pair or a `type` string; could the combination be invalid?
- Ask one edge-case scenario from the spec; can the model answer it?

## Sources

mattpocock/skills `domain-modeling` (glossary discipline, ADR sparingly) ·
Evans, *Domain-Driven Design* (ubiquitous language) · Fowler, *Refactoring*
ch. 3 (Primitive Obsession, Repeated Switches, Shotgun Surgery).
