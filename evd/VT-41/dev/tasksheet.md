# VT-41 · dev tasksheet — one CodeQL version, one PR
CODE-SCOPE: .github/ CHANGELOG.md evd/VT-41/ docs/pm/ docs/backlog/

Branch `fix/VT-41-codeql-pins` from main af20c6f.

| T | Task | State |
|---|---|---|
| T1 | Diagnose why two of three PRs were red: init and analyze must match, so each single-path PR breaks the pair | done — proof.md §1 |
| T2 | Verify the new SHA upstream before trusting it: it must exist, and belong to the tag the comment claims | done — proof.md §2 |
| T3 | Apply the one SHA to all three usages (codeql.yml init + analyze, scorecard.yml upload-sarif) | done |
| T4 | Group `github/codeql-action*` in dependabot.yml so the next bump is one PR | done |
| T5 | CI green on the combined change, then merge and close #69/#70/#71 pointing here | see proof.md §4 |
