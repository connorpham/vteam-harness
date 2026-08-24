---
name: verify
description: "Create and run the verification gate for this repo — the profile's ordered step manifest (ledgers → lockfile → lint → types → unit → build → reality checks → integration → e2e), with exact closing lines recorded. Also the standard for WRITING tests — expected values cite the spec or the schema, every behavior gets a boundary pair, no tests that mirror the implementation. Invoked standalone and as the /dev verify step, and before declaring ANY code change done."
argument-hint: "[all|unit|e2e|gate] [--filter <pattern>] [--headed]"
---

> **Model routing for this tool** (from `model-routing.data.yaml`, snapshot 2026-08-17):
> `frontier` → **fable** · `workhorse` → **opus** · `standard` → **sonnet** · `utility` → **haiku**
> Roles → tiers: ba-challenger: standard · ba-draft: standard · dev-r1: workhorse · dev-r2: standard (high-stakes: workhorse) · dev-r3: workhorse · explore: utility · qa-challenger: standard · sa-background: workhorse · sa-challenger: workhorse · sa-writer: workhorse
> Resolve at runtime: `python3 .vteam/scripts/model_route.py <role> --tool claude-code [--high-stakes]` — high-stakes diffs (review.high_stakes_*) bump dev-r2 to the workhorse tier.
> Spawning a subagent: pass the resolved name as the Agent tool's `model` parameter.


# /verify — the verification gate

**Why this exists:** "it should work" is not a verdict. A change is done only when
the gate below is green and the exact output lines are quoted back.

**Immutable principles:**
1. **Report honestly.** A failing step is reported with its real output — never
   softened, never skipped silently. A step that could not run (missing env, no
   DB): say which and why.
2. **Tests encode the spec, not the code.** Every expected value cites its source —
   a spec section or a schema model/field (as a comment on the assertion). A test
   that mirrors what the implementation returns proves nothing.
3. **Boundary pairs.** Each behavior gets the passing input AND the adjacent
   failing one (duplicate vs fresh identifier; sufficient vs insufficient balance;
   active vs cancelled record).
4. **The gate order is fixed** — cheapest and most blind-spot-covering first:
   ledgers (docs-shrink + ledger schema) → lockfile → lint → types → unit → build →
   post-build reality checks → integration → e2e. A red early step stops the chain.
   The bookkeeping steps run before lint because they are cheapest and catch the
   class of damage every later step is blind to (overwritten ledgers, fabricated
   report rows, a lockfile from a second package manager).
5. **Visible, human-readable process.** Narrate each step with a `▶` line as it
   starts; the final report leads with a plain-language verdict anyone can read,
   with the raw quoted output BELOW it, never instead of it.
6. **A new gate must prove it can go RED — in the same PR.** Adding or changing a
   gate step or check script requires running it against a VIOLATING input, seeing
   it red in the right place, reverting — and pasting that red evidence into the PR
   body. A gate that has never been red does not exist (see provenance: two
   always-green gates shipped before this rule).

## R0 — BOOTSTRAP (only what's missing)

The stack profile (`stack.profile` in `vteam.config.yaml` →
`profiles/<name>/gates.yaml`) declares each step's command and its bootstrap
recipe. A step whose tooling is absent is either bootstrapped now or declared
skipped WITH a reason in the manifest — `gate` treats an undeclared missing step as
RED, never as a silent skip.

## R1 — WRITE TESTS (when the request is "write tests" / a change needs coverage)

Placement (profile-specific paths come from the profile; the layers are universal):

| Layer | What |
|---|---|
| Unit | pure logic: pricing, balance math, validators — mocked data layer OK |
| Integration (real DB) | **spec invariants that real SQL must hold** (non-negative stock, cross-table consistency): any function using raw queries / transactions / DB constraints MUST have a test at this layer — mocks don't execute SQL, so they prove nothing here |
| Integration (route) | API handlers with a mocked data layer |
| E2E | critical flows only: sign-in, the core money/booking flow |

- Read the code under test FIRST; derive expecteds from spec/schema, cite them in
  a comment.
- **Red first.** For NEW behavior: write the test before the implementation and
  RUN it — it must FAIL for the expected reason before the code makes it pass. A
  test never seen red proves nothing (it may pass vacuously). Record the red run
  in the task-sheet.
- Unit tests never touch the dev DB. E2E uses the real dev server + DB; test rows
  carry the `ZZTEST` marker and are cleaned up.
- Auth-gated routes/pages: test both sides of the gate (right role passes, other
  role blocked).
- Keep tests deterministic — no wall-clock, row-order, or leftover-data reliance.

## R2 — RUN THE GATE

```bash
bash .vteam/scripts/gate.sh          # the profile's fixed step order
bash .vteam/scripts/gate.sh e2e      # …including the e2e tail (needs DB + env)
```

The script stops at the first red step and prints `GATE: RED at <step>`; green
ends with `GATE: GREEN`. Either way, **quote the closing lines of each step
verbatim** in your report. Pre-existing failures unrelated to the current change:
report them as such explicitly — they don't excuse new ones.

## R3 — REPORT

One block to the user: per-step status table + the quoted result lines + what was
NOT run and why. If invoked from /dev, the same block goes into the task-sheet.

A confusing failure that turned out to be env/flaky/tooling (not the code under
test) → append the lesson (+ INDEX line, tags `env`/`flaky`) to
`docs/qa/knowledge-base.md` so the next run doesn't re-debug it. When a failure
makes no sense, grep that file's INDEX for `env`/`flaky` first — read only
matching lessons, never the whole file.

## Definition of Done
- [ ] Gate ran in the fixed order; stopped at first red (or all green)
- [ ] Exact closing lines quoted for every step that ran — no paraphrased "tests pass"
- [ ] New behavior has tests with spec/schema-cited expecteds + a boundary pair
- [ ] Unit tests never touched the dev DB; e2e rows ZZTEST-marked and cleaned up
- [ ] Anything skipped is named with the reason
- [ ] A new/changed gate script in this change carries red-proof on a violating
      input — pasted into the PR body (principle 6)
- [ ] Report leads with the plain-language verdict; raw output quoted below it
