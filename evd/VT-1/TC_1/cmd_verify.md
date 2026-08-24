# TC_1 — command transcripts (captured 2026-08-24T04:42:37Z at 574bd6c)

## doctor (AC-1)

```console
$ node bin/vteam.mjs doctor
✅ manifest verified (55 framework-owned files intact)
✅ gate selftests green (22 discovered checks prove they can red)
PREFLIGHT: GREEN — the ticket→design→code→git chain runs end-to-end
```

## npm test (AC-2)

```console
$ npm test
  ✅ PASS verdict → nothing to resume
  ✅ --json carries the same derivation
  ✅ resume is a pure reader (two runs, identical output)
  ✅ README's "141 checks" claim matches the suite (141)

E2E: GREEN — 141/141 checks passed
```

## audit after install (AC-4 — baseline before install: 62 C)

```console
$ node bin/vteam.mjs audit --json | jq '.score, .grade'
score 91 A
```

## hooks untouched (AC-1)

```console
$ git status --porcelain | grep githooks | wc -l
0
$ git config core.hooksPath
.githooks
```
