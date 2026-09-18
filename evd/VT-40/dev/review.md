# Review dossier — VT-40 (a derived port is a starting point, not a promise)

**Provenance, stated plainly:** both cards were written by the implementing session, not by spawned
reviewer agents. Every bullet is a command run on 2026-09-18; outputs are in `proof.md`.

## R1 — implementation review
APPROVE

Tried to break:
- removed the stepping at core/scripts/lane_env.sh:86 and ran `bash core/scripts/lane_env.sh --selftest` — RED (`a port another lane already claims must be stepped over, got 3648`).
- made a lane treat its OWN marker as somebody else's at core/scripts/lane_env.sh:67 — RED (`the same worktree must derive the same environment twice`). That is the subtler failure: without the self-exclusion every re-run would walk to a new port and nothing downstream would hold still.
- ran the selftest five times in a row after the fix: green every time. Before it, the outcome depended on which temp directory `mktemp` handed out.
- checked the walk terminates: `free_port` (core/scripts/lane_env.sh:71) counts 800 attempts and wraps at 3900 back to 3100, then returns the derived port rather than looping forever.

Traces: core/scripts/lane_env.sh:71, core/scripts/lane_env.sh:67, `bash core/scripts/lane_env.sh --selftest`, `node bin/vteam.mjs doctor`

## R2 — adversarial read
APPROVE

Tried to break:
- asked whether stepping can hand two lanes the same port anyway: `claimed_by_others` (core/scripts/lane_env.sh:63) reads every marker under the lanes root except this lane's own, so a port is skipped while any other lane's marker holds it. Two lanes started at the exact same instant could still race — markers are files, not locks — and that is a narrower window than the 1-in-800 birthday problem this replaces, worth naming rather than pretending away.
- asked whether the output stays deterministic: for a fixed set of markers it is, and the same worktree+lane derives byte-identical output twice (an existing assertion). The port a lane lands on now depends on which lanes already exist, which is the point: it is an allocation, not a pure hash.
- checked the step is never silent — the emitted environment prints the original port and where it went, and the selftest fails if that line is missing.
- checked the new selftest block cannot poison the older assertions: it runs LAST and removes its markers, because the marker assertion above globs `a-*/lane.env` and picked up the R2 marker when the block sat in the middle (that is exactly how it failed the first time).

Traces: core/scripts/lane_env.sh:63, core/scripts/lane_env.sh:71, `bash .vteam/scripts/lane_env.sh --selftest`
