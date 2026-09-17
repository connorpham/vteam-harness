# Mutation probes — the fix is broken on purpose, its test must go RED, then restored

Two kinds. **Whole-file revert** (`git show HEAD:<file>`) is valid only when the test lives in
ANOTHER file — conformance for ctx.py, evd_check's selftest for evdpack, e2e for manifest/update,
a render probe for copilot. For the four fixes whose selftest sits in the same file, a whole-file
revert takes the new test with it and proves nothing (the first attempt did exactly that and read
GREEN); those use a **code-only mutation** below, with the new selftest kept in place.
(run 2026-09-17 15:52 on branch fix/VT-24-code-review-fixes, working tree = the fix)

$ python3 core/scripts/gate.py --selftest
exit 0
gate selftest: OK (green + substitution, red stops, run-less red, silent-skip red, declared skip loud, requires_cmd green/skip/red, 2 WEAK banners, echo-test tripwire — advisory (6 fixtures): fails-without-blocking, still-prints, banner on GREEN, passes silently leaving no banner, non-boolean reds, a hard red BEFORE and AFTER it still stops the run, and a bookkeeping-only run stays WEAK while naming the advisory)
```

## 9a ctx.py parity (conformance) — reverted `core/scripts/lib/ctx.py`
```
$ node tests/conformance.mjs
exit 1
empty inline-list element (must die in both)        ❌  ✅   —  ❌
first key indented (must die, never drop the rest)  ❌  ✅   —  ❌
```

$ python3 core/scripts/schedule_check.py --selftest
exit 0
schedule_check selftest: OK (on-schedule green + 3 reds + parser guard + hour units at 8h/day, rescaled at 4h/day, unknown unit red)
```

$ python3 core/scripts/bdd_report_check.py --selftest
exit 0
bdd_report_check selftest: OK (good green + 6 mutations red + And/But inheritance)
```

$ python3 core/scripts/graph_check.py --selftest
exit 0
graph_check selftest: OK (coherent graph green + 9 reds + 2 new greens: dangling, cycle, done-sans-verdict, done-with-FAIL, identical repeat, loop budget, out-of-scope commit — + loud skips: undeclared scope, remote tracker — + attribution, 17 positive / 12 negative: leading key attributed (bare/`type:`-prefixed/`feat(KEY):`/multi-scope `feat(a,KEY):`/`[KEY]`/`Revert "…"`), prose mention + longer key + merge-commit NOT, both directions proven end-to-end on the same out-of-scope directory)
```

## 10 attach section (evd_check selftest) — reverted `core/scripts/lib/evdpack.py`
```
$ python3 core/scripts/evd_check.py --selftest
exit 1
❌ P-1 [Done]: 21 problem(s), and the ticket is closed
❌ P-1 [Closed]: 21 problem(s), and the ticket is closed
❌ P-1 [Resolved]: 21 problem(s), and the ticket is closed
    _selftest()
  File "/Users/connorpham/Documents/vteam/core/scripts/evd_check.py", line 792, in _selftest
ImportError: cannot import name 'replace_section' from 'evdpack' (/Users/connorpham/Documents/vteam/core/scripts/lib/evdpack.py)
```

## 4 YAML quote (render probe) — reverted `adapters/copilot.mjs`
```
$ node --input-type=module -e import {render} from "./adapters/copilot.mjs"; import fs from "node:fs"; const d=fs.readFileSync("core/workflows/plan.md","utf8").match(/^description:\s*(.*)$/m)[1]; const t=render({name:"plan",description:d,args:"",body:"x"},{noSubagentNote:""}).text.split("\n")[1]; if(!/^description: "[^"]*"$/.test(t)){console.log("NOT QUOTED:",t.slice(0,50));process.exit(1)} console.log("QUOTED-OK")
exit 1
NOT QUOTED: description: Greenfield planning intake — for proj
```

## 6 prune (e2e 5b) — reverted `src/cli/manifest.mjs`
```
$ node tests/e2e.mjs
exit 1
  ✅ doctor ran the selftests
3. installed gate selftests (discovered — mirrors doctor)
  ✅ README's selftest count matches discovery (33)
  ✅ selftest annotate.py
  ✅ selftest app_check.sh
  ✅ selftest bdd_report_check.py
```

