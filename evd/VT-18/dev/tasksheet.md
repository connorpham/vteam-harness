# VT-18 — DEV tasksheet

CODE-SCOPE: core/scripts/

Two checkers and their selftests. No config change: `done_statuses` keeps its meaning, and the
decision file's location is already `paths.pm`.

## Steps

- **T0** — both gaps were met head-on rather than theorised: TB-9's dependency and TB-7's closure
  each produced a red that was *correct under the old rules and wrong about the world*.
- **T1** — decide what "settled" means before coding, because the whole feature turns on it:
  only `✅ DECIDED` releases anything. `🟡 PROVISIONAL` and `🔴 OPEN` do not, so a machine's own
  provisional call cannot close a ticket.
- **T2** — an unsettled decision edge prints and exits 0. A gate that reds on an unanswered question
  would punish the team for asking, which is the opposite of what the decision queue is for.
- **T3** — the same family in `log_check`: a cited Q/D/A must exist. Guarded by
  `if unknown and known_decisions`, so a repo with no decisions file is not failed for having none.
- **T4** — prove each branch in the selftest, including the two new GREENs, not only the reds.
