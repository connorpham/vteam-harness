# VT-17 — DEV tasksheet

CODE-SCOPE: core/scripts/ profiles/

The checker and the manifests that call it. `.vteam/` is an always-legal deploy home, so the
runtime copy needs no declaration.

## Steps

- **T0** — confirm the gap rather than assume it: `grep -rn evd_check core/workflows/*.md` returns
  12 hits; `grep -rn evd_check profiles/*/gates.yaml .vteam/scripts/gate.sh` returns none.
- **T1** — decide the failure policy before writing code, because a sweep that fails everything is
  a sweep nobody keeps: closed + non-legacy = error, everything else = report.
- **T2** — read the expected case count from the report's own citations, so the number cannot drift
  from the claim.
- **T3** — reuse `check_tree` unchanged; the sweep is a caller, not a second implementation.
- **T4** — prove it by breaking a real pack and watching the gate go red, then restoring it.
