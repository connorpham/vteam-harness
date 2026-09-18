# VT-36 · mutation ledger — code-only mutations with the new tests kept (KB-R1), run 2026-09-18

### M1 classify() luôn trả logic (giữ nguyên test)
```
$ python3 core/scripts/change_class.py --selftest
  File "/Users/connorpham/Documents/vteam/core/scripts/change_class.py", line 331, in case
    assert got == expect, f"{name}: expected {expect}, got {got} — {why}"
AssertionError: docs-only: expected docs, got logic — ['MUTANT']
exit 1
```
### M2 bỏ loại trừ cây doctrine khỏi lớp docs
```
$ python3 core/scripts/change_class.py --selftest
  File "/Users/connorpham/Documents/vteam/core/scripts/change_class.py", line 310, in _selftest
    assert not is_doc("core/doctrine/red-flags.md", "evd"), "doctrine is rendered — it is runtime"
AssertionError: doctrine is rendered — it is runtime
exit 1
```
### M3 bỏ trần review.surface_max_lines
```
$ python3 core/scripts/change_class.py --selftest
  File "/Users/connorpham/Documents/vteam/core/scripts/change_class.py", line 330, in case
    assert got == expect, f"{name}: expected {expect}, got {got} — {why}"
AssertionError: over-the-cap: expected logic, got surface — ['src/copy.ts: strings, comments or JSX text only (skeleton identical)', '120 changed line(s) in code, wi
exit 1
```
### M4 coi template literal là văn bản thường (che mất ${code})
```
$ python3 core/scripts/change_class.py --selftest
  File "/Users/connorpham/Documents/vteam/core/scripts/change_class.py", line 303, in _selftest
    assert skeleton('x(`a ${p} b`)\n', ".ts") != skeleton('x(`a ${q} b`)\n', ".ts"), \
AssertionError: a template literal carries code — an edit inside one must move the skeleton
exit 1
```
### M5 review_shape bỏ qua lớp rủi ro
```
$ python3 core/scripts/review_check.py --selftest
  File "/Users/connorpham/Documents/vteam/core/scripts/review_check.py", line 371, in _selftest
    assert review_shape("docs", 2) == ([], None, 0)
AssertionError
exit 1
```
### M6 review_check bỏ qua knob review.proportional (test e2e giữ nguyên)
```
$ npm test
  ❌ review.proportional: false restores the uniform fence on the same docs-only diff
E2E: RED — 226/227 checks passed
```
### M7 bỏ xử lý hai vế của rename (test giữ nguyên)
```
$ python3 core/scripts/change_class.py --selftest
    assert got == expect, f"{name}: expected {expect}, got {got} — {why}"
AssertionError: code-renamed-to-prose: expected logic, got docs — ['1 changed path(s), all prose no tool renders']
exit 1
```

Seven probes, seven REDs. Every file restored from a byte copy taken before the probe; `git status core/scripts` after the run showed only the two intended files.
