---
name: dev-error-handling
description: "Use when writing anything that can fail — I/O, network, database, parsing, user input — when deciding whether to throw, return, retry, log or swallow, and when a production error is unhelpful ('something went wrong') or duplicated across logs."
role: dev
loads: T3
applies: always
---

# Error handling — fail fast, fail loud, fail once

## Identity

You separate what *can* go wrong (operational: network, disk, bad input) from
what *must not* (programmer errors: null where a value is guaranteed, an
impossible enum). The first you handle at the boundary with a good message;
the second you let crash loudly so it gets fixed. You never write `catch {}`
and you never log an error twice.

## When this applies

- Every call that touches I/O, another service, the database, or user input.
- Any `try`/`catch`, `.catch`, `Result`, or error return you write.
- A retry, timeout, fallback or "default value on failure".
- Reading a log or error report that does not say what happened.

## Decide

| Situation | Do | Because |
|---|---|---|
| Expected failure (validation, not found, conflict) | Return it as data (typed result / domain error) | Callers must handle it; a throw is easy to forget |
| Unexpected failure (bug, invariant broken) | Throw/raise; let the top-level handler log and crash the request | Recovering from a bug hides it |
| Third-party call fails | Wrap in a domain error with context; keep the cause | The caller needs "payment declined", not `ECONNRESET` |
| Retry? | Only idempotent operations, bounded attempts, backoff with jitter | Unbounded retries turn an outage into a self-DDoS |
| Where to log | Once, at the boundary that handles it, with correlation id | Log-and-rethrow doubles every error in the aggregator |
| User-facing message | From the spec verbatim when it exists; never the internal message | Internals leak; spec messages are the contract |
| Partial failure in a batch | Report per item; never "some failed" | The operator must know which |

## Rules

- **Validate at the edge, trust inside.** Parse the request into a typed value
  once; inner code assumes validity. *Otherwise:* every function defends against
  every input and none of them agree.
- **Fail fast.** Check preconditions first; do no side effect before all inputs
  are known good. *Otherwise:* a half-applied operation is the hardest bug class.
- **Preserve the cause.** Wrap with context (`what`, `which id`), keep the
  original as `cause`. *Otherwise:* the stack trace points at your wrapper.
- **No empty catch, no catch-all that continues.** `catch (e) {}` and
  `except Exception: pass` are prohibited. *Otherwise:* the failure surfaces
  three layers away as corrupted data.
- **Cleanup is unconditional**: `finally`, `defer`, context managers, `using`.
  *Otherwise:* the connection pool leaks one handle per failure.
- **Messages say what happened and what to do**, with identifiers: "Order 4711:
  payment declined by provider (code 51); no retry" — not "error processing
  order". *Otherwise:* the on-call engineer opens a debugger for a known case.
- **Timeouts on every outbound call.** *Otherwise:* one slow dependency holds
  every worker.

## Reviewer lens

- Find every `catch`; what does each one do with the error? Any that swallow?
- Trace one failure path end to end: how many times is it logged?
- Is any non-idempotent operation retried?
- Do outbound calls have timeouts?

## Sources

nodebestpractices §2 Error Handling (operational vs programmer errors, central
handler, no swallow) · wshobson/agents `error-handling-patterns` (exceptions vs
Result, cleanup, pitfalls) · OWASP Error Handling & Logging cheat sheets.

Rationalizations, red flags and a worked example live in `reference/dev-error-handling.md` — opened when needed, never loaded by default.
