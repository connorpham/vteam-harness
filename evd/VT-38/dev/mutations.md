# VT-38 · mutation ledger — code-only mutations with the tests kept (KB-R1), run 2026-09-18

### M1 (graph) bỏ --no-merged: nhánh đã merge lại tính là đang chạy
```
$ npm test
  ❌ a branch already merged into the protected branch is NOT in flight
E2E: RED — 233/234 checks passed
exit 0
```
### M2 (graph) bỏ phát hiện status drift
```
$ node src/cli/graph.mjs --selftest
graph selftest FAILED: In Progress with no unmerged branch is drift, not flight: []
exit 1
```
### M3 (gate) luật drift không miễn cho ticket đang bị chặn
```
$ python3 core/scripts/graph_check.py --selftest
✅ graph_check: work graph coherent (3 tickets, loop budget 4/day, scope armed where declared)

exit 1
```
### M4 (gate) bỏ hẳn cảnh báo drift
```
$ python3 core/scripts/graph_check.py --selftest
✅ graph_check: work graph coherent (3 tickets, loop budget 4/day, scope armed where declared)

exit 1
```

Four probes, four REDs; both files restored from byte copies and the selftests re-run green afterwards.
