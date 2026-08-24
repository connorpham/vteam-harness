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

## Phase 9 — Per-project customization ✅ (first-adopter feedback round)
A real adopter audited vteam against four mature repos and rejected it on FIT,
not value — every objection was a wrong assumption baked into install time.
This phase answers the ones that are configuration, and records the ones that
are not (below).
- `git.merge_strategy` (merge|squash|rebase) + dual verdict anchors: `COMMIT:`
  for the code, `VERIFIED-AT:` for the clock. Adversarial review found the
  structural bug this closes — on squash/rebase repos the pinned branch sha is
  discarded at merge, and `stale_verdict_check` warn-and-continued, making the
  framework's marquee gate a PERMANENTLY GREEN no-op on the most common merge
  strategy in the industry. An unanchorable verdict is now RED with
  instructions; "cannot verify" and "verified clean" are different verdicts.
- `autonomy.self_merge`: per-project off switch for agent-merged PRs (honored
  at `level: full` only), rendered into the team workflow and the ops table.
- `/docs` — the read-then-ask documentation bootstrapper for
  mature-but-undocumented repos: reads the codebase first (inferences marked
  `⚠ UNVERIFIED`), interviews the owner in ONE batched question table, writes
  spec shards split `DRAFT-FROM-CODE` vs `OWNER-CONFIRMED` plus decision/KB/
  known-issues seeds, and PROPOSES a config patch it never applies. Kills the
  "vteam requires pre-existing documentation" objection: it creates the oracle.
- `docs.task_context` (`always:` + `by_label:`): per-ticket background reading
  for /dev T1; a mapped-but-missing file is reported loudly, never guessed.
- `vteam board`: read-only local dashboard over the proof trail (ticket columns,
  ledger badges + token accounting, evidence verdicts, decision queue).
  Read-only by CONSTRUCTION — loopback bind only, exactly `GET /` and
  `GET /api/state`, 405 on any write, 404 on everything else, no static
  serving: a board that could transition a ticket would be a second write path
  around the gates. Own `--selftest` with 14 red mutations.
- E2E 73 → 82 checks.

## Phase 10 — Compatibility as machinery (NEXT, not yet done)
The honest finding behind Phase 9: **vteam has never been run against a repo
that isn't its own or its first adopter's.** The e2e suite builds synthetic
repos using vteam's own defaults — it proves vteam agrees with itself, not that
it fits the world, while the README says "any repo". Known open items, by damage:
- `init` must DETECT then PROPOSE (dry-run by default on a repo with history):
  print the config it inferred, the collisions it found, and the file list it
  would write — approval before the first byte.
- BUG: `.claude/skills/<name>/SKILL.md` is force-written; a repo-level skill of
  the same name is silently overwritten (reproduced 2026-08-18). Same
  writeIfAbsent + `*.new` + loud rule the doctrine files already follow.
- `--gates-only` install mode: the back half without the team doctrine, for
  repos that already have their own role agents.
- A compatibility fixture matrix: gitflow+squash+GitLab+Python, trunk-based,
  monorepo, husky-managed hooks, existing `.claude/agents`, no tests, `develop`
  default branch — each asserting either "works" or "refuses clearly". Silence
  or false green is a failure.
- Undeclared prerequisites: README documents none, while 13 gates need python3,
  4 need bash, and 3 need Pillow (non-stdlib). A JS/TS team on Windows without
  WSL cannot run this today.
- No `vteam uninstall` — ~30 files, a rewritten core.hooksPath, appended
  .gitignore and a merged settings.json, with no way back. People do not try
  what they cannot undo.
- `team.size` claims (DESIGN §7) have zero consumers in machinery — multi-human
  support is documentation, not mechanism. Either implement or say so plainly.
- Providers: GitLab CI profile, Trello tracker; committed-evidence is legally
  impossible for regulated data (PII in git forever) and needs a documented
  answer, not a config flag.

