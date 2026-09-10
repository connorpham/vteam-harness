# VT-19 — command verification

## AC1 — the grammar accepts type: and still rejects a typo
```
$ python3 core/scripts/competency_check.py --selftest
competency_check selftest: OK (valid file green + 7 mutations red + index missing/stale red)

$ python3 core/scripts/competency_check.py
✅ competency_check: 31 competencies well-formed and indexed under /Users/connorpham/Documents/vteam/docs/team/competencies
```

## AC2 + AC3 — a Bug ticket routes on its type, not on the word
```
$ route_check.py --ticket TB-9 --role dev   (TB-9 is type: Bug)
  routed: dev-async-work                     ← term:queue in body   ⚠ body-only
  routed: dev-debugging                      ← type:Bug in type; term:regression in criteria+body
  ⚠ pulled in by a word appearing ONLY in the prose, not in the title, labels, summary or criteria: dev-async-work
```

Before this ticket the same row read `dev-debugging ← term:bug in body ⚠ body-only`.

## AC4 — the before/after numbers
```
ticket    files   tokens   body-only
TB-1          5     4179   -
TB-2          5     4179   -
TB-3         11    11726   dev-api-design, dev-async-work, dev-domain-modeling
TB-4         14    16164   dev-api-design, dev-async-work, dev-content-pipelines, dev-observability
TB-5         12    13221   dev-api-design, dev-concurrency-and-transactions, dev-domain-modeling, dev-observability
TB-6         10    10805   dev-data-modeling, dev-mobile-craft, dev-query-performance
TB-7          7     6755   -
TB-8          8     8186   -
TB-9          9     9648   dev-async-work
total        81    84863   5/9 pairs still body-only

before (VT-16 measurement): 84 files / 88191 tokens
```

## The residual, said plainly

TB-9 is a ticket about focus outlines. It loads `dev-async-work` because the word **queue**
appears once in its prose. `type:` cannot reach that — the ticket's type is Bug and the false
match is a `term:`. Five of nine dev pairs are still in that shape. That is D13 (B) or (C),
and this ticket deliberately does not touch it.
