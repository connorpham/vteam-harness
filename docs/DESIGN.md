# vteam — Architecture & Extraction Design

Source: a production harness built inside the framework's first adopter
(six pipelines + team doctrine + gate scripts), inventoried 2026-08-17.
This document records how that harness became a portable, multi-tool framework;
decisions here are the house of record for the extraction — code comments point here.

**Design boundary (standing rule):** the framework repo contains ZERO
project specifics — no adopter names, keys, domains, accounts, or dates-as-law.
Everything project-shaped lives in the TARGET repo's `vteam.config.yaml`,
profiles, providers and ledgers. Adaptation is configuration, never forking;
improvement flows back as generic gates/doctrine via the 14-day framework
review. A PR that hardcodes any adopter detail into core is rejected on sight.

## 1. Layer model

```
┌─────────────────────────────────────────────────────────────┐
│ ADAPTERS  (render-time)                                     │
│ claude-code · cursor · windsurf · codex · copilot           │
│ Thin renderers: core workflow MD → tool-native format.      │
├─────────────────────────────────────────────────────────────┤
│ CORE  (tool-agnostic, English)                              │
│ doctrine/   ops, raci, review-standard, model-routing,      │
│             roles/{pm,ba,sa,dev,qa,design,devops}           │
│ workflows/  team, pm, ba, dev, qa, verify-gate, guidelines  │
│ scripts/    gates (py/mjs/sh) + scripts/lib (ctx, config)   │
│ templates/  decisions.md, log.md, changes.md, KB,           │
│             known-issues, plan.yaml, specs-INDEX            │
│             (acceptance dossier: generated at runtime)      │
│ locales/    en.yml, vi.yml (prose vocab for owner-facing    │
│             output — gates use neutral sentinels, §4)       │
├─────────────────────────────────────────────────────────────┤
│ PROFILES  (stack)          │ PROVIDERS  (services)          │
│ nextjs-prisma, node,       │ tracker: jira, github, linear, │
│ python, generic            │          markdown (offline)    │
│ → gates.yaml step manifest │ design:  figma, none           │
└─────────────────────────────────────────────────────────────┘
                    ↓  npx vteam init
┌─────────────────────────────────────────────────────────────┐
│ TARGET REPO                                                 │
│ vteam.config.yaml · .vteam/scripts/ · docs/{pm,qa,adr,team} │
│ + tool dirs (.claude/skills/… or .cursor/… etc.)            │
│ + .githooks/pre-push · CI snippet                           │
└─────────────────────────────────────────────────────────────┘
```

Dependency direction is strictly downward: adapters read core; core reads config;
nothing in core knows which tool or tracker is in play (it calls provider
interfaces).

## 2. The config contract — `vteam.config.yaml`

Everything the inventory found hardcoded becomes one of: config value, profile
step, provider method, or template variable. Canonical example:

```yaml
version: 1
project:
  name: My Project
  key: PROJ                  # ticket prefix; replaces hardcoded key regexes
  language: vi               # owner-facing output locale; framework stays EN
  go_live: 2027-01-01
  adopted: 2026-08-17        # anchor for date-grandfathered rules (§5)
paths:                       # all ledger/oracle locations, no more literals
  specs: docs/specs
  backlog: docs/backlog      # markdown-tracker tickets
  pm: docs/pm
  qa: docs/qa
  adr: docs/adr
  team: docs/team
  design: docs/design
  evidence: evd
specs:
  sources: []                # original docs verbatim_gate compares shards against
docs:
  task_context: {always: [], by_label: {}}  # per-ticket background reading;
                             # /dev T1 resolves always + the ticket's labels/type;
                             # populated by /docs, applied by the owner
stack:
  profile: nextjs-prisma     # selects profiles/<name>/gates.yaml
  package_manager: npm
git:
  protected_branch: main
  branch_pattern: "^(feat|fix)/{key}-[0-9]+-"
  merge_strategy: merge      # squash/rebase discard branch shas -> verdicts pin TWO
                             # anchors: COMMIT (code) + VERIFIED-AT (clock); the stale
                             # gate falls back to the clock, and an unanchorable
                             # verdict is RED, never a warning
  hooks: managed             # managed | external (repo has real branch protection)
  code_paths: [src/]         # "product code" for the review fence + stale scans
tracker:
  provider: jira             # jira | github | markdown (linear: roadmap)
  done_statuses: [Done, Closed, Resolved]
  review_status: "In Review"
design:
  provider: figma            # figma | none
team:
  size: 1                    # >1 relaxes single-writer/claim invariants (§7)
  capacity_per_day: 0.8
autonomy:
  level: full                # off | assisted | full
  self_merge: true           # per-project off switch for agent-merged PRs (level: full only)
  exemptions: [real-money, legal, purchasing, credentials, data-deletion]
review:
  reviewers: 2               # fresh reviewer agents per diff (+1 high-stakes)
  high_stakes_paths: ["prisma/schema.prisma", "src/lib/"]
  high_stakes_terms: [wallet, topup, refund, balance]  # the project's own risk vocabulary
models:
  routing: default           # points at a data file, not doctrine (§6)
```