## Phase 11 — One rule, one home ✅ (consistency round)
A 3-agent adversarial review asked "does the code conflict with itself?" and
found 10 HIGH answers. This phase closes them:
- ONE config dialect: ctx.py learned flow mappings (bracket-aware), ctx.mjs
  stopped splitting on bare commas, both reject tab indentation with the same
  loud message, ctx.sh refuses flow shapes instead of misreading them, and
  migrate.mjs lost its private regex parser. `tests/conformance.mjs` (15
  fixtures, incl. the README's own config verbatim) now runs in `npm test` —
  the permanent fence against parser drift.
- ONE ledger grammar: `lib/ledger.py` is the home; log_check, perf_report and
  the board all read it (the 6 rows the review caught them disagreeing on are
  now selftest fixtures).
- H1 (main was RED): init no longer invents code_paths — undetectable → `[]`
  + loud warning; doctor warns on empty but reds on configured-lies; the
  pre-push fence FAILS CLOSED on empty. E2E 82 → 95 checks.
- Scalar config values normalize everywhere a list is expected (a scalar
  `done_statuses` used to make stale_verdict silently green).
- review_check reads `review.reviewers` (R1..RN, +1 high-stakes) — the knob is
  machine-enforced now, not decorative. evd_check enforces BOTH verdict
  anchors (COMMIT + VERIFIED-AT).
- Legacy honesty: gates.yaml steps support `requires_cmd` probes; the node
  profiles skip the unit step LOUDLY when no real test script exists, an
  `echo`-shaped test script trips a tripwire, and a run where no suite executed
  prints GREEN (WEAK) naming what did not run.
- doctor discovers selftests dynamically (19 today) — the root cause of the
  drifting "17 vs 18" counts is gone. Counts in earlier phase records are
  point-in-time history, left as written.

## Phase 12 — Team accountability ✅ (the two-humans round)
`team.size` gains its machinery: ledger row v2 (`| Date | Lane | Actor | Item
| Result | Link |`, one home in lib/ledger.py incl. `resolve_actor` — VTEAM_ACTOR
env else `git config user.name`), log_check reds unattributed ledgers at
size > 1, `doctor --migrate` upgrades legacy ledgers (`—` rows), perf_report
adds the per-person table + per-human routing 🚩, the board rolls up by actor,
and init writes a union-merge gitattribute so two appenders never conflict.
Honesty note ships inside the report: artifacts/tokens/routing per person,
never chat. Still prose: WIP=size, claim TTL, self-merge review at >1.
E2E 95 → 104 checks.

## Phase 13 — Scale round ✅ (hours, 24/7, cross-model review, code map, shared-file merges)
Five owner asks, each shipped with its proof:
- `team.hours_per_day: 8` — plan costs accept `12h` alongside `1.5d`;
  schedule_check normalizes onto one person-day scale (selftest: rescale at
  4h/day, unknown unit red).
- 24/7 on a subscription: `ops-247.md` — shifts-not-a-daemon, per-OS recipes
  (launchd+caffeinate / systemd timer+inhibit / cron+lock), what never relaxes
  at 03:00, and the honest limit: unattended continuity, not unlimited
  throughput. Every recipe linted (plutil / bash -n / systemd by hand).
- Cross-model review: `review.external.<id>` + `external_review.mjs` — the
  brief goes to the external CLI on stdin, the returned card is validated
  against review_check's own bar BEFORE it is written (12 red mutations in the
  selftest); an invalid card is never written, so the fence stays shut.
- Code map (CPG-lite): `code_map.py build/query` — stdlib symbol+import index,
  paths-only answers capped and loud on truncation; /dev T1 and /docs D0 read
  the map's answer instead of the tree. Named honestly: lexical, not Joern.
- Union-merge extended to every append-only shared file (ledger, hatch-log,
  knowledge-base, known-issues; decisions.md deliberately excluded — its
  in-place status edits deserve real conflicts). Proven in e2e: two branches
  append the same KB file, merge lands clean with both lines.
E2E 108 checks; doctor discovers 21 selftests.

## Phase 14 — The graph round ✅ (MAST closure)
Sources: MAST (arXiv 2503.13657, NeurIPS 2025 — the 14-mode failure taxonomy),
Anthropic's "Building Effective Agents" (complexity only when it pays). Ten of
the 14 MAST modes already had a vteam gate; this round closes the four that
need graph structure, and makes the implicit graph visible:
- `vteam graph` (mirror, always exit 0): READY/BLOCKED tables computed from
  backlog + plan + ledger + evidence; findings = dangling edges, dependency
  cycles (SCC-based, budgeted), Done-without-verdict. --json byte-stable
  pinned to the commit; --dot for Graphviz. blocked_by parsing lives in ONE
  home (board.parseTicket, mirroring tracker.py).
