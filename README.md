# vteam

**Proof-of-done for AI agents.** Your agent can't say *done* anymore — it has to prove it.

vteam installs a virtual software team into your repository — a PM, a BA, an architect, a developer and a QA — together with **13 machine gates that exit non-zero** when work is claimed but not proven. It runs on Claude Code, Cursor, Windsurf, Codex and Copilot, and it was extracted from a harness that ran a real project autonomously: 37+ merged PRs, 113+ confirmed review findings, 24/7 scheduled sessions, one human owner spending ~15 minutes a day. Every rule exists because something specific broke without it.

- [Install and first run](#install-and-first-run)
- [Requirements](#requirements)
- [The problem it solves](#the-problem-it-solves)
- [The five laws](#the-five-laws)
- [What ships](#what-ships): [workflows](#workflows-9-rendered-for-your-tool) · [gates](#gates-13-checks-that-exit-non-zero) · [board](#the-board) · [paper trail](#the-paper-trail) · [model routing & cost](#model-routing-and-cost-control)
- [Configuration](#configuration)
- [Command reference](#command-reference)
- [What you get out of it](#what-you-get-out-of-it)
- [Known limits](#known-limits)
- [Status](#status)

---

## Install and first run

```bash
npx vteam-harness audit    # 1. grade this repo 0-100. No install, no writes, no network.
npx vteam-harness init     # 2. install the team + the gates
npx vteam-harness doctor   # 3. prove the install: every selftest (19 today) + provider preflight
```

Then open your agent tool and run `/team` to start a workday, or `/dev PROJ-12` for one ticket.

**Start with `audit`.** It works on any repository, vteam installed or not, and scores six dimensions — can anything fail red, do pushes get checked, does evidence outlive the chat session, is there a review trail, are approvals tied to commits, can your checks prove they can fail. For every ❌ it names the exact artifact *a machine would need to see*. Add `--json` for scripts.

Claude Code users can install through the plugin instead of the terminal:

```
/plugin marketplace add connorpham/vteam-harness
/plugin install vteam@vteam-harness
/vteam:setup
```

**Working in a mature repo with no documentation?** Run `/docs` first. It reads your codebase, asks you one batched round of questions, and writes the spec shards, decision records and known-issues the other lanes assume already exist — marking every sentence `DRAFT-FROM-CODE` or `OWNER-CONFIRMED`, so nothing it inferred can be mistaken for something you confirmed.

**Starting from nothing — no code, no docs, just an idea?** Run `/plan`. It interviews you section by section (Why, Capabilities, Constraints, Non-goals, Success signal — with a one-round steering menu after every drafted section), then writes a brief, a PRD whose requirement rows carry machine-checkable codes, and an architecture spine when the answers earn one. The PRD registers as a source document, so the verbatim gate guards everything `/ba` later shards from it — planning output that is load-bearing, not decorative.

---

**Want proof before belief?** [The 15-minute tour](docs/TUTORIAL.md) — install into a scratch repo and watch every gate refuse you for the right reason, then let you through: DoR red→green, the push fence blocking undossiered code, and a QA verdict that **expires when the code changes after it**. No AI calls, no services.

## Requirements

| Requirement | Why | If missing |
|---|---|---|
| **Node.js ≥ 20** | the installer CLI and the board | `npx` won't run |
| **git** | repo root, hooks, the review fence, verdict anchoring | `init` refuses with one clear line |
| **Python 3** | 10 of the 13 gates are Python | `doctor` diagnoses it and stops — it never crashes on it |
| **bash** | 3 gates, the pre-push fence, the session hook | on Windows use WSL or Git Bash |
| **Pillow** (`pip install pillow`) | the two screenshot-evidence gates analyse pixels | those gates report *"CANNOT CHECK — Pillow missing"* and go red; they never quietly pass |

The npm package itself has **zero dependencies** — nothing is downloaded at install time beyond the package, and there are no install scripts.

---

## The problem it solves

AI agents write code well and are terrible at being **accountable** for it. Left alone, an agent will:

- say *"done"* with nothing to prove it,
- review its own work and approve it,
- invent an answer when the spec is silent,
- quietly skip the step that was inconvenient,
- produce a report that reads well and points at nothing.

vteam does not ask an agent to be more careful. It makes *done* a machine's verdict: a gate exits non-zero, a push is refused, a verdict expires. Prose can be ignored; an exit code cannot.

---

## The five laws

| Law | What it means in practice |
|---|---|
| **A gate that has never been red does not exist** | Every checking gate ships a `--selftest` mutation proof: feed it a violating input, watch it fail. `doctor` discovers every selftest-bearing check and runs them all (19 today). An always-green check gets fixed or deleted. |
| **Evidence that only lives in the session isn't evidence** | Screenshots, review cards, verdicts, decisions — everything durable lands in a committed file or the tracker, and every outward write is **read back** to confirm it landed. |
| **A verdict is valid only for the code it examined** | Each QA verdict pins two anchors: `COMMIT:` for the code and `VERIFIED-AT:` for the clock. When the code moves, the verdict expires and the ticket returns to the queue. A verdict that can't be anchored is red — *"cannot verify"* and *"verified clean"* are different answers. |
| **Autonomy is a ladder, not a switch** | `off` → `assisted` → `full`. Quality gates never relax at any level; only *wait-for-human* gates flip, with a labelled, reversible paper trail. Real money, legal, credentials and data deletion are never auto-decided. |
| **Agents don't chat** | One brief → one card → done. Briefs are file paths and scope, never pasted walls of text. Exactly one rebuttal round, and it must be paid for with runnable evidence. Your token bill stays sane. |

---

## What ships

### Workflows (9, rendered for YOUR tool)

| Command | Role | What it does |
|---|---|---|
| `/team` | Everyone | A full **workday**: clears your decision queue first, then works every unblocked item — dev tickets sequentially, BA drafts and architecture records in parallel background lanes, QA between dev tasks — until only *you* can move things forward. Ends with a one-page desk report. |
| `/pm` | Project manager | Reads the tracker, sprint plan and decision queue, picks the highest-value unblocked work, dispatches it, and funnels everything needing a human into ONE table. Never invents answers. |
| `/ba` | Business analyst | Turns a spec into a runnable backlog: byte-checked verbatim spec shards, user stories with *testable* Given/When/Then criteria, every gap becoming a structured question instead of a guess. Challenger-reviewed before tickets are filed. |
| `/dev` | Developer | Ticket → branch → minimal implementation → verification gate → self-review with machine-measured design fidelity → two fresh reviewer agents (three on high-stakes diffs) → PR → a 7-part plain-language report on the ticket. |
| `/qa` | QA engineer | Verify-only: derives expectations from the SPEC, never the ticket prose; runs 2–5 test cases in a real browser; collects annotated evidence; cross-checks every claim; gets a challenger sign-off; writes a report a non-programmer understands in two minutes. Never touches product code. |
| `/docs` | Docs bootstrapper | Reads the codebase, interviews you once in a batched table, writes spec shards, decision seeds, known-issues and a **proposed** config patch — split `DRAFT-FROM-CODE` vs `OWNER-CONFIRMED`, and it never edits your config itself. |
| `/plan` | Greenfield intake | For projects with neither code nor docs: interviews you through a five-field kernel with a steering menu per section, writes brief → coded PRD → optional architecture spine, challenger-reviewed, and arms the verbatim gate by registering the PRD as a source document. Never invents a requirement — unanswered questions go to the decision queue. |
| `/verify` | The gate | Lint → types → unit → build → reality checks → integration → e2e, cheapest-first. A skipped step must declare why; a silent skip is a failure. |
| `guidelines` | Method | Behavioural defaults that prevent classic LLM coding mistakes: think first, surgical diffs, red-first tests. |

### Gates (13 checks that exit non-zero)

The count rule, stated once: a *gate* is a script that exits non-zero on your work. Helper libraries and the resolver/report tools are not counted, and the pre-push fence is listed separately below.

Each one ships a `--selftest` that feeds it a violating input and proves it goes red.

| Gate | Blocks |
|---|---|
| `gate.py` | the verification pipeline itself — runs your stack profile's ordered steps and stops at the first red; a step that can't run without a declared `skip_reason` is a manifest error, not a skip |
| `dor_check.py` | a ticket entering DEV without testable acceptance criteria, a spec citation, an estimate and a declared scope — with a durable waiver path for real exceptions |
| `review_check.py` | a push whose review dossier is missing, malformed, or approves without a "what I tried to break" list |
| `evd_check.py` | evidence that doesn't exist, doesn't open, or whose report skips the template — including every claim in the report that no evidence file backs |
| `evd_ui_check.py` | screenshots that are blank, error pages or the wrong region — detected by pixel analysis, not by filename |
| `stale_verdict_check.py` | a "done" ticket whose code changed after the verdict, and any verdict that cannot be anchored to a commit or timestamp |
| `log_check.py` | a dispatch ledger row that breaks the schema, or a ledger edited anywhere but the end |
| `verbatim_gate.py` | a spec shard that has drifted from the source document it was copied from |
| `comment_check.py` | a ticket report missing any of its seven required sections |
| `schedule_check.py` | *"we're on schedule"* as an opinion — the plan is a structured file and this computes the answer |
| `lockfile_check.sh` | a second package manager's lockfile sneaking into the repo — one repo, one package manager |
| `docs_shrink_check.sh` | a ledger silently losing more than 20% of its lines (an accidental overwrite, not an edit) |
| `preflight.sh` | starting work when the tracker, design source, git remote or database isn't actually reachable — every link is pinged for real |

Plus the **pre-push fence** (`.githooks/pre-push`): no direct pushes to the protected branch, no product code on a branch outside your configured grammar, no push without its review dossier — and a **secret scan with no escape hatch that fails closed**: if the diff base is unavailable it scans the full outgoing content rather than passing.

Three more gates ship with the `nextjs-prisma` profile: design-token drift, UI fidelity measured against the design's own node data, and browser evidence capture.

### The board

```bash
npx vteam-harness board          # http://127.0.0.1:4177
```

The proof trail as one local page: ticket columns by status, ledger rows with `done`/`blocked`/`failed` badges and token accounting, evidence per ticket with its verdict and pinned commit, and the decision queue front and centre whenever something needs you.

Read-only **by construction**: it binds `127.0.0.1` only, answers exactly `GET /` and `GET /api/state`, serves no files, and has no mutating endpoint at all — every write attempt gets a 405, because a board that could transition a ticket would be a second write path around the gates. Every panel names the file it read; empty panels tell you which file to create instead of rendering a plausible blank.

### The paper trail

Your project's memory, all machine-readable: a **decision queue** so nothing needing you is ever scattered, an append-only **dispatch ledger**, session minutes, an **acceptance dossier** (the one file you read to sign off), and a knowledge base with **graduation rules** — lessons don't pile up, they become gates and then get deleted.

### Model routing and cost control

Doctrine speaks in tiers so it never rots — `frontier / workhorse / standard / utility`: expensive models for expensive-if-wrong decisions, cheap models for checklist work, and **never a downgrade at a quality gate**. One data file (`model-routing.data.yaml`) holds role→tier routing, high-stakes overrides (a diff touching money bumps the second reviewer up a tier), prices, and the exact model name each tool expects.

```bash
python3 .vteam/scripts/model_route.py dev-r2 --tool claude-code                 # → sonnet
python3 .vteam/scripts/model_route.py dev-r2 --tool claude-code --high-stakes   # → opus
```

Because the ledger records tokens and tier per ticket, `perf_report.py` answers questions instead of guessing: who did what at what cost, whether the model choice was sane (flagging frontier use without an approved escalation trail, or a cheap model doing DEV work), where the tokens went (outliers above 2× the median, monthly trend, a cost band honestly labelled an estimate). Routing changes get argued from that report, never from vibes.

---

## Configuration

Everything project-specific lives in one file. Adaptation is configuration, never forking.

The config dialect is deliberately small and **identical across all three runtimes**: flow mappings like `{ payment: [a.md, b.md] }` parse the same in the Python gates and the Node CLI (a conformance suite enforces it), tab indentation is a loud error everywhere, and the shell helper refuses shapes outside its subset instead of misreading them.

```yaml
# vteam.config.yaml — generated by init, edited by you
project:  { name: My Project, key: PROJ, language: en }   # reports in your language
paths:    { specs: docs/specs, pm: docs/pm, qa: docs/qa, evidence: evd }
stack:    { profile: node, package_manager: npm }         # generic | node | python | nextjs-prisma
git:
  protected_branch: main
  branch_pattern: "^(feat|fix)/{key}-[0-9]+-"             # your grammar, enforced by the fence
  merge_strategy: merge                                   # merge | squash | rebase
  hooks: managed                                          # or external, if you own hook wiring
tracker:  { provider: markdown }                          # markdown | jira | github
design:   { provider: none }                              # none | figma
autonomy: { level: assisted, self_merge: false }          # gates never relax; merges can stay human
review:
  reviewers: 2
  high_stakes_paths: ["prisma/schema.prisma"]             # a diff here gets an extra reviewer
  high_stakes_terms: [wallet, refund, payout]             # your project's risk vocabulary
docs:
  task_context:                                           # what /dev reads before coding
    always: [docs/architecture.md]
    by_label: { payment: [docs/specs/billing.md] }
```

Four knobs worth setting deliberately:

- **`git.merge_strategy`** — `squash` and `rebase` discard branch commits when a PR lands, so verdicts anchor by timestamp instead of by sha. Set this to match your repo or the stale-verdict gate will tell you it cannot anchor.
- **`autonomy.self_merge`** — whether an agent may merge its own green PR. Only honoured at `level: full`, and you can keep it `false` there.
- **`review.high_stakes_terms`** — the words that mean money or irreversibility *in your product*. A diff mentioning them gets an extra reviewer at a higher tier.
- **`docs.task_context`** — which background documents `/dev` must read for which kind of ticket. A file listed here but missing is reported loudly, never guessed around.

Supported surfaces: **agent tools** Claude Code (native skills and subagents), Cursor, Windsurf, Codex and Copilot (the last two with a documented sequential-review fallback where subagents don't exist); **trackers** Jira (ADF flattening, attachment read-back, link-direction verification), GitHub Issues (`PROJ-123` ⇄ issue `#123`, labels carry the status machine) or a markdown backlog that needs no external service at all; **design source** Figma (fidelity measured against the design's own node data, because measuring code with code is self-grading) or none.

---

## Command reference

| Command | What it does |
|---|---|
| `npx vteam-harness audit [--json]` | grade any repo's agent accountability 0–100. No install needed, never writes, no network. |
| `npx vteam-harness init [--yes]` | install into the current repo. Every flag value is validated before the first byte is written; invalid input exits 1 having written nothing. Flags: `--name --key --language --profile --tracker --design --autonomy --tools`. |
| `npx vteam-harness doctor [--json]` | prove the install: prerequisites, config parse, manifest integrity, hook wiring, routing freshness, every selftest (discovered dynamically — 19 today), live provider pings. |
| `npx vteam-harness update` | refresh framework files. `.vteam/manifest.json` makes *"never touches your files"* checkable: only files whose hash matches what the framework last wrote get overwritten; anything you edited is kept and the new version is parked as `*.new`. |
| `npx vteam-harness board [--port N]` | the read-only local dashboard. |
| `npx vteam-harness doctor --migrate [--apply]` | rewrite legacy pre-vteam markers in existing ledgers and evidence. Dry-run by default. |

---

## What you get out of it

**If you're a solo owner or founder:** the team works while you sleep, and your daily touchpoint is a 15-minute desk report — what got done with live evidence links, what needs you as batched questions with ready-made proposals and stated reversal costs, what's at risk in the next seven days. When the backlog drains you read one acceptance file and sign off in batches.

**If you're a developer:** you stop babysitting the agent. Underspecified tickets bounce back to analysis before you waste a session. Reviews come from fresh agents with empty context held to a written standard, so an approval without a "what I tried to break" list is invalid and a fabricated finding voids the whole card. Your PRs carry committed review dossiers anyone can audit months later.

**If you're leading a team:** work-in-progress is limited by design, crashed sessions can't orphan tickets (claims carry timestamps and TTLs), two sessions can't grab the same work, and *"we're on schedule"* becomes a number a script computes from a structured plan rather than a sentence someone typed.

**If you care about cost:** token discipline is a first-class rule set, expensive models are routed only to expensive-if-wrong decisions, and every ticket's tokens and tier land in the ledger — so overspend has nowhere to hide and routing gets tuned from data.

**If you're handing work to someone else:** every claim in the repository is traceable. A verdict names the commit it examined. A review names what it tried to break. Evidence is a file, not a memory of a chat.

---

## Known limits

Stated plainly, because a framework about honest reporting should be honest about itself:

- **It suits a repo willing to adopt the practice.** vteam creates the ledgers, specs and evidence layout it needs (and `/docs` bootstraps documentation from your code), but it does expect that from now on decisions land in files and evidence gets committed. If your team won't commit evidence, this is the wrong tool.
- **`init` writes its layout using defaults it does not yet infer from your repo.** Review the generated `vteam.config.yaml` before your first run — especially `protected_branch`, `branch_pattern` and `merge_strategy`. Detect-then-propose is the next thing being built.
- **Repo-level Claude Code skills with the same names are currently overwritten** by `init` (`team`, `pm`, `ba`, `dev`, `qa`, `verify`, `docs`, `guidelines`). If you have your own skill by one of those names, back it up first. This is a known bug, not a design choice, and it is being fixed.
- **There is no `uninstall` command yet.** Removing vteam today means deleting `vteam.config.yaml`, `.vteam/`, the rendered tool directories, `.githooks/pre-push`, and resetting `core.hooksPath`.
- **The CI snippet it writes is GitHub Actions.** On other platforms call `bash .vteam/scripts/gate.sh` from your own pipeline — the gates themselves are platform-agnostic.
- **One human owner plus agents is the tested shape.** `team.size > 1` is documented but not yet enforced by machinery; treat multi-human support as best-effort.
- **Trackers are markdown, Jira and GitHub Issues.** Linear and Trello are not implemented.
- **Evidence is committed to git.** If your screenshots would contain regulated or personal data, decide your policy before enabling the screenshot gates — a committed image is permanent.

---

## Status

Working, and the proof ships with it: `npm test` runs [tests/e2e.mjs](tests/e2e.mjs) — **95 checks** plus a 15-fixture parser-conformance suite (the Python, Node and shell config readers must agree byte-for-byte, and configs they must reject must die in all of them) covering fresh repo → `init` → **doctor green**, manifest-guarded `update`, invalid input writing nothing, the board's read-only fence, and the pre-push fence and secret scan actually going red. CI runs it on every push. Also dogfooded against a real project's artifacts: 500+ verbatim spec rows, a 41-row ledger and real review dossiers all pass the ported gates.

Published on npm as **`vteam-harness`** (the name `vteam` was blocked for similarity); the command is still `vteam`. Pre-1.0 — expect sharp edges, and see [Known limits](#known-limits) above.

- Architecture and design decisions: [docs/DESIGN.md](docs/DESIGN.md)
- Build history and what's next: [docs/ROADMAP.md](docs/ROADMAP.md)
- The incidents behind the rules: [core/doctrine/provenance.md](core/doctrine/provenance.md)
- The excuses agents use to route around gates: [core/doctrine/red-flags.md](core/doctrine/red-flags.md)

## Layout

```
core/        tool-agnostic source: doctrine, workflows, gates, templates, locales
adapters/    one renderer module per tool — see adapters/README.md to add yours
profiles/    stack profiles for the verification gate (generic, node, python, nextjs-prisma)
providers/   tracker and design-source adapters (markdown, jira, github / figma, none)
plugins/     the Claude Code plugin
bin/, src/   the installer CLI (audit · init · doctor · update · board · doctor --migrate)
tests/       the end-to-end suite behind every claim above
```

## License

MIT
