# Review dossier — VT-39 (the ledger's cost column stops being testimony)

**Provenance, stated plainly:** both cards were written by the implementing session, not by spawned
reviewer agents. Every bullet is a command that was run on 2026-09-18; the outputs live in
`proof.md` and `mutations.md`. By its own classifier this ticket is `logic` class (python and JS
changed), so it pays the full fence.

## R1 — implementation review (one mutation per rule)
APPROVE

Tried to break:
- counted `cache_read` as new spend at core/scripts/cost_check.py:68 and ran `python3 core/scripts/cost_check.py --selftest` — RED (`AssertionError: {'2026-09-18': 900010.0}` against the expected `10.0`). This is the mutation that matters most: 938M of cache reads against 3.3M of output in this repo would have swamped every ratio and made the check permanently, meaninglessly red.
- removed the staleness branch at core/scripts/cost_check.py:135 — RED (`assert finding` on the fixture whose ledger runs 25 days past the newest measured row). Without it the check would have stayed green on exactly the condition this ticket exists to catch.
- removed the divergence branch at core/scripts/cost_check.py:117 — RED; the 40× fixture came back as "audited within 10×".
- made the unmeasured-days line list every date instead of three plus a count at core/scripts/cost_check.py:130 — RED (`+7 more` missing). A check that prints one line per unsynced day on a repo that never syncs is a check people delete.
- let malformed rows contribute to the claimed total by dropping the guard at core/scripts/cost_check.py:77 — RED (`TypeError: float() argument must be … not 'NoneType'`), proving the grammar really comes from `lib/ledger.py` rather than a private re-parse.
- ran the whole gate afterwards: `GATE: GREEN (16 steps ran, 1 declared skips) — 2 ADVISORY FAILED: cost, schedule`, and `npm test` 234/234.

Traces: core/scripts/cost_check.py:68, core/scripts/cost_check.py:135, core/scripts/gate.py:187, `python3 core/scripts/cost_check.py --selftest`, `bash .vteam/scripts/gate.sh`

## R2 — adversarial read: does it claim more than it measured, or shout at the wrong people?
APPROVE

Tried to break:
- looked for an invented per-ticket number: there is none. `claimed_by_day` (core/scripts/cost_check.py:73) and `measured_by_day` (core/scripts/cost_check.py:61) both key on the DATE only, and the closing line of every run says a session log never knows which ticket a token belonged to. A per-ticket figure was the obvious feature to add and it would have been fabrication.
- attacked the quiet path: a repo that never ran `usage --sync` gets exactly ONE line and exit 0 (core/scripts/cost_check.py:104, asserted in the selftest by `len(lines) == 1`), and the fresh-install e2e asserts the gate does not even record an advisory failure there. Most repos will never sync; this check had to be useful to them or invisible to them, never noisy.
- attacked the blocking question: the step carries `advisory: true` in all six profiles and sits in gate.py's BOOKKEEPING set (core/scripts/gate.py:187), so it can never upgrade a WEAK banner into a strong one and can never fail a commit. I checked the real gate output rather than the manifest alone.
- attacked the tolerance: at 8× the check stays silent and at 40× it speaks, both asserted. A percentage tolerance would have been wrong — an estimate typed from memory is not a measurement with error bars, so the unit is a FACTOR.
- checked the incentive the wording creates: the divergence line ends "never edit the row to match the measurement", and `pm.md` says the same. Without that sentence the cheapest way to clear this check is to rewrite the ledger, which would leave the repo with a silent check and a falsified record — strictly worse than before the ticket.
- checked I did not duplicate `perf_report.measured_section`, which already compares claimed-vs-measured per PERSON over the whole period. It is a desk-report paragraph, not a gate, it is not per day, and it does not detect staleness — the finding that is real here. The new step imports `parse_usage_dir` from it rather than re-deriving the usage grammar, matching the H4 lesson that one grammar gets one home.

Traces: core/scripts/cost_check.py:61, core/scripts/cost_check.py:104, core/scripts/gate.py:187, `python3 core/scripts/cost_check.py`, `npm test`
