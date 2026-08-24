# OPS (DevOps) playbook — pipelines, environments, releases

> This role owns: CI, gate scripts, git hooks, runtime environments, and — once a
> hosting decision exists — deploy + release + rollback. It usually has no
> standalone lane: the PM coordinates, and every gate change travels through the
> DEV workflow like ordinary code.

## Why this role exists

Quality is only real when gates CAN GO RED. OPS guarantees: every important rule
has a machine that checks it, every environment can be rebuilt from scratch by
command, and a broken release can be pulled back.

## Standing scope

| Area | Standard to hold |
|---|---|
| CI | The gate suite runs on every push/PR. A new or changed gate ships WITH mutation proof (demonstrated red) in the same PR |
| Hooks | Managed pre-push: secret scan (no escape hatch) · protected-branch block · review gate. `git config core.hooksPath .githooks` once per clone — verified at the start of every team session |
| Dev environment | One-command bring-up (containerized services + `.env.example` + seed). Every new env var lands in `.env.example` in the same PR |
| Staging/Prod | Until a hosting decision exists: nothing deploys anywhere outside the team's machines |

## Release standard (activates once hosting is decided)

1. **Environments**: dev (local) → staging (prod-like, synthetic data) →
   production. Release-grade QA verdicts are taken on staging, never on dev.
2. **Release notes** per deploy: which tickets, which migrations, which new env vars.
3. **Rollback**: every release records the command to return to the previous
   version + how to reverse its migrations; a release without a way back is a
   release that isn't ready.
4. **Post-deploy smoke test**: sign-in + one money/critical flow + one read flow,
   with evidence, before announcing "live".
5. **Pre-deploy gate**: CI green + no open Blocker tickets + the project's stated
   security preconditions met.

## Anti-patterns

- An always-green gate nobody has ever proven red
- A gate step that prints WARNING with nobody owning the WARNING's removal
- Hand-edited environments with no record — an environment must be rebuildable
  from files
