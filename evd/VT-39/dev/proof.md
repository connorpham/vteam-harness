# VT-39 · proof — commands run on 2026-09-18 with their real output

## 1. The gap this ticket closes

```
$ grep -c "tok ≈" docs/pm/log.md          # every dispatch row carries a hand-typed estimate
$ grep -rn "tok_k" core/scripts/lib/ledger.py core/scripts/log_check.py
  lib/ledger.py parses it · log_check.py never compares it to anything
```

`npx vteam-harness usage` has measured the real numbers all along (per day, per model: sessions,
messages, input, cache-read, cache-write, output) and `usage --sync` publishes them to
`{paths.pm}/usage/<actor>.md`, which `perf_report.py:parse_usage_dir` already reads. Nothing put the
two next to each other, and nothing noticed when the measured side stopped being written.

## 2. The new step, run against THIS repo

```
$ python3 core/scripts/cost_check.py
⚠️  2026-08-18: the ledger claims ≈300k, the session logs measured ≈3,854k — 13× apart (tolerance 10×). A finding about the ESTIMATE: say what the day actually cost next time, never edit the row to match the measurement.
⚠️  2026-08-21: the ledger claims ≈250k, the session logs measured ≈3,444k — 14× apart (tolerance 10×). A finding about the ESTIMATE: say what the day actually cost next time, never edit the row to match the measurement.
ℹ️  8 day(s) with ledger rows and no measured row (2026-09-03, 2026-09-07, 2026-09-08 … +5 more) — not audited, not a fault.
⚠️  the measured record STOPPED: newest ledger row 2026-09-18, newest measured row 2026-08-24 — 25 days apart (limit 7). Run `npx vteam-harness usage --sync` and commit the file; until then every cost number in this repo is self-reported.
   (per DAY only: a session log knows the day and the model, never which ticket a token belonged to)
exit 1
```

Three findings, all real:

1. **The measured record stopped 25 days ago.** This is the finding the ticket was written for. The
   two divergences below are visible; a record nobody keeps is not, and it is the one that silently
   returns every cost number in the repo to self-reported.
2. **On the only two days that were measured, the estimates were ~13× low** (300k claimed against
   3,854k measured; 250k against 3,444k). Both rows stay exactly as written — the finding is about
   how the estimate was made, and editing history to silence the check would destroy the signal.
3. **Eight days have ledger rows and no measured row** — reported once, compactly, as a fact rather
   than a fault.

## 3. Selftest

```
$ python3 core/scripts/cost_check.py --selftest
cost_check selftest: OK (match green + 40× divergence named + staleness names both dates +
no-usage-dir quiet + unmeasured days compact + cache-read excluded + malformed tok ignored via lib/ledger)
exit 0
```

The four fixtures the ticket asked for, plus four more: a divergence inside the tolerance stays
quiet, a 3-day staleness gap is not stale, a junk date is skipped rather than fatal, and the ledger
grammar is imported from `lib/ledger.py` so a malformed `tok≈90k` (no spaces) contributes nothing.

## 4. In the gate

```
$ bash .vteam/scripts/gate.sh
▶ cost: python3 .vteam/scripts/cost_check.py
🟡 advisory cost: FAILED — reported, not blocking; the condition is about the project, not about this change
GATE: GREEN (16 steps ran, 1 declared skips) — 2 ADVISORY FAILED: cost, schedule
exit 0
```

The step reports and never blocks, exactly like `schedule`. On a fresh install, where nothing was
ever synced, it prints one line and does not fail at all — the e2e asserts that:

```
✅ the cost step RAN and is quiet on a repo with no measured record
```

## 5. Suite and manifest

```
$ npm test
conformance: OK — 17 fixtures, ctx.py == ctx.mjs (== ctx.sh on its scalar subset), error fixtures red in both.
conformance: OK — ledger grammar, 10 rows, lib/ledger.py == board.mjs parseLedger (kind/tok/actor/malformed).
E2E: GREEN — 234/234 checks passed

$ node bin/vteam.mjs doctor
✅ manifest verified (177 framework-owned files intact)
✅ gate selftests green (39 discovered checks prove they can red)
```

(doctor also reds on `core.hooksPath` pointing at the main checkout — a git-worktree artefact of the
shared config, not this change.)

## 6. Mutations

`mutations.md` — five code-only mutations, tests kept, all RED.
