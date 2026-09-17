════ BEFORE proofs (HEAD 32cefbe) ════

## 1. gate.py --help runs the gate (perl alarm 6s)
```
▶ docs-shrink: bash .vteam/scripts/docs_shrink_check.sh
✅ docs/pm + docs/adr ledgers show no abnormal shrink
▶ ledger: python3 .vteam/scripts/log_check.py
exit 120
```

## 2. stale_verdict_check in profiles
```
0 of 6 profiles
```

## 3. update.mjs reads tracker.provider?
```
0
```

## 4. copilot render of plan.md → YAML
```
---
description: Greenfield planning intake — for projects that have NEITHER code NOR documentation. Interviews the owner section by section (a five-field kerne…
YAML ERROR: mapping values are not allowed here
```

## 8. bdd_report_check --root <dir>
```
IsADirectoryError: [Errno 21] Is a directory: '/tmp'
```

## 9. ctx parity
```
py  [a,,b] → ['a', '', 'b']
py  indented first line → {'a': 1}
mjs [a,,b] → THROWS: ctx: vteam.config.yaml:1: outside the vteam YAML subset (anchors/multiline): ""
mjs indented first line → {"a":1}
```

## 10. attach regex erases everything after the heading
```
Notes for QA survived: False
```

## 11. schedule_check takes the FIRST dated cell as due
```
burning: ['Q1 — due 2026-01-01 (OVERDUE)']
```

## 7. detectProfile: prisma + package.json, no next
```
  profile: nextjs-prisma
```

════ AFTER — same probes, working tree = the fix ════

## 1. gate.py --help
```
gate.py — the verification-gate driver: runs the stack profile's step manifest.

exit 0 — no ▶ step line
gate: unknown flag(s) --bogus — usage: gate.py [--help] [<tail> …] (a tail names a `tail: true` step, e.g. e2e)
exit 2
```

## 2. stale_verdict in profiles
```
profiles/generic/gates.yaml:1
profiles/go/gates.yaml:1
profiles/nextjs-prisma/gates.yaml:1
profiles/python/gates.yaml:1
profiles/node/gates.yaml:1
profiles/rust/gates.yaml:1
```

## 3. update.mjs reads tracker.provider
```
55:  for (const [kind, key, builtin] of [["tracker", "tracker.provider", "markdown"],
```

## 4. copilot render → YAML
```
description: "Greenfield planning intake — for projects that have NEITHER code N…
```

## 8. bdd --root
```
✅ bdd_report_check: no *.bdd.md reports — nothing to check
```

## 9. ctx parity
```
ctx: vteam.config.yaml:1: empty value in an inline list — outside the vteam YAML subset
ctx: vteam.config.yaml:1: the first key must start at column 0
mjs: ctx: vteam.config.yaml:1: empty value in an inline list — outside the vteam YAML subset
mjs: ctx: vteam.config.yaml:1: the first key must start at column 0
```

## 10. attach keeps trailing prose
```
Notes for QA survived: True
```

## 11. schedule Due column
```
burning: []
```

## 7. detectProfile
```
(e2e 5c: prisma+express → node; prisma+next → nextjs-prisma — 192/192)
```

## Suite
```
npm test: 192/192 · doctor: 33 selftests green, manifest 171 files intact · gate.sh: GREEN (14 steps, stale-verdict ran, schedule advisory)
```
