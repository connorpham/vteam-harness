# VT-16 — routing cost, measured

Run on d4b7462+ against the field trial's backlog at
`~/Documents/testbed-base/docs/backlog` (9 tickets, TB-1..TB-9).

## AC1/AC5 — cost per ticket per lane
```
$ python3 core/scripts/route_check.py --backlog <testbed>/docs/backlog --json | summarise
ticket  lane    files   words  tokens   body-only matches
TB-1    ba          2    1782    2405   -
TB-1    dev         5    3096    4179   -
TB-1    pm          1     837    1129   -
TB-1    qa          9    6602    8912   -
TB-2    ba          2    1782    2405   -
TB-2    dev         5    3096    4179   -
TB-2    pm          1     837    1129   -
TB-2    qa          9    6602    8912   -
TB-3    ba          2    1782    2405   -
TB-3    dev        13   10596   14304   dev-api-design, dev-async-work, dev-debugging, dev-domain-modeling, dev-observability
TB-3    pm          1     837    1129   -
TB-3    qa         10    7370    9949   qa-security-probes
TB-4    ba          2    1782    2405   -
TB-4    dev        15   12793   17270   dev-api-design, dev-async-work, dev-content-pipelines, dev-debugging, dev-observability
TB-4    pm          1     837    1129   -
TB-4    qa         10    7370    9949   qa-security-probes
TB-5    ba          2    1782    2405   -
TB-5    dev        13   10613   14327   dev-api-design, dev-concurrency-and-transactions, dev-debugging, dev-domain-modeling, dev-observability
TB-5    pm          1     837    1129   -
TB-5    qa         11    8469   11433   qa-combinatorial-design, qa-security-probes
TB-6    ba          2    1782    2405   -
TB-6    dev        10    8004   10805   dev-data-modeling, dev-mobile-craft, dev-query-performance
TB-6    pm          1     837    1129   -
TB-6    qa         10    7370    9949   -
TB-7    ba          2    1782    2405   -
TB-7    dev         7    5004    6755   -
TB-7    pm          1     837    1129   -
TB-7    qa          9    6602    8912   -
TB-8    ba          2    1782    2405   -
TB-8    dev         8    6064    8186   -
TB-8    pm          1     837    1129   -
TB-8    qa          9    6602    8912   -
TB-9    ba          2    1782    2405   -
TB-9    dev         8    6064    8186   dev-debugging
TB-9    pm          1     837    1129   -
TB-9    qa          9    6602    8912   -
dev: files 5-15, tokens 4179-17270
qa: files 9-11, tokens 8912-11433
pairs with a body-only match: 8 of 36
```

## AC2 — the flag, and the clearest false matches
```

TB-6 / dev: 10 files, 8004 words ≈ 10805 tokens
  always (5): dev-codebase-design, dev-error-handling, dev-identity, dev-security-basics, dev-testing-craft
  routed: dev-data-modeling                  ← term:migration in body   ⚠ body-only
  routed: dev-debugging                      ← term:bug in summary+body; term:regression in body
  routed: dev-frontend-craft                 ← label:ui in labels; term:component in labels+title+summary+body; term:css in body
  routed: dev-mobile-craft                   ← term:permission in body   ⚠ body-only
  routed: dev-query-performance              ← term:pagination in body   ⚠ body-only
  ⚠ pulled in by a word appearing ONLY in the prose, not in the title, labels, summary or criteria: dev-data-modeling, dev-mobile-craft, dev-query-performance

1 ticket/lane pairs · 10 competency files · ≈10805 tokens total
1 pair(s) load at least one competency matched only in the prose.
A body-only match is a SIGNAL, not a verdict: a ticket may legitimately describe its subject only in the body. Read the token before deleting it.
```

TB-6 is a CSS focus-ring ticket. `dev-mobile-craft` and `dev-query-performance` are
pulled in by "permission" and "pagination" appearing in its prose.

## AC3 — the flags behave
```
$ route_check.py --ticket TB-8 --role qa

TB-8 / qa: 9 files, 6602 words ≈ 8912 tokens
  always (7): qa-case-writing, qa-heuristics, qa-hostile-inputs, qa-identity, qa-report-writing, qa-requirement-smells, qa-test-design
  routed: qa-accessibility-verification      ← label:ui in labels; term:screen in criteria+body; term:contrast in summary+criteria+body
  routed: qa-user-mindset                    ← label:ui in labels; term:screen in criteria+body; term:page in summary+criteria+body; term:button in title+summary+criteria+body

1 ticket/lane pairs · 9 competency files · ≈8912 tokens total
0 pair(s) load at least one competency matched only in the prose.

$ route_check.py --json | python3 -c "import json,sys; json.load(sys.stdin); print(\"valid JSON\")"
valid JSON, 36 rows
```

## AC4 — a report, not a gate
```
default exit: 0   (body-only matches present, still 0)
--strict exit: 1
```

## Correction, 2026-09-11 — the instrument was undercounting

Found in an end-to-end review of the flow, not by a gate. `route_check.py` shipped with only four
of the six `applies:` token kinds implemented: `always`, `label:`, `term:` and (later) `type:`.
**`profile:` and `path:` were silently ignored**, so every figure this pack published was a floor,
not a measurement. A second bug compounded it: the CLI read `stack.profile` from the repo the
script *ran from* rather than the repo whose backlog was being measured, which dropped the profile
match even after the token was implemented.

Both are fixed. The corrected figures, one instrument, one reading:

| | files | tokens |
|---|---|---|
| published here | 84 | 88,191 |
| **actual** | **102** | **113,156** |
| worst single ticket | 15 / 17,270 | **15 / 17,459** |

The *conclusions* survive, and the direction was never in doubt — the worst ticket still opens
fifteen competency files, and body-only matches are still the cause. What was wrong is the
absolute size of the problem: it is **21% larger** than this pack reported. The rejected
narrowing experiment was run with the same broken instrument on both sides, so its comparison
holds even though its absolutes do not.
