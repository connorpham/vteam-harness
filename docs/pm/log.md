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