- `graph_check.py` (gate, exit 1): dangling/cycle edges; done ⇒ PASS verdict
  in the H1 (MAST 1.2 — closure outside RACI rights); byte-identical repeated
  dispatch (MAST 1.3); `team.loop_budget_per_day` exceeded (MAST 1.5 —
  termination as a NUMBER in config, machine-consumed from birth); commits
  outside the tasksheet's declared `CODE-SCOPE:` (MAST 2.3 — self-expansion;
  undeclared scope = loud note, never silent). Remote trackers: edge/closure
  checks skip LOUDLY, ledger checks still run.
- Mirror and gate are fenced together: graph.mjs's selftest runs graph_check
  against its own fixture and asserts finding-for-finding agreement.
- Deliberately NOT built (Anthropic's rule — no complexity without proof):
  routing engines, parallel fan-out, plan.yaml `dependencies` (next: Phase 15
  candidate), LangGraph-style orchestration.
E2E 109 → 119; doctor discovers 22 selftests.

## Phase 15 — QA as a person, not a route ✅ (evidence review round)
Five questions from the owner ("is the region boxed? could a stranger
understand it? are the steps to reach the TC complete? is the thinking
readable? does QA think like a real user?") found three real holes, all now
machine-closed:
- `*_boxed.png` was required only on FAIL/NEW-BUG, so a PASS could ship an
  unannotated full-page screenshot and stay green. Now required on EVERY
  executed UI TC — and `annotate.py box --label` is mandatory: a red rectangle
  with no caption explains nothing to the stranger the evidence is for.
- Nothing described HOW the tester reached the screen, so "exact URL" quietly
  legitimised deep-linking. Every executed UI TC now carries a gate-checked
  journey — `AS:` (account+role), `PRECONDITION:`, `ENTRY:`, `AFTER:`, `BACK:` —
  and an `ENTRY:` that is only a URL is REFUSED: typing an address proves the
  address, not the product (a missing menu item, a wrong permission and an
  unreachable row all hide behind a deep link). A URL kept beside the click path
  is welcome as a second check.
- `AFTER:` and `BACK:` did not exist as concepts. They do now, and they name the
  four moves a real person makes that a script skips: look for the confirmation,
  glance at the list behind, refresh (a save that dies on reload is not a save),
  press Back and Cancel and expect the right state.
- The thinking, not just the form: `roles/qa.md` opens with "You are a person,
  not a route"; qa.md's V2 designs the journey and V4 walks it from ENTRY; step
  screenshots are named for what they show.
evd_check selftest grows the journey battery: full walk green, each of the five
fields demanded by name, 3 URL-only ENTRYs red, click-path+URL green,
unannotated PASS red.

## Phase 16 — Durable execution as a READER ✅ (`vteam resume`)

The 2026 graph-standard audit scored vteam weakest on durable execution
(checkpoint/resume, the LangGraph 1.0 headline). The first attempt stored a
`.checkpoint` file per ticket — and was reworked before release, because it
violated the framework's own oldest law (`ops.md` §1 / `ops-247.md` §1: all
state is external and single-owner; a stored checkpoint is a second source of
truth nothing keeps honest — it can say "review done" while `dev/review.md`
does not exist, and its lane list `plan/docs/dor/...` wasn't even the system's
real vocabulary).

What shipped instead: `npx vteam-harness resume <KEY>` — a pure reader, like
`graph`. It derives the furthest PROVEN stage from artifacts that already have
one owner each — the claim comment (+2h TTL), `feat|fix/<KEY>-*` branches,
`evd/<KEY>/dev/tasksheet.md` (T1), `dev/review.md` (T4b), `REPORT.md` H1
verdict (same word-boundary law as evd_check), and the ledger rows — then
prints the one next dispatch (resume /dev · hand to /qa · orphaned → recovery
lane · STOP, someone holds it). Wired into pm.md P0.1c and dev.md T0.4;
doctrine sentences in ops.md §1 / ops-247.md §1 amended per the supersession
law rather than left contradictory. Selftest proves all 9 derivation rungs and
the precedence order; e2e section 19 walks the ladder on a real install.

Deliberately NOT built: checkpoint files, a resume daemon, automatic
re-dispatch. The reader tells a human (or /pm) where to re-enter; dispatch
stays with the PM lane.

## Non-goals for v1
- Multi-human teams beyond best-effort `team.size > 1` (DESIGN §7)
- Mobile/desktop evidence capture (web via Playwright only; interface left open)
- Tracker write-back beyond jira/markdown
