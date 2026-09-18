# Review dossier — VT-36 (the risk class picks the review shape)

**Provenance, stated plainly:** both cards were written by the implementing session, not by spawned
reviewer agents. Every bullet is a command that was run on 2026-09-18; the outputs are in
`proof.md` and `mutations.md`. This ticket is `logic` class by its own classifier, so it pays the
full fence it just made proportional.

## R1 — implementation review (one mutation per rule)
APPROVE

Tried to break:
- forced `classify` to return `logic` unconditionally at core/scripts/change_class.py:209 neighbourhood and ran `python3 core/scripts/change_class.py --selftest` — RED (`docs-only: expected docs, got logic`). Restored from a byte copy.
- deleted the rendered-tree exclusion at core/scripts/change_class.py:58 neighbourhood — RED: `doctrine is rendered — it is runtime`. Without it, an edit to `core/doctrine/red-flags.md` would have counted as prose and needed no review at all, which is the worst possible hole in this design.
- removed the `review.surface_max_lines` cap at core/scripts/change_class.py:294 — RED: 120 changed lines of pure string bodies came back `surface`; volume is its own risk.
- made template literals blankable at core/scripts/change_class.py:143 — RED: `a template literal carries code`. `${x}` inside a backtick string is executable and must move the skeleton.
- deleted the docs/surface branches of `review_shape` at core/scripts/review_check.py:167 — RED in review_check's own selftest.
- removed the `review.proportional` knob's effect at core/scripts/review_check.py:292 and ran `npm test` — RED on exactly one check, `review.proportional: false restores the uniform fence` (226/227), which is the reversal the ticket promises.

Traces: core/scripts/change_class.py:106, core/scripts/change_class.py:294, core/scripts/review_check.py:167, `python3 core/scripts/change_class.py --selftest`, `npm test`

## R2 — adversarial read: can an agent talk its way into a lighter fence?
APPROVE, with one CONFIRMED finding fixed in this same branch

Tried to break:
- **CONFIRMED and fixed:** renamed a code file to prose (`src/rate.ts` → `docs/rate.md`) — the first version read only the NEW path of a rename from `git diff --name-status`, so deleting executable code came back `docs` and would have needed no card. `changed()` at core/scripts/change_class.py:209 now emits both sides of every R/C row, and two selftest cases pin it (`code-renamed-to-prose` → logic, `prose-renamed-to-prose` → docs). M7 in mutations.md is the proof it bites.
- tried to hide logic inside a string: changing `"hi"` to `"bye"` is surface, but `x(\`a ${p} b\`)` to `x(\`a ${q} b\`)` is logic — the skeleton keeps template literals verbatim on purpose (core/scripts/change_class.py:143).
- tried the JSX false positive: `if (a > b) return <i/>` could look like a prose run between `>` and `<`. The run regex refuses brackets and operators and rejects any run containing a JS keyword, so that line stays logic; the selftest asserts exactly this pair.
- tried a config-only change: `config.yaml` with `limit: 5` → `limit: 500` is `logic`, because a threshold moves the product without a line of code changing. Same for lockfiles, migrations, `.env`, SQL and Prisma schemas.
- checked the class cannot be declared: nothing in `review_check` reads a class from the dossier, the ticket or an argument — it calls `change_class.classify` on the diff it is about to gate, and prints what it found on every verdict, green or red (core/scripts/review_check.py:292 neighbourhood).
- checked the blast radius on real history: classified the last 40 commits of main (proof.md §1) — 12 `docs`, 28 `logic`, zero `surface`. Nothing that touched code was reclassified downward, which is the number that matters.
- checked what does NOT move: the verification gate, the evidence pack, the ledger row, the stale-verdict rule and the escape hatch are untouched; `bash .vteam/scripts/gate.sh` is GREEN with 15 steps as before.

Traces: core/scripts/change_class.py:209, core/scripts/change_class.py:143, core/scripts/review_check.py:292, `python3 core/scripts/change_class.py --base 4cdd431^ --sha 4cdd431`, `npm test`
