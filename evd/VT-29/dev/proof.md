# VT-29 · proof — commands run on 2026-09-17 with their real output

## 1. CI's failure, reproduced in a clone made exactly like actions/checkout for PR #75
```
$ GITHUB_BASE_REF=feat/VT-26-first-run bash .vteam/scripts/docs_shrink_check.sh   # pre-fix
before: shallow=no, a82e874 files=12
✅ docs/pm + docs/adr ledgers show no abnormal shrink
after:  shallow=a82e8748, a82e874 files=501
❌ graph_check: 1 coherence violations
   - VT-26: commit a82e8748 touches outside the declared CODE-SCOPE (…): .claude-plugin/marketplace.json, .claude/agents/…
```
CI runs 35228436089 (pull_request, RED at graph, RED again on rerun) vs 35228430618 (push of the same commit, GREEN) — the only difference is `GITHUB_BASE_REF`.

## 2. Selftest RED before the fix, GREEN after
```
$ bash core/scripts/docs_shrink_check.sh --selftest   # new case, old fetch line
docs_shrink_check selftest: FAIL — PR-mode base fetch turned a full clone SHALLOW (.git/shallow appeared) — later gate steps read commit parents
exit 1
$ bash core/scripts/docs_shrink_check.sh --selftest   # after removing --depth=1
docs_shrink_check selftest: OK (grow green + 2 shrink mutations red + declared-intent hatch + PR-mode fetch keeps the clone full)
exit 0
```

## 3. The fixed step in the same PR clone
```
before: shallow=no a82e874 files=12
✅ docs/pm + docs/adr ledgers show no abnormal shrink
after:  shallow=no a82e874 files=12
✅ graph_check: work graph coherent (28 tickets, loop budget 4/day, scope armed where declared)
```

## 4. Repo checks
(appended below after the gate run)
```
$ bash .vteam/scripts/gate.sh
GATE: GREEN (14 steps ran, 1 declared skips) — 1 ADVISORY FAILED: schedule
$ npm test
conformance: OK — 17 fixtures, ctx.py == ctx.mjs (== ctx.sh on its scalar subset), error fixtures red in both.
conformance: OK — ledger grammar, 10 rows, lib/ledger.py == board.mjs parseLedger (kind/tok/actor/malformed).
E2E: GREEN — 199/199 checks passed
```
