# VT-3 — verification, real runs (branch feat/VT-3-competencies, 2026-08-28)

```console
$ python3 core/scripts/competency_check.py --selftest
competency_check selftest: OK (valid file green + 7 mutations red + index missing/stale red)

$ node bin/vteam.mjs update            # renders doctrine → docs/team/competencies/, skills → .claude/skills/dev-*/
✓ .vteam runtime refreshed
✓ doctrine refreshed in docs/team
✓ claude-code workflows re-rendered

$ ls docs/team/competencies/dev/ | wc -l        → 11  (10 competencies + INDEX.md)
$ ls -d .claude/skills/dev-* | wc -l            → 10
$ grep -l '{(paths|project|team|review|git|stack|autonomy)\.[a-z_]*}' .claude/skills/*/SKILL.md  → none

$ python3 .vteam/scripts/competency_check.py
✅ competency_check: 10 competencies well-formed and indexed under /Users/connorpham/Documents/vteam/docs/team/competencies

$ bash .vteam/scripts/gate.sh          (generic profile: docs-shrink · ledger · graph · verbatim · competencies · test)
▶ competencies: python3 .vteam/scripts/competency_check.py
✅ competency_check: 10 competencies well-formed and indexed …
conformance: OK — 15 fixtures, ctx.py == ctx.mjs (== ctx.sh on its scalar subset), error fixtures red in both.
conformance: OK — ledger grammar, 10 rows, lib/ledger.py == board.mjs parseLedger (kind/tok/actor/malformed).
E2E: RED — 136/142 checks passed
   ❌ README claims "141" but the suite ran 142        → fixed (README truth guard; the suite grew by one check)
   ❌ doctor exits 0 / doctor ran the selftests ×3     → evd_check.py + evd_ui_check.py selftests: "Pillow missing"
                                                         on this machine's python 3.9 — PRE-EXISTING (identical on main,
                                                         see evd/VT-2 probe notes); CI installs pillow. Not this diff.
$ node bin/vteam.mjs doctor
   selftests discovered: 23 (competency_check.py among them); the same two Pillow reds; PREFLIGHT: GREEN

$ python3 .vteam/scripts/dor_check.py VT-3      → ✅ ready
$ python3 .vteam/scripts/log_check.py           → ✅ ledger well-formed
$ python3 .vteam/scripts/graph_check.py         → ✅ work graph coherent
```

Confirmation from inside the agent tool: after `update`, the ten competencies
appeared in this Claude Code session's skill list by their "Use when…"
descriptions (dev-identity … dev-stack-nextjs-prisma) — the model-invoked path
works, not just the lane-invoked one.
