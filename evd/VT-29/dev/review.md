# Review dossier — VT-29 (docs_shrink_check made PR clones shallow)

**Provenance, stated plainly:** both cards were written by the implementing session, not by
spawned reviewers. Every bullet below is a command that was run on 2026-09-17 with the output it
produced; the reproduction that drove the fix is in `evd/VT-29/dev/proof.md` §1.

## R1 — implementation review (mutation probes)
APPROVE

Tried to break:
- put `--depth=1` back on the base fetch at core/scripts/docs_shrink_check.sh:83 and ran `bash core/scripts/docs_shrink_check.sh --selftest` — RED: "PR-mode base fetch turned a full clone SHALLOW (.git/shallow appeared)". Restored.
- kept `--depth=1` AND deleted the new assertion at core/scripts/docs_shrink_check.sh:57 — selftest GREEN, so the assertion is the only thing that bites; the other four selftest cases cannot see this defect. Restored.
- ran the fixed step inside a clone built exactly like actions/checkout for PR #75 (`git fetch origin +refs/heads/*… +0021b3d…:refs/remotes/pull/75/merge`, `git checkout refs/remotes/pull/75/merge`): before and after, `.git/shallow` absent, `git show --name-only --format= a82e8748` = 12 files, `python3 .vteam/scripts/graph_check.py` coherent. The pre-fix step in the same clone: shallow = a82e8748, 501 files, graph RED — byte-for-byte the CI message.
- checked the mirror and the manifest: `cmp core/scripts/docs_shrink_check.sh .vteam/scripts/docs_shrink_check.sh` identical; `node bin/vteam.mjs doctor` → manifest verified, 171 files intact.

Traces: core/scripts/docs_shrink_check.sh:83, core/scripts/docs_shrink_check.sh:57, `bash core/scripts/docs_shrink_check.sh --selftest`, `python3 .vteam/scripts/graph_check.py`

## R2 — adversarial read: does dropping the depth limit break anyone else?
APPROVE

Tried to break:
- a user whose CI checks out with the default `fetch-depth: 1` (shallow from the start): `git clone --depth 1 -b feat/VT-27-benchmark-scorecard …`, then `GITHUB_BASE_REF=feat/VT-26-first-run bash .vteam/scripts/docs_shrink_check.sh` — ✅ passes, and `git diff FETCH_HEAD HEAD --name-only` still resolves (10 files). A fetch without `--depth` into an already-shallow repo neither fails nor deepens what it does not need.
- looked for the same pattern elsewhere: `grep -rn -- "--depth" core/scripts profiles/*/scripts` — only this line. `preflight.sh` and `gate.py` run no fetch.
- asked whether the fix could hide a real shrink: the comparison base is unchanged (`FETCH_HEAD` of the base branch, core/scripts/docs_shrink_check.sh:85); only the depth flag went. The two shrink mutations in the selftest still RED (part of the same OK line).
- checked the new selftest fixture does not depend on the machine's default branch name: `base_branch` is read from `origin/HEAD` of the pair built at core/scripts/docs_shrink_check.sh:50, so `main`/`master` both work; and `git checkout -q -- .` first restores the ADR mutation the previous case left dirty.
- the PR-mode comparison failing to fetch (base branch missing on origin) is pre-existing behaviour — `>/dev/null 2>&1` swallows it and `FETCH_HEAD` may be stale. Left alone: out of this ticket's scope, noted in the ticket's "Out of scope".

Traces: core/scripts/docs_shrink_check.sh:85, core/scripts/docs_shrink_check.sh:50, `git clone --depth 1 -b feat/VT-27-benchmark-scorecard https://github.com/connorpham/vteam-harness`, `grep -rn -- "--depth" core/scripts`
