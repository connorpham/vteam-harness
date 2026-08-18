# DRAFT — r/ClaudeAI post (evidence story)

> **DRAFT — the owner posts this, not an agent.** Target: r/ClaudeAI (crossed 1M
> members July 2026), cross-post to r/ClaudeCode; adapt the tool angle for r/cursor
> ("works in Cursor too — same gates"). This subreddit rewards **workflow testimony
> with receipts**, not announcements. Every `[SCREENSHOT: ...]` below must be a real
> capture from a real session before posting — if a screenshot can't be produced,
> cut the claim.

---

**Title options:**

1. Claude said "done." A gate said no. Here's the diff it didn't mention.
2. I stopped trusting my agents' "done" — now a script has to agree. Real transcripts inside.
3. My Claude Code team ships with 15 gates that can actually fail. Here's what they caught this week.

---

**Body:**

Like everyone here I've had the moment: Claude says *"All tests pass, the feature
is complete ✅"* and the build is broken, or the test never ran, or the "fix" is a
renamed command.

I run a virtual team (PM/BA/DEV/QA workflows) on a real project, on a schedule,
mostly unattended. The only reason I can sleep is that "done" stopped being
something the agent says and became something a script verifies. Concretely:

**1. The claim.**

[SCREENSHOT: agent session — the dev lane's final message claiming the ticket is
done, verify green, ready for review]

**2. The gate disagreeing.**

[SCREENSHOT: terminal — `review_check` / pre-push hook rejecting the push: no
committed review dossier for this diff, exit code 1, the push physically blocked]

This isn't a prompt asking Claude to double-check. It's a pre-push hook. There is
no way to push to main without a committed review card from a *fresh* reviewer
agent — and a card without a "what I tried to break" list is invalid.

**3. My favorite part — the gates themselves are tested.**

My old harness once shipped two checks that had **never been red** (one compared a
git diff that was never staged — always green, always useless). So now every gate
carries a `--selftest`: it builds a violating fixture and proves it goes red.

[SCREENSHOT: `doctor` output — 17 selftests green, each one a check that just
proved it can fail]

**4. Verdicts expire.**

QA passes a ticket → the verdict records the exact commit it examined. Someone
(agent or me) touches the code afterward → the verdict is stale and the ticket
re-queues automatically.

[SCREENSHOT: `stale_verdict_check` re-queuing a Done ticket after a post-verdict
commit]

**5. Grade your own repo (this part needs no install):**

```
npx vteam-harness audit
```

0–100 across six dimensions (gates, hooks, evidence, review trail, verdicts,
self-proof). It writes nothing and works on any repo — mine scored embarrassingly
low before all this.

[SCREENSHOT: audit output on a typical repo — the red ❌ lines with "a machine
would need to see:" fixes]

It's open source (`vteam-harness` on npm, MIT), works with Claude Code / Cursor /
Windsurf / Codex / Copilot, and the whole thing runs with zero external services
if you use the markdown tracker. Honest limits: pre-1.0, sweet spot is a solo
owner + virtual team, trackers are Jira/GitHub/markdown (no Linear yet).

Happy to answer anything — especially "what does it catch that prompting doesn't",
because I have a provenance file of incidents behind every gate.

---

**Comment-thread prep (have ready):**

- The BMAD #2003 / Spec Kit #1784 links for "how is this different from X" replies
  — frame respectfully: those tools own planning; this is the enforcement layer.
- A 30-second asciinema of one gate going red.
- The audit run against a popular open-source repo (pick one, verify the output
  is fair before citing it).
