# Dispatch ledger

One row per dispatched item, APPEND AT END (dates non-decreasing — machine-checked
by log_check.py). Result column takes exactly 3 values: `done` · `blocked: <why>` ·
`failed: <which gate>`. Rows from the adoption date carry `· tok ≈ <N>k`.
Actor = the HUMAN whose session dispatched the row — `VTEAM_ACTOR` env if set,
else `git config user.name`; never invented. With `team.size > 1` the column is
machine-mandatory (log_check reds a legacy header and any empty Actor cell).

| Date | Lane | Actor | Item | Result | Link |
|---|---|---|---|---|---|
| 2026-08-17 | DEV | Connor Pham | PR #32 README rewrite + 3 diagrams | done (frontier) · tok ≈ 400k | PR #32 |
| 2026-08-17 | DEV | Connor Pham | PR #33 release 0.10.1 | done (frontier) · tok ≈ 40k | PR #33 |
| 2026-08-18 | DEV | Connor Pham | PR #15 /plan greenfield intake 0.5.0 + PR #21 field-trial findings 0.6.0 | done (frontier) · tok ≈ 300k | PR #21 |
| 2026-08-19 | DEV | Connor Pham | PR #22 consistency round + PR #23 team actors 0.7.0 | done (frontier) · tok ≈ 90k | PR #23 |
| 2026-08-21 | DEV | Connor Pham | PR #34 vteam usage — measured per-person model/token history | done (frontier) · tok ≈ 250k | PR #34 |
| 2026-08-24 | DEV | Connor Pham | PR #35 checkpoint store (superseded by PR #36 — see decisions D1) | done (utility) · tok ≈ 60k | PR #35 |
| 2026-08-24 | DEV | Connor Pham | PR #36 resume rework — reader not store, doctrine reconciled | done (frontier) · tok ≈ 120k | PR #36 |
| 2026-08-24 | DEV | Connor Pham | PR #37 review holes — TTL knob, ledger fence, README truth guard | done (frontier) · tok ≈ 100k | PR #37 |
| 2026-08-24 | QA | Connor Pham | VT-1 self-install verified (doctor+gates+audit 91/A) | done · tok ≈ 30k | evd/VT-1 |
| 2026-08-24 | DEV | Connor Pham | PR #39 README command reference end-to-end + commands.svg + usage synthetic filter | done (frontier) · tok ≈ 60k | PR #39 |
| 2026-08-24 | DEV | Connor Pham | PR #41 security posture — SECURITY.md, Scorecard+CodeQL+provenance CI, pinned actions, best-practices dossier | done (frontier) · tok ≈ 50k | PR #41 |
| 2026-09-03 | DEV | Connor Pham | PR #57 README for both surfaces — 9 relative links absolutised for the npm page, selftest count 22→25 (prose+transcript+svg), e2e guard so it cannot drift again | done (frontier) · tok ≈ 90k | PR #57 |
| 2026-09-03 | DEV | Connor Pham | PR #58 README describes the last three releases — specialists section + diagram, watchable dev/QA sessions, CHANGELOG, 2 drift guards | done (frontier) · tok ≈ 110k | PR #58 |
| 2026-09-07 | DEV | Connor Pham | VT-3 competencies — DEV craft layer (10 files) + competency_check gate + /dev routing | done (frontier) · tok ≈ 350k | branch feat/VT-3-competencies |
| 2026-09-07 | DEV | Connor Pham | VT-4 QA competencies — 9 files distilled from ai-qa + reference tables + /qa routing | done (frontier) · tok ≈ 300k | branch feat/VT-4-qa-competencies |
| 2026-09-07 | DEV | Connor Pham | 0.16.0 — VT-3+VT-4 competency layer integrated onto main (DEV 10 + QA 9), README reconciled, gate 14→15 / selftest 25→26 | done (frontier) · tok ≈ 120k | release/0.16.0 |
| 2026-09-08 | DEV | Connor Pham | VT-5 /team parallel mode — parallel_check gate + PM-coordinated worktree fan-out (pm/team rewritten, team.parallel knob) | done (frontier) · tok ≈ 200k | branch feat/VT-5-parallel-team |
| 2026-09-08 | DEV | Connor Pham | VT-6 peer coordination — coord_check gate + agents chat to split/hand off work (team/pm rules, coord_budget knob) | done (frontier) · tok ≈ 200k | branch feat/VT-6-agent-coordination |
| 2026-09-08 | DEV | Connor Pham | VT-7 /team parallel uses Orca orchestration as transport — orca_team.sh helper + parallel-transport doctrine, team/pm rewired off the disabled ListAgents path | done (frontier) · tok ≈ 150k | branch feat/VT-7-orca-transport |
| 2026-09-08 | REV | Connor Pham | VT-7 review — R1 APPROVE-w-Q + R2 REQUEST-CHANGES(2 CONFIRMED) fixed + re-review APPROVE | done · tok ≈ 260k | evd/VT-7/dev/review.md |
| 2026-09-08 | DEV | Connor Pham | VT-8 BDD human report — bdd_report_check gate + doctrine/template, /dev & /qa emit optional *.bdd.md | done (frontier) · tok ≈ 130k | branch feat/VT-8-bdd-report |
| 2026-09-08 | DEV | Connor Pham | VT-9 /qa output layer from ai-qa — evd_index + xlsx_export (6-sheet ISO 29119-3 workbook) + exact-fit annotate + evd_check readability rules (v2-strict/legacy-warn) + evidence.md | done (frontier) · tok ≈ 400k | branch feat/VT-9-qa-output-layer |
| 2026-09-09 | DEV | Connor Pham | VT-10 parallel-worktree mode — gates read sibling tasksheets from git, bookkeeping never CODE-SCOPE, landed≠in-flight (topological), leading-key attribution + doctrine + orca_team.sh trust (ported from the testbed hot-fixes) | done (workhorse) · tok ≈ 1150k | PR https://github.com/connorpham/vteam-harness/pull/60 · merged 9680188 · evd/VT-10/dev/ |
| 2026-09-09 | REV | Connor Pham | VT-10 review — 4 fresh reviewers over 3 rounds, 10 CONFIRMED (incl. the PM hot-fix being weaker than the original, multi-scope attribution false negative) all fixed; final R1+R2 APPROVE | done · tok ≈ 400k | evd/VT-10/dev/review.md |
| 2026-09-09 | DEV | Connor Pham | 0.17.0 — VT-5..VT-10 released together (parallel /team + coord + Orca transport, BDD report, /qa evidence layer, worktree-safe gates), CHANGELOG entry derived from the 17 commits since 88a75dc, gate 15→18 / selftest 26→32 / suite 158→164, npm test + gate GREEN on the release branch | done (workhorse) · tok ≈ 60k | release/0.17.0 · PR #64 |
