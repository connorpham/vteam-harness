# VT-5 — parallel_check probes (real runs, branch feat/VT-5-parallel-team, 2026-09-08)

```console
# selftest — every rule proves it can go red
$ python3 core/scripts/parallel_check.py --selftest
parallel_check selftest: OK (parse + nest/equal/disjoint + conflicts: disjoint green, overlap red, missing-scope red, over-cap comparison)

# OFF by default (this repo, team.parallel: 1) → inert green
$ python3 .vteam/scripts/parallel_check.py
✅ parallel_check: parallel mode off (team.parallel=1) — nothing to check

# turn parallel ON (team.parallel: 2) with 4 real in-flight VT-* branches that all touch README/core
$ python3 .vteam/scripts/parallel_check.py
❌ parallel_check: 5 problems in the in-flight set
   - 4 DEV branches in flight but team.parallel=2 — over the concurrency cap (VT-2, VT-3, VT-4, VT-5)
   - VT-5: no CODE-SCOPE in its tasksheet — can't prove it is disjoint from the others (add CODE-SCOPE at /dev T1)
   - VT-2 and VT-3 share edit territory (core ∩ core/doctrine/competencies) — serialize them; parallel branches on one file merge blind
   - VT-2 and VT-4 share edit territory (core ∩ core/doctrine/competencies/qa) — serialize them; parallel branches on one file merge blind
   - VT-3 and VT-4 share edit territory (core/doctrine/competencies ∩ core/doctrine/competencies/qa) — serialize them; parallel branches on one file merge blind
exit=1
```
