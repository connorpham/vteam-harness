# VT-9 — live probes with the RUNTIME copies (.vteam/scripts), 2026-09-08

```console
## A. legacy pack (evd/VT-1 copy): new readability rules are WARNINGS only
$ evd_check.py --evd <VT-1 copy> --expect-tcs 1
  ⚠️ warnings from the new rules: 8
❌ evd_check: 1 problems
   - MISSING verifysheet.md — QA designs the test plan (V1/V2: EXPECTED with spec citations + the TC journeys) BEFORE touching a browser, and the plan commits with the dossier

## B. v2 pack (KIND on every case, COVERAGE, ENVIRONMENT, ORACLE): indexed → GREEN
$ evd_index.py --evd <v2>
EVD-INDEX: WROTE   /private/tmp/claude-501/-Users-connorpham-Documents-vteam/89054c28-407b-4e1f-a00c-494521cc47bb/scratchpad/v2pack/PROJ-2/manifest.md
$ evd_index.py --evd <v2> --check
EVD-INDEX: CURRENT  (/private/tmp/claude-501/-Users-connorpham-Documents-vteam/89054c28-407b-4e1f-a00c-494521cc47bb/scratchpad/v2pack/PROJ-2)
  exit=0
$ evd_check.py --evd <v2> --expect-tcs 3
✅ evd_check: /private/tmp/claude-501/-Users-connorpham-Documents-vteam/89054c28-407b-4e1f-a00c-494521cc47bb/scratchpad/v2pack/PROJ-2 meets the evidence standard
  exit=

## C. v2 mutations → RED (the rules bite on readable packs)
$ (EXPECTED: works as expected) evd_check.py --evd <v2>
❌ evd_check: 1 problems
   - TC_1_the_total_recalculates/manifest.md: EXPECTED is 'works as expected' — a judgement, not a value. Write what the screen shows (the number, the label, the state) with its citation; if that cannot be written, the expected behaviour is not yet known
$ (a case added AFTER indexing) evd_index.py --check + evd_check
  unblock: python3 .vteam/scripts/evd_index.py --evd /private/tmp/claude-501/-Users-connorpham-Documents-vteam/89054c28-407b-4e1f-a00c-494521cc47bb/scratchpad/v2pack/PROJ-2
   - manifest.md: the index no longer matches the case folders — an index that lies is worse than none; run python3 .vteam/scripts/evd_index.py --evd /private/tmp/claude-501/-Users-connorpham-Documents-vteam/89054c28-407b-4e1f-a00c-494521cc47bb/scratchpad/v2pack/PROJ-2

## D. the workbook — 6 sheets, never invents; --strict names undeclared fields
$ xlsx_export.py --evd <v2>
XLSX: WROTE  /private/tmp/claude-501/-Users-connorpham-Documents-vteam/89054c28-407b-4e1f-a00c-494521cc47bb/scratchpad/v2pack/PROJ-2/PROJ-2_testcases.xlsx
  6 sheets · 3 case(s): 3 pass · 0 fail · 0 blocked · 0 defect(s)
  14728 bytes  /private/tmp/claude-501/-Users-connorpham-Documents-vteam/89054c28-407b-4e1f-a00c-494521cc47bb/scratchpad/v2pack/PROJ-2/PROJ-2_testcases.xlsx
$ xlsx_export.py --evd <VT-1 copy> --strict   (legacy pack has undeclared fields)
      REPORT.md: no ORACLE: line, in the report or the pack manifest
      TC_1: no TITLE:
      verifysheet.md: missing
  --strict: the pack is not complete enough to report from.
  exit=

## E. annotate — exact-fit box, caption below (coordinates intact)
$ annotate.py box --rect 420,180,260,44 --label "TC_1: 'Tổng' đọc 450.000 ₫ …"
ANNOTATE: OK  /private/tmp/claude-501/-Users-connorpham-Documents-vteam/89054c28-407b-4e1f-a00c-494521cc47bb/scratchpad/live_shot_boxed2.png  (1 region(s) boxed, caption below)
  orig (800, 500) → (800, 539) | width kept: True | caption rows below: 39
  box corner (420,180) is red: True | 5px outside untouched: True | interior untouched: True
```

## F. exit codes re-captured without a pipe (the earlier `exit=` blanks were a zsh $PIPESTATUS display bug, not a tool failure)
```console
$ evd_check.py --evd <v2> --expect-tcs 3            → exit=0
  ✅ evd_check: /private/tmp/claude-501/-Users-connorpham-Documents-vteam/89054c28-407b-4e1f-a00c-494521cc47bb/scratchpad/v2pack/PROJ-2 meets the evidence standard
$ xlsx_export.py --evd <v2> --strict                → exit=0   (fully declared pack: strict passes)
    6 sheets · 3 case(s): 3 pass · 0 fail · 0 blocked · 0 defect(s)
$ xlsx_export.py --evd <VT-1 legacy copy> --strict  → exit=1   (undeclared fields: strict REFUSES and names them)
    6 sheets · 1 case(s): 1 pass · 0 fail · 0 blocked · 0 defect(s)
    ! 4 declared unknown(s), printed in the workbook's section 5:
        REPORT.md: no ENVIRONMENT: line, in the report or the pack manifest
        REPORT.md: no ORACLE: line, in the report or the pack manifest
        verifysheet.md: missing
```
