# VT-39 · dev tasksheet — the ledger's cost column stops being testimony
CODE-SCOPE: core/scripts/cost_check.py core/scripts/gate.py core/workflows/pm.md profiles/ src/cli/init.mjs core/templates/ tests/e2e.mjs .vteam/ .claude/ docs/team/ README.md docs/GUIDE.md CHANGELOG.md evd/VT-39/ docs/pm/ docs/backlog/

Branch `feat/VT-39-cost-audit` from main d53eeb8.

| T | Task | State |
|---|---|---|
| T1 | `core/scripts/cost_check.py` — per-day comparison, staleness, compact unmeasured line, quiet when nothing was ever measured | done |
| T2 | Wire as ADVISORY step `cost` after `ledger` in all six profiles + gate.py BOOKKEEPING | done |
| T3 | Knobs `ledger.cost_tolerance_factor` (10) and `ledger.usage_max_stale_days` (7) in init, the example config and the documented block | done — conformance OK |
| T4 | `core/workflows/pm.md` step 6: the estimate is audited, and never edited to match | done |
| T5 | Selftest (4 required fixtures + 4 more) and one e2e check on a fresh install | done — 234/234 |
| T6 | Five code-only mutations, tests kept | done — mutations.md |
| T7 | Run it on this repo and record the real output | done — proof.md §2 |

## New script rather than extending `log_check.py`, and why
`log_check` is a BLOCKING grammar gate: it reds on a malformed row, a missing Actor column, an
evidence link that does not resolve. This audit is advisory by construction — it compares an
estimate with a measurement, and those differ. Putting it inside `log_check` would force one of two
bad outcomes: make the grammar gate non-blocking, or make an estimate blocking. Separate step,
separate exit semantics, same pattern the repo already uses for `schedule`.

## Column choice, stated
Measured "new spend" = `input + cache_write + output`. `cache_read` is excluded — re-reading context
already paid for is not new work, and it dwarfs everything else (938M against 3.3M of output here),
so including it would make every ratio meaningless. `input` is included because it is new spend; under
caching it is a rounding error, so the figure is in practice output + cache-write.

## Two bugs my own edits caused, found by the gate and recorded rather than quietly fixed
- The comment I added to the `vteam.config.yaml` template in `src/cli/init.mjs` contained backticks. The template is a JS template literal, so the backtick CLOSED it and `vteam update` died with `Unexpected identifier 'tok'`. It failed while my command was grepping its output for "error", so the failure was invisible for two steps — the mistake was filtering a command's output instead of reading its exit code.
- My first insertion of the `cost:` step into the six `gates.yaml` files landed between `ledger:` and its `run:` line, producing a step with no `run`. The gate caught it immediately (`GATE: RED at ledger — manifest step has no run`), which is the manifest rule from VT-24 doing its job.