## 3 provider follows config (e2e 5b) — reverted `src/cli/update.mjs`
```
$ node tests/e2e.mjs
exit 1
  ✅ doctor ran the selftests
3. installed gate selftests (discovered — mirrors doctor)
  ✅ README's selftest count matches discovery (33)
  ✅ selftest annotate.py
  ✅ selftest app_check.sh
  ✅ selftest bdd_report_check.py
```

## 1 gate --help — code-only mutation in `core/scripts/gate.py`: `if any(a in ("--help", "-h") for a in args):` → `if False and any(a in ("--help", "-h") for a in args):`
```
$ python3 core/scripts/gate.py --selftest
exit 1
    assert r.returncode == 0 and "GATE-RAN" not in r.stdout and "gate.py" in r.stdout, \
AssertionError: --help must print usage and run no step:
```

## 1b gate unknown flag — code-only mutation in `core/scripts/gate.py`: `    if flags:
        # Every` → `    if False and flags:
        # Every`
```
$ python3 core/scripts/gate.py --selftest
exit 1
    assert r.returncode == 2 and "unknown flag" in r.stdout and "GATE-RAN" not in r.stdout, \
AssertionError: an unknown flag must exit 2 and run nothing:
```

## 11 Due column (header ignored, first dated cell) — code-only mutation in `core/scripts/schedule_check.py`: `        if "due" in low:  # a header row` → `        if False and "due" in low:  # a header row`
```
$ python3 core/scripts/schedule_check.py --selftest
exit 1
    assert b == ["Q4 — due 2026-01-09 (4 days left)"], b
AssertionError: ['Q4 — due 2026-01-09 (4 days left)', 'Q5 — due 2026-01-01 (OVERDUE)']
```

$ python3 core/scripts/schedule_check.py --selftest
exit 0
schedule_check selftest: OK (on-schedule green + 3 reds + Due column by header + parser guard + hour units at 8h/day, rescaled at 4h/day, unknown unit red)
```

$ python3 core/scripts/bdd_report_check.py --selftest
exit 0
bdd_report_check selftest: OK (good green + 6 mutations red + And/But inheritance + --root <dir> scans instead of crashing)
```

## 12 configured homes ignored — code-only mutation in `core/scripts/graph_check.py`: `legal = always_legal(c)` → `legal = ALWAYS_LEGAL`
```
$ python3 core/scripts/graph_check.py --selftest
exit 1
    assert r.returncode == 0, \
AssertionError: a commit under the CONFIGURED evidence dir must not read as derailment:
```

## 9b ctx.mjs first-key indent — code-only mutation in `core/scripts/lib/ctx.mjs`: `if (lines.length && lines[0][1] !== 0) {` → `if (false) {`
```
$ node tests/conformance.mjs
exit 1
tab indentation (must die)                          ✅  ✅   —  ✅
malformed flow: entry without value (must die)      ✅  ✅   —  ✅
malformed flow: unterminated mapping (must die)     ✅  ✅   —  ✅
malformed flow: unterminated list (must die)        ✅  ✅   —  ✅
```

## 7 detectProfile ignores next — code-only mutation in `src/cli/init.mjs`: `return has("prisma/schema.prisma") && deps.next ? "nextjs-prisma" : "node";` → `return has("prisma/schema.prisma") ? "nextjs-prisma" : "node";`
```
$ node tests/e2e.mjs
exit 1
  ✅ legacy ledger + team.size 2 → log_check RED naming the Actor column
E2E: RED — 191/192 checks passed
```

## 11b Due fallback (first instead of last dated cell) — code-only mutation in `core/scripts/schedule_check.py`: `cell = dated[-1] if dated` → `cell = dated[0] if dated`
```
$ python3 core/scripts/schedule_check.py --selftest
exit 1
    assert b == ["Q6 — due 2026-01-09 (4 days left)"], b
AssertionError: ['Q6 — due 2026-01-01 (OVERDUE)']
```

## 8 bdd --root value read as a file (the old shape) — code-only mutation in `core/scripts/bdd_report_check.py`: `    if a.files:
        files = [Path(f) for f in a.files]` → `    if a.files or a.root:
        files = [Path(f) for f in (a.files or [a.root])]`
```
$ python3 core/scripts/bdd_report_check.py --selftest
exit 1
    assert r.returncode == 0 and "nothing to check" in r.stdout, \
AssertionError: --root <dir> must scan, not crash:
IsADirectoryError: [Errno 21] Is a directory: '/var/folders/p5/gwpz6jg12xg02_9vfw8fb25m0000gn/T/tmpc89g4lev'
```
