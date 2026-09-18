# VT-32 · proof — every line below is a command run on 2026-09-18 in the worktree and its real output

## 1. RED before, GREEN after (the selftest assertions were written first)

```
$ python3 core/scripts/review_check.py --selftest        # assertions added, no implementation yet
NameError: name 'count_rounds' is not defined
exit 1
$ python3 core/scripts/review_check.py --selftest        # after the implementation
review_check selftest: OK (valid card green + 4 mutations red + parser + reviewers=3 dossier red + round ceiling read/counted/lifted)
exit 0
```

## 2. Code-only mutations, test kept, source restored from the byte-identical mirror

```
$ perl -0pi -e '…insert "return []" as the first statement of round_gaps…' core/scripts/review_check.py
$ python3 core/scripts/review_check.py --selftest
AssertionError: 2 rounds under max_rounds=1 must RED
exit 1
$ cp .vteam/scripts/review_check.py core/scripts/review_check.py && cmp … && python3 … --selftest
restored from the identical mirror
review_check selftest: OK …

$ perl -0pi -e '…LIFT_TAG review.max_rounds → "NEVERMATCHES"…' core/scripts/review_check.py
$ python3 core/scripts/review_check.py --selftest
AssertionError: a SECURITY-tagged finding lifts the ceiling
exit 1
$ cp .vteam/scripts/review_check.py core/scripts/review_check.py   → restored, selftest OK
```

## 3. Real runs

Knob absent (this repository's config as committed):
```
$ python3 .vteam/scripts/review_check.py VT-29 --sha HEAD
✅ review_check: VT-29 — dossier complete (R1, R2; R3 (high-stakes) not required for this diff) · review.max_rounds not set — no ceiling on fix rounds (init sets 1)
$ printf '## Challenger card — demo\nAPPROVE\n\n## Round 2 — re-challenge\nAPPROVE\n' > docs/specs/reviews/demo-backlog.md
$ python3 .vteam/scripts/review_check.py --ba demo
✅ review_check: demo — 2 challenger round(s) (ba.challenger_rounds not set — no ceiling; init sets 1)
$ python3 .vteam/scripts/review_check.py --ba nope
❌ review_check: docs/specs/reviews/nope-backlog.md missing — B3 records the challenger card there
```

Knobs switched on temporarily (`ba.challenger_rounds: 1`, `review.max_rounds: 1` in vteam.config.yaml, reverted afterwards with `git checkout -- vteam.config.yaml`):
```
$ python3 .vteam/scripts/review_check.py VT-25 --sha HEAD      # evd/VT-25/dev/review.md has "## Round 2 — CI (Linux) red…"
❌ review_check: VT-25 — 1 gaps
   - 2 rounds recorded (`## Round N` headings) but review.max_rounds is 1 — answer the remaining finding in the dossier (answered, not fixed: why), do not open another round; a SECURITY-tagged finding lifts the ceiling
$ python3 .vteam/scripts/review_check.py VT-29 --sha HEAD
✅ review_check: VT-29 — dossier complete (R1, R2; R3 (high-stakes) not required for this diff) · 1 round(s) within max_rounds=1
$ python3 .vteam/scripts/review_check.py --ba demo             # fixture with "## Round 2"
❌ review_check: demo — 2 rounds recorded (`## Round N` headings) but ba.challenger_rounds is 1 — … a SPEC-tagged finding lifts the ceiling
$ printf '## Challenger card\nCONFIRMED SPEC: story 3 contradicts §4.B\nAPPROVE\n\n## Round 2\nAPPROVE\n' > docs/specs/reviews/demo-backlog.md
$ python3 .vteam/scripts/review_check.py --ba demo
✅ review_check: demo — 2 challenger round(s) within ba.challenger_rounds=1
```
The VT-25 line is why the knob is opt-in for existing repositories (tasksheet, "Decision taken here").

## 4. Repo checks

```
$ node bin/vteam.mjs update
✓ .vteam runtime refreshed · ✓ doctrine refreshed in docs/team · ✓ claude-code workflows re-rendered
$ node bin/vteam.mjs doctor
✅ manifest verified (171 framework-owned files intact) · ✅ gate selftests green (34 discovered checks prove they can red)
$ node tests/conformance.mjs
conformance: OK — 17 fixtures, ctx.py == ctx.mjs (== ctx.sh on its scalar subset), error fixtures red in both.
conformance: OK — ledger grammar, 10 rows, lib/ledger.py == board.mjs parseLedger (kind/tok/actor/malformed).
$ grep -c "Round ceiling" .claude/skills/dev/SKILL.md .claude/skills/ba/SKILL.md
1 · 1
```
(gate and npm test lines appended below after the final run)

```
$ npm test
conformance: OK — 17 fixtures … · conformance: OK — ledger grammar, 10 rows …
E2E: GREEN — 199/199 checks passed
$ bash .vteam/scripts/gate.sh
GATE: GREEN (14 steps ran, 1 declared skips) — 1 ADVISORY FAILED: schedule   # advisory pre-existing (A3 overdue, D17/D18 burning)
```
