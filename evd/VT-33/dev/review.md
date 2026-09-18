# Review dossier — VT-33 (measure the doctrine a lane loads at start)

**Provenance, stated plainly:** both cards were written by the implementing session, not by
spawned reviewers. Every bullet is a command that was run on 2026-09-18; outputs are in `proof.md`.

## R1 — implementation review (mutation probes)
APPROVE

Tried to break:
- removed the `is_file` guard at core/scripts/context_budget.py:104 with the selftest kept — RED (`FileNotFoundError` on the deliberately missing identity file): a file that is not there is never "loaded".
- forced `over_budget` to False at core/scripts/context_budget.py:136 — RED (`a tiny budget must print the over-budget line`): the budget comparison is the only thing that prints the warning.
- neutered the `always` filter at core/scripts/context_budget.py:87 — RED: the mandatory list lost `dev-x.md`, so INDEX-driven loads are really counted, not inferred.
- ran `python3 .vteam/scripts/gate.py` on the branch: `▶ context-budget:` runs, prints the per-lane totals and `✅ context_budget: every lane within 40000 tokens`, and the step is in the BOOKKEEPING set at core/scripts/gate.py:187 so a repo where only bookkeeping ran still reads WEAK.

Traces: core/scripts/context_budget.py:104, core/scripts/context_budget.py:136, core/scripts/gate.py:187, `python3 core/scripts/context_budget.py --selftest`, `python3 .vteam/scripts/gate.py`

## R2 — adversarial read: is the number honest?
APPROVE

Tried to break:
- asked whether "mandatory" flatters the framework: the rule at core/scripts/context_budget.py:71 is structural (role / identity / INDEX / INDEX `always`) and is stated in the docstring; it errs towards counting MORE (pm's `roles/sa.md`, read only at the SA step, is counted as mandatory), never less.
- asked whether it hides the competencies: every competency the INDEX marks `always` is added to the mandatory total with its `Loads at` step; the ones that wait for a matching ticket are not named by the skill at all, so they appear nowhere — the ticket's table says so and names the four (dev) and five (qa) that do load.
- checked the approximation is the same for every lane and visible: `≈tokens = bytes / 4` is printed in the header line of every run and in `--json` as `tokens_are`.
- checked it cannot block anyone: exit 0 on over-budget (selftest asserts it), `advisory: true` in all six manifests (profiles/generic/gates.yaml:59 and siblings), usage errors exit 2 only when asked for a lane that does not exist.
- read the measured table against intuition: dev's skill alone is 35 722 bytes; that is the largest single item in every lane, which is the finding the critique missed — the weight is the lane text, not the 31 competency files.

Traces: core/scripts/context_budget.py:71, profiles/generic/gates.yaml:59, `python3 .vteam/scripts/context_budget.py --all --json`, `node bin/vteam.mjs doctor`
