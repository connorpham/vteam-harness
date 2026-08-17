# vteam

**One command puts a whole virtual AI team to work on your repo.**

vteam is an agent-agnostic orchestration framework — in the family of BMAD Method,
SpecKit, OpenSpec and Superpowers — extracted from a production harness that ran a
real project autonomously (37+ PRs, 113+ confirmed review findings, 24/7 scheduled
sessions). It installs a virtual team (PM · BA · SA · DEV · QA) into any repository,
for any AI coding tool.

```bash
npx vteam init
```

The installer asks a few questions (stack, issue tracker, language, autonomy level)
and generates:

- **Workflows** for your tool — Claude Code skills, Cursor rules, Windsurf workflows,
  Codex AGENTS.md sections, Copilot instructions — all rendered from one core.
- **Machine gates** — scripts that can actually go red: definition-of-ready checks,
  evidence validation, review-card enforcement, ledger schema checks, verdict
  staleness detection. Every gate ships with a mutation self-test.
- **The paper trail** — decision queue, dispatch ledger, session minutes, acceptance
  dossier, knowledge base with graduation rules.
- **Doctrine** — reviewer standard, RACI, role playbooks, model routing, operating
  cadence — each rule living in exactly one file.

## Why another framework?

Most spec-driven frameworks tell the agent *what to build*. vteam's core insight is
about *how a team of agents stays honest*:

1. **A gate that has never been red does not exist.** Every new gate must prove it
   can fail before it ships.
2. **Evidence that only exists in the session isn't evidence.** Everything durable
   goes to a committed file or the tracker, and every outward write is re-read back.
3. **Autonomy is a ladder, not a switch.** Quality gates never relax; only
   wait-for-human gates flip — with a documented, reversible, labelled trail and a
   hard exemption list (real money, legal, credentials, data deletion).
4. **One rule, one home.** Changing a rule means deleting the old sentence in the
   same commit. Everything else is a pointer.
5. **Agents don't chat.** One brief → one card. Briefs are paths + scope, never
   pasted content. Exactly one rebuttal round, paid for with evidence.

## Status

Early extraction. See [docs/DESIGN.md](docs/DESIGN.md) for architecture and
[docs/ROADMAP.md](docs/ROADMAP.md) for the build plan.

## Layout

```
core/        tool-agnostic framework source (doctrine, workflows, gates, templates)
adapters/    per-tool renderers (claude-code, cursor, windsurf, codex, copilot)
profiles/    stack profiles for the verification gate (nextjs-prisma, node, python, generic)
providers/   tracker + design-source adapters (jira, github, linear, markdown / figma, none)
bin/, src/   the npx installer CLI
```

## License

MIT
