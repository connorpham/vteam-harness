# VT-3 — gate probes against a COPY of docs/team/competencies (real runs, 2026-08-28)

```console
$ python3 .vteam/scripts/competency_check.py --root <copy>
✅ competency_check: 10 competencies well-formed and indexed under /private/tmp/claude-501/-Users-connorpham-Documents-vteam/89054c28-407b-4e1f-a00c-494521cc47bb/scratchpad/comp
exit=0

# AC-2 — '## Reviewer lens' removed from dev-api-design.md
❌ competency_check: 1 problems under /private/tmp/claude-501/-Users-connorpham-Documents-vteam/89054c28-407b-4e1f-a00c-494521cc47bb/scratchpad/comp
   - dev/dev-api-design.md: missing section `## Reviewer lens`
exit=1

# AC-3 — description turned into a procedure
❌ competency_check: 3 problems under /private/tmp/claude-501/-Users-connorpham-Documents-vteam/89054c28-407b-4e1f-a00c-494521cc47bb/scratchpad/comp
   - dev/dev-api-design.md: description must start with `Use when` — it is the trigger, not the summary
   - dev/dev-api-design.md: description narrates a procedure ('then') — agents follow the summary and skip the body; describe the PROBLEM
   - dev/INDEX.md is stale — run `competency_check.py --write-index`
exit=1

# AC-4 — INDEX.md no longer matches the files (dev-debugging.md removed)
❌ competency_check: 1 problems under /private/tmp/claude-501/-Users-connorpham-Documents-vteam/89054c28-407b-4e1f-a00c-494521cc47bb/scratchpad/comp
   - dev/INDEX.md is stale — run `competency_check.py --write-index`
exit=1

# back to green
✅ competency_check: 10 competencies well-formed and indexed under /private/tmp/claude-501/-Users-connorpham-Documents-vteam/89054c28-407b-4e1f-a00c-494521cc47bb/scratchpad/comp
exit=0
```
