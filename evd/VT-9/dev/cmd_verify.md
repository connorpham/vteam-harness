# VT-9 — verification (branch feat/VT-9-qa-output-layer, 2026-09-08)

```console
# ported / merged tools — selftests (all from the RUNTIME copies in .vteam/scripts)
$ annotate.py --selftest      → passed (exact-fit box, caption below w/ width intact, multi-rect,
                                  empty/malformed/zero-size refused, auto-diff boxed side by side)
$ evd_index.py --selftest     → PASS (15 checks)
$ xlsx_export.py --selftest   → passed (18 honesty mutations, each one reported)
$ evd_check.py --selftest     → OK — legacy fixture green + 9 original mutations red
                                  + v2 readable pack green + 14 readability mutations red
                                  (vague EXPECTED/ACTUAL, invalid KIND, no boundary/whole-screen,
                                  no ENVIRONMENT/ORACLE, COVERAGE missing/lens-less/reasonless/ghost-TC,
                                  write-readback w/o db_verify, bare TC_n, stale index)

$ node bin/vteam.mjs update   → 6 scripts + lib synced to .vteam (diff -q: all in sync),
                                  evidence.md → docs/team, qa.md → .claude/skills/qa
$ grep '{(paths|…)\.[a-z_]*}' .claude/skills/*/SKILL.md docs/team/evidence.md → none
$ node bin/vteam.mjs doctor   → ✅ gate selftests green (32 discovered checks prove they can red)

$ bash .vteam/scripts/gate.sh → docs-shrink · ledger · graph · verbatim · competencies · parallel ·
                                  coord · bdd-report · test — all ran; conformance OK (15 fixtures,
                                  10 ledger rows); ONLY red was the README e2e-count guard
                                  ("claims 161, suite ran 164": +3 selftest-bearing scripts) → fixed
$ node tests/e2e.mjs          → E2E: GREEN — 164/164 checks passed
                                  incl. "README's selftest count matches discovery (32)" ✅
```

## Legacy compatibility, proven (not assumed)
```console
$ <main's UNTOUCHED evd_check + its lib> --evd evd/VT-1 --expect-tcs 1
❌ evd_check: 1 problems
   - MISSING verifysheet.md — …
$ <VT-9 evd_check> --evd evd/VT-1 --expect-tcs 1
   8 × ⚠️ (the new readability rules, as WARNINGS)  +  the SAME single pre-existing ❌
```
The one red on evd/VT-1 predates VT-9 (main's own gate produces it); VT-9 added
zero errors to legacy packs and eight warnings that say exactly what a stranger
would be missing. Live probes (v2 pack green → mutations red, index staleness,
workbook + --strict exit codes, exact-fit box): evd/VT-9/dev/cmd_probe.md.
