# VT-30 · proof — commands run on 2026-09-18 with their real output

## 1. Selftests carrying the new RED cases
```
$ python3 core/scripts/verbatim_gate.py --selftest
verbatim_gate selftest: OK (match green + drift/ghost red + notes exempt + unbolded/AC-A01 codes + configured-but-vacuous red)
$ python3 core/scripts/graph_check.py --selftest
graph_check selftest: OK (coherent graph green + 9 reds + 2 new greens: dangling, cycle, done-sans-verdict, done-with-FAIL, identical repeat, loop budget, out-of-scope commit — + loud skips: undeclare
$ bash core/scripts/app_check.sh --selftest
app_check selftest: OK (SKIP on unset url + UP on a live server + health path joined + DOWN red naming app.start + FOREIGN red on a stranger's server + trailing flag refused)
$ node profiles/nextjs-prisma/scripts/token_check.mjs --selftest
token_check selftest: OK (extractor matrix green + code_paths roots skip missing dirs)
```

## 2. The two e2e checks (§5b) on a fresh install
```
  ✅ gate.sh names its transcript file and the file carries the GATE line
  ✅ preflight on a local-only repo (no origin) is GREEN and names the local-merge rule
E2E: GREEN — 201/201 checks passed
```

## 3. Gate and suite on the branch
```
$ bash .vteam/scripts/gate.sh
GATE: GREEN (14 steps ran, 1 declared skips) — 1 ADVISORY FAILED: schedule
📝 transcript: /var/folders/p5/gwpz6jg12xg02_9vfw8fb25m0000gn/T//vteam-gate-vteam.log
$ npm test
conformance: OK — 17 fixtures, ctx.py == ctx.mjs (== ctx.sh on its scalar subset), error fixtures red in both.
conformance: OK — ledger grammar, 10 rows, lib/ledger.py == board.mjs parseLedger (kind/tok/actor/malformed).
E2E: GREEN — 201/201 checks passed
```

## 4. Testbed dry run of the two new rules (~/Documents/testbed-base, its own config)
```
$ python3 ~/Documents/vteam/core/scripts/graph_check.py
✅ graph_check: work graph coherent (10 tickets, loop budget 4/day, scope armed where declared)
$ python3 ~/Documents/vteam/core/scripts/verbatim_gate.py      # NEW rule
❌ verbatim_gate: 2 source document(s) configured but NO coded requirement rows recognised — the gate would pass vacuously (field finding E4).
   A coded row starts `| CODE |` or `| **CODE** |` with CODE like REQ-AUTH-12, AC-A01, TB-5. Sources: /Users/connorpham/Documents/testbed-base/docs/requirements/REQ-001-media-contacts.md, /Users/conno
$ python3 .vteam/scripts/verbatim_gate.py                       # the rule shipped today (0.19.0)
verbatim_gate: 0 coded rows across 2 shards
RESULT: every coded row matches the sources verbatim ✅
```
The testbed's REQ documents number their rows (`| 1 | Name | …`) and carry no codes: the shipped gate reported "0 coded rows … ✅" for the whole trial. That is E4 in the wild, and it is why the new rule REDs rather than warns.

## 5. Mutations
See mutations.md — seven code-only mutations, tests kept, all RED; the first M2 attempt is recorded as invalid and redone.
