# VT-4 — QA competency gate probes (real runs on a copy, 2026-09-07)

```console
$ competency_check.py --root <copy>   # dev(10) + qa(9), reference/ ignored
✅ competency_check: 19 competencies well-formed and indexed under /private/tmp/claude-501/-Users-connorpham-Documents-vteam/89054c28-407b-4e1f-a00c-494521cc47bb/scratchpad/qc
exit=0

# AC-2 — Reviewer lens removed from qa-security-probes.md
❌ competency_check: 1 problems under /private/tmp/claude-501/-Users-connorpham-Documents-vteam/89054c28-407b-4e1f-a00c-494521cc47bb/scratchpad/qc
   - qa/qa-security-probes.md: missing section `## Reviewer lens`
exit=1

# AC-3 — description made procedural + INDEX drift
❌ competency_check: 3 problems under /private/tmp/claude-501/-Users-connorpham-Documents-vteam/89054c28-407b-4e1f-a00c-494521cc47bb/scratchpad/qc
   - qa/qa-security-probes.md: description must start with `Use when` — it is the trigger, not the summary
   - qa/qa-security-probes.md: description narrates a procedure ('then') — agents follow the summary and skip the body; describe the PROBLEM
   - qa/INDEX.md is stale — run `competency_check.py --write-index`
exit=1

# reference/ tables are NOT policed (a table over the word budget is fine there)
reference files: 4 — longest 1981 words, gate still green

# back to green
✅ competency_check: 19 competencies well-formed and indexed under /private/tmp/claude-501/-Users-connorpham-Documents-vteam/89054c28-407b-4e1f-a00c-494521cc47bb/scratchpad/qc
exit=0
```
