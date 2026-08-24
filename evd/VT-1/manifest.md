# VT-1 — requirement, plainly

vteam must be an adopter of itself: installed by its own `init`, measured by
its own `audit`, its release history in its own ledger, its verification in
its own evidence tree — because a proof-of-done framework whose own repo
cannot prove done is marketing, not engineering.

Scope of this evidence: the self-install (AC-1), the gate wiring to the real
test suite (AC-2), the seeded-and-gated ledger (AC-3), and the audit score
delta 62/C → ≥85 (AC-4).

Known, deliberate limit — stated so nobody discovers it as a surprise: this
repo keeps its own minimal pre-push fence (no-main-push + secret scan) instead
of the rendered adopter fence, so the branch-grammar and review-dossier legs
are not self-applied. The gates that ARE self-applied from this commit on:
docs_shrink, log_check, graph_check, verbatim_gate, and the full npm suite via
`.vteam/test.sh` — locally through `gate.sh` and on CI through
`.github/workflows/vteam-gate.yml`.
