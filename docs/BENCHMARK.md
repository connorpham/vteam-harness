# vteam vs BMAD — one frozen login spec, one held-out judge

**Status 2026-09-17: scoring in progress.** Both arms ran on 2026-09-03/04 (same spec,
same scaffold, same agent CLI, same model — the only variable is the framework). The
held-out judge (39 black-box probes, calibrated to 0% on an empty arm and 100% on a
reference solution) is being run against both arms now; the scorecard lands in this file
**whichever way it goes**. Until then this page carries only what is already true:

| | arm-a (vteam) | arm-b (BMAD) |
|---|---|---|
| Run | 2026-09-03 → 09-04 | 2026-09-03 |
| Commits after the shared baseline | 25 | 11 |
| Claims filed (`CLAIMS.md`) | yes — one row per AC | yes — one row per AC |
| State at stop | **11 files left uncommitted** (a throttle migration and its tests mid-ticket) — scored as committed, per protocol §3 | clean |
| Cost from session logs | not recoverable — the arms ran in an environment whose Claude Code logs are not on this machine; `RUNLOG.md` carries what was noted by hand | same |

Harness, protocol and calibration evidence: `~/Documents/vteam-vs-bmad/` (PROTOCOL.md,
`results/_calibration`, `results/_reference`) — not in this repo because the judge is the
held-out exam and must stay out of any arm's reach.
