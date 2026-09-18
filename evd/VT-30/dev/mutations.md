# VT-30 · mutation ledger — every probe is a code-only mutation with the new test kept (KB-R1), run 2026-09-18

### M2 verbatim_gate: old bold-only, digits-only ROW regex restored (test kept) — FIRST ATTEMPT INVALID (the mutation script failed on a regex escape and never changed the file; exit 0 below is that non-mutation). Redone as a string replace:
```
$ python3 core/scripts/verbatim_gate.py --selftest
verbatim_gate selftest: OK (match green + drift/ghost red + notes exempt + unbolded/AC-A01 codes + configured-but-vacuous red)
exit 0
```
### M3 verbatim_gate: configured-but-vacuous rule deleted (test kept)
```
$ python3 core/scripts/verbatim_gate.py --selftest
RESULT: every coded row matches the sources verbatim ✅

exit 1
```
### M4 token_check: existence filter removed from pickRoots (test kept)
```
$ node profiles/nextjs-prisma/scripts/token_check.mjs --selftest

Node.js v24.15.0
exit 1
```
### M5 app_check: owner_check call removed (FOREIGN test kept)
```
$ bash core/scripts/app_check.sh --selftest
app_check selftest: FAIL (a stranger's server must be FOREIGN, got: APP: UP http://127.0.0.1:54649 (HTTP 200))
core/scripts/app_check.sh: line 118: 88846 Terminated: 15          ( cd "$td" && exec python3 -u -m http.server 0 --bind 127.0.0.1 ) > "$td/srv.log" 2>&1
exit 1
```
### M7 graph_check: E14 ledger-row rule deleted (m0 test kept)
```
$ python3 core/scripts/graph_check.py --selftest
✅ graph_check: work graph coherent (3 tickets, loop budget 4/day, scope armed where declared)

exit 1
```
### M1a preflight (fixed) on a repo with no origin
```
$ bash .vteam/scripts/preflight.sh  # in a fixture without origin
⚠️  Hosting CLI    skipped — no origin remote, nothing to push to
PREFLIGHT: GREEN — the ticket→design→code→git chain runs end-to-end
exit 0
```
### M1b preflight mutated back to miss on no-origin (same fixture)
```
$ bash .vteam/scripts/preflight.sh
❌ Git            no origin remote
PREFLIGHT: RED — clear the ❌ items above, then re-run
exit 0
```
### M6 gate.sh reverted to exec (no transcript) — the e2e check's regex
```
$ bash core/scripts/gate.sh --help | grep -c '📝 transcript:'
0
exit 1
```

### M2 (redo) — old regex restored by exact string replace
```
$ python3 core/scripts/verbatim_gate.py --selftest
    assert ROW.match("| AC-A01 | 2 | `GET /login` renders |").group(1) == "AC-A01"
AttributeError: 'NoneType' object has no attribute 'group'
exit 1
```

Summary: M1b RED (PREFLIGHT: RED), M2 RED, M3 RED (exit 1), M4 RED (exit 1), M5 RED (FOREIGN not detected), M6 RED (0 transcript lines), M7 RED (exit 1). Every file restored; `git status` shows only the seven intended files.
