---
name: dev-async-work
description: "Use when work leaves the request — a queue, a worker, a scheduled job, a webhook you send or receive, an email, a report, a third-party call that can be slow. Also when a dependency starts failing and the question is what your system does about it, and when a job has run twice and someone was charged twice."
role: dev
loads: T3
applies: label:queue, label:jobs, label:webhook, term:queue, term:worker, term:cron, term:webhook, term:retry, term:idempotent
---


# Async work — at-least-once is the default, so idempotency is not optional

## Identity

You treat every queue, scheduler and webhook as a machine that will deliver the same
message twice, out of order, and at the worst possible moment. So you never ask "will
this run twice" — you make running twice harmless, and you decide in advance what the
system does when the thing it depends on is down. A job with no retry policy, no
dead-letter and no idempotency key is not asynchronous; it is a coin toss with a delay.

## When this applies

- Work moves out of the request: queue, worker, scheduled job, batch.
- A webhook is sent or received; an email or notification is dispatched.
- A third-party call can be slow, rate-limited or down.
- A job is added to a scheduler, or two schedulers might run the same job.
- A dependency starts failing and the blast radius is the question.

## Decide

| Question | Choose | Because |
|---|---|---|
| Delivery guarantee to assume | **At-least-once**, always | Exactly-once across a network is a marketing claim; the broker retries on ambiguous acks |
| Making a handler safe to repeat | An **idempotency key** the handler stores, unique-constrained, checked before the effect | The key turns the second delivery into a no-op the database enforces |
| What goes in the message | An **id and an intent**, not a snapshot of state | Stale payloads apply yesterday's decision to today's row |
| Retry policy | Bounded attempts, **exponential backoff with jitter** | Fixed-interval retries from many workers re-synchronize into a thundering herd |
| What to retry | Transient only — timeouts, 5xx, connection resets | Retrying a 400 burns the queue and the log |
| After the last attempt | A **dead-letter queue** with the payload and the reason, and an alert | A silently dropped job is a support ticket you will not connect to this cause |
| Ordering | Assume none; if order matters, partition by key rather than serialize everything | Global ordering removes the parallelism you moved the work for |
| A dependency is failing | **Circuit breaker** — closed, open, half-open — plus a timeout on every call | Without a breaker, every worker queues behind the same dead service |
| Protecting yourself from load | **Throttle** inbound (rate limit) and apply **backpressure** upstream | A queue that accepts faster than it drains converts a spike into an outage later |
| Scheduled jobs | One owner (a leader or a lock), and idempotent by design | Two instances of the same cron is the normal failure, not the exotic one |

## Rules

- **Give every handler an idempotency key backed by a unique constraint.**
  *Otherwise:* the retry that saves the job charges the customer twice.
- **Send ids, not state, and re-read inside the handler.** *Otherwise:* a message
  delayed five minutes overwrites a newer value.
- **Bound every retry and add jitter.** *Otherwise:* a downstream blip becomes a
  self-inflicted denial of service.
- **Set a timeout on every outbound call, and a total budget for the handler.**
  *Otherwise:* a hung socket holds a worker forever and the queue grows silently.
- **Route exhausted jobs to a dead-letter queue and alert on its depth.**
  *Otherwise:* failures are invisible until a customer reports them.
- **Verify webhook signatures and make the receiver idempotent on the provider's
  event id.** *Otherwise:* anyone can post you an order, twice.
- **Return 2xx fast on inbound webhooks and do the work asynchronously.**
  *Otherwise:* the provider times out and retries, multiplying the work.
- **Make scheduled jobs single-owner and safe to run twice.** *Otherwise:* a deploy
  overlap runs the billing job in duplicate.
- **Decide the degraded mode in the design, and name what gets shed first.**
  *Otherwise:* the system chooses for you, and it chooses the checkout.

## Rationalizations

| Excuse | Reality |
|---|---|
| "The broker guarantees exactly-once." | It guarantees at-least-once and hides the retry. Design for the duplicate. |
| "Retries fix transient errors." | Unbounded retries manufacture the outage they were meant to survive. |
| "We'll add the dead-letter queue later." | Until then, every permanent failure is deleted without a trace. |
| "Two crons can't both fire." | During a rolling deploy, they do. |

## Red flags

- A handler with no idempotency key, or a key with no unique constraint.
- A message carrying a full entity snapshot instead of an id.
- Retries with a fixed interval, or with no cap.
- An outbound call with no timeout; a webhook receiver doing the work inline.
- No dead-letter queue, or one nobody alerts on.
- A cron job that is not safe to run twice.

## Example

Ticket: "email the invoice when payment succeeds". Wrong: send the email inline in the
payment webhook handler and return 200 at the end. A provider retry sends two emails; a
slow SMTP server makes the provider time out and retry, sending more. Right: verify the
signature, store the provider's event id under a unique constraint, return 200
immediately, enqueue a job carrying only the invoice id; the worker re-reads the
invoice, checks an `invoice_email_sent` key before sending, retries transient failures
with backoff and jitter up to five attempts, then dead-letters with the reason. Running
the whole thing twice sends one email.

## Reviewer lens

- What is this handler's idempotency key, and what constraint enforces it?
- Does the message carry an id, or a snapshot of state?
- What is the retry cap, the backoff, and is there jitter?
- Which failures are retried, and which are not?
- Where do exhausted jobs go, and who is alerted?
- Every outbound call: what is the timeout and the total handler budget?
- Inbound webhook: signature verified? 2xx returned before the work?
- Any scheduled job: single-owner? safe to run twice?
- What is the degraded mode, and what gets shed first?

## Sources

Field study of `nilbuild/developer-roadmap` @ `74a645b`. Its `backend` roadmap devotes
a whole "Mitigation Strategies" band to Graceful Degradation, Throttling,
Backpressure, Loadshifting and Circuit Breaker, and a Message Brokers section to Kafka
and RabbitMQ — all defined, none decidable. Measured gap in this doctrine before this
file: `background job`, `cron`, `rate limit` and `circuit breaker` appeared in **zero**
competencies. Complements `dev-error-handling`, which decides *whether* to retry, not
how a worker survives.
