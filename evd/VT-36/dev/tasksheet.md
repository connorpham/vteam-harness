# VT-36 · dev tasksheet — measure the risk class, stop the review theatre
CODE-SCOPE: core/scripts/ core/workflows/ core/doctrine/ core/templates/ src/cli/init.mjs tests/e2e.mjs .vteam/ .claude/ docs/team/ docs/GUIDE.md README.md CHANGELOG.md evd/VT-36/ docs/pm/ docs/backlog/

Branch `feat/VT-36-change-class` from main 3b9b95d.

| T | Task | State |
|---|---|---|
| T1 | Establish the cost with evidence from this repo, not estimates (VT-29 ≈60k tokens for one deleted flag; 12/40 commits touch no executable file) | done — proof.md §1 |
| T2 | `change_class.py`: skeleton comparison (strings, comments, JSX text vs identifiers), four classes, fails closed | done |
| T3 | `review_check`: `review_shape(class, reviewers)`; docs → no card, surface → one card + one bullet; class printed on every verdict | done |
| T4 | Knobs `review.proportional` (default true) and `review.surface_max_lines` (40) in init, the example config and the documented block | done |
| T5 | Doctrine: red-flags row 2 rewritten with the measured rule + a corollary; dev.md T4b tells the lane to run the classifier BEFORE briefing reviewers | done |
| T6 | Tests: classifier selftest (17 cases), review_check shape cases, 5 e2e checks incl. the reversal knob | done — 227/227 |
| T7 | Seven code-only mutations, tests kept | done — mutations.md |
| T8 | The audience question goes to the decision queue, not into my own judgement | done — the queue's newest row |

## Decisions taken here, reversible, recorded
- Default is ON. The knob turns the uniform fence back in one line, and the class is printed on every verdict so a reader always knows which shape was applied and why.
- Markdown under `core/doctrine/`, `core/workflows/`, `core/templates/`, `docs/team/`, `.claude/`, `.github/`, `.vteam/`, `profiles/`, `adapters/`, `providers/` is NOT prose: it is rendered into the runtime. A doctrine edit is never `docs` class.
- `surface` still requires a card. A string can be a shell command, a SQL fragment or a selector a test asserts on; what changes is the number of bullets, never the traces.
