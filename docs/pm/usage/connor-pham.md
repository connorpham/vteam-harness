# Measured AI usage — Connor Pham

<!-- written by `vteam usage --sync` — measured from local session logs.
     Counts only: models, tokens, session times. NEVER chat content.
     Machine-read by perf_report; do not hand-edit — re-run the sync. -->

ACTOR: Connor Pham
UPDATED: 2026-08-24
WINDOW: 2026-08-01 → 2026-08-24

## Daily by model

| Date | Source | Model | Sessions | Msgs | Input | CacheRead | CacheWrite | Output |
|---|---|---|---|---|---|---|---|---|
| 2026-08-17 | claude | <synthetic> | 1 | 1 | 0 | 0 | 0 | 0 |
| 2026-08-17 | claude | claude-fable-5 | 1 | 17 | 32 | 1134400 | 90519 | 47179 |
| 2026-08-18 | claude | <synthetic> | 1 | 2 | 0 | 0 | 0 | 0 |
| 2026-08-18 | claude | claude-fable-5 | 1 | 187 | 3147 | 61007925 | 2761368 | 226649 |
| 2026-08-18 | claude | claude-opus-5 | 1 | 59 | 118 | 21714212 | 788504 | 73848 |
| 2026-08-19 | claude | <synthetic> | 1 | 1 | 0 | 0 | 0 | 0 |
| 2026-08-19 | claude | claude-fable-5 | 1 | 81 | 162 | 50924325 | 677698 | 90277 |
| 2026-08-21 | claude | claude-fable-5 | 3 | 99 | 198 | 48505328 | 1724281 | 125813 |
| 2026-08-21 | claude | claude-haiku-4-5-20251001 | 1 | 1 | 10 | 23648 | 7924 | 102 |
| 2026-08-21 | claude | claude-opus-5 | 1 | 97 | 194 | 71084732 | 1482736 | 102597 |
| 2026-08-24 | claude | claude-fable-5 | 1 | 67 | 134 | 16791256 | 405184 | 84663 |
| 2026-08-24 | claude | claude-haiku-4-5-20251001 | 1 | 33 | 268 | 4492458 | 154724 | 21279 |
| 2026-08-24 | claude | claude-sonnet-5 | 1 | 5 | 10 | 784406 | 202726 | 5730 |

## Recent sessions

| Started (UTC) | Source | Model | Branch | Duration | Msgs | Input | Output |
|---|---|---|---|---|---|---|---|
| 2026-08-21 04:44 | claude | claude-haiku-4-5-20251001 | feat/scale-round | 0m | 1 | 10 | 102 |
| 2026-08-21 04:43 | claude | claude-fable-5 | feat/scale-round | 0m | 1 | 2 | 171 |
| 2026-08-21 04:41 | claude | claude-fable-5 | feat/scale-round | 0m | 1 | 2 | 178 |
| 2026-08-17 09:16 | claude | claude-fable-5 | main | 163h30 | 647 | 4259 | 777686 |

## Ledger cross-check

- claimed `tok ≈` 1390k · measured in+out 782k
- ✅ every done day has a session, every heavy day has a ledger row
