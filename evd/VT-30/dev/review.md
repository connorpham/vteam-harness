# Review dossier — VT-30 (gates that crashed, lied or went vacuously green in a real repo)

**Provenance, stated plainly:** both cards were written by the implementing session, not by
spawned reviewers. Every bullet is a command that was run on 2026-09-18 with its output kept in
`proof.md` / `mutations.md`.

## R1 — implementation review (mutation probes, one per fix)
APPROVE

Tried to break:
- restored the bold-only, digits-only ROW regex at core/scripts/verbatim_gate.py:33 with the new assertions kept — `python3 core/scripts/verbatim_gate.py --selftest` RED (`AttributeError … 'group'` on the `AC-A01` row). The first attempt at this probe did not mutate the file (a `re.sub` escape error); it is recorded as invalid and was redone by exact string replace.
- deleted the configured-but-vacuous block at core/scripts/verbatim_gate.py:104 — selftest RED (the temp repo with prose-only sources came back exit 0).
- removed the existence filter inside `pickRoots` (profiles/nextjs-prisma/scripts/token_check.mjs:42) — `--selftest` RED: a missing `src/` was returned instead of skipped, which is exactly the ENOENT path of E5.
- removed the `owner_check` call at core/scripts/app_check.sh:78 — `--selftest` RED: `a stranger's server must be FOREIGN, got: APP: UP http://127.0.0.1:… (HTTP 200)`.
- deleted the E14 block at core/scripts/graph_check.py:389 — `--selftest` RED at m0 (an In Review ticket without a row passed).
- mutated an installed preflight back to `miss "Git"` in a fixture without origin — `PREFLIGHT: RED`; the shipped version prints the ⚠️ rule and `PREFLIGHT: GREEN` (core/scripts/preflight.sh:66).
- reverted gate.sh to a bare `exec` — the transcript regex the e2e check uses matched 0 lines (core/scripts/gate.sh:11 is what emits it).

Traces: core/scripts/verbatim_gate.py:33, core/scripts/app_check.sh:78, core/scripts/graph_check.py:389, profiles/nextjs-prisma/scripts/token_check.mjs:42, `python3 core/scripts/verbatim_gate.py --selftest`, `bash core/scripts/app_check.sh --selftest`

## R2 — adversarial read: does any fix hurt an honest repo?
APPROVE

Tried to break:
- ran the two new rules against the testbed with its own config: graph_check coherent; verbatim_gate RED because its REQ documents carry no coded rows — and the version shipped today prints `0 coded rows across 2 shards … ✅` for the same repo. The RED is the finding, not a regression; recorded in the ticket's out-of-scope and the tasksheet.
- looked for a false FOREIGN: `owner_check` (core/scripts/app_check.sh:35) canonicalises both cwd and root with `pwd -P` (macOS `/var` vs `/private/var` would otherwise flag the repo's own server), accepts every registered worktree, and returns "ours" when the host is remote, `lsof` is missing, or the pid/cwd cannot be read — unknown never REDs.
- checked the E14 rule against the existing fixtures: the graph selftest's m1c won't-fix (`closed-by: Q2`, no row) still passes; m3's done ticket needed a row in the fixture, which is the rule doing its job; this repo and the testbed both had zero In Review/Done tickets without rows before the rule shipped.
- checked that gate.sh still works from a subdirectory (the `cd` to the toplevel was dropped in the first rewrite and restored) and that `PIPESTATUS[0]` — not tee's exit — decides the exit code: `bash .vteam/scripts/gate.sh` on this branch exits 0 with the advisory schedule failure and would exit 1 on a RED step as before.
- confirmed the ROW regex change cannot loosen the byte comparison: matching decides which lines are compared, `truth[code] != line` still compares whole lines, so an unbolded shard against a bolded source drifts at character 2 and REDs as before.
- ran `npm test` (201/201) and the gate (GREEN) after `node bin/vteam.mjs update`, so the mirrors under `.vteam/`, `.claude/` and `docs/team/` follow the sources and the manifest verifies.

Traces: core/scripts/app_check.sh:35, core/scripts/graph_check.py:389, core/scripts/gate.sh:11, `python3 ~/Documents/vteam/core/scripts/verbatim_gate.py` (run in ~/Documents/testbed-base), `node bin/vteam.mjs doctor`
