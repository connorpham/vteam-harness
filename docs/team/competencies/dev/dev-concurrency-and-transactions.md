---
name: dev-concurrency-and-transactions
description: "Use when two requests can touch the same row — balances, stock, seats, invites, slugs, counters — and when a write depends on a value the code read a moment earlier. Also when a transaction is opened, when an isolation level is chosen or left to a default, and when a bug report says a duplicate or a wrong total appeared that 'could not happen'."
role: dev
loads: T3
applies: label:data, label:payment, label:concurrency, path:prisma/, term:transaction, term:lock, term:race, term:concurrent
---


# Concurrency and transactions — the anomaly the default level still allows

## Identity

You assume two of every request arrive at once, because in production they do. So you
never treat "read, decide, write" as safe just because it is wrapped in a transaction —
you name the isolation level, name the anomaly it still permits, and close that gap
with a constraint, a lock or a retry. You know the database is the only participant
that can actually serialize anything, and that a check in application code is a
suggestion.

## When this applies

- A write path reads a value, decides on it, then writes (balance, stock, quota).
- Uniqueness matters: slug, invite code, email, idempotency key.
- A transaction is opened, or an isolation level is chosen or left to default.
- Two rows must change together, or a counter is incremented.
- A read replica is queried, or a bug says a duplicate appeared that "cannot happen".

## Decide

| Question | Choose | Because |
|---|---|---|
| Isolation level | Name it explicitly. PostgreSQL defaults to **Read Committed**, which permits nonrepeatable reads, phantom reads and serialization anomalies | Each command gets a **new snapshot**, so two `SELECT`s in one transaction can disagree |
| Read-decide-write on one row | `SELECT … FOR UPDATE` (pessimistic) **or** a version column with a guarded `UPDATE … WHERE version = ?` (optimistic) | Read Committed permits lost updates in complex operations; the transaction alone does not stop it |
| Which of the two | Optimistic when contention is rare (no lock across think time); pessimistic when it is common or the work is short (retry storms cost more than the lock) | Pick on measured contention, not taste |
| Invariant across rows or ranges | **Repeatable Read** or **Serializable**, and be ready to retry | PostgreSQL's Repeatable Read is stronger than the SQL standard: it prevents phantoms too, leaving only serialization anomalies |
| Using Repeatable Read or Serializable | Catch `could not serialize access …` and **retry the whole transaction from the beginning** | The docs require it: "Applications using this level must be prepared to retry transactions due to serialization failures" — and only *updating* transactions can hit it |
| Enforcing uniqueness | A **unique constraint**, and handle the violation | Check-then-insert has a window; two concurrent requests both pass the check |
| Transaction scope | Open late, commit early; never span an HTTP call, a queue publish or user think time | A transaction holds locks and a connection for its whole life |
| Lock ordering across tables | One documented order, everywhere | Two paths taking A→B and B→A deadlock under load, not in tests |
| Reading from a replica | Only where staleness is acceptable, and say how stale | Asynchronous replication means read-your-own-write can fail |

## Rules

- **Name the isolation level in the code or the config, never inherit it silently.**
  *Otherwise:* you have shipped Read Committed's anomalies without deciding to.
- **For every read-decide-write path, write down which anomaly could break it and
  what closes the gap.** *Otherwise:* the review cannot tell a safe path from a lucky one.
- **Let the database enforce uniqueness and handle the violation as a normal
  outcome.** *Otherwise:* a duplicate appears under load and the log says nothing.
- **Retry serialization failures with backoff, and cap the attempts.** *Otherwise:*
  a hot row turns into a retry storm that looks like an outage.
- **Make retried transactions idempotent, or key them.** *Otherwise:* the retry that
  saves you charges the customer twice.
- **Keep external calls out of transactions.** *Otherwise:* a slow third party holds
  a row lock and the pool drains.
- **Take locks in one order and document it.** *Otherwise:* the deadlock arrives at
  peak traffic and is unreproducible.
- **Write a test that runs the two paths concurrently.** *Otherwise:* the only test
  is production.

## Rationalizations

| Excuse | Reality |
|---|---|
| "It's in a transaction, so it's atomic." | Atomic is not isolated. Read Committed still permits lost updates. |
| "We check before inserting." | Two requests both pass the check. Only the constraint decides. |
| "Serializable is too slow." | Measure it. PostgreSQL's predicate locks do not block; they cause retries. |
| "It's never happened." | It happens at concurrency you have not reached yet, and it corrupts quietly. |
| "The ORM handles it." | The ORM picks a default you did not read. Print the level and look. |

## Red flags

- `findFirst` / `SELECT` followed by `create` / `INSERT` with no unique constraint behind it.
- A counter read in application code before `value = value + 1`.
- A transaction wrapping an HTTP request, a queue publish or a file upload.
- `Serializable` used with no retry handler anywhere.
- Two code paths locking the same two tables in different orders.
- A read-after-write served from a replica.

## Example

Ticket: "let a user redeem an invite code once". Wrong: `SELECT` the code, check
`used === false`, `UPDATE used = true`, insert the membership — inside one Read
Committed transaction. Two clicks redeem twice. Right: a unique constraint on
`(code)` for the redemption row so the second insert fails, **or** `UPDATE invites SET
used = true WHERE code = ? AND used = false` and treat **zero rows affected** as
"already redeemed" — the decision moves into the database, where it can be serialized.
Add a concurrent test that fires both requests at once.

## Reviewer lens

- Which isolation level does this path run at, and who chose it?
- For each read-decide-write: which anomaly could break it, and what closes the gap?
- Is uniqueness enforced by a constraint, or by a check in code?
- Any `Serializable` / `Repeatable Read`: where is the retry, and is it capped?
- Is the retried operation idempotent or keyed?
- Does any transaction span a network call or user think time?
- Do two paths lock the same tables in different orders?
- Is there a test that runs the conflicting paths concurrently?

## Sources

PostgreSQL documentation, *Transaction Isolation* — the anomaly table, the Read
Committed per-command snapshot, the stronger-than-standard Repeatable Read, the
`could not serialize access` errors and the verbatim requirement that applications
retry. Field study of `nilbuild/developer-roadmap` @ `74a645b`: its `backend` roadmap
names Transactions, ACID and Failure Modes but defines them without a single
decidable rule — this file supplies the decisions. Complements `dev-data-modeling`
(schema shape) and `dev-error-handling` (whether to retry at all).
