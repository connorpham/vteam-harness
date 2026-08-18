# DRAFT — X launch thread

> **DRAFT — the owner posts this, not an agent.** Formula per the research: tweet 1
> = one concrete artifact transformation + a screen-recording GIF (Task Master's
> launch tweet playbook: 0→15.5k stars in 9 weeks). Record the GIF before posting —
> a real terminal session, no mockups. Sustain afterward with weekly changelog
> threads and explicit retweet asks. Tag tool accounts where relevant
> (@AnthropicAI's Claude Code, @cursor_ai, @windsurf_ai) sparingly — once, in the
> tool-support tweet, not in tweet 1.

---

**Tweet 1 (the hook + GIF):**

Your AI agent: "Done ✅ All tests pass."

vteam: `review_check: RED — no committed review dossier for this diff. Push blocked.`

Proof-of-done for AI agents. The agent doesn't get to say done anymore — a machine
does.

[GIF: split terminal — agent's "done" claim on top; pre-push hook going red and
blocking the push below; then the gate going green after a real review card lands]

**Tweet 2 (what it is):**

vteam = a virtual AI team (PM · BA · architect · DEV · QA) + 15 machine gates, for
any repo on Claude Code, Cursor, Windsurf, Codex or Copilot.

One command:

npx vteam-harness init

Everything the agents claim must survive a script that can exit non-zero.

**Tweet 3 (the differentiator — gates that prove themselves):**

The uncomfortable lesson from running this on a real project: my own checks were
broken. Two of them had NEVER been red — green forever, catching nothing.

So now every gate ships a --selftest: build a violating fixture, watch it fail.

A gate that has never been red does not exist.

**Tweet 4 (verdicts pinned to commits):**

QA passes a ticket → the verdict records the exact commit it examined.

Code moves after the verdict → the verdict is stale, the ticket re-queues.
Automatically.

No more approvals that quietly apply to code nobody reviewed.

**Tweet 5 (the funnel — audit):**

Not ready to install anything? Grade your repo first:

npx vteam-harness audit

0–100 across gates / hooks / evidence / review trail / verdicts / self-proof.
Writes nothing. Works on any repo. For every ❌ it names the artifact a machine
would need to see.

[SCREENSHOT: audit output with grade banner]

**Tweet 6 (tool coverage + plugin):**

Claude Code users, no terminal needed:

/plugin marketplace add connorpham/vteam-harness
/plugin install vteam@vteam-harness
/vteam:setup

Same gates drive Cursor, Windsurf, Codex, Copilot — one team, any agent tool.

**Tweet 7 (the receipts / comparison):**

Every framework in this family tells agents to be rigorous. We compared who
VERIFIES the work — BMAD, Spec Kit, OpenSpec, Superpowers, Task Master — with
sources, star counts, and genuine credit where they lead:

[link: docs/COMPARISON.md]

Fairness is the point. So is the empty column.

**Tweet 8 (close + ask):**

Extracted from a harness that ran a real production project: 37+ merged PRs, 113+
confirmed review findings, one human at ~15 min/day.

MIT, zero runtime deps, npm: vteam-harness

⭐ https://github.com/connorpham/vteam-harness

RT appreciated — this category decides via comparison posts, and the verification
column is still empty.

---

**Follow-up cadence (owner):** weekly changelog threads ("vteam 0.x — what shipped,
what went red this week"), a bookmark-bait thread enumerating all 15 gates with
one-line failure modes, and reply-with-receipts in the standing "agent lied about
tests" complaint threads.
