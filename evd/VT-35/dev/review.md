# Review dossier — VT-35 (one worktree, one port, one database, one scratch dir)

**Provenance, stated plainly:** both cards were written by the implementing session, not by
spawned reviewers. Every bullet is a command that was run on 2026-09-18 with its output kept in
`proof.md`.

## R1 — implementation review (mutation probes, one per moving part)
APPROVE

Tried to break:
- made `check_lane_envs` (core/scripts/parallel_check.py:398) return before reading any worktree — `python3 core/scripts/parallel_check.py --selftest` RED: the two-worktrees-no-markers case came back `[]`.
- disabled the duplicate-port branch at core/scripts/parallel_check.py:424 — selftest RED: `two lanes on one port must red`.
- dropped the lane name from the hash key at core/scripts/lane_env.sh:44 — `bash core/scripts/lane_env.sh --selftest` RED: `reviewer lane R1 derived the author's port 3885`, i.e. the author and their reviewer back on one server, which is E13 in one line.
- put app_check's URL line back to config-only (core/scripts/app_check.sh:171) — `bash core/scripts/app_check.sh --selftest` RED: with `APP_URL` set to a closed port the script printed `APP: SKIP` instead of `APP: DOWN`.
- wrote the parallel selftest case before any implementation and ran it: `NameError: name 'worktree_branches' is not defined` — the RED-before that proves the case exercises new code.

Traces: core/scripts/parallel_check.py:398, core/scripts/parallel_check.py:424, core/scripts/lane_env.sh:44, core/scripts/app_check.sh:171, `python3 core/scripts/parallel_check.py --selftest`, `bash core/scripts/lane_env.sh --selftest`

## R2 — adversarial read: can the rule misfire, and do the two writers agree?
APPROVE

Tried to break:
- looked for a false RED in sequential work: `check_lane_envs` counts only in-flight branches that are CHECKED OUT in a worktree (core/scripts/parallel_check.py:363 `git worktree list --porcelain`) and returns `[]` below two of them; the selftest asserts the single-worktree exemption. The gate stays inert-green when `team.parallel <= 1` exactly as before (main returns before the call at core/scripts/parallel_check.py:256).
- checked the two hash writers cannot disagree: `lane_marker` (core/scripts/parallel_check.py:384) and `derive()` (core/scripts/lane_env.sh:40) both fnv1a the `pwd -P` / `Path.resolve()` realpath, so macOS `/var` vs `/private/var` spellings land on one slug; the lane_env selftest additionally asserts equality with `init.mjs derivePort()` for lane `main`, so a plain checkout's DEV lane is on the port init wrote into `app.url`.
- checked the default marker root is the same string on both sides: the helper prints `${TMPDIR:-/tmp}/vteam-lanes` with doubled slashes collapsed; python joins `TMPDIR` (which ends in `/` on macOS) with `vteam-lanes` — `Path` normalises the same way; `VTEAM_LANES_ROOT` overrides both and is what the selftests and e2e use.
- tried a non-sqlite repo: with no `provider = "sqlite"` in `prisma/schema.prisma` the helper prints a hint and no `DATABASE_URL` (core/scripts/lane_env.sh:52) — it never invents a Postgres URL; the selftest asserts the hint line.
- read the marker parser for hostile content: `dict(line.split("=", 1) …)` only, values compared as strings; a hand-edited marker with an empty `PORT` is skipped rather than colliding with every other empty one (`elif port:`).
- ran `node bin/vteam.mjs update` then `doctor`: manifest 174 files intact, 36 selftests discovered; the only ❌ is the shared git config's absolute `core.hooksPath`, which every worktree fork today reported and which this change does not touch.

Traces: core/scripts/parallel_check.py:363, core/scripts/parallel_check.py:384, core/scripts/lane_env.sh:40, core/scripts/lane_env.sh:52, core/doctrine/parallel-transport.md:107, `node bin/vteam.mjs doctor`