`scripts/lib` ships one context module per language used by gates (`ctx.py`,
`ctx.mjs`, `ctx.sh`): resolves repo root via `git rev-parse --show-toplevel`
(kills the `ROOT = parents[4]` ×7 bug class), loads `vteam.config.yaml`, loads
`.env`. Six duplicated `load_env()` copies collapse into it.

## 3. Provider interfaces

**Tracker** (the deepest external coupling — Jira semantics were baked into gate
logic, not just API calls). The interface exposes *semantics*, not HTTP:

- `get_issue(key) → {status, status_category, assignee, labels, links, estimate, description_text}`
  (ADF flattening is a jira-provider concern)
- `search(query) → [issue]` — provider-native query passed through per-provider recipes
- `transition(key, category)` — category ∈ {in_progress, in_review, done}; the
  provider maps to concrete status names via config
- `comment(key, body) → read_back()` · `attach(key, file) → {name, md5, url}`
- `link(blocker, blocked)` — direction fixed by the interface, not by memory
- `worklog(key, minutes)` — optional capability; gates skip loudly if absent

The **markdown provider** (a `docs/backlog/` directory with one file per ticket,
frontmatter status) makes the whole framework runnable with zero external
services — the demo/e2e path, and the fallback for teams without a tracker.

**Design source**: `figma` (node JSON, styles export, frame match) or `none`
(fidelity gates collapse to the screenshot-evidence layer; the ui-fidelity
tolerance tables are *generated from the target's own design source at install
time*, never shipped as constants — the source doc is explicit that generic
4px-grid rules would grade a real design as wrong).

## 4. Locale strategy — neutral sentinels

~25 machine-checked Vietnamese literals live inside 6 gates (`hoàn thành|chặn|hỏng`,
`TRẠNG THÁI:`, `ĐẠT/KHÔNG ĐẠT`, hedge-phrase blacklist, 【7 markers】…). Decision:
**option (b) from the inventory** — gates check language-neutral sentinels; prose
around them is localized via `locales/*.yml`.

- Ledger result enum → `RESULT: done|blocked|failed` (+ `tok≈`)
- Evidence state line → `STATE:` ; narrow-scope flag → `NARROW-SCOPE:`
- QA verdicts → `PASS | FAIL | PARTIAL | NEW-BUG | BLOCKED | UNCLEAR`
  (`evd_check.py` already dual-lists EN aliases — that precedent becomes the rule)
- Hedge-phrase blacklist and write-verb patterns move into `locales/<lang>.yml`
  as per-language word lists; gates load the list for `project.language`.
- The 7-part ticket-comment markers become locale-keyed headings with stable
  sentinel ids (`[R1]…[R7]`), so `comment_check` checks ids, prose stays localized.

Migration note for the first adopter: this is a breaking change to
existing artifacts; the installer's `vteam doctor --migrate` rewrites old markers.

## 5. Dates-as-law → config anchors

The harness carries ~15 dated rules (autonomy 08/08/2026, evd-in-git 12/08/2026,
`ENFORCE_TOK_FROM`, go-live…). In vteam:

- Rules are stated **undated** in doctrine — a fresh install has no history.
- Grandfathering thresholds anchor to `project.adopted`.
- The narrative *why* of each rule ("this exists because X broke") moves to
  `core/doctrine/provenance.md` — the pedagogical incident log, project-anonymized.
  Doctrine reads as doctrine; provenance carries the scars.

## 6. What ships where (from the inventory)

**Extract as-is (generic already):** karpathy-guidelines; review-card standard +
`review_check` form checks; decision-queue format (3-state, never delete, reversal
cost, exemption list); question bar (3 conditions); loop guards; token discipline
(one brief → one card, paths-not-content, single rebuttal round); single-writer
ledger + append-at-end; evidence namespace split (`evd/<T>/` QA vs `evd/<T>/dev/`);
verdict-pinned-to-commit + staleness check; verbatim-shard-by-code + changes
ledger; DoR machine gate + durable waiver; screenshot quality gate (dominant-color
blank detection, manifest, hedge blacklist); fidelity-as-numbers doctrine;
self-review-before-reviewers with staged-diff protocol; docs-shrink guard;
pre-push (secret scan first, hatches logged); claim/recovery protocol; role
playbooks; RACI + transition-rights table; autonomy ladder; cadence mapping
(standup→desk report … retro→framework review every 14 days); light path;
mutation self-test convention (`--selftest`); plain-language bar + `▶` narration.

