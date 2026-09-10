# VT-13 — effectiveness trial (run for the owner to judge; NO verdict issued here)

BASE-COMMIT: dfa10f1 · CAPTURED-AT: 2026-09-10T10:32:42Z

Three tests. The first is machine-objective. The second and third are run against
**prior art the competencies did not write**: `VT-11`, a ticket the owner authored on
2026-09-09, before any of these files existed. That is the only uncontaminated
subject available — I cannot produce a clean "before" from inside the session that
produced the competencies, and I am not pretending otherwise.

**No PASS/FAIL is written in this file.** Closure is QA's act; issuing my own verdict
on my own work is the self-certification the doctrine exists to prevent.

---

## Test 1 — VT-13's own acceptance criteria, checked by command

| AC | Claim | Result |
|---|---|---|
| 1 | `competency_check` exits 0, 31 well-formed and indexed | ✅ exit 0, 31 |
| 2 | `gate.sh` GREEN, 164/164 | ✅ GATE: GREEN (9 steps, 1 skip) |
| 3 | the nine DEV/QA files are conditionally routed | ✅ 0 of 9 are `always` |
| 3 | …so DEV stays 3,897 words and QA 6,367 | ❌ **now 3,096 / 4,663** |
| 4 | BA/PM cost stated, not hidden (BA 2,155, PM 1,076) | ❌ **now 1,696 / 837** |
| 5 | CI on PR #66 all pass | ✅ gate · e2e(20) · e2e(22) · CodeQL js-ts · CodeQL python |

**AC3 and AC4 no longer hold as written, and the cause is my own mistake.** I pinned
those criteria to a live measurement, and VT-14 then moved it. The routing *claim*
holds; the *numbers* do not. `ba-acceptance-criteria` says a criterion needs "a
concrete typed value" — it does not say to pin to a value a sibling ticket changes.
The fix is an anchor: "unchanged **relative to the pre-VT-13 baseline**", not an
absolute. Recorded rather than quietly re-baselined.

---

## Test 2 — `ba-acceptance-criteria` + `ba-story-slicing` on VT-11

VT-11 is a well-formed ticket: it has `Why`, a `Spec / oracle` section citing spec
sections, `Acceptance criteria (testable)` in Given/When/Then, and a specific
`Out of scope`. It is a fair subject, not a straw man — and it does two things
**better than my own VT-13/VT-14**: a whole-ticket oracle section, and an out-of-scope
list naming real alternatives (Turborepo caching, Yarn PnP, the `.next` collision).

Findings, with confidence marked. Each cites the rule it comes from.

| # | Finding | Rule | Confidence |
|---|---|---|---|
| 1 | **AC2 carries six behaviours** — `prisma-generate`, `typegen`, `types`, `build`, `token-check`, `e2e` in one `Then`. A partial result cannot be recorded: if `e2e` fails and the other five pass, AC2 is neither passed nor failed. | "One behaviour per criterion; split on every 'and' in the `Then`" | **strong** |
| 2 | **AC3 has no refusal side.** It specifies the `< 15.5` behaviour (declared skip naming the version) and says nothing about `≥ 15.5`, where `typegen` must actually run and pass. Half the rule is unspecified — and it is the half that will regress silently when the fleet upgrades. | "Write the refusal for every rule you write" | **strong** |
| 3 | **AC4 is not decidable as written**: "a per-worker port (documented env **or** template variable) … doctrine says which". Two different implementations both satisfy it, and the deciding is deferred out of the criterion. | "Concrete and typed … the tester picks the value otherwise" | **strong** |
| 4 | **AC5 has the same fork** — "strips Prisma's query string before `psql` (**or** uses Prisma to ping)" — and no failing side (unreachable DB). | same as #3, plus the refusal rule | **strong** |
| 5 | **AC1 bundles a second behaviour** in its tail: "a root-layout repo keeps today's values" is a separate, testable regression criterion. And "`stack:` (e.g. `stack.app_dir`, `stack.prisma_schema`)" — "e.g." means the key names are not pinned, so a verifier cannot tell whether different keys pass. | one behaviour · concrete value | **strong** |
| 6 | **AC6 is a Definition of Done, not an acceptance criterion** — selftests, README counts, gate and doctor are process gates, and it bundles four of them. It also says the fixture "proves 1–3", which leaves **AC4 and AC5 with no named test**. | criterion vs DoD; one behaviour | medium — arguably deliberate |
| 7 | **No criterion cites its own source.** The ticket has an excellent whole-ticket `Spec / oracle`, but per-criterion traceability is absent, so a verifier cannot tell which spec line AC2 rests on. | "Cite the source on every criterion" | medium |

`ba-story-slicing`: nine numbered problems, estimate **1d**, spanning
`src/cli/init.mjs`, `profiles/*/gates.yaml`, `core/scripts/gate.py`, `tests/e2e.mjs`
and the README. Applying the vertical-slice test — "after this ships, a user can …" —
gives **five separately demonstrable slices**: (a) detection writes the paths,
(b) gate steps use the detected paths and package manager, (c) `typegen` version
skip, (d) per-worker port, (e) `db-check.sh` template. Each is usable alone; (a) is
the narrowest complete path and de-risks the rest. **Finding: five slices and a
1-day estimate in one ticket** — medium confidence, since the owner may be sizing
the patch rather than the discovery.

---

## Test 3 — `qa-combinatorial-design` on VT-11's real parameter space

Every dimension below is taken from VT-11's own text, not invented:

| Dimension | Values | Source in VT-11 |
|---|---|---|
| app location | root · `apps/*` | Why#1, AC1 |
| schema location | root · `packages/*` | Why#2, AC1 |
| package manager | npm · pnpm · yarn | Why#6, AC2 (`{package_manager}`) |
| Next version | < 15.5 · ≥ 15.5 | Why#3, AC3 |
| parallel | 1 · > 1 | Why#7, AC4 |

```
exhaustive              : 48 combinations
VT-11 AC6 proposes      : 1 monorepo fixture  →  1/48 = 2.1% covered
pairwise (2-way)        : 8 cases             →  83% fewer than exhaustive
pairs required          : 48   ·   pairs NOT covered: 0   ✓ machine-verified 100%
```

The eight cases, and the two combinations that need an explicit constraint rather
than a case, are in the run output. The competency's rule — "state the exhaustive
count, name the strength, have a tool prove the coverage" — turns AC6's
"a monorepo fixture" into **8 cases at a named strength with verified coverage**.

**This is the clearest evidence of effect in the trial**: a number the ticket does
not contain, on a matrix the ticket does contain, produced by a tool that checks
itself.

---

## What this trial does NOT show

- **No before/after delta.** I cannot run an uncontaminated baseline from this session.
- **Nothing about the reported symptom.** The owner's complaint is that the agent
  forgets on a long task. This trial measures whether the competencies produce
  findings — not whether the context they cost degrades a full run. That needs a
  real `/dev` or `/qa` task instrumented end to end, and it has not been done.
- **No independent verification.** Every finding above is mine, against rules I wrote.
  Findings 1–5 are checkable by reading VT-11 in thirty seconds; #6 and #7 are
  judgement calls and are marked as such.
