# VT-9: /qa output layer from ai-qa — readable evidence, exact boxing, Excel test cases

- status: In Progress
- assignee: Connor Pham
- estimate: 1d
- labels: qa, no UI

## Why

Owner review 2026-09-08 of a real /qa run: the evidence folder is unreadable to a
stranger, the red box does not hug the region it claims to prove, and there is no
spreadsheet a manager can open. The owner's standalone `ai-qa` framework solves
all three, on a pack format that is a SUPERSET of vteam's (same TC_*/manifest.md,
same required fields, same _boxed.png) with tools that never invent a value
(missing → NOT DECLARED). Port that output layer into /qa.

## Spec / oracle

spec §`qa` V4 (annotated evidence) + V5b/V7 (report + close) and the `evd_check`
docstring (house of record for the pack contract). Source: connorpham/ai-qa
`core/scripts/{annotate,evd_index,xlsx_export}.py`, `lib/{evdpack,xlsx}.py`,
`core/doctrine/evidence.md` (read in full 2026-09-08). Layout standard for the
workbook: ISO/IEC/IEEE 29119-3 §7–9.

## Acceptance criteria (testable)

0. **Given** a finished vteam evidence pack, **When** `xlsx_export.py --evd <pack>`
   runs, **Then** it writes `<TICKET>_testcases.xlsx` with Summary / Test Cases /
   Defects / Traceability / Evidence sheets and prints NOT DECLARED for any field
   the pack lacks — never a guessed value; **and Given** `--strict` with undeclared
   fields, **Then** it exits 1 naming them.
1. **Given** `evd_index.py --evd <pack>`, **When** it runs, **Then**
   `manifest.md` gains (between markers) an index answering "what was tested" and
   "which case is this file from", regenerated from the case manifests;
   `--check` exits 1 when the index no longer matches the folder.
2. **Given** `annotate.py box --rect X,Y,W,H`, **When** it draws, **Then** the box
   hugs exactly that rectangle (4-px border, no padding inflation) and the caption
   is burned in on a bar BELOW the image (coordinates undisturbed), word-wrapped,
   font scaled to width; `diff` keeps vteam's auto-detected difference boxes.
3. `evd_check.py` gains the readability rules a stranger needs: `KIND:` from the
   six kinds (+ pack must include a boundary and a whole-screen case), EXPECTED /
   ACTUAL that is only a judgement word ("works", "failed") is RED, `COVERAGE:`
   block declaring security + accessibility as a case or a reasoned waiver,
   `ENVIRONMENT: <name — url>` in REPORT.md, `KIND: write-readback` needs
   db_verify.md, and a stale index is RED. Every new rule has a selftest mutation.
4. `core/doctrine/evidence.md` ported (manifest field meanings, COVERAGE,
   ENVIRONMENT, PERSONA/HEURISTIC/OBSERVATIONS) with cross-refs to the qa-*
   competencies; `/qa` V4/V7 + DoD wire annotate → evd_index → xlsx_export; `.xlsx`
   ignored in git (regenerated from text).
5. `gate.sh` GREEN, e2e green, no unresolved `{vars}`; all ported selftests green;
   a REAL run of xlsx_export + evd_index against `evd/VT-1` recorded in evidence.

## Out of scope

- ai-qa's browser.mjs / api_check.mjs / db_verify.py / tracker.py (drivers; vteam
  has its own; separate ticket if wanted).
- Changing the required-field set or the two-anchor (COMMIT/VERIFIED-AT) law.
- Rewriting existing evd/VT-* packs to the new fields (new rules apply to new
  packs; existing ones are checked by the rules they were made under — see
  tasksheet for the compatibility note).

## Comments

### 2026-09-08 Connor Pham
claimed 2026-09-08T18:30:00Z · branch feat/VT-9-qa-output-layer
