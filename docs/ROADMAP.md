# vteam — Build roadmap

Extraction from the source harness (the first adopter's), phased so every phase leaves the repo in a
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

## Phase 4 — Providers ✅
Shipped: jira tracker provider (ADF flattening, v2-comments quirk, attach/link
with read-back, changelog judged_at, honest ping); figma design provider
(frames/match/node_link, learn_styles → design-language with file-version,
check_version); design interface with built-in `none`; the four
tracker-coupled gates — comment_check ([R1]..[R7]), stale_verdict_check
(pinned-COMMIT-first), schedule_check (plan.yaml contract), preflight
(provider pings, hooksPath check, declared-or-warned DB leg).
Deferred to Phase 6 dogfood: nextjs-prisma stack plugins (token_check,
ui-evidence, ui_fidelity) — ported against the real app they instrument.

### Original Phase 4 scope (for reference)
- Tracker interface + `jira` (port jira-api recipes, ADF flattening, v2-comments
  quirk, attach read-back) + `markdown` (offline backlog — enables zero-service
  demo + e2e)
- Design interface + `figma` (frames, styles → generated design-language +
  tolerance tables) + `none`
- `github`/`linear` tracker providers: v1.1

## Phase 5 — Installer CLI ✅
Shipped: `npx vteam init` (interactive or fully flag-driven with --yes; writes
config, .vteam runtime, docs skeletons never clobbering ledgers, rendered
doctrine, managed hooks + hooksPath, .gitignore evidence rules, CI workflow,
adapters), `vteam doctor` (python3 prerequisite check, config parse via the gates' own
parser, runtime + manifest integrity, hooksPath, model-routing staleness at
the configured path, all 17 selftests — python/shell/node, context libs
included — and provider preflight), `vteam update` (manifest-guarded: only
overwrites files whose hash matches what the framework last wrote; anything
user-edited is kept with the new version parked as *.new). Adapters: claude-code, cursor, windsurf, codex (+AGENTS.md
pointer), copilot (+instructions pointer) — non-Claude tools get the
no-subagent adapter note. E2E-proven in a fresh repo: init → commit → doctor
exit 0 with preflight GREEN. `doctor --migrate` ships with Phase 6.

### Original Phase 5 scope (for reference)
- `npx vteam init`: prompts (stack, tracker, tool(s), language, autonomy) →
  writes vteam.config.yaml, `.vteam/scripts/`, docs skeletons, hooks, CI snippet,
  tool adapters
- `vteam doctor`: preflight (port of preflight.sh, provider-aware, per-leg
  severity) + install-integrity check (hooksPath, gitignore shape, config drift)
- `vteam update`: re-render adapters/scripts from a newer package version
  without touching user ledgers
- Adapters: claude-code first; cursor, windsurf, codex, copilot as thin renderers

## Phase 6 — Prove it ✅ (except npm publish — owner-gated)
Shipped: the three nextjs-prisma stack plugins (token_check with its fixtures
self-check; ui-evidence + ui_fidelity on a pluggable auth strategy, no default
password shipped); `vteam doctor --migrate [--apply]` (legacy sentinel
rewriter — results, verdicts, decision statuses, manifest sentinels, [R1]..[R7]
markers, ISO dates incl. day ranges; prose untouched; dry-run default).
E2E: blank-repo init → doctor exit 0 (Phase 5).
Dogfood (source project, evaluation branch `chore/vteam-dogfood`): installed
with jira+figma+nextjs-prisma, migrated 18 real files (~139 rewrites), then —
against REAL artifacts — log_check green on the 41-row ledger, verbatim_gate
green on 503 coded rows / 10 shards, review_check green on a migrated dossier,
jira provider ping green on the live project, figma leg correctly reporting a
429 rate limit. DB leg red only because the worktree had no node_modules.
Remaining: a full /team session on the dogfood branch (separate session).
npm publish: DONE — first published as `vteam-harness@0.1.0` (npm blocked the
name `vteam` for similarity; the bin command stays `vteam`); `0.2.0` is the
Phase 7 hardening release.

### Original Phase 6 scope (for reference)
- E2E: `init` into a blank fixture repo (markdown tracker, generic profile) and
  run a scripted workday
- Dogfood: install vteam into the source project (`vteam doctor --migrate` rewrites old
  sentinels), run one real /team session, diff outcomes vs the legacy harness
- npm publish `vteam@0.1.0`

## Phase 7 — Hardening ✅ (framework audit round)
A 9-agent adversarial audit (4 dimensions + empirical install test) drove this
phase; every fix below closes a confirmed finding.
- init: validate EVERYTHING before the first write (invalid flags exit 1 with
  zero files); YAML-safe quoting with a parse-back round-trip proof; non-TTY
  without --yes fails fast; non-git dirs get one clean line; `.env` gitignored
  (tokens never commit); existing hook managers (husky/.git/hooks) detected and
  NEVER silently disabled — config records `git.hooks: external` instead
- update: the `.vteam/manifest.json` mechanism — "never touches your files" is
  now checkable, not a promise; refreshes the pre-push hook/CI/gitignore under
  the same rule; config re-read through the real parser (ctx.mjs), not regexes
- doctor: python3 prerequisite diagnosis, manifest verification leg, staleness
  at the configured paths.team, 17 selftests across python/bash/node
- gates: selftests added to gate.py (driver), stale_verdict_check,
  docs_shrink_check, tracker lib, ctx.sh, ctx.mjs — every checking gate now
  carries mutation proof; evd_check regex-escapes filesystem names
- security: pre-push secret scan FAILS CLOSED (no base → scan the full outgoing
  content); ticket keys validated before any path/URL is built (traversal dead);
  jira provider requires https, refuses redirects (Basic auth never re-sent),
  URL-quotes path parts; preflight parses .env as inert text and redacts
  credentials from printed remote URLs; gates.yaml documented as a trust boundary
- config knobs wired: git.branch_pattern (pre-push fence), models.routing +
  paths.team (model_route/perf_report/doctor), stack.package_manager +
  project.key ({vars} in gates.yaml), review.reviewers + team.size (rendered
  into dev/team workflows); specs.sources explicit, self-comparison rejected
- proof: tests/e2e.mjs (fresh repo → init → doctor GREEN, manifest-guarded
  update, clean failures, pre-push fence + secret scan go red for real) wired
  as `npm test` + GitHub Actions CI
- locales: first-adopter domain vocabulary removed from core defaults (design
  boundary: zero project specifics); en/vi key parity

## Phase 8 — Proof-of-done campaign ✅ (build + content; posting is owner-gated)
Positioning shipped: "Proof-of-done for AI agents" — the wedge is the one axis no
competitor occupies (verified against live GitHub/npm/PyPI data, 2026-08-18).
- `vteam audit` (src/cli/audit.mjs): top-of-funnel 0-100 accountability grader —
  six dimensions (gates/hooks/evidence/review-trail/verdicts/self-proof), works on
  any repo with no install, never writes, `--json`, bounded scan, `--selftest`
  with a true mutation proof (deleting the high fixture's manifest drops 100→92);
  wired into bin/vteam.mjs as the first usage line. `doctor --json` added.
- GitHub Issues tracker provider (providers/tracker/github.py): full Tracker
  interface over stdlib urllib — PROJ-123 ⇄ issue #123, labels carry the status
  machine, read-back on every write, honest attach (evidence dir is the record),
  redirect-refusing token hygiene, `--selftest` against an in-memory GitHub, zero
  network. init offers `--tracker github`.
- Zero-gatekeeper install: Claude Code plugin marketplace at the repo root
  (`/plugin marketplace add connorpham/vteam-harness` → `/plugin install
  vteam@vteam-harness` → `/vteam:setup`), validated with `claude plugin validate`;
  SessionStart doctrine re-injection hook template (≤15 lines, survives /clear and
  compaction) installed per-repo by init — deliberately NOT a plugin-level hook.
- Content layer: README repositioned (category line, 60-second start, "Who
  verifies the work?"); docs/COMPARISON.md — the canonical who-verifies-the-work
  comparison (BMAD #2003/#1332, Spec Kit #1784, Task Master's self-report loop,
  Agent OS v3 retreat, Ruflo's supply-chain-only verify — all sourced, all
  star-counts dated, vteam's own limits included); core/doctrine/red-flags.md
  ("the 12 excuses", each mapped to the gate that catches it; referenced from the
  dev and qa workflows); npm keywords extended (proof-of-done, quality-gates,
  ai-accountability, code-review, spec-driven-development, github, jira).
- Owner-gated (drafts ready in docs/launch/): awesome-claude-code submission
  (eligibility: 14 days of history or 100 stars), clau.de plugin-directory
  submission, HN first-person essay (outline from provenance incidents), r/ClaudeAI
  evidence post (screenshots to capture), X launch thread (GIF to record), npm
  publish of the release carrying all of the above.

## Non-goals for v1
- Multi-human teams beyond best-effort `team.size > 1` (DESIGN §7)
- Mobile/desktop evidence capture (web via Playwright only; interface left open)
- Tracker write-back beyond jira/markdown
