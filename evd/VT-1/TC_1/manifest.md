# TC_1 — self-install passes every self-applied gate

TYPE: NON-UI
RESULT: PASS

REQUIREMENT: VT-1 AC-1..AC-4 — init without clobbering, doctor green, the
real suite wired into the gate profile, audit ≥ 85.

STEPS:
1. From a clean main at 574bd6c, run
   `node bin/vteam.mjs init --yes --name vteam --key VT --language en
   --profile generic --tracker markdown --design none --autonomy assisted
   --tools claude-code`.
2. `git status --porcelain` — confirm `.githooks/` is NOT in the diff and
   `git config core.hooksPath` still prints `.githooks` (AC-1).
3. Set `git.code_paths: [src/, core/, bin/]` and `project.adopted: 2026-08-24`
   in vteam.config.yaml; create `.vteam/test.sh` running `npm test` (AC-2).
4. `node bin/vteam.mjs doctor` — expect manifest verified + all selftests
   green + PREFLIGHT GREEN (AC-1).
5. `npm test` — expect 141/141 e2e, 15 conformance fixtures, 10 ledger-fence
   rows (AC-2).
6. `node bin/vteam.mjs audit` — expect score ≥ 85 (AC-4; baseline before
   install was 62/C, captured in the review that opened this ticket).

EXPECTED: every command exits 0 with the numbers above.
ACTUAL: doctor GREEN (55 manifest files, 22 selftests) · 141/141 + 15 + 10
green · audit 91 A · hooks untouched — full transcripts in cmd_verify.md.
