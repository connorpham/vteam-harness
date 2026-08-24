# VT-1 — PASS

COMMIT: 574bd6c07b71c27689974909cb2605a68913f7ce
VERIFIED-AT: 2026-08-24T04:42:37Z

## 1. What was verified

That vteam, installed into its own repository by its own `init`, passes every
gate it ships to adopters — and that the install measurably closed the
self-audit gap the 2026-08-24 framework review named as the top credibility
hole (score 62/C: no ledger, no evidence, no anchored verdicts of its own).

## 2. How it was verified

All commands ran at the pinned commit on a clean tree, transcripts captured
verbatim in TC_1/cmd_verify.md:

- `node bin/vteam.mjs init --yes … --key VT` — then `git status` reviewed by
  hand: the repo's pre-existing `.githooks/pre-push` fence and
  `core.hooksPath` were NOT touched (AC-1).
- `node bin/vteam.mjs doctor` — manifest integrity (55 framework-owned files)
  plus all 22 discovered gate selftests, PREFLIGHT GREEN (AC-1).
- `npm test` — 141/141 e2e checks, 15 ctx conformance fixtures, 10
  ledger-grammar fence rows (AC-2; `.vteam/test.sh` wires this same suite
  into the gate profile).
- `node bin/vteam.mjs audit` — score after install (AC-4).

## 3. Test cases

- TC_1/ — NON-UI verification of AC-1..AC-4 (this is a CLI framework: the
  honest evidence is real command transcripts, not screenshots).
  RESULT: PASS — see TC_1/manifest.md and TC_1/cmd_verify.md.

## 4. Verdict rationale

Every acceptance criterion is backed by a machine's exit code, not a claim:
doctor GREEN, 141/141 + 15 + 10 green, audit 91/A (target was ≥ 85, from
62/C). The one deliberate limit is recorded in the root manifest: the repo
keeps its own minimal pre-push fence rather than the full adopter fence, so
branch-grammar/dossier enforcement is NOT self-applied — stated, not hidden.
