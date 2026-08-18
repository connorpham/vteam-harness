---
description: Bootstrap the vteam proof-of-done harness in the current repo — grade it first (npx vteam-harness audit), install (npx vteam-harness init), verify (npx vteam-harness doctor). Use when the user asks to set up vteam, add proof-of-done gates, or install the virtual AI team.
---

# vteam setup — proof-of-done for AI agents

First explain, in substance, these 5 lines and nothing grander:

1. Agents say "done"; vteam makes them prove it — machine gates that actually go red.
2. Every checking gate ships a `--selftest` mutation proof (green fixture + red mutations): the gate itself is tested, not trusted.
3. Evidence is pinned to commits — claims carry command + real output written to files, not chat scrollback.
4. `.vteam/manifest.json` guards updates (user edits are never silently clobbered) and the secret scan fails closed.
5. The same gates drive Claude Code, Cursor, Windsurf, Codex, and Copilot — one team, any agent tool.

Then run the funnel in order. Show the user each command's REAL output; never claim a step succeeded without it.

## 1. Grade the repo first

```
npx vteam-harness audit
```

Scores the repo 0-100 on proof-of-done before changing anything, so the user sees the gap the install closes. If the installed vteam-harness predates the audit command (the CLI prints usage without `audit`), say exactly that and continue with step 2 — do not fake a score.

## 2. Install

```
npx vteam-harness init
```

Interactive; `--yes` accepts defaults, and flags like `--key PROJ --profile node --tools claude-code` skip prompts. Ask before running it: it writes `vteam.config.yaml`, `.vteam/` (gates + manifest), `.claude/` (skills + SessionStart hook), `.githooks/pre-push`, CI workflow, and docs skeletons. It refuses to run twice — an existing install updates with `npx vteam-harness update`.

## 3. Verify — nothing is trusted untested

```
npx vteam-harness doctor
```

Preflight + install integrity against the manifest + every installed gate's `--selftest`. Green doctor is the definition of installed; anything red gets reported to the user verbatim, not smoothed over.

When doctor is green, tell the user to start a workday with `/team`.
