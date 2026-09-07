---
name: dev-stack-nextjs-prisma
description: "Use when the project runs Next.js (App Router) with Prisma — when writing a route handler, server action, server/client component, Prisma query, transaction or migration, and when a page is slow, a query returns stale data, or a bulk update 'lost' rows."
role: dev
loads: T3
applies: profile:nextjs-prisma
---

# Next.js + Prisma — the idioms and the traps of this stack

## Identity

You know where the server/client boundary is and keep secrets, database access
and authorization on the server side of it. You use Prisma through its typed
query API, in transactions where several rows change, with the indexes the
schema declares, and you deploy migrations with `migrate deploy` — never
`migrate dev` — in CI. You have been bitten by `updateMany` returning a count
and by an N+1 in a server component; you check for both by reflex.

## When this applies

- Any file under `app/`, `src/app/`, `prisma/`, or importing `@prisma/client`.
- A server action, route handler, layout, or page fetching data.
- A Prisma `create/update/delete/…Many`, `$transaction`, or raw query.
- A migration, a seed, or a `schema.prisma` change.

## Decide

| Question | Choose | Because |
|---|---|---|
| Server or client component? | Server by default; `"use client"` only for interactivity (state, effects, browser APIs) | Client bundles grow and leak; data belongs on the server |
| Data fetching | In the server component / route handler with Prisma directly; no internal `fetch` to your own API from the server | A server calling its own HTTP API doubles latency and loses types |
| Mutations | Server actions or route handlers that **re-authenticate and authorize**; validate with a schema (zod) at the top | The client is untrusted even when it is your own React |
| Several rows change together | `prisma.$transaction(async (tx) => …)` and use **`tx`** inside, never the outer client | The outer client escapes the transaction silently |
| Bulk update/delete | Capture ids first → `updateMany({ where: { id: { in } } })` → re-fetch by ids; **always a `where`** | `updateMany` returns `{ count }`, not rows; `@updatedAt` is not touched by bulk writes |
| Relations in a list | `include`/`select` in the list query, or a `findMany … where: { parentId: { in } }` batch | A query per row in `.map` is the classic N+1 |
| Large lists | Cursor pagination on `(createdAt, id)` with `take` capped | `skip` degrades linearly and duplicates under inserts |
| Soft delete | A `deletedAt` field with a default `where` at the repository seam; `findFirst` not `findUnique` when filtering it | `findUnique` cannot filter on non-unique fields |
| Raw SQL | `$queryRaw` with tagged-template parameters only; never `$queryRawUnsafe` with input | Interpolation is injection |
| Migrations in CI/prod | `prisma migrate deploy`; shadow DB only locally with `migrate dev` | `migrate dev` resets or drifts a production database |
| Serverless | One `PrismaClient` singleton per process; `connection_limit` sized to the platform | Each cold start otherwise opens a new pool |

## Rules

- **Auth on the server, per action.** Read the session in the server action /
  handler; check ownership in the query (`where: { id, ownerId }`).
  *Otherwise:* the "Delete" button hidden in the UI is one `fetch` away.
- **Validate the whole input with a schema at the top of the action.**
  *Otherwise:* a form field renamed on the client writes `undefined` to the DB.
- **`select` what the page needs.** *Otherwise:* the password hash rides along
  into a server component prop and out to the client.
- **Indexes match `where`/`orderBy`; every relation field is indexed** (`@@index`).
  *Otherwise:* the first thousand rows are fine and the ten-thousandth page
  times out.
- **Revalidate what you changed** (`revalidatePath`/`revalidateTag`) after a
  mutation. *Otherwise:* the user saves and sees the old value.
- **External calls stay outside the transaction.** *Otherwise:* a slow payment
  API holds a DB transaction open past its timeout.
- **Environment: secrets only in server code; `NEXT_PUBLIC_` is public.**
  *Otherwise:* the key is in the bundle.

## Rationalizations

| Excuse | Reality |
|---|---|
| "The component needs a click handler, I'll make the whole page client." | Split: server page passes data; a small client island handles the click. |
| "I'll fetch from `/api/...` inside the server component, it's cleaner." | It is a network hop to yourself, without types, with double auth. |
| "`migrate dev` worked on staging." | Until it prompts to reset the database in a non-interactive CI. |
| "Prisma is typed, I don't need input validation." | Types check *your* code; the request body comes from anywhere. |

## Red flags

- `"use client"` at the top of a page or layout.
- `await prisma.x.findUnique` inside a `.map`.
- `prisma.` (outer client) inside a `$transaction` callback.
- `updateMany`/`deleteMany` without `where`, or its result used as rows.
- `$queryRawUnsafe`, or `process.env.SECRET` in a client component.
- `prisma migrate dev` in a CI script.

## Example

```ts
// app/orders/[id]/actions.ts
"use server";
export async function cancelOrder(input: unknown) {
  const { id } = CancelSchema.parse(input);                 // validate first
  const user = await requireUser();                          // authenticate
  const result = await prisma.$transaction(async (tx) => {
    const order = await tx.order.findFirst({ where: { id, customerId: user.id, status: "OPEN" } });
    if (!order) return { ok: false as const, error: "NOT_CANCELLABLE" };
    await tx.order.update({ where: { id }, data: { status: "CANCELLED", cancelledAt: new Date() } });
    return { ok: true as const };
  });
  revalidatePath(`/orders/${id}`);
  return result;
}
```

## Reviewer lens

- For each server action/handler: where is `requireUser()` and where is the owner condition in the query?
- Any Prisma call inside a loop? Any outer `prisma` inside `$transaction`?
- Which fields reach the client — is `select` used on anything sensitive?
- Does the migration script say `deploy`?

## Sources

affaan-m/ECC `prisma-patterns` (transactions, updateMany, cursor pagination,
soft delete, serverless pooling) · github/awesome-copilot `nextjs` instructions ·
alan2207/bulletproof-react (feature folders, unidirectional imports) · Prisma
and Next.js official docs (server actions, revalidation, `migrate deploy`).
