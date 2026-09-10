# VT-17 — command verification

## T0 — the gap, before any code
```
$ grep -c evd_check core/workflows/qa.md
13
$ git show HEAD~1:profiles/nextjs-prisma/gates.yaml | grep -c evd_check   # before this ticket
0
0
```

## AC1 + AC5 — the sweep, and the legacy pack it reports without failing
```
$ python3 core/scripts/evd_check.py --sweep
⚠️  VT-1 [Done] (legacy pack — pre-dates the KIND standard): 1 problem(s) — reported, not failed, because the pack pre-dates this standard
     - MISSING verifysheet.md — QA designs the test plan (V1/V2: EXPECTED with spec citations + the TC journeys) BEFORE touching a browser, and the plan commits with the dossier
✅ evd_check --sweep: 0 pack(s) green, 1 reported without failing
exit: 0
```

## AC2 — the existing path and the selftest are untouched
```
$ python3 core/scripts/evd_check.py --selftest
evd_check selftest: OK (fixture green + 9 mutations red — incl. missing/TC-less verifysheet — + the UI journey: full walk green, each of AS/PRECONDITION/ENTRY/AFTER/BACK demanded by name, 3 URL-only ENTRYs red, click-path+URL green, unannotated PASS red; v2 readable pack green + 14 readability mutations red: vague EXPECTED/ACTUAL, invalid KIND, no boundary/whole-screen, no ENVIRONMENT/ORACLE, COVERAGE missing/lens-less/reasonless/ghost-TC, write-readback w/o db_verify, bare TC_n, stale index — legacy pack stays green)
```

## AC3 — the step runs in the gate
```
▶ evd: python3 .vteam/scripts/evd_check.py --sweep
✅ evd_check --sweep: 0 pack(s) green, 1 reported without failing
GATE: GREEN (10 steps ran, 1 declared skips)
```

## AC4 — it goes RED on the exact failure that shipped past the author

Run on the field-trial repo, where TB-8 is Done. A real case folder was moved away and put back.
```
$ mv evd/TB-8/TC_4_the_failure_edge_is_exactly_zero_pixels /tmp/ && bash .vteam/scripts/gate.sh
▶ evd: python3 .vteam/scripts/evd_check.py --sweep
❌ TB-8 [Done]: 3 problem(s), and the ticket is closed
     - manifest.md: the index no longer matches the case folders — an index that lies is worse
       than none; run python3 .vteam/scripts/evd_index.py --evd .../evd/TB-8
GATE: RED at evd

$ mv /tmp/TC_4_... back && python3 .vteam/scripts/evd_index.py --evd evd/TB-8 && bash .vteam/scripts/gate.sh
✅ TB-8 [Done]: meets the evidence standard
✅ evd_check --sweep: 5 pack(s) green, 0 reported without failing
GATE: GREEN (15 steps ran, 4 declared skips)
```

## What this does not claim

The sweep cannot tell whether a pack's evidence is *true* — only whether the pack is complete
and internally consistent. TB-8's first pack would have been caught by this gate; its FALSE
claim about the filter bar ("nothing at all", when four controls change 184-484 pixels) would
not. That needed a challenger who re-measured. Structure is gateable; honesty is not.
