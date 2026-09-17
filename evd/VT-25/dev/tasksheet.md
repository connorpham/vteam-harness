# Tasksheet — VT-25 (the five untested tools)

CODE-SCOPE: core/scripts/ profiles/nextjs-prisma/scripts/ tools/prepublish-check.mjs tests/ README.md CHANGELOG.md docs/backlog/ evd/VT-25/ docs/pm/

(Scope widened from `core/scripts/orca_team.sh` to `core/scripts/` on 2026-09-17: wiring the
stale-verdict step into the testbed's gate exposed that `stale_verdict_check.py` reads a
ticket closed by decision — graph_check's `closed-by:` — as UNVERIFIABLE. Fixed here, deliberately.)


## Plan
1. `orca_team.sh --selftest` — fake `orca` on PATH (reachable / unreachable / run-create), HOME in a temp dir for `trust`
2. `auth.mjs` — export stays; `--selftest` drives `signIn` with a fake Playwright context (csrf → callback → session), `loadAuth` with `EVD_AUTH_MODULE`
3. `ui_fidelity.mjs` — pure logic (`normColor`, `compare`, `INTENT_OK`, `toKebab`, the verdict rule) lifted into exported functions; playwright imported lazily inside `main()`; `--selftest` runs without a browser
4. `ui-evidence.mjs` — same shape: arg parsing, headed policy, shots.json validation exported; `--selftest`
5. `prepublish-check.mjs` — `check({root, run})` with an injectable runner; `--selftest` on a fixture repo with a stubbed npm proves all five refusals + the clean path
6. tests/e2e.mjs: one section invoking the five; README counts; CHANGELOG under 0.19.0

## Rule
Behaviour of every tool is unchanged — only structure moves so a test can reach it. Each selftest carries at least one forced red.
