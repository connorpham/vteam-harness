# Review dossier — VT-34 (stop state when a session ends mid-ticket)

**Provenance, stated plainly:** both cards were written by the implementing session, not by
spawned reviewers. Every bullet is a command that was run on 2026-09-18 with the output it
produced; the RED-before lines and the five mutation probes are in `evd/VT-34/dev/proof.md`.

## R1 — implementation review (mutation probes)
APPROVE

Tried to break:
- raised `STOP_STATE_MAX_DAYS` at core/scripts/graph_check.py:290 from 7 to 7000 and ran `python3 core/scripts/graph_check.py --selftest` — RED: "a 7-day-old stop state on an open ticket must red". Restored.
- made the `Blocked` exemption in `check_stop_states` (core/scripts/graph_check.py:295) match a status that never occurs — RED: "Blocked (with the stop state as the reason) must pass". The exemption is load-bearing, not decorative.
- replaced the `grep -v '^- stop-state: '` at core/scripts/stop_state.sh:97 with a plain `cat` — RED: "second run must not duplicate the tasksheet line". Idempotency is proven by the second run, not assumed.
- dropped the `ahead` leg of the skip condition at core/scripts/stop_state.sh:47 — RED: "ahead-of-base must record (+1)". A clean tree with committed WIP still counts as work in flight.
- removed the SessionEnd row from `HOOK_EVENTS` at adapters/claude-code.mjs:30 and ran `node tests/e2e.mjs` — RED on exactly the two settings checks (205/207), green on the script-install checks, which is why both kinds exist.

Traces: core/scripts/graph_check.py:290, core/scripts/graph_check.py:295, core/scripts/stop_state.sh:97, core/scripts/stop_state.sh:47, adapters/claude-code.mjs:30, `python3 core/scripts/graph_check.py --selftest`, `bash core/scripts/stop_state.sh --selftest`

## R2 — adversarial read: can the hook hurt a user, and can the rule red the innocent?
APPROVE

Tried to break:
- a session that ends on the protected branch with a clean tree: tests/e2e.mjs:547 runs the installed hook on `main` after the fixture is reverted — nothing written, exit 0. No noise on every exit.
- a user whose `.claude/settings.json` already carries their own hooks: the t14 fixture (`env.MY_VAR`, a `PreToolUse` entry) survives the merge and gains exactly one `SessionEnd` entry (tests/e2e.mjs, "SessionEnd entry merged alongside the user's hooks too"); when both vteam entries are present the file is not rewritten (`added.length === 0` at adapters/claude-code.mjs:114), so a second `vteam update` is byte-neutral.
- the hook must never fail the session: the template ends in `exit 0` after `2>/dev/null`, and `stop_state.sh` returns 0 on every branch of `record()` including "not a git repository" and "no ticket key" (selftest cases 4–6 assert the outcome AND the exit code).
- the hook must never commit or change ticket status: `grep -n "git commit\|git add\|status:" core/scripts/stop_state.sh` → hits only inside the `--selftest` fixture (core/scripts/stop_state.sh:109, :125, building the temp repo); `record()` itself runs `git status --porcelain`, `git rev-list --count`, `git log -1` and reads nothing else. Status changes stay a lane decision (workflows/dev.md, "Stopping mid-ticket", core/workflows/dev.md:451).
- can the rule red a legitimate hand-off? A fresh `recorded:` line passes (selftest); a file with no `recorded:` line falls back to mtime, so a hand-written note cannot dodge the clock forever (selftest, `os.utime` to 2026-01-01 → RED). A Done ticket is skipped before the status is even parsed; a `Blocked` ticket is exempt by its raw status because `tracker.status_category` folds Blocked into `todo`.
- lowercase branch keys: `feat/proj-1-x` derives `PROJ-1` (the `tr` at core/scripts/stop_state.sh:31 also upper-cases `VTEAM_TICKET=proj-1`, asserted by case 6), matching `KEY_RE`'s upper-case tickets so the evidence dir name equals the backlog key.

Traces: tests/e2e.mjs:536, tests/e2e.mjs:547, adapters/claude-code.mjs:114, core/scripts/stop_state.sh:31, core/workflows/dev.md:451, `node tests/e2e.mjs`, `grep -n "git commit\|git add\|status:" core/scripts/stop_state.sh`
