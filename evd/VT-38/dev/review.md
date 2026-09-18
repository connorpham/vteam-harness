# Review dossier — VT-38 (a merged branch is not work in flight)

**Provenance, stated plainly:** both cards were written by the implementing session, not by spawned
reviewer agents. Every bullet is a command run on 2026-09-18; outputs live in `proof.md` and
`mutations.md`. `logic` class by the repo's own classifier, so the full fence applies.

## R1 — implementation review (one mutation per rule)
APPROVE

Tried to break:
- removed `--no-merged` from the branch listing at src/cli/graph.mjs:658 and ran `npm test` — RED on exactly the check that matters (`a branch already merged into the protected branch is NOT in flight`, 233/234). That single flag is the difference between 21 in flight and 1.
- deleted the stale-WIP detection at src/cli/graph.mjs:726 — RED in the plan selftest (`In Progress with no unmerged branch is drift, not flight`).
- removed the blocked-ticket exemption from the gate's drift rule at core/scripts/graph_check.py:449 — RED (`a ticket waiting on another is blocked, not drifting`). Without it the rule would nag about every ticket that is legitimately parked behind a decision, and a warning that cries wolf is a warning nobody reads.
- disabled the drift warning entirely in core/scripts/graph_check.py — RED in its selftest.

Traces: src/cli/graph.mjs:658, src/cli/graph.mjs:726, core/scripts/graph_check.py:449, `npm test`, `node src/cli/graph.mjs --selftest`

## R2 — adversarial read: does this hide work, or invent status?
APPROVE

Tried to break:
- asked whether the fix can HIDE real work: a branch counts as in flight when it is unmerged, and `-a` includes `remotes/*` (src/cli/graph.mjs:668 strips the remote prefix), so a teammate's pushed branch counts too. The dangerous direction would be under-reporting, and the fallback at core/scripts/graph_check.py:434 deliberately lists ALL branches when the protected branch is missing — a fresh clone or a CI checkout then over-reports rather than concluding nothing is running.
- checked the drift rule cannot fail a build: it appends to `notes`, and `graph_check` prints notes with ⚠️ and returns 0 unless `errs` is non-empty. Confirmed on this repo, where the rule fires for VT-2 and the gate is GREEN.
- refused the tempting data fix: VT-2 shipped as PR #55 with no dispatch row, so In Review would trip the E14 rule, and the only retroactive row the grammar accepts would carry an invented `tok ≈ N`. The ticket keeps the state its record supports, the gap is written into the ticket, and the grammar question is the decision queue's newest row. Nine other tickets were corrected only where a merged branch AND a dispatch row backed the new status.
- checked the nine corrections did not silently close anything: six moved to In Review, which is not a closure — Done still requires a QA PASS verdict, and `graph_check`'s done-without-verdict rule is untouched. VT-14 moved backwards to To Do, which is the honest direction for a ticket blocked by an unfinished one.
- re-ran the full gate and suite after the corrections: `GATE: GREEN (15 steps)`, `E2E: GREEN — 234/234`, and the plan now reads 34 schedulable · 1 in flight · 1 blocked · 1 stale WIP.

Traces: src/cli/graph.mjs:668, core/scripts/graph_check.py:434, `npx vteam-harness graph --plan`, `bash .vteam/scripts/gate.sh`
