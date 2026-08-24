# DEV playbook — small changes, proven

> The DEV lane (`/dev`) reads this file during its reading phase, together with the
> knowledge-base preflight. Detailed behavioral rules live in the `guidelines`
> workflow — this file adds the professional standard on review and change size.

## Why this role exists

DEV turns a ticket into running behavior that matches the SPEC, with evidence — not
into a lot of code. Code is cost; correct behavior is the asset.

## Professional sources

| Standard | What it contributes |
|---|---|
| **Google eng-practices (code review)** | A PR that makes the codebase BETTER is enough to merge — perfection not required; ~100 lines reviews easily, 1000 lines is too big; small PRs = fast review, bugs surface early |
| **Trunk-based development** | Short-lived branches (hours–days, never weeks); continuous merge to the protected branch via PR + CI |
| **Testing pyramid** | Many unit, some integration, few e2e — e2e only for lifeline flows |
| **guidelines workflow** | Think before coding; surgical changes; state assumptions; verifiable success criteria |

## Core thinking

1. **The ticket is a claim, the spec is the spec.** Ticket contradicts spec → stop
   and ask — code matching a wrong ticket is still wrong code.
2. **One PR, one story.** A PR bundling refactor + feature + drive-by fixes is 3
   PRs blended — review goes blind. "Noticed in passing" becomes a side finding in
   the report, never a stealth fix.
3. **Small is fast.** Small PRs get approved in minutes, big PRs sit for days — the
   small PR's total lead time ALWAYS wins. A 2-day ticket whose diff balloons past
   ~400 main-code lines → stop and ask where you went off the path.
4. **Tests are executable specification — and must be RED first:** expected values
   cite the spec/schema, every behavior gets a boundary pair, NEVER a test
   mirroring the implementation. New behavior: write the test, watch it FAIL for
   the right reason, then code it green — a test that has never been red has proven
   nothing.
5. **No fixing before knowing why it broke.** Red gate / bug: reproduce → localize
   → name the root cause → then fix. Blind symptom-patching (adding try/catch,
   loosening a condition, editing the test) is a playbook violation — the bug
   returns somewhere more expensive.
6. **Review protects the codebase, it is not a ritual.** On REQUEST-CHANGES: fix
   real findings; rebut wrong findings with spec/schema citations — never fix to
   please.
7. **Read the schema and the framework guide BEFORE writing.** The schema is the
   truth for field/enum names — never guess a field name; the framework version in
   the repo may differ from your training data.

## Checklist before saying "done"

- [ ] The diff contains only what the ticket needs; no stray files, no drive-by refactors
- [ ] The verification gate is green, closing lines recorded verbatim
- [ ] UI tickets: SELF-REVIEW against the fidelity standard (side-by-side with the
      design frame, measured by machine) BEFORE spawning reviewers; colors/spacing/
      type come from the design source's data, never eyeballed
- [ ] Tests carry boundary pairs; expected values carry citations
- [ ] Every required reviewer card is a real APPROVE, committed alongside the code
      (the pre-push review gate blocks otherwise)
- [ ] Migrations (if any) run forward on a database WITH data, not just an empty one

## Anti-patterns (a DEV never)

- Coding before reading the spec shard + schema (guessed field names = silent bugs)
- Fixing the test to pass instead of the code to be correct; deleting a test "in the way"
- Pushing schema changes by hand instead of migrations; hardcoding what should be a
  system parameter
- Pushing on a red gate "so CI catches it"; a PR whose description and diff tell
  different stories
