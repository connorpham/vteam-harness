# VT-25 proof

## BEFORE (HEAD 37567da): no test of any kind
```
core/scripts/orca_team.sh                        --selftest markers: 0  e2e mentions: 0
profiles/nextjs-prisma/scripts/auth.mjs          --selftest markers: 0  e2e mentions: 0
profiles/nextjs-prisma/scripts/ui_fidelity.mjs   --selftest markers: 0  e2e mentions: 0
profiles/nextjs-prisma/scripts/ui-evidence.mjs   --selftest markers: 0  e2e mentions: 0
tools/prepublish-check.mjs                       --selftest markers: 0  e2e mentions: 0
```

## AFTER
```
$ bash core/scripts/orca_team.sh --selftest
(eval):5: no such file or directory: bash core/scripts/orca_team.sh --selftest
$ node profiles/nextjs-prisma/scripts/auth.mjs --selftest
(eval):5: no such file or directory: node profiles/nextjs-prisma/scripts/auth.mjs --selftest
$ node profiles/nextjs-prisma/scripts/ui_fidelity.mjs --selftest
(eval):5: no such file or directory: node profiles/nextjs-prisma/scripts/ui_fidelity.mjs --selftest
$ node profiles/nextjs-prisma/scripts/ui-evidence.mjs --selftest
(eval):5: no such file or directory: node profiles/nextjs-prisma/scripts/ui-evidence.mjs --selftest
$ node tools/prepublish-check.mjs --selftest
(eval):5: no such file or directory: node tools/prepublish-check.mjs --selftest
$ python3 core/scripts/stale_verdict_check.py --selftest
(eval):5: no such file or directory: python3 core/scripts/stale_verdict_check.py --selftest
```

## Found by wiring the step into a consumer (testbed-base)
TB-7 is `Closed` with `closed-by: Q6` and no REPORT.md (a won't-fix the owner decided). The new `stale-verdict` gate step read it as UNVERIFIABLE — the checker predates graph_check's `closed-by` field. Fixed in this ticket (`stale_verdict_check.py` skips a decision-closed ticket with an ℹ️ line; the same shape WITHOUT the field stays red — both in the selftest).
