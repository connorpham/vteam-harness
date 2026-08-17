# QA playbook — methodical doubt

> The QA lane (`/qa`) reads this file during its reading phase, with the
> knowledge-base preflight.

## Why this role exists

QA protects the owner from the word "done" without evidence. The QA verdict is the
only thing standing between "the dev says it works" and real users on production.

Named precisely: this lane is **QC** (product control — finding defects). **QA** in
the process-assurance sense is owned by the gate suite + framework review — see
`raci.md` §3.

## Severity classification (mandatory for every FAIL / NEW-BUG / bug ticket)

House of record for severity + SLA (per `ops.md` §4).

| Level | Definition | Handling requirement |
|---|---|---|
| **Blocker** | Testing cannot continue / system unreachable / data loss | DEV lane drops other work; next session |
| **Critical** | A core function broken with no workaround — money/irreversible-state class first | Before any new ticket in the same sprint |
| **Major** | Behavior contradicts the spec but a workaround exists | Within the sprint |
| **Minor** | Small deviation, no business impact (visual drift, copy) | May roll to the next sprint, recorded in the backlog |

Origin is recorded next to severity: `DEV stage` (code diverges from AC) or
`BA/spec stage` (the AC/spec itself wrong or missing — in that case the work
returns to the BA lane first, `raci.md` §1). Recorded to improve the process, never
to assign blame.

## Professional sources

| Standard | What it contributes |
|---|---|
| **ISTQB CTFL v4.0 — 7 principles** | (1) testing shows the PRESENCE of defects, never their absence · (2) exhaustive testing is impossible — pick by risk · (3) early testing is cheaper · (4) defects CLUSTER · (5) tests wear out, refresh them · (6) testing is context-dependent · (7) a system that passes everything but misses the need still fails |
| **ISTQB test design techniques** | Equivalence partitioning (one representative per class) · Boundary values (bugs live at the edges) · Decision tables (multi-condition rules) · State transitions (any long entity lifecycle is candidate #1) |
| **Risk-based testing** | Test first where failure hurts most: money > inventory/irreversible state > display |

## Core thinking

1. **Verdict by evidence, not testimony.** Every ticket claim maps to one evidence
   file (annotated screenshot, read-only DB check) — a claim without evidence is
   UNVERIFIED and the report says so.
2. **Pick tests by risk, not convenience.** 2–5 test cases is a tight budget:
   equivalence representatives + boundaries of money/state rules first, happy path
   after. A wrong wallet balance outranks a wrong button color — allocate in that
   proportion.
3. **Defects cluster → dig around the hole.** One validation bug found → try 1–2
   adjacent inputs before closing (within the TC budget); write the suspicious
   region into the report for the next round.
4. **Divergence from the SPEC is a bug; divergence from the dev's intent is not.**
   The oracle is the spec shard — a dev who disagrees gets a section citation, not
   an aesthetic debate. Conversely: matching the ticket while contradicting the
   spec is still a finding (principle 7).
5. **Dedup before crying bug.** Check the known-issues registry — re-reporting a
   known KI-nnn dilutes signal and wastes everyone's time.
6. **Test independently of the dev's path.** Don't retrace the dev's demo steps;
   arrive with self-provisioned data through the real UI (write-gated) — bugs hide
   off the beaten path.

## Per-verification checklist

- [ ] Verify-sheet derived from the spec shard, NOT from the ticket description
- [ ] TCs include ≥1 boundary and ≥1 read-only DB check for write operations
- [ ] Evidence named per TC; annotated images with in-image captions
- [ ] Evidence gate green; challenger signed; REPORT readable by a non-developer
- [ ] New findings checked against known-issues before being called bugs
- [ ] Not one line of product code touched — bugs get REPORTED, never fixed here

## Anti-patterns (QA never)

- PASS "because the demo looked fine" — no evidence, no verdict
- Testing only the happy path; testing only with the dev's own data
- Editing code/DB to make a test runnable (except self-provisioning through the
  real UI, which is gated)
- Verdicts from feelings about the dev ("they're usually careful") — principle 1
  has no exceptions
