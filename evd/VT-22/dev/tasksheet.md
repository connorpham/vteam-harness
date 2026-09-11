# VT-22 — DEV tasksheet

CODE-SCOPE: core/scripts/ src/cli/ profiles/ tests/ core/workflows/ README.md CHANGELOG.md package.json

`CHANGELOG.md` and `package.json` were added when `graph_check` reded the round-2 commit for
touching them: a review finding was that the suite's version tripwire was failing, and the fix for
it is a version bump — so the release files are part of this ticket's footprint, not drift.
`core/workflows/` was added for the same honest reason: a reviewer required `closed-by:` to be
documented where a ticket author reads it, which is `/pm`, not only in the checker that enforces it.

Recorded rather than hidden: I reported "gate GREEN" in round 3 and a reviewer found it RED. I had
run the gate BEFORE committing, so `graph_check` had not yet seen the commit whose scope it judges.
The claim was true of the working tree and false of the branch, which is the distinction that
matters to everyone but me.

`tests/` and `README.md` are in scope because two findings were about coverage and about numbers
the README publishes; the suite's own tripwire caught the second.

## Steps

- **T0** — reproduce every blocker before accepting it. All four reproduced; two (the `Closed`
  bypass and the prefix match) were verified with a throwaway fixture before a line was changed.
- **T1** — fix the rules that had become inert first: a gate that passes everything is worse than
  no gate, because it is believed.
- **T2** — then the consumer-facing reds: a step that fails a repo for its history gets switched
  off by the people it was meant to help.
- **T3** — then the instrument, and re-measure: the prefix fix moves the D13 input from 98 to 94.
- **T4** — then coverage, because the honest answer to "what covers this?" was "nothing" for four
  branches and for one whole file.
