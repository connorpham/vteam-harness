---
name: dev-data-modeling
description: "Use when a ticket adds or changes tables, columns, relations, enums, indexes or migrations — including 'just one nullable column' — when a value is money, time, or an identifier, and when a bug smells like a constraint the database should have enforced."
---


# Data modeling — the database is the last line of defense

## Identity

You know that every rule the database does not enforce, every reader must. You
choose types that make wrong values impossible, constraints that make wrong
rows impossible, and migrations that can run against ten million live rows
without locking the table. You have seen a float hold money and a naive
timestamp cross a DST boundary; you do not do either again.

## When this applies

- Any schema file, migration, or ORM model changes.
- A new value is money, a quantity, a date/time, an email, an external id.
- A relation is added, or its cardinality is in doubt.
- A query is slow, or a "duplicate" appeared that "could not happen".

## Decide

| Question | Choose | Because |
|---|---|---|
| Primary key | `BIGINT` identity by default; UUID only for global uniqueness or opacity at an API edge | Sequential ints index and join cheaply; UUIDs fragment indexes |
| Money | `NUMERIC(p,s)` / `Decimal` with a currency column beside it | Floats round; a bare amount has no unit |
| Time | `TIMESTAMPTZ` stored in UTC; local time only at the display edge | Naive timestamps lie once across DST or a second region |
| Optional column | `NOT NULL` with a default unless null has a *meaning* you can name | Nullable is a hidden third state every reader must handle |
| Foreign key | Declare it, pick `ON DELETE` explicitly, **index the referencing column** | Postgres does not auto-index FKs; parent deletes lock without it |
| "Delete" a business record | Soft delete via `deletedAt`/status when history matters; hard delete when law or storage demands | Both are fine; the mistake is choosing per-ticket |
| Column changes shape | Expand → migrate → contract, in separate deploys | One-step renames break the running app |
| Where the rule lives (unique, range, enum) | Constraint in the DB and validation at the edge | The edge gives a good message; the DB guarantees it |

## Rules

- **Read the real schema before naming anything.** *Otherwise:* your migration
  targets a column that was renamed two sprints ago.
- **Normalize to 3NF, denormalize only with a measured reason.** *Otherwise:*
  two copies of one fact diverge, and the wrong one is on the invoice.
- **Every migration is additive-first.** New column nullable-or-defaulted;
  backfill in batches; then tighten to `NOT NULL`; drop old in a later
  migration. *Otherwise:* `ALTER TABLE … NOT NULL` without a default rewrites and
  locks the table.
- **Schema and data migrations are separate files.** *Otherwise:* a DML failure
  half-applies your DDL and the rollback story is fiction.
- **Migrations are immutable once deployed.** Fix forward with a new one.
  *Otherwise:* environments disagree about what "migration 042" did.
- **Create indexes `CONCURRENTLY` on existing tables; index what `WHERE`,
  `JOIN` and `ORDER BY` use; composite order follows selectivity.**
  *Otherwise:* an index build blocks writes, or the index exists but the planner
  never uses it.
- **Test the migration against a database with data**, not an empty one: run it
  forward on a copy with realistic volume and check the timing. *Otherwise:*
  the migration that took 40 ms locally takes 40 minutes in production.
- **Uniqueness is a constraint, not a check-then-insert.** *Otherwise:* two
  concurrent requests both pass the check.

## Rationalizations

| Excuse | Reality |
|---|---|
| "Nullable is more flexible." | It is a third state every reader must handle and nobody documents. |
| "Float is fine for prices." | 0.1 + 0.2. The accountant will find it. |
| "I'll add the index if it gets slow." | It gets slow at 2 a.m., on the parent-table delete. |
| "One migration is simpler." | Simpler to write; impossible to roll back half-way. |
| "We don't have production-sized data to test with." | Generate it. `INSERT … SELECT generate_series` takes one minute. |

## Red flags

- `Float`/`Double` on anything you can pay with.
- `DateTime` without a time zone story.
- A FK declared with no index on the child column.
- `NOT NULL` added to an existing populated table in one migration.
- `deleteMany`/`updateMany` without a `where`.

## Example

Ticket: "record which warehouse a lot arrived at". Wrong: `Lot.warehouse String?`.
Right: migration 1 adds `Lot.warehouseId BIGINT NULL REFERENCES Warehouse(id) ON
DELETE RESTRICT` + `CREATE INDEX CONCURRENTLY lot_warehouse_id_idx`; backfill
from the receiving log in 10k-row batches; migration 2 sets `NOT NULL`.

## Reviewer lens

- For each new column: type, nullability, default — could a wrong value be stored?
- For each new FK: is there an index on the referencing column? What is `ON DELETE`?
- Is any `NOT NULL`, unique or type change applied to a populated table in one step?
- Was the migration run against data? Where is the timing?

## Sources

wshobson/agents `database-design:postgresql` (identity, FK indexing, NUMERIC,
TIMESTAMPTZ) · affaan-m/ECC `database-migrations` (expand/contract, immutable
migrations, production-size testing) · PostgreSQL docs *Don't Do This* wiki.
