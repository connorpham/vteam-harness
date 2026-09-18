# VT-36 · proof — commands run on 2026-09-18 with their real output

## 1. The cost this ticket attacks, measured on this repo
```
$ grep -oE "\| VT-[0-9]+ [^|]*\| done · tok ≈ [0-9]+k" docs/pm/log.md   # the ledger records tokens per ticket
VT-29 | done · tok ≈ 60k      ← the smallest change of the week: one deleted --depth=1 flag
$ git show --stat 4cdd431 | tail -3
 9 files changed, 156 insertions(+), 7 deletions(-)   ← 5 of the 9 are procedure
$ for c in $(git log --no-merges --format=%H -40 main); do change_class.py --base $c^ --sha $c; done | sort | uniq -c
   28 logic
   12 docs
```
12 of 40 commits touch no executable file. Each paid for two fresh reviewer agents, and VT-33
measured a reviewer's mandatory doctrine load at ≈17k tokens — so ≈35k tokens per commit bought
cards about a README. That is the theatre this ticket removes.

## 2. The classifier against real commits of this repo
```
$ python3 core/scripts/change_class.py --base a2c84c9^ --sha a2c84c9
  change-class: docs (a2c84c9^…a2c84c9)
    · 6 changed path(s), all prose no tool renders
$ python3 core/scripts/change_class.py --base 4cdd431^ --sha 4cdd431
  change-class: logic (4cdd431^…4cdd431)
    · .vteam/manifest.json: configuration, data or a lockfile — behaviour moves here without a line of code changing
$ python3 core/scripts/change_class.py --base a82e874^ --sha a82e874
  change-class: logic (a82e874^…a82e874)
    · docs/assets/fence-demo.svg: added code file (a file that appears or disappears has no skeleton to compare)
$ python3 core/scripts/change_class.py --base 1257176^ --sha 1257176
  change-class: logic (1257176^…1257176)
    · .claude/skills/verify/SKILL.md: this scanner does not parse .md
```

## 3. Selftests
```
$ python3 core/scripts/change_class.py --selftest
  change_class selftest: OK (skeleton: strings/comments/JSX text vs identifiers, template literals
   and unparsable files refuse to judge · classes: docs, surface (string + JSX copy), logic (const
  ant, config, new file, deleted test, over the cap), high-stakes (path + term))
$ python3 core/scripts/review_check.py --selftest
  review_check selftest: OK (valid card green + 4 mutations red + parser + reviewers=3 dossier red + round ceiling read/counted/lifted)
```

## 4. End to end on a fresh install (tests/e2e.mjs §5b)
```
    ✅ change_class calls a docs-only diff `docs`
    ✅ review_check needs NO dossier for a docs-only diff, and says why
    ✅ review.proportional: false restores the uniform fence on the same docs-only diff
    ✅ review_check demands the dossier again once code moves
  E2E: GREEN — 227/227 checks passed
```

## 5. Gate and suite on the branch
```
$ bash .vteam/scripts/gate.sh
GATE: GREEN (15 steps ran, 1 declared skips) — 1 ADVISORY FAILED: schedule
$ npm test
conformance: OK — 17 fixtures, ctx.py == ctx.mjs (== ctx.sh on its scalar subset), error fixtures red in both.
conformance: OK — ledger grammar, 10 rows, lib/ledger.py == board.mjs parseLedger (kind/tok/actor/malformed).
E2E: GREEN — 227/227 checks passed
```

## 6. Mutations
mutations.md — seven code-only mutations, tests kept, all RED, including the rename hole the adversarial card found (M7).
