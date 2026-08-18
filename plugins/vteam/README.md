# vteam — Claude Code plugin

Bootstrap for [vteam-harness](https://github.com/connorpham/vteam-harness):
proof-of-done for AI agents. The plugin is deliberately small — it carries one
skill and no hooks, because the real install is the npm package, not the plugin.

## Install

```
/plugin marketplace add connorpham/vteam-harness
/plugin install vteam@vteam-harness
```

## Use

```
/vteam:setup
```

Explains proof-of-done in 5 lines, grades the repo (`npx vteam-harness audit`),
installs the harness (`npx vteam-harness init`), and verifies it
(`npx vteam-harness doctor` — every gate's `--selftest` must pass).

## What this plugin does NOT do

- It does not duplicate the installer: gates, workflows, doctrine, and the
  per-repo SessionStart hook are all written by `npx vteam-harness init`.
- It ships no plugin-level hooks on purpose: a plugin hook would fire in every
  repo you open; vteam's SessionStart doctrine re-injection belongs only to
  repos that installed vteam, so `init` wires it into that repo's
  `.claude/settings.json` instead.
