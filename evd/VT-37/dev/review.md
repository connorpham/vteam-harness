# Review dossier — VT-37 (the graph computes the execution plan)

**Provenance, stated plainly:** both cards were written by the implementing session, not by spawned
reviewer agents. Every bullet is a command run on 2026-09-18; outputs are in `proof.md` and
`mutations.md`. By its own classifier this ticket is `logic` class, so it pays the full fence.

## R1 — implementation review (one mutation per rule)
APPROVE

Tried to break:
- flattened Kahn so dependencies stop making levels at src/cli/graph.mjs:663 neighbourhood and ran `node src/cli/graph.mjs --selftest` — RED (`chain must be 3 waves: [0]`). Restored from a byte copy.
- made an undeclared CODE-SCOPE read as an EMPTY scope at src/cli/graph.mjs:637 — RED (`an undeclared scope conflicts with everything, loudly`). This is the mutation that matters most: it would have put two agents with unknown scopes in one batch, which is exactly the collision `parallel_check` exists to red.
- removed the `team.parallel` ceiling from the batching at src/cli/graph.mjs:724 — RED (`team.parallel is a ceiling, not a suggestion`).
- let a ticket whose branch is already pushed stay dispatchable at src/cli/graph.mjs:649 neighbourhood — RED (`a ticket with a branch pushed is running, never dispatchable again`).
- reverted the cycle-shape normalisation at src/cli/graph.mjs:672 — RED (`--plan must exit 0: graph: c is not iterable`). This was a REAL bug while writing: the model carries cycles as `{path, display}`, the first draft read plain arrays, and a repo with a cycle crashed the plan.
- let a missing day-cost count as zero at src/cli/graph.mjs:747 — RED (`a missing day-cost makes the number incomplete — it is never guessed`).

Traces: src/cli/graph.mjs:663, src/cli/graph.mjs:637, src/cli/graph.mjs:724, `node src/cli/graph.mjs --selftest`, `npm test`

## R2 — adversarial read: does the plan weaken anything, or claim more than it measured?
APPROVE

Tried to break:
- checked the plan cannot relax a gate: it writes nothing, runs no step, and `bash .vteam/scripts/gate.sh` is GREEN with the same 15 steps before and after. `graph` still exits 0 in every mode — it is a mirror; `dor_check`, `schedule_check`, `evd_check` and `parallel_check` remain the enforcers.
- checked it cannot dispatch anything on its own: /pm and /team read it and adjudicate; the plan itself prints `decided_by_the_lane_not_here`, and the e2e asserts that list is present and non-empty. A plan that silently decided the priority overrides would be the dangerous version of this ticket.
- attacked the scope comparison with the pair that actually collides: `src/` vs `src/auth/a.ts`. The first draft called them disjoint because it trusted the caller to strip the trailing slash; `scopesOverlap` normalises both sides itself now (src/cli/graph.mjs:637) and the selftest pins that exact pair.
- attacked the QA lane split: an In Review ticket gets `next_lane: qa` and its own evidence directory as scope, so a verification never eats a code slot — and the batching compares each entry's COMPUTED scope, not the raw tasksheet map, which the first draft got wrong (the QA item then conflicted with everything).
- checked the false claims are recorded, not quietly dropped: reviewers already run in parallel and gate-step caching would save 1.4 % here. Both are in proof.md §1 and in the ticket's Out of scope, so the next session does not re-open them on the same wrong premise.
- checked the numbers are the repo's own: 170,772 bytes of ordering input vs 9,720 bytes of plan, both measured by `stat` on the real files, and the critical path reports INCOMPLETE on this repo because no ticket carries a day-cost — the honest answer rather than a fabricated schedule.

Traces: src/cli/graph.mjs:637, src/cli/graph.mjs:672, src/cli/graph.mjs:747, `npx vteam-harness graph --plan`, `bash .vteam/scripts/gate.sh`
