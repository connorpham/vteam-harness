# VT-35 · dev tasksheet — one worktree, one port, one database, one scratch dir
CODE-SCOPE: core/scripts/lane_env.sh core/scripts/parallel_check.py core/scripts/app_check.sh core/workflows/team.md core/doctrine/parallel-transport.md .vteam/ .claude/ docs/team/ tests/e2e.mjs README.md CHANGELOG.md evd/VT-35/ docs/pm/ docs/backlog/

Branch `feat/VT-35-lane-isolation` from main d58433e.

## Shape chosen, and why
The smallest change that makes isolation machine-checkable rather than prose:
- **`lane_env.sh`** derives `PORT` / `APP_URL` / `DATABASE_URL` (sqlite only, absolute file under a
  per-lane scratch dir) / `VTEAM_SCRATCH` / `VTEAM_LANE` from the worktree's realpath, with the
  SAME fnv1a scheme as `init`'s `derivePort`, so a plain checkout's DEV lane lands on the port init
  already wrote into `app.url`. The database lives OUTSIDE the tree (no .gitignore change, no dirty
  tree, no per-repo ignore rules to ship). Non-sqlite datasources get a hint, never a guessed URL.
- **Marker, not prose:** the helper writes `<lanes-root>/<slug>/lane.env`; `parallel_check`
  recomputes the slug from each in-flight worktree's realpath and reads the markers. RED when two
  in-flight worktrees exist and one has no marker, or two markers claim one port or one database.
  One in-flight worktree is sequential work and exempt. Config-independent: no new knob.
- **`app_check` honours `APP_URL`** between `--url` and `app.url`, so the lane's server is the one
  probed (and VT-30's FOREIGN check still applies to it).
- Rejected: a per-worktree `vteam.config.yaml` (would fork the config the gates read); putting the
  DB under the worktree (needs ignore rules every existing repo lacks); a new config knob (the
  environment is a fact of the worktree, not a choice).

| T | Task | State |
|---|---|---|
| T1 | `lane_env.sh` + `--selftest` (stable, distinct across worktrees and lanes, marker, parity with `derivePort`, non-sqlite hint) | done |
| T2 | `app_check.sh` honours `APP_URL`; selftest case at the CLI layer | done |
| T3 | `parallel_check.py`: `worktree_branches`, `lane_marker`, `check_lane_envs`; selftest RED-before (NameError) → GREEN | done |
| T4 | Doctrine: team.md rule 4, parallel-transport.md rule 4 (+ heading "Four rules") | done |
| T5 | e2e: helper installed, port parity with init, R1 lane distinct, marker written | done |
| T6 | Mutations M1–M4 (code-only, tests kept) — see proof.md | done |
| T7 | `vteam update`, doctor (36 selftests, manifest 174), gate GREEN, npm test 219/219, README 35→36 / 214→219, PR | done — proof.md §4 |
