---
name: dev-query-performance
description: "Use when a page or endpoint is slow, when a list grows, when an ORM sits between the code and the database, and when a query is written inside a loop. Also when pagination is added, when a cache is introduced, and when a fix is 'add an index' before anyone has looked at a plan."
role: dev
loads: T2
applies: label:performance, label:slow, path:prisma/, term:slow, term:query, term:pagination, term:cache, term:orm
---


# Query performance — measure the plan, not the wall clock

## Identity

You never guess at slowness. You reproduce it with realistic data, read the plan the
database actually chose, and change one thing at a time. You know most "slow endpoint"
tickets are not slow queries at all — they are many fast queries, and the fix is to
stop issuing them. You add a cache only after the query is honest, because a cache
over a bad query hides the bug and adds an invalidation bug.

## When this applies

- An endpoint, page or report is slow, or gets slower as data grows.
- A query is written inside a loop, or an ORM relation is accessed per item.
- A list becomes paginated, or an existing pagination reaches deep pages.
- A cache, a materialized view or a denormalized column is proposed.
- Someone proposes "add an index" as the fix.

## Decide

| Question | Choose | Because |
|---|---|---|
| First move on a slow path | Count the **queries** before timing them | The classic cause is N+1: one query for the list, then one per row |
| Fixing N+1 | Eager-load, join, or batch by id (`WHERE id IN (…)`) — one round trip | Latency per query dominates; 200 fast queries beat one slow query only in a benchmark |
| Second move | Read `EXPLAIN (ANALYZE, BUFFERS)` on real data volume | Estimated cost and actual rows diverging is the signal; a plan on ten rows tells you nothing |
| Index choice | Index what `WHERE`, `JOIN` and `ORDER BY` actually use; composite order follows selectivity | An index the planner does not choose costs writes and buys nothing |
| Before adding an index | Check the query shape first — a function on the column, a leading wildcard or a type mismatch disables the index | Otherwise you add an index and the plan is unchanged |
| Pagination | **Keyset** (`WHERE id > ?`) for anything deep or infinite-scroll; offset only for small, bounded lists | `OFFSET 100000` reads and discards 100,000 rows every time |
| `SELECT *` | Name the columns, especially with large text or JSON | Wide rows defeat index-only scans and inflate every transfer |
| Connection pool size | Small and bounded, sized to database cores, not to app concurrency | A pool larger than the database can serve turns queueing into timeouts |
| Introducing a cache | Only after the query is correct and measured; decide the **invalidation** in the same change | An un-invalidated cache is a stale-data bug with better latency |
| Cache key | Every input that changes the result, tenant and permission included | A key missing the tenant serves one customer another's data |

## Rules

- **Count queries per request before you optimize anything.** *Otherwise:* you tune
  the one query the profiler showed and leave the ninety-nine it hid.
- **Reproduce with production-sized data.** *Otherwise:* the plan you optimized is
  not the plan production runs.
- **Read the plan before touching the schema.** *Otherwise:* "add an index" becomes a
  write cost with no read benefit.
- **Change one thing, re-measure, record both numbers in the PR.** *Otherwise:*
  nobody can tell which change helped, or undo the one that did not.
- **Never leave a query inside a loop.** *Otherwise:* the endpoint is fine in staging
  and quadratic in production.
- **Use keyset pagination for anything that can go deep.** *Otherwise:* page 500 is a
  full scan and page 1 hides it.
- **Decide invalidation when you add the cache, not after.** *Otherwise:* the first
  incident is someone seeing deleted data.
- **Put the tenant and the viewer's permissions in every cache key.** *Otherwise:*
  the cache becomes an access-control bug.

## Rationalizations

| Excuse | Reality |
|---|---|
| "The ORM will optimize it." | The ORM issues what you asked for, once per item, exactly as written. |
| "Just add an index." | An index the planner rejects costs writes and changes nothing. Read the plan. |
| "We'll cache it." | Now you have a slow query and an invalidation problem. |
| "Offset pagination is fine." | It is, until page 200, and then it is a full scan on every request. |

## Red flags

- An `await` inside a `for` loop over rows; a relation accessed per item in a template.
- `OFFSET` with a large page number, or a paginator that always runs `COUNT(*)`.
- `SELECT *` on a table with a JSON or text column.
- An index added in the same commit as the report, with no plan attached.
- A cache with no documented invalidation, or a key with no tenant in it.
- A connection pool sized to the number of app instances.

## Example

Ticket: "the orders page takes 8 seconds". Wrong: add an index on `orders.created_at`
and cache for five minutes — now it is fast, sometimes wrong, and the cause unknown.
Right: count the queries, find 1 + 200 (customer fetched per order), batch them into
one `WHERE id IN (…)`, re-measure — 8s to 400ms with no schema change. Then
`EXPLAIN (ANALYZE)` the remaining query on real volume, and add an index only if the
plan justifies it. Switch to keyset pagination and put both numbers in the PR.

## Reviewer lens

- How many queries does this request issue? Who counted?
- Is any query inside a loop, or any relation accessed per row?
- For a new index: where is the `EXPLAIN` before and after?
- Was the measurement taken on production-sized data?
- Pagination: keyset or offset, and how deep can it go?
- Any `SELECT *` where the row is wide?
- New cache: what invalidates it, and does the key include tenant and permissions?
- Pool size: what is it sized against?

## Sources

Field study of `nilbuild/developer-roadmap` @ `74a645b`. Its `backend` roadmap names
the N+1 Problem, Database Indexes and Profiling Performance; `postgresql-dba` adds
`EXPLAIN`, the query planner, MVCC and vacuum. All are defined, none decidable — and
`n+1` appeared in **zero** competencies in this doctrine before this file. Complements
`dev-data-modeling` (which owns the schema, types and constraints) and `dev-api-design`
(which owns the list contract, not what happens behind it).
