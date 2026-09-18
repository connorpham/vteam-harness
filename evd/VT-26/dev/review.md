# Review dossier — VT-26 (first-run page)

**Provenance:** self-review by the implementing session; the change is documentation plus one
test-extractor path. No product code (`src/ core/ bin/`) is touched, so the push fence does not
demand this file — it exists because the README now makes claims a reader will check.

## R1 — every claim on the new front page traces to an artifact
APPROVE

Tried to break:
- ran every command the README shows in a scratch repo on 2026-09-17: `audit` → `0/100 · grade F` verbatim; `init --yes && doctor` → `34 discovered checks`; `git push origin main` → refused; product code on `feat/SHOP-12-discount` without a dossier → `review_check … NOT in commit`; `audit` again → `91/100 · grade A` — the SVG at docs/assets/fence-demo.svg carries exactly those lines and nothing invented
- checked the numbers against their sources: **199 checks** = tests/e2e.mjs:1 self-verified count; 34 = `discoverSelftests` on core/scripts; 18 gate steps = `grep -c '^  [a-z-]*:$' profiles/nextjs-prisma/gates.yaml`; 64 files / 18,602 lines = the review's own measurement in evd/VT-24/dev/proof.md:1
- tried to make the suite miss the move: `node tests/e2e.mjs` still finds a selftest-count claim (`(34 today)`) and the `**199 checks**` line in README.md; `node tests/conformance.mjs` reads the config block from docs/GUIDE.md:324 and parses it in all three languages — both green after the split
- looked for a README link that now dangles: `docs/GUIDE.md#what-it-actually-looks-like` → docs/GUIDE.md:7, `#known-limits` → docs/GUIDE.md:578, docs/BENCHMARK.md exists (a status page until the scorecard lands), docs/security/ exists
- read docs/GUIDE.md end to end for the seam: the moved text is byte-identical to README lines 62–678 at 37567da (`sed -n 62,678p` was the move), so no sentence was rewritten in the move

Traces: docs/GUIDE.md:7, docs/GUIDE.md:324, tests/conformance.mjs:31, `node tests/e2e.mjs` (199/199), `node tests/conformance.mjs` (17 fixtures)

## R2 — what the rewrite might have broken for a reader
APPROVE

Tried to break:
- the old README's "Five things nothing else here does" is gone from the front page; the claim survives only in docs/COMPARISON.md where it is argued with sources — the front page no longer asserts superiority it has not measured (the benchmark line says "whichever way it goes")
- the audience choice is not hidden: docs/pm/decisions.md D17 states both readings, names (a) as the README's default and the reversal cost as one file — the owner can flip it
- the plugin-install line and the "not for you (yet)" bullets were checked against docs/GUIDE.md:578 (known limits) so the front page promises nothing the limits section retracts
- the animated SVG degrades to a static frame in viewers without CSS animation (each line's keyframes end at opacity 1) — verified by parsing: 20 `<text>` lines, well-formed XML, 6.3 KB, no script

Traces: docs/pm/decisions.md:31, docs/GUIDE.md:578, docs/assets/fence-demo.svg:1, `python3 -c 'import xml.etree.ElementTree as ET; ET.parse("docs/assets/fence-demo.svg")'`
