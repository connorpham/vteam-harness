# VT-37 · mutation ledger — code-only mutations with the tests kept (KB-R1), run 2026-09-18

### M1 Kahn bỏ qua phụ thuộc (mọi việc về wave 0)
```
$ node src/cli/graph.mjs --selftest
graph selftest FAILED: chain must be 3 waves: [0]
exit 1
```
### M2 scope chưa khai báo bị coi là rỗng (thay vì xung đột với tất cả)
```
$ node src/cli/graph.mjs --selftest
graph selftest FAILED: an undeclared scope conflicts with everything, loudly
exit 1
```
### M3 bỏ trần team.parallel
```
$ node src/cli/graph.mjs --selftest
graph selftest FAILED: team.parallel is a ceiling, not a suggestion
exit 1
```
### M4 việc đang chạy vẫn được phát lại
```
$ node src/cli/graph.mjs --selftest
graph selftest FAILED: a ticket with a branch pushed is running, never dispatchable again
exit 1
```
### M5 chỉ đọc một dạng dữ liệu cycle (lỗi thật đã bắt được khi viết)
```
$ node src/cli/graph.mjs --selftest
graph selftest FAILED: --plan must exit 0: graph: c is not iterable

exit 1
```
### M6 thiếu day-cost bị lặng lẽ tính là 0 (đường găng vẫn báo complete)
```
$ node src/cli/graph.mjs --selftest
graph selftest FAILED: a missing day-cost makes the number incomplete — it is never guessed
exit 1
```

Six probes, six REDs; `src/cli/graph.mjs` restored from a byte copy after each one, and the selftest re-run green afterwards.
