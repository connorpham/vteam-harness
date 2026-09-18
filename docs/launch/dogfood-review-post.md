# DRAFT — "I ran my AI-agent framework on itself. It found 13 defects in its own gates."

> **DRAFT — the owner posts this, not an agent.** First-person, personal blog or
> dev.to, then submitted to HN / r/ClaudeAI. Every number below is backed by a committed
> artifact in this repo (`evd/VT-24/dev/`, `evd/VT-25/dev/`, PR #72, PR #73); the
> `[SCREENSHOT]` marks want a real capture. Nothing here may be rounded up.

## The one-line version

vteam's whole pitch is *a gate that has never been red does not exist*. On 2026-09-17 I
read every one of its 64 files — 18,602 lines — and found **three gates the workflows
named that no profile ever ran**. The framework had been shipping prose where it promised
machinery, and its own gates could not see it.

## What the read found (all 13, no cherry-picking)

| # | Defect | How it hid |
|---|---|---|
| 1 | `preflight.sh` probed the gate driver with `gate.py --help` — and the driver read every argument as a *tail name*, so the probe **ran the entire gate** (lint, tsc, build, tests) silently at the start of every dev/PM/BA session | Output was discarded (`>/dev/null`) |
| 2 | `stale_verdict_check` — "a verdict expires when the code moves", the feature the README leads with — was cited by five workflows and wired into **zero** of the six gate manifests | The workflow prose said "run it"; nothing checked that a manifest did |
| 3 | Switch your tracker from markdown to GitHub after install → `update` never installed the provider, `init` refused because the config existed. A dead end with no error naming it | Both halves were individually correct |
| 4 | Two of five adapters emitted **invalid YAML** frontmatter (a description containing `kernel: Why, …`) | Nobody ran those two tools |
| 5 | Packaged agents and the session hook were written *outside* the manifest guard — a consumer never received an upstream change and was told "kept YOURS" about a file it never touched | The message sounded like a feature |
| 6 | `update` never removed files the package stopped shipping; a retired gate lingered forever and dropped out of the manifest, where `doctor` could not see it. **This repo's own gate manifest mirror was six weeks behind its source**, and a stray `.new` had been committed | The framework's own copy of itself drifted |
| 7 | Profile detection keyed on `prisma/` alone — an Express + Prisma repo got the Next.js profile and reddened on `next typegen` | Worked on every repo I had |
| 8–13 | a `--root` flag that crashed on any directory; two config parsers that disagreed on `[a,,b]` and both silently dropped keys after an indented first line; `--attach` erasing every section after its own; a deadline reader that took the *first* date in a row (the day the question was asked); `evd/` hardcoded in three checkers; dead code | Edge cases nobody had typed |

## What I did about it, and what that cost

Every fix carries a test that was **red before** the fix, and a mutation probe that reds
again when the fix is reverted — 13 of 13 ([`mutations.md`](../../evd/VT-24/dev/mutations.md)).
The first attempt at four of those probes proved nothing: reverting a whole file reverted
the new test with it, and the suite read green. That is recorded too, because a test that
does not bite is the exact failure mode the framework exists to catch.

Then the five tools that had **no test of any kind** got one each (VT-25) — offline, with a
fake `orca`, a fake Playwright context, a stubbed npm. Their first CI run was **red on
Linux**: my review card had claimed `stat -f` falls back to `stat -c`; on GNU, `stat -f`
means *file-system* status and succeeds with the wrong output. A reviewer statement about
a platform the reviewer did not run on is testimony. CI was the reviewer.

And wiring the stale-verdict gate into a real consumer repo turned it **red within the
hour** — on a won't-fix ticket closed by a decision, not a QA verdict. The checker predated
that concept. Fixed, with the green/red pair in its selftest.

`npm test`: 172 → 199 checks. Doctor: 33 → 34 selftests.

## What this says about the category

Most AI-agent frameworks are markdown. They cannot have this bug, because they have no
gates to leave unwired — and they cannot catch the agent that says "done" either. The
day I found three unwired gates is also the day the same machinery caught a real closure
defect in a second repo. Both are the same fact: **enforcement you can test is
enforcement you can be wrong about, and find out.**

`[SCREENSHOT: the mutation ledger — 13 probes, 13 RED]`
`[SCREENSHOT: the pre-push fence refusing a push without a review dossier]`

Repo: github.com/connorpham/vteam-harness · the review: `evd/VT-24/dev/proof.md` ·
try it without installing: `npx vteam-harness audit`.
