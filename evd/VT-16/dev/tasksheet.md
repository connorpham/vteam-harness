# VT-16 — DEV tasksheet

CODE-SCOPE: core/scripts/

One new script and nothing else. No `applies:` line is touched — the ticket's whole point is
that changing one needs a decision first (D13), and a scope line that permitted
`core/doctrine/` would make it easy to slide into doing it.

## Steps

- **T0** — confirm the tool is missing before writing it: `grep -rln applies core/scripts/`
  returns `competency_check.py` (grammar only), `gate.py`, `evd_index.py`,
  `bdd_report_check.py`, `lib/ctx.sh`. None answers "which competencies does this ticket load".
- **T1** — measure the cost first, by hand, so the tool has a number to reproduce.
- **T2** — run the tempting fix as an experiment and let it fail on the evidence rather than
  on taste: narrowing the match scope, then listing what it drops.
- **T3** — write the script so the *location* of each match is part of the output; that is the
  distinction the whole diagnosis rests on.
- **T4** — verify on both repos, keep it exit-0 by default, file D13.
