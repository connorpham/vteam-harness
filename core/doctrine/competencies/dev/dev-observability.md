---
name: dev-observability
description: "Use when a change ships something you will have to debug from the outside — a new endpoint, worker, integration or migration — and when the only answer to 'is it working?' is a screenshot. Also when an incident is being investigated and the logs do not say enough, and when an alert fires that nobody can act on."
role: dev
loads: T3
applies: label:incident, label:observability, term:metric, term:tracing, term:alert, term:monitoring
---


# Observability — build what you will need at 3 a.m., before 3 a.m.

## Identity

You ship nothing you could not diagnose from the outside. Before writing the happy
path you decide what a stranger will need to answer three questions: is it working,
which request failed, and why. You know logs, metrics and traces answer different
questions and none substitutes for another, and that an alert nobody can act on is
worse than no alert because it trains the team to ignore the channel.

## When this applies

- A new endpoint, worker, scheduled job or third-party integration ships.
- A migration or a risky change goes out.
- An incident is investigated and the evidence is thin, or an alert fires on a cause rather than a symptom.
- The only answer to "is this working in production?" is someone checking manually.

## Decide

| Question | Choose | Because |
|---|---|---|
| Which pillar answers this | **Metric** = is it healthy and how much; **trace** = where the time went in this request; **log** = what happened in this one case | Asking a log for a rate, or a metric for a cause, is the usual dead end |
| Log format | Structured (key–value or JSON), one event per line | `grep` on prose stops working at the scale where you need it |
| What every log line carries | A **correlation / trace id**, the tenant, the actor, the operation | Without a shared id you cannot follow one request across services |
| What never goes in a log | Secrets, tokens, full payloads, personal data beyond an id | Logs are copied to more places than any database, and kept longer |
| Metric shape | Counters and histograms with **low-cardinality** labels; never a label per user or request id | High-cardinality labels are how monitoring bills and outages happen |
| Where to add a trace span | Every outbound call and every queue hop | The gap between spans is where the latency actually lives |
| What to alert on | **Symptoms users feel** — error rate, latency, queue depth, staleness — not CPU | Cause-based alerts fire when nothing is wrong and stay quiet when it is |
| Every alert | A stated target, a duration so a blip does not page, and the first action | An alert with no duration is a pager attached to noise; one with no action trains the team to ignore the channel |
| Verifying a release | A metric or check that would have caught the last incident of this kind | "It deployed" is not "it works" |

## Rules

- **Decide the three questions before writing the feature: is it working, which
  request failed, why.** *Otherwise:* you add logging during the incident, from a
  laptop, under pressure.
- **Generate a correlation id at the edge and propagate it everywhere, including
  into queued jobs.** *Otherwise:* the worker's error cannot be tied to the request
  that caused it.
- **Log structured events, not sentences.** *Otherwise:* the field you need is inside
  a string and nothing can aggregate it.
- **Never log a secret, a token or a full payload — log ids.** *Otherwise:* the breach
  is in the log aggregator, which more people can read than the database.
- **Keep metric labels low-cardinality and finite.** *Otherwise:* one label per user
  takes down the metrics backend before the feature takes down anything.
- **Span every outbound call and every queue hop.** *Otherwise:* the trace shows your
  service as fast and the user as waiting.
- **Alert on symptoms, with a duration, a stated target and the first action.**
  *Otherwise:* the team mutes the channel and the real page arrives there.
- **Add the check that would have caught the last incident of this kind.**
  *Otherwise:* the same failure ships twice and is found the same way twice.

## Rationalizations

| Excuse | Reality |
|---|---|
| "We have logs." | You have text. Without ids and structure you cannot follow one request or count anything. |
| "We'll add metrics if it becomes a problem." | You will add them *during* the problem, blind, and the history will be missing. |
| "Alert on CPU — it catches everything." | It catches nothing users feel, and it fires during every deploy. |
| "The trace id is in the gateway logs." | Then it is not in the worker's, which is where the failure is. |

## Red flags

- A correlation id that stops at the queue boundary; a token or full body in a log.
- A metric labelled with a user id, an email or a request id.
- An alert on CPU, memory or disk with no user-facing symptom behind it.
- An alert with no duration, target or first action; a new integration with no span.

## Example

Ticket: "add a payment webhook". Wrong: `console.log('webhook received')` and ship —
when a customer says the order never arrived there is nothing to look at. Right: a
correlation id from the provider's event id; one structured event per outcome
(`received`, `duplicate`, `verified`, `failed`) carrying that id, the tenant and the
event type but never the payload; a counter per outcome and a duration histogram
labelled only by outcome; a span around the signature check and the enqueue; and an
alert on `failed` rate over five minutes naming "provider signature or our clock" as
the likely cause and "check the DLQ, then the provider dashboard" as the first action.

## Reviewer lens

- Can a stranger answer "is it working" from a dashboard, without asking anyone?
- Is there a correlation id, and does it survive the queue boundary?
- Do any logs carry secrets, tokens or full payloads?
- Are metric labels low-cardinality and finite?
- Which outbound calls have no span?
- Does each new alert name a symptom, a duration, a target and a first action?
- What check would have caught the last incident of this kind, and is it here?

## Sources

Field study of `nilbuild/developer-roadmap` @ `74a645b`. Its `backend` roadmap lists
Observability, Instrumentation, Telemetry and Monitoring as four topics and defines each
in a paragraph, with no decision in any. Measured gap here before this file: `tracing`
and `metric` appeared in **zero** competencies while `log` appeared in fifteen — the
easy pillar was everywhere, the two answering "how much" and "where" were absent.
Complements `dev-error-handling`, which decides where to log.
