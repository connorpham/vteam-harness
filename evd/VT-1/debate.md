# VT-1 — verifier vs challenger

### verifier — the claim holds
The four ACs are each anchored to an exit code captured in TC_1/cmd_verify.md:
doctor GREEN (manifest 55 files + 22 selftests), gate suite 141/141 + 15 + 10,
audit 91/A against a ≥85 target, hooks provably untouched (git status empty for
.githooks/ after init). Nothing in this evidence is self-reported prose; every
number can be regenerated from the pinned commit.

### challenger — what I tried to break
1. "Init silently clobbered the repo's own fence" — checked `git status`
   after init: `.githooks/` absent from the diff, `core.hooksPath` unchanged.
   Not broken, but note init SKIPPED the fence because hooks existed — the
   adopter-grade fence (branch grammar, dossier leg) is therefore NOT active
   here. Demanded this be stated in the manifest rather than glossed; it is.
2. "The audit jump is circular — vteam grades itself with its own rubric" —
   partially conceded: the rubric is vteam's. But 62→91 measures the same
   rubric before/after, and the rubric's inputs (ledger rows, evidence files,
   anchored verdicts) now exist as git-tracked artifacts anyone can inspect.
3. "The QA ledger row and this debate are written by the same actor" — true
   and unavoidable at team.size 1; the mitigation is that every claim above
   is a command transcript, not testimony. Flagged, not blocking.
Verdict stands: PASS.
