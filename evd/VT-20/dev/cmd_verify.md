# VT-20 — command verification

## AC1 — the three unreachable skills can now be reached
```
/ba    competenc x3
/pm    competenc x3
/qa    competenc x9
/dev   competenc x9
```

Before this ticket /ba and /pm both returned **0**, and the reach audit read 28/31.

## AC2 — the new rules red on the exact bug
```
$ (temporarily strip the loading paragraph from /ba) && competency_check
❌ competency_check: 1 problems
   - ba/: the /ba workflow never mentions competencies, so none of its 2 file(s) is ever
     read by the lane — a competency the lane cannot reach is decoration
```

## AC3 — the corrected measurement
```
profile: matches on 9/9 tickets
dev total: 98 files / 108365 tokens (published as 81 / 84,863)
worst ticket: 15 files
```

## AC4 — the consumer repo, before and after
```
before the source INDEX was regenerated:
  $ vteam update && competency_check      (in the consuming repo)
  ❌ - dev/INDEX.md is stale — run `competency_check.py --write-index`

after:
  ✅ competency_check: 31 competencies well-formed and indexed
```

```
▶ doctrine-source: python3 .vteam/scripts/competency_check.py --root core/doctrine/competencies
GATE: GREEN (11 steps ran, 1 declared skips)
```

## AC5 — no rule is stated twice in one role's always set
```
always-rule titles shared inside one role: 0
```
