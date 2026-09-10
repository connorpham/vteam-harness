# VT-15 — command verification

Every block below is a command and its real output, run on dfa10f1+ (working tree).

## AC1 — the doctrine now names the second rendering mode
```
$ grep -ril "forced.colors\|high contrast" core/doctrine/
core/doctrine/competencies/qa/reference/forced-colors.md
core/doctrine/competencies/qa/qa-accessibility-verification.md
core/doctrine/competencies/qa/reference/qa-accessibility-verification.md
core/doctrine/competencies/dev/dev-frontend-craft.md
core/doctrine/competencies/dev/reference/dev-frontend-craft.md
```

## AC2 — both competencies still inside competency_check's 1100-word ceiling
```
qa/qa-accessibility-verification: 1100 words
dev/dev-frontend-craft: 1089 words
ba/ba-acceptance-criteria: 962 words
qa/qa-requirement-smells: 798 words
```

## AC3 — the falsification question is present on both sides
```
$ grep -c "if this check passed and the behaviour were still broken" core/doctrine/competencies/ba/ba-acceptance-criteria.md core/doctrine/competencies/qa/qa-requirement-smells.md
core/doctrine/competencies/qa/qa-requirement-smells.md:1
core/doctrine/competencies/ba/ba-acceptance-criteria.md:1
```

## AC5 — competency_check and the full gate
```
$ python3 core/scripts/competency_check.py
✅ competency_check: 31 competencies well-formed and indexed under /Users/connorpham/Documents/vteam/docs/team/competencies
```

## AC4 — `gate e2e` now reaches e2e (proved on the testbed, not by reading YAML)

The same guard was applied to `~/Documents/testbed-base/.vteam/profiles/nextjs-prisma/gates.yaml`
(testbed commit `18e6c66`) and the tail mode run before and after.

```
before  $ bash .vteam/scripts/gate.sh e2e
        ▶ integration: pnpm run test:integration
        [ERR_PNPM_NO_SCRIPT] Missing script: test:integration
        GATE: RED at integration                          (14 steps ran, 4 declared skips)

after   $ bash .vteam/scripts/gate.sh e2e
        ▶ e2e: pnpm run test:e2e
        ⚠️  skipped integration: requires_cmd probe failed — no test:integration script in
            package.json — integration suite not adopted on this repo
        GATE: GREEN (15 steps ran, 3 declared skips)
```

The probe itself, checked on the repo where one script is present and the other is not:

```
$ node -e "const s=(require('./package.json').scripts)||{};process.exit(s['test:integration']?0:1)"; echo $?
1        → declared skip
$ node -e "const s=(require('./package.json').scripts)||{};process.exit(s['test:e2e']?0:1)"; echo $?
0        → the step runs
```

## What this evidence does NOT claim

The `npm` → `{package_manager}` change in the same two manifests is a **portability** fix, not
a bug fix, and the difference was measured rather than assumed. On the testbed,
`npm run test:e2e` at the repo root resolves the script, runs Playwright (`2 passed`) and
creates no `package-lock.json`, so `lockfile_check` stays green. It would bite a repo where
npm is absent or where the script lives only inside a workspace package. Stated here because
the honest version of this ticket is smaller than the tempting one.
