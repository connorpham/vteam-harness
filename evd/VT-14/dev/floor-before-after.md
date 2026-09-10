# VT-14 — the /qa floor, three milestones

BASE-COMMIT: dfa10f1 · CAPTURED-AT: 2026-09-10T08:37:08Z

Floor = skill catalogue + lane SKILL.md + role doc + INDEX + `always` competencies,
accumulated by the end of a task, before the ticket/spec/code are read.

```
  before VT-14            always 6367 words   floor  21169 tok
  after moving 3 sections always 5407 words   floor  19873 tok   -1296
  after routing user-mindset always 4663 words   floor  18869 tok   -1004
                                              TOTAL -2300 (10.9%)
```

Honest limits, recorded so the number is not read as more than it is:

- The second saving applies only to a **non-UI** verification. On a UI ticket
  `qa-user-mindset` matches and loads exactly as before, so the saving is the
  first line only (−1,296).
- −10.9% is an improvement, not a fix. The two heaviest items are untouched:
  `qa/SKILL.md` at 6,844 tokens (34% of the floor) and the 40-skill catalogue at
  3,498 tokens, paid in every session regardless of lane.
- The catalogue grew by ~1,050 tokens in VT-13 and that was not measured at the
  time. VT-14 does not undo it.
