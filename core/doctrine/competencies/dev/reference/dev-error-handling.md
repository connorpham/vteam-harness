<!-- Reference detail for dev-error-handling. Moved out of the competency body so the
     lane spends its context on the ticket, not on the rulebook. The competency is
     the METHOD; this is the argument, the smell list and the worked case. -->

# dev-error-handling — rationalizations, red flags, example

> `/dev` opens this at the review step, and whenever an excuse for skipping a
> rule appears. Read the row that fits the change in front of you; never paste
> the whole file into a report.

## Rationalizations

| Excuse | Reality |
|---|---|
| "I'll catch everything so the page doesn't crash." | The page shows stale data and the bug goes unreported for a quarter. |
| "Logging here too is harmless." | Triplicate errors bury the real one and inflate the bill. |
| "A default value is safer than throwing." | A silent default is a wrong answer delivered with confidence. |
| "Retries make it more reliable." | Retries of a non-idempotent write make it *more* wrong, faster. |

## Red flags

- `catch` block whose body is a comment, a `console.log`, or `return null`.
- An error message with no identifier in it.
- `try` wrapping fifty lines.
- A retry loop with no maximum.
- A user sees the words "undefined", "null", or a stack frame.

## Example

```ts
// edge: parse once, typed
const cmd = parseTopUp(req.body);            // throws ValidationError → 422 by the handler
// core: expected failure as data
const result = await wallet.topUp(cmd);      // Result<Receipt, InsufficientFunds | LimitExceeded>
if (!result.ok) return problem(422, result.error);
// unexpected: let it throw; the request handler logs ONCE with requestId and returns 500
```
