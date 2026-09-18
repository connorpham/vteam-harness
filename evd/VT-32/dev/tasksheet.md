# VT-32 · dev tasksheet — round ceilings for review and BA challenger
CODE-SCOPE: core/scripts/review_check.py core/workflows/dev.md core/workflows/ba.md core/templates/vteam.config.example.yaml src/cli/init.mjs docs/GUIDE.md .vteam/ .claude/skills/ evd/VT-32/ docs/pm/ docs/backlog/ CHANGELOG.md

Branch `feat/VT-32-cost-ceilings` from main d9b1e7e, in an isolated worktree.

## Plan
| T | Task | State |
|---|---|---|
| T1 | Selftest assertions for `count_rounds` / `round_gaps` written BEFORE the code (RED: `NameError: count_rounds`) | done — proof.md §1 |
| T2 | `review_check.py`: `ROUND_HEAD`, `count_rounds` (highest N), `round_gaps` (ceiling ≤ 0 = off; high-stakes or lift tag = off), `read_ceiling`; main reads `review.max_rounds`; `--ba <feature>` mode reads `ba.challenger_rounds` on `{paths.specs}/reviews/<feature>-backlog.md`; docstring rule 5 | done — GREEN, proof.md §1 |
| T3 | Config: `ba.challenger_rounds: 1` + `review.max_rounds: 1` in the init template, docs/GUIDE.md block, core/templates example | done — conformance OK |
| T4 | Doctrine: dev.md T4b (brief = prioritised attack list; round ceiling paragraph; `## Gate rerun` is not a round), ba.md B3 (ceiling; already-coded spec → no challenger round for the shard); `vteam update` re-rendered both skills, mirror identical, doctor manifest 171 intact | done |
| T5 | Mutation probes (code-only, test kept): neuter `round_gaps` → RED; remove the SECURITY lift → RED; restored from the identical mirror both times | done — proof.md §2 |
| T6 | Real runs: VT-29 dossier green with the no-ceiling note; BA mode on a fixture; knobs switched on temporarily → VT-25 RED (2 rounds), VT-29 green, BA 2 rounds RED, SPEC tag lifts | done — proof.md §3 |
| T7 | Gate GREEN (14 steps; advisory `schedule` pre-existing), npm test 199/199, review dossier R1/R2, PR to main | done — proof.md §4 |

## Decision taken here, reversible, for the owner to confirm
**Absent knob = no ceiling (printed on the green line); the init template sets both knobs to 1; this repository's own config is left without them.** Reason: `evd/VT-25/dev/review.md` records `## Round 2 — CI (Linux) red on the first push`, a legitimate second round under the new text's own rule (a gate rerun, not a review round — the heading predates that rule). With the knob on, `review_check.py VT-25 --sha HEAD` goes RED (proof.md §3), which would turn a merged, honest dossier into a violation after the fact. `vteam update` never rewrites a project's config, so pre-0.19.1 repos opt in by adding the two lines; new repos get the ceiling from init. Alternative rejected: default 1 when absent — same retroactive RED in every existing consumer, including the testbed.

## Self-review (T4a)
- The BA check reads the reviews file from the worktree, not the commit, because the BA lane runs before any push; said in the code comment.
- `count_rounds` counts by the highest N, not the number of headings, so a `## Round 2` heading recorded once is one extra round and a doc that says "Round 3" without "Round 2" still counts three.
- The lift tag is a whole-word match (`\bSECURITY\b` / `\bSPEC\b`): "SPECIFICATION" or "security" in prose does not lift the BA/review ceiling by accident — verified in the selftest by the SECURITY case and by inspection for SPEC.
- Doctor in this worktree reports `core.hooksPath` as an absolute path to the main checkout's `.githooks` — a worktree artefact of the shared git config, not this change.
