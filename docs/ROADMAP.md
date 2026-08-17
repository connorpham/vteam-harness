# vteam — Build roadmap

Extraction from the Shop Xoài harness, phased so every phase leaves the repo in a
usable state. Source of truth for scope: [DESIGN.md](DESIGN.md).

## Phase 0 — Foundation ✅ (this commit)
- Repo scaffold, README, DESIGN, ROADMAP
- `vteam.config.yaml` schema + canonical example
- `core/scripts/lib/` context modules (ctx.py / ctx.mjs / ctx.sh): repo-root
  resolution, config + env loading — the one place gates read state from

## Phase 1 — Core doctrine (EN)
- Translate + genericize `docs/team/` → `core/doctrine/`:
  ops (runbook, supersession law, house-of-record table, cadence), raci,
  review-standard, roles/{pm,ba,sa,dev,qa,design,devops}
- `provenance.md`: anonymized incident log carrying the "why" of each rule
- `model-routing` → data file + doctrine stub with staleness warning

## Phase 2 — Workflows (EN, tool-neutral)
- `core/workflows/`: team, pm, ba, dev, qa, verify, guidelines
- Strip dates-as-law → `project.adopted` anchors; strip project anecdotes →
  provenance; replace literals with `{config}` template vars
- Frontmatter schema for the adapter contract (DESIGN §8)

## Phase 3 — Gates ✅ (core set)
Shipped: ctx/vocab/tracker lib (markdown provider built in), log_check,
verbatim_gate, review_check, evd_check, evd_ui_check, dor_check, annotate,
docs_shrink_check, gate.py driver + gate.sh, 4 profile manifests, pre-push
template, locales en/vi. All checking gates carry `--selftest` mutation proof.
Deferred to Phase 4 (tracker/design-coupled): schedule_check, stale_verdict_check,
comment_check, preflight; and the nextjs-prisma stack plugins (token_check,
ui-evidence, ui_fidelity).

### Original Phase 3 scope (for reference)
- Port scripts to `core/scripts/` on top of ctx lib; neutral sentinels
  (DESIGN §4) + `locales/{en,vi}.yml`
- Every gate keeps/gains `--selftest` (mutation self-test is a ship requirement:
  a gate that has never been red does not exist)
- `profiles/`: gates.yaml manifests — nextjs-prisma (full port of gate.sh),
  node, python, generic (each step present or loudly skipped)
- Pre-push hook template + CI snippet generator

## Phase 4 — Providers
- Tracker interface + `jira` (port jira-api recipes, ADF flattening, v2-comments
  quirk, attach read-back) + `markdown` (offline backlog — enables zero-service
  demo + e2e)
- Design interface + `figma` (frames, styles → generated design-language +
  tolerance tables) + `none`
- `github`/`linear` tracker providers: v1.1

## Phase 5 — Installer CLI
- `npx vteam init`: prompts (stack, tracker, tool(s), language, autonomy) →
  writes vteam.config.yaml, `.vteam/scripts/`, docs skeletons, hooks, CI snippet,
  tool adapters
- `vteam doctor`: preflight (port of preflight.sh, provider-aware, per-leg
  severity) + install-integrity check (hooksPath, gitignore shape, config drift)
- `vteam update`: re-render adapters/scripts from a newer package version
  without touching user ledgers
- Adapters: claude-code first; cursor, windsurf, codex, copilot as thin renderers

## Phase 6 — Prove it
- E2E: `init` into a blank fixture repo (markdown tracker, generic profile) and
  run a scripted workday
- Dogfood: install vteam into shop_xoai (`vteam doctor --migrate` rewrites old
  sentinels), run one real /team session, diff outcomes vs the legacy harness
- npm publish `vteam@0.1.0`

## Non-goals for v1
- Multi-human teams beyond best-effort `team.size > 1` (DESIGN §7)
- Mobile/desktop evidence capture (web via Playwright only; interface left open)
- Tracker write-back beyond jira/markdown
