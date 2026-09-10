<!-- Reference detail for dev-security-basics. Moved out of the competency body so the
     lane spends its context on the ticket, not on the rulebook. The competency is
     the METHOD; this is the argument, the smell list and the worked case. -->

# dev-security-basics — rationalizations, red flags, example

> `/dev` opens this at the review step, and whenever an excuse for skipping a
> rule appears. Read the row that fits the change in front of you; never paste
> the whole file into a report.

## Rationalizations

| Excuse | Reality |
|---|---|
| "The UI doesn't show that button to non-admins." | The API does not know about the UI. |
| "IDs are UUIDs, nobody can guess them." | They leak in URLs, logs and referers; ownership still needs a check. |
| "It's an internal tool." | Internal tools have the fewest reviews and the most privileges. |
| "The ORM protects against injection." | Only when you use its query API — `$queryRaw` with a template string does not. |

## Red flags

- `params.id` used in a query without an owner/tenant condition.
- A route with no auth middleware, or `authorize` applied to "most" routes.
- String interpolation inside SQL, shell, or HTML.
- A secret-looking literal in code or a test fixture.
- `catch` returning the raw error message to the client.

## Example

```ts
// BAD: any authenticated user reads any order
const order = await db.order.findUnique({ where: { id: params.id } });
// GOOD: scoped to the caller; 404 hides existence
const order = await db.order.findFirst({ where: { id: params.id, customerId: user.id } });
if (!order) return problem(404);
```
