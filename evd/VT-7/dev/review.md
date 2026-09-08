# Review dossier — VT-5 + VT-6 + VT-7 (branch feat/VT-7-orca-transport vs main)

Two fresh reviewers under `docs/team/review-standard.md`, on the combined diff.

## R1 — spec reviewer
**Verdict: APPROVE-WITH-QUESTIONS.** Diff maps cleanly to the three tickets; both
new gates are opt-in-safe (inert at team.parallel=1, verified exit 0); every count
claim machine-green (e2e 160/160, doctor 28 selftests, 17-gate table, "14 of 17").
No reproducible defect.
Tried to break: ran both gates live at parallel=1 → inert green; ran both
--selftest → each rule has a red fixture; hashed all 108 manifest entries → match,
doctor green; `node tests/e2e.mjs` → 160/160 incl. the count-drift self-checks;
`orca_team.sh status` + a bad-CLI fallback + `bogus`→exit 2; grepped rendered
skills for {vars} → none.
Traces: parallel_check.py:100-102 + coord_check.py:119-121 (inert guards, exit 0);
README.md:263-279 (17 rows); evd/VT-6/dev/chat_transcript.md:7-18.

## R2 — challenger
**Verdict: REQUEST-CHANGES → all findings FIXED + re-verified (see Fixes).**
Tried to break: prefix-not-nested inputs (`src`/`src2`, `src/a`/`src/ab`);
coord_check parser on no-trailing-pipe / From==To / separator / round==budget;
orca_team.sh under a faked-Linux `env -i` harness with a logging bare `orca`;
forced team.parallel=2 end-to-end + gate.py BOOKKEEPING diff.
- CONFIRMED C1 — `orca_team.sh` resolve_cli fell through to bare `orca` on Linux
  when orca-ide absent (violates its own no-bare-orca invariant; GNOME screen
  reader). Reproduced with the faked-Linux harness.
- CONFIRMED C2 — `coord_check.py` ROW regex required a trailing outer pipe, so a
  handoff row without it was silently dropped → GREEN when it should be RED.
- QUESTION Q1 — `paths_touch` divergent between the two gates (parallel_check did
  not norm inputs); masked today by pre-norming callers.
Verified negatives: classic prefix false-positive NOT present (the `+ "/"` guard);
From==To can't be made green; no off-by-one on budget/cap; no clean-repo regression.

## Fixes (each closed with a reproducing command)
- **C1** — resolve_cli on Linux now returns orca-ide or EMPTY (never bare `orca`);
  transport_up guards empty → fallback. Closed:
  `env -i PATH=<fakebin w/ logging orca> … orca_team.sh status` → fallback taken,
  `orca_ran.log` absent ("bare orca NOT run ✓").
- **C2** — parse_log rewritten: a row starts with `|`, trailing outer pipe
  OPTIONAL (dead ROW regex removed). Closed: coord_check --selftest now includes a
  no-trailing-pipe row that IS caught ("no-trailing-pipe row caught").
- **Q1** — parallel_check.paths_touch now norm()s internally (parity with
  coord_check); added prefix regressions (`src`/`src2`, `src/a`/`src/ab` → not
  overlap; trailing slash normalized). Closed: parallel_check --selftest green.
- **Q3 (R1)** — orca_team.sh now parses Orca JSON with python3 (reachable flag +
  run id) instead of literal greps. Closed: `open-run` → `RUN=run_2ec4f439f77d`.

## Answered QUESTIONS
- **R1-Q1 (VT-6 AC4 "two agents message each other" not literally met):** ACCEPTED
  by supersession, recorded honestly. Direct sibling chat could not run because
  `ListAgents` is disabled for spawned subagents (evd/VT-6/dev/chat_transcript.md);
  the coord_check CODE is proven by selftest, and VT-7 supplies the working
  transport (Orca bus, evd/VT-7/dev/cmd_verify.md). AC4 stands as "transport wired
  + guardrail proven"; the live 2-worker run is the optional Hướng-1 follow-up.
- **R1-Q2 (manifest folds 0.13.1→0.16.0 catch-up):** INTENDED. `vteam update`
  regenerates the whole manifest, which is REQUIRED to manifest the new gate
  scripts; all 108 hashes verified + doctor green. Not a defect; a separate
  manifest-only chore was not worth a second branch.
- **R1-Q3 (JSON brittleness):** FIXED (see Q3 above).
- **R1 minor (.gitignore *.bak):** kept deliberately — it prevents the exact
  stray `sed -i.bak` artifact this branch already had to clean (vteam.config.yaml.bak).

## Re-review (targeted, fresh agent) — C1 + C2 closure
**Verdict: APPROVE.** Both findings genuinely closed, related fixes hold, no new
defect. Verified: faked-Linux `env -i` harness → bare `orca` NOT invoked, exit 0;
`coord_check` no-trailing-pipe handoff → RED (not dropped); 3-cell row → malformed
(not dropped); correctly-reflected no-pipe row → still GREEN (no over-fire);
`parallel_check` `src`/`src2` → not overlap; `open-run` run id via JSON.
Non-blocking caveat: `ORCA_CLI_COMMAND=orca` on Linux runs bare orca (deliberate
user override, checked first) — now documented in resolve_cli as the caller's
responsibility.
