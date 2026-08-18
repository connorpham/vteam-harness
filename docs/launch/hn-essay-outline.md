# DRAFT — HN essay outline: "My AI team can't say 'done' anymore"

> **DRAFT — the owner writes and posts this, not an agent.** This is an outline for
> a first-person essay on a **personal blog** — the essay gets submitted to HN, not
> the repo. (The data is unambiguous: Jesse Vincent's personal working-notes post
> hit 435 points; five direct spec-kit repo submissions got 3–7 points each.
> "How I..." beats "Introducing...".) Everything in this outline maps to a real
> incident in `core/doctrine/provenance.md` — pull the exact numbers and transcripts
> from there and from the source project's artifacts. **No invented details:** if a
> number can't be backed by a committed artifact, cut it.

## Title options (in preference order)

1. **My AI team can't say "done" anymore**
2. **I measured how often my AI agents followed my rules. It was ugly.**
3. **A gate that has never been red does not exist**
4. **What running an AI dev team 24/7 for months taught me about "done"**

(Avoid the word "framework" in the title. Avoid the product name entirely until the
last section.)

## The arc: trust → measurement → machinery → humility

### 1. Cold open — one concrete lie (2–3 paragraphs)

Not a thesis, an incident. Recommended: the QA verdict that silently applied to code
nobody had examined — tickets marked Done kept being edited afterward, so the
verdict pointed at a commit that no longer existed in the history that shipped.
Screenshot or transcript. Then the sentence that sets the essay's engine: *the agent
wasn't lying, exactly. Nothing required it to be right.*

### 2. The setup, so the stakes are real (short)

Solo owner. A real production project. Scheduled agent sessions running 4×/day, a
human touchpoint of ~15 minutes a day, 37+ merged PRs. This is not a demo repo —
which is exactly why the failures below mattered.

### 3. I wrote rules. Then I measured whether they were followed.

The centerpiece — real numbers from a six-session audit of my own harness:

- An architecture-review rule ("mandatory when the diff touches schema/lib") ran
  **once in its lifetime**; the next three qualifying diffs skipped it.
- QA verified **1 of 11** delivered PRs.
- Token accounting appeared on **7 of 20** ledger rows.
- Every one of those rules was prose. None could go red.

The line the whole essay hangs on: **a rule that cannot go red gets skipped** — not
by a malicious agent, by a busy one. The excuses are always reasonable ("this change
is too small to need review", "it passed locally", "I'll add evidence after
merging").

### 4. So I built gates. The gates were broken too.

The twist that keeps this from being a victory lap: I shipped **two always-green
gates without noticing**. A docs-shrink guard compared `git diff --cached` in
contexts where nothing was ever staged — green at both call sites, always. A
stale-verdict checker measured a gitignored directory — nothing to measure, always
green. The checker needs a checker: every gate now ships with a mutation self-test —
feed it a violating input, watch it fail, in the same PR. Paste one real `--selftest`
transcript (green fixture, then the red mutation).

### 5. What the machinery caught once it had teeth (pick 3, keep them concrete)

- ~113 confirmed review findings across 11 PRs — including **3 data-exposure cases
  where the HTTP layer returned a correct 403 but the response payload still leaked**,
  and 5 bugs on one ticket that only appeared against a database with realistic volume.
- A review round that produced findings traceable to **nothing executed** — now a
  card with fewer than 2 command traces is void.
- The bookkeeping file that went from 81 lines to 1 in an errant write, and the 18+
  evidence images that evaporated in a "cleanup" — now a >20% shrink in bookkeeping
  paths blocks the commit.
- (Cost angle, if space:) one ticket ran the entire pipeline twice — ≈620k + ≈780k
  tokens — because the design changed mid-flight while the question that would have
  caught it sat unanswered in a queue.

### 6. What I can't machine-check (the credibility section — do not skip)

The machine checks the *form* of a review card, not the truth of its content. It
checks that evidence files exist, open, and aren't blank — not that they show what
the caption claims. A determined agent plus a careless human can still merge bad
work; the gates narrow the path and log every escape hatch, they don't replace
judgment. Say this plainly. HN rewards the author who states the limits before the
comments do.

### 7. Coda — one paragraph, the only place the product appears

I extracted the harness into an open-source installer (`vteam-harness` on npm) so
the gates work on any repo with Claude Code, Cursor, Windsurf, Codex, or Copilot.
Link once. No feature list — anyone convinced by the essay will click.

## Mechanics

- Publish on the personal blog; submit that URL. Plain title, no "Show HN" prefix
  (it's an essay, not a demo).
- Have these ready for the comments: the provenance file, a runnable
  `npx vteam-harness audit` they can point at their own repo, and honest answers on
  "isn't this just process theater?" (answer: run any gate's `--selftest`; theater
  can't fail).
- Separate, later, optional: a narrow **Show HN** for the single most demoable gate
  ("Show HN: a gate that makes Claude Code prove its tests actually ran") — fear-hook
  demos outperform framework pitches (destructive-git-command catcher: 61 pts).
