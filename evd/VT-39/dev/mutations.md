# VT-39 · mutation ledger — code-only mutations with the tests kept (KB-R1), run 2026-09-18

Each probe mutated `core/scripts/cost_check.py` only, kept the new selftest, ran it, and restored
the file from a byte copy taken beforehand.

### M1 cache-read counted as new spend (938M of re-reads would swamp every ratio)
```
$ python3 core/scripts/cost_check.py --selftest
    assert got == {"2026-09-18": 10.0}, got
AssertionError: {'2026-09-18': 900010.0}
exit 1
```

### M2 staleness detection removed (the measured record may stop in silence)
```
$ python3 core/scripts/cost_check.py --selftest
    assert finding, lines
AssertionError: ['ℹ️  1 day(s) with ledger rows and no measured row (2026-09-18) — not audited, not a fault.', '✅ cost_check: 1 day(s) audited within 10×, measured record current', …]
exit 1
```

### M3 divergence never reported
```
$ python3 core/scripts/cost_check.py --selftest
    assert finding, lines
AssertionError: ['✅ cost_check: 1 day(s) audited within 10×, measured record current', '   (per DAY only: a session log knows the day and the model, never which ticket a token belonged to)']
exit 1
```

### M4 one line per unmeasured day instead of one compact line
```
$ python3 core/scripts/cost_check.py --selftest
    assert len(compact) == 1 and "+7 more" in compact[0], lines
AssertionError: ['ℹ️  10 day(s) with ledger rows and no measured row (2026-09-02, 2026-09-03, 2026-09-04, 2026-09-05, 2026-09-06, 2026-09-07, 2026-09-…']
exit 1
```

### M5 malformed ledger rows contribute to the claimed total
```
$ python3 core/scripts/cost_check.py --selftest
    out[r["date"]] = out.get(r["date"], 0.0) + float(r["tok_k"])
TypeError: float() argument must be a string or a number, not 'NoneType'
exit 1
```

Five probes, five REDs. After the last restore `--selftest` is green and the file is byte-identical
to the copy taken before the first probe.
