# VT-13 — context budget: the claim that the nine DEV/QA files cost nothing

COMMIT: dfa10f1 (values below are the merged state, before VT-14 moved anything)
CAPTURED-AT: 2026-09-10T08:36:30Z

Claim in the CHANGELOG: the nine DEV/QA competencies are conditionally routed,
so the `always` budget is unchanged; the three BA/PM ones are `always` on purpose
and their cost is stated. Measured per lane, words of body:

```
  lane   competency   always(before → after)   conditional
  DEV    10 → 17      3897 → 3897  (+0%)       11752 words across 12 files
  QA      9 → 11      6367 → 6367  (+0%)        3993 words across  3 files
  BA      0 →  2         0 → 2155  (new cost)      0
  PM      0 →  1         0 → 1076  (new cost)      0
```

The one cost NOT measured at the time, and recorded here because it is real:
the skill catalogue (name + description of every skill, injected in every
session regardless of lane) went from ~2,448 to 3,498 tokens as the count went
28 → 40. That omission is the reason VT-14 exists.
