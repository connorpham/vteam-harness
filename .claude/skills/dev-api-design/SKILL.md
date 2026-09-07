---
name: dev-api-design
description: "Use when adding or changing an HTTP endpoint, server action, RPC, webhook or public function contract — its URL, verbs, payload, errors, pagination or auth — and when a client complains that the API 'sometimes' behaves differently."
---


# API design — a contract a stranger can use without reading your code

## Identity

You design endpoints for the client you will never meet. Every response shape
is stable, every error is machine-readable, every write can be retried safely,
and every list can be paged without duplicates. You know that an API is the
hardest thing to change after it ships, so you spend the design minutes now.

## When this applies

- A route, handler, server action, GraphQL field, or webhook is created or changed.
- A response or request type changes shape.
- A client needs a list, a search, a bulk operation, or a long-running job.
- Authentication or authorization is involved in any way — that is always.

## Decide

| Question | Choose | Because |
|---|---|---|
| Style | Match what the codebase already has (REST, tRPC, server actions…) | Consistency beats theoretical fit; one style per service |
| Resource naming | Plural nouns, hierarchy only when ownership is real (`/orders/{id}/items`) | Verbs in URLs multiply; hierarchy beyond two levels breaks |
| Create/update semantics | `POST` create, `PUT` full replace, `PATCH` partial; all idempotent except plain `POST` | Clients retry; a retried `POST` must not double-charge |
| Non-idempotent writes (payment, order) | Require an `Idempotency-Key`; store result per key | Network retries are the norm, not the exception |
| Errors | One envelope: `type`, `title`, `status`, `detail`, `instance`, field errors — RFC 9457 shape or the repo's existing one | Clients branch on a code, never on a message string |
| Lists | Cursor pagination with a stable secondary sort; `limit` capped | Offset pages skip/duplicate under concurrent inserts |
| Breaking change | New version or new field with the old kept; never mutate an existing field's meaning | The client you cannot see is already parsing it |
| Validation | At the edge, whole payload, before any side effect; unknown fields rejected on writes | Mass assignment starts with "extra fields are ignored" |
| Authorization | Per request **and per resource** (ownership/tenant check), not just "logged in" | IDOR is the most common real-world API bug |

## Rules

- **Read the existing endpoints first**; copy their conventions exactly (naming,
  envelope, status codes, auth middleware). *Otherwise:* the API has two dialects
  and every client learns both.
- **Status codes mean what HTTP says**: 200/201/204 success, 400 malformed, 401
  unauthenticated, 403 forbidden, 404 not found *or not yours*, 409 conflict,
  422 semantically invalid, 429 throttled, 5xx ours. *Otherwise:* clients cannot
  tell "retry" from "give up".
- **Never leak internals**: no stack traces, SQL, or model names in responses;
  404 for resources the caller may not know exist. *Otherwise:* the error body
  is the attacker's site map.
- **Every write validates then acts, in a transaction where multiple rows
  change.** *Otherwise:* a half-applied request is a support ticket with no
  clean repro.
- **Timeouts and limits on everything inbound**: body size, page size, string
  length, array length. *Otherwise:* one client can take the service down by
  accident.
- **Document the contract where the code lives** (schema/type/OpenAPI generated
  from the source of truth, never hand-maintained separately). *Otherwise:* the
  docs describe last quarter's API.

## Rationalizations

| Excuse | Reality |
|---|---|
| "Clients won't retry this." | Every mobile network retries. Idempotency is a day-one requirement. |
| "Offset pagination is simpler." | Until the list changes under the client and row 20 appears twice. |
| "It's an internal API." | Internal APIs live longest and get the fewest reviews. |
| "Logged-in is enough authorization." | Logged-in as *whom*, for *whose* order? Check ownership. |

## Red flags

- A URL with a verb in it (`/getOrders`, `/order/cancel`).
- An error returned as `{ message: "..." }` only.
- A list endpoint with no `limit` cap.
- A `POST` that charges, sends or creates with no idempotency story.
- A handler that looks up `params.id` and never compares an owner.

## Example

`POST /orders` with header `Idempotency-Key: 7f3…` → 201 with `Location`; the
same key again → 200 with the same body, no second order. `GET /orders?cursor=…
&limit=50` → `{ items, nextCursor }`, sorted by `(createdAt, id)`. Any failure →
`{ "type": "…/insufficient-balance", "status": 422, "detail": "…", "errors":
[{ "field": "amount", "code": "exceeds_balance" }] }`.

## Reviewer lens

- Send the same write twice; what happens? Where is the idempotency key stored?
- Request another user's resource id; 403/404 or the data?
- Add an unknown field to a write; rejected or silently stored?
- Page through a changing list; any duplicate or skipped row?

## Sources

Zalando RESTful API Guidelines · Microsoft REST API Guidelines · RFC 9457
(Problem Details) · OWASP REST Security & Mass Assignment cheat sheets ·
wshobson/agents `api-design-principles`.
