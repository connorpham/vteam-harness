# Review dossier — VT-32 (round ceilings for review and BA challenger)

**Provenance, stated plainly:** both cards were written by the implementing session, not by
spawned reviewers. Every bullet is a command that was run on 2026-09-18 with the output it
produced; the outputs are pasted in `evd/VT-32/dev/proof.md`.

## R1 — implementation review (mutation probes)
APPROVE

Tried to break:
- wrote the selftest assertions before the code and ran `python3 core/scripts/review_check.py --selftest` — RED `NameError: name 'count_rounds' is not defined`; GREEN after the implementation at core/scripts/review_check.py:66 and core/scripts/review_check.py:72.
- inserted `return []` as the first statement of `round_gaps` (core/scripts/review_check.py:72) and re-ran the selftest — RED "2 rounds under max_rounds=1 must RED". Restored from the byte-identical mirror.
- replaced the SECURITY lift tag in `LIFT_TAG` (core/scripts/review_check.py:63) with a word that never matches — RED "a SECURITY-tagged finding lifts the ceiling". Restored.
- switched both knobs on in `vteam.config.yaml` and ran `python3 .vteam/scripts/review_check.py VT-25 --sha HEAD` — RED naming 2 rounds vs max_rounds 1 (the dossier's real `## Round 2` heading); `VT-29 --sha HEAD` — green "1 round(s) within max_rounds=1"; reverted the config with `git checkout -- vteam.config.yaml`.
- ran `--ba` (core/scripts/review_check.py:188) on a two-round fixture: knob absent → green with the "no ceiling" note; knob 1 → RED; a `CONFIRMED SPEC:` line → green; a missing file → RED naming the path B3 writes.

Traces: core/scripts/review_check.py:63, core/scripts/review_check.py:72, core/scripts/review_check.py:188, core/scripts/review_check.py:285, `python3 core/scripts/review_check.py --selftest`, `python3 .vteam/scripts/review_check.py VT-25 --sha HEAD`

## R2 — adversarial read: does the ceiling misfire, and does the prose match the code?
APPROVE

Tried to break:
- looked for a false RED on prose: `ROUND_HEAD` (core/scripts/review_check.py:62) matches only a heading (`#{2,4}` at line start) followed by `Round <digits>`; "in the second round we…" inside a bullet does not count. `count_rounds` takes the highest N, so one `## Round 2` recorded once is two rounds, not three.
- looked for a false green on prose: the lift is a whole-word match, so "security" in lowercase and "SPECIFICATION" do not lift; the selftest covers `CONFIRMED SECURITY:` positively; the SPEC case was run by hand on the BA fixture (proof.md §3).
- checked the doctrine says what the code does: core/workflows/dev.md:362 names the knob, the `## Round N` convention, the two lifts, "answered, not fixed", and that a gate rerun is `## Gate rerun`, not a round; core/workflows/ba.md:202 names the knob, the SPEC lift and the `--ba` command; core/workflows/ba.md:210 states the already-coded-spec rule. Rendered skills carry the same text (`grep -c "Round ceiling"` → 1 in each).
- checked the config surface stays parseable by all three parsers: `node tests/conformance.mjs` OK after adding `ba.challenger_rounds` and `review.max_rounds` to the init template (src/cli/init.mjs), docs/GUIDE.md block and core/templates/vteam.config.example.yaml; init's own round-trip proof runs at generation time.
- asked whether an existing consumer goes red on upgrade: `vteam update` leaves the config alone, absent knob = ceiling off, so the testbed and this repo stay green; the only way to a retroactive RED is opting in, and the tasksheet shows exactly which dossier (VT-25) would need relabelling first.

Traces: core/scripts/review_check.py:62, core/workflows/dev.md:362, core/workflows/ba.md:202, core/workflows/ba.md:210, `node tests/conformance.mjs`, `node bin/vteam.mjs update`
