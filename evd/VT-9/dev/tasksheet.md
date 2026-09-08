# VT-9 task-sheet — /qa output layer from ai-qa

CODE-SCOPE: core/scripts/annotate.py core/scripts/evd_check.py core/scripts/evd_index.py core/scripts/xlsx_export.py core/scripts/lib/evdpack.py core/scripts/lib/xlsx.py core/doctrine/evidence.md core/workflows/qa.md README.md .gitignore docs/backlog/VT-9.md docs/pm/log.md docs/team/ .claude/skills/ .vteam/ evd/VT-9/

Competencies: dev-identity · dev-codebase-design · dev-testing-craft · dev-error-handling.

## Requirement

/qa's evidence must be readable by a stranger, its boxes must hug the region
they prove, and the pack must export to a workbook a manager opens — exactly
what the owner's ai-qa does. Port that output layer; keep vteam's laws.

## Design decisions (why this shape)

- **Format compatibility, verified live:** ai-qa's pack format is a superset of
  vteam's (same TC_*/manifest.md, same 7 required fields, same _boxed.png). The
  ported tools read a REAL vteam pack (copy of evd/VT-1): index written, 6-sheet
  workbook exported, 3 honest "declared unknowns" — never a guessed value.
- **One vocabulary:** evd_check now imports KINDS/VAGUE_VALUE/fields from
  lib/evdpack.py — the same source xlsx_export prints from (ai-qa's lesson:
  separate lists made the gate and the report disagree).
- **Legacy compatibility policy:** a pack is "v2" when any TC declares KIND:.
  v2 packs get the readability rules as ERRORS; legacy packs as WARNINGS, so
  evd/VT-1..8 stay green while new evidence is held to the readable bar. One
  exception: a stale index is RED regardless — an index that lies is worse than
  none. (Ticket AC + out-of-scope note.)
- **annotate.py = merge, not replace:** ai-qa's exact-fit 4-px box (no PAD
  inflation — the "khoanh vùng sai" root cause), caption BELOW (vteam's top band
  shifted every coordinate), word-wrap, width-scaled font, need_pillow degrade,
  malformed/zero-size refusal + vteam's multi-`--rect` and its auto-detect
  `diff` (connected components) which ai-qa lacks; `--old/--new` kept as
  aliases of `--left/--right` so existing callers do not break. Unicode-capable
  fonts first (captions carry Vietnamese diacritics).
- xlsx_export `_load_project` re-pointed at vteam's `Ctx()` so project.name/key
  and `project.language` (bilingual headers) reach the workbook.
- `.xlsx` is git-ignored: regenerated from text in a second; a workbook in a
  diff is a workbook nobody can review.

## AC → proof

| AC | Proof |
|---|---|
| 0 xlsx_export on a real pack; NOT DECLARED; --strict exits 1 | cmd_probe.md (live VT-1 copy) + xlsx_export --selftest (18 honesty mutations) |
| 1 evd_index writes/checks the index | cmd_probe.md; evd_index --selftest (15 checks); stale-index red in evd_check selftest |
| 2 exact-fit box, caption below, auto-diff kept | annotate --selftest + live PNG probe (corner red, outside/interior untouched, width intact) |
| 3 evd_check readability rules, each with a mutation | evd_check --selftest (14 new mutations); legacy evd/VT-1 stays green |
| 4 evidence.md ported; qa.md V2/V4/tree/V5b/V7/DoD; .gitignore | files + cmd_verify.md |
| 5 gate GREEN, e2e, no {vars}, live runs recorded | cmd_verify.md |

## Side findings

- SF-1 ai-qa's browser.mjs/api_check.mjs/db_verify.py/tracker.py are drivers
  vteam already covers differently — out of scope, separate ticket if wanted.
- SF-2 existing evd/VT-* packs are legacy (no KIND); a follow-up could add
  KIND/COVERAGE/ENVIRONMENT to them so they graduate to v2.
- SF-3 T4b two-agent review of THIS diff not yet run.
