# VT-22 — DEV tasksheet

CODE-SCOPE: core/scripts/ src/cli/ profiles/ tests/ README.md

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