**Parameterize:** every path (§2), ticket-key regex, branch grammar, protected
branch, done-status sets, high-stakes review triggers (path + vocabulary),
capacity model, seed users/password (config + env only — the literal default
password in source does not ship), `origin/main` base defaults (keep the
three-dot-fallback logic for shallow CI clones verbatim — hard-won).

**Stack plugins (optional, per profile):** `token_check.mjs` (Tailwind v4 + Next
only), `ui_fidelity.mjs`/`ui-evidence.mjs` (web + Playwright; **pluggable auth
strategy** replaces the hardcoded Auth.js csrf→callback sequence), prisma/postgres
oracle steps (qa V3b clean-DB branch collapses gracefully when the profile has no
migration tool — but the skip is loud, never silent).

**Gate manifest:** `gate.sh`'s *order and philosophy* (cheapest, most
blind-spot-covering first; ledgers → lockfile → lint → types → unit → build →
reality checks → integration → e2e) becomes `profiles/<name>/gates.yaml`:
ordered steps, per-step `requires`, and `skip_reason` mandatory for absent steps
— re-closing the silent-skip hole the original explicitly fixed.

**Do not ship:** `sprint_plan.py` story data (keep only the dependency-aware
bin-packer, reading a structured plan file); model prices as doctrine
(`model-routing` becomes a data file with a staleness warning); macOS keepawake
specifics (move to an ops appendix per-OS); `annotate.py` zen-qa residue;
project anecdotes inline (→ provenance.md).

**Structured plan file:** `schedule_check.py`'s brittle markdown-table parsing is
replaced by a `docs/pm/plan.yaml` contract (sprints, items, day-costs,
dependencies, question-blocks). Human-readable markdown views are generated,
never parsed.

## 7. Team-size positioning

The source harness presumes one human owner + one machine (global WIP=1,
<2h claim-orphan heuristic, single-writer ledger, self-merge). vteam v1 keeps
this as the **default and documented sweet spot** (`team.size: 1`).

What `size > 1` does TODAY, as machinery (the team round, 2026-08):
- the ledger's **Actor column becomes mandatory** — log_check reds a legacy
  header and any empty Actor cell; identity is `VTEAM_ACTOR` env, else
  `git config user.name`, never invented (lib/ledger.py `resolve_actor`)
- `doctor --migrate --apply` upgrades a legacy ledger (rows get `—`,
  honest "unattributed history")
- perf_report grows a **per-person table** (items, lanes, Σ/median tokens,
  routing 🚩 per human) and attributes every flag to its person; the board
  rolls the ledger up by actor
- two humans appending the same ledger merge conflict-free: init writes a
  `merge=union` gitattribute for the append-only file

Still prose, not gates (stated here so nobody oversells): WIP limit = size,
the 2h claim TTL (raci.md is its one home; the PM recovery lane enforces it),
and self-merge-requires-human-review at size > 1. vteam measures artifacts,
tokens and routing per person — never anyone's chat.

## 8. Adapter contract

Core workflows are markdown with a small frontmatter schema (`name`,
`description`, `command`, `args`; `triggers`/`phases` are reserved for a
future contract revision — no adapter maps them yet). Adapters only:

1. render frontmatter to the tool's native metadata,
2. rewrite `{paths.*}`/`{project.*}` template vars from config,
3. map "spawn subagent" instructions to the tool's mechanism (Claude Code:
   Task/Agent; tools without subagents: a documented single-context fallback
   where reviewer passes run sequentially with explicit role switches),
4. install the command surface (`/team`, `/dev <KEY>`, `/qa <KEY>`, `/ba <feature>`,
   `/verify`).

Gates and templates are shared verbatim across tools — they live in
`.vteam/scripts/` in the target repo, not per-tool.

## 9. Command renames (source → vteam)

| source | vteam | rationale |
|---|---|---|
| /team | `/team` | unchanged — the flagship |
| /pm-task | `/pm` | shorter, tool-neutral |
| /ba-task | `/ba` | |
| /lam-task | `/dev` | "lam" is Vietnamese; DEV lane |
| /qa-verify-ticket | `/qa` | |
| /run-test | `/verify` | it's the gate, not just tests |
| karpathy-guidelines | `guidelines` | invoked by /dev, not user-facing |
