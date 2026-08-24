# vteam

[![npm](https://img.shields.io/npm/v/vteam-harness?color=%23C03B2B&label=npm)](https://www.npmjs.com/package/vteam-harness)
[![ci](https://github.com/connorpham/vteam-harness/actions/workflows/ci.yml/badge.svg)](https://github.com/connorpham/vteam-harness/actions/workflows/ci.yml)
[![node](https://img.shields.io/node/v/vteam-harness)](https://nodejs.org)
[![license](https://img.shields.io/npm/l/vteam-harness)](LICENSE)
[![OpenSSF Scorecard](https://api.scorecard.dev/projects/github.com/connorpham/vteam-harness/badge)](https://scorecard.dev/viewer/?uri=github.com/connorpham/vteam-harness)
[![codeql](https://github.com/connorpham/vteam-harness/actions/workflows/codeql.yml/badge.svg)](https://github.com/connorpham/vteam-harness/actions/workflows/codeql.yml)

**Proof-of-done for AI agents.** Your agent can't say *done* anymore — it has to prove it.

vteam installs a virtual software team into your repository — a PM, a BA, an architect, a developer and a QA — together with **14 machine gates that exit non-zero** when work is claimed but not proven. It runs on Claude Code, Cursor, Windsurf, Codex and Copilot, and it was extracted from a harness that ran a real project autonomously: 37+ merged PRs, 113+ confirmed review findings, 24/7 scheduled sessions, one human owner spending ~15 minutes a day. Every rule exists because something specific broke without it.

### Five things nothing else here does

|  | | |
|---|---|---|
| **Done is an exit code** | A gate exits non-zero. A push is refused. There is nothing to argue with. | [see the 14 gates ↓](#gates-14-checks-that-exit-non-zero) |
| **A verdict dies when the code moves** | QA passed it, one commit landed on top — the pass expired by itself and the ticket came back. | [watch it happen ↓](#what-it-actually-looks-like) |
| **Every gate proves it can fail** | Each one ships a `--selftest` that feeds it a violating input and checks it goes red. A gate that has never been red gets deleted. | [the law ↓](#the-five-laws) |
| **QA tests like a person, not a route** | Reaching a screen by typing its address is *refused* — name the button a user clicks, or the test proved the URL and nothing else. | [what proof means ↓](#what-a-verdict-has-to-carry) |
| **Measure your gap in 10 seconds** | `npx vteam-harness audit` grades any repo 0–100 without installing anything, and names the artifact each ❌ is missing. | [start here ↓](#install-and-first-run) |

<p align="center">
  <img src="https://raw.githubusercontent.com/connorpham/vteam-harness/main/docs/assets/lifecycle.svg" alt="One ticket's path through vteam: /ba, then dor_check exits 1 on a vague ticket; /dev, then /verify plus the push fence refuse code with no committed review dossier; /qa, then evd_check demands a verdict pinned to both a commit and a timestamp; Done. When code changes after the verdict, stale_verdict_check expires it and the ticket comes back to /dev." width="100%">
</p>

- [Install and first run](#install-and-first-run) · [what it actually looks like](#what-it-actually-looks-like)
- [Requirements](#requirements)
- [The problem it solves](#the-problem-it-solves)
- [The five laws](#the-five-laws)
- [What ships](#what-ships): [workflows](#workflows-9-rendered-for-your-tool) · [gates](#gates-14-checks-that-exit-non-zero) · [graph](#the-graph) · [board](#the-board) · [code map](#the-code-map-cpg-lite) · [cross-model review](#cross-model-review) · [evidence](#what-a-verdict-has-to-carry) · [paper trail](#the-paper-trail) · [model routing & cost](#model-routing-and-cost-control) · [24/7](#running-it-247-on-a-subscription)
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
npx vteam-harness doctor   # 3. prove the install: every selftest (22 today) + provider preflight
```

Then open your agent tool and run `/team` to start a workday, or `/dev PROJ-12` for one ticket.

**Start with `audit`.** It works on any repository, vteam installed or not, and scores six dimensions — can anything fail red, do pushes get checked, does evidence outlive the chat session, is there a review trail, are approvals tied to commits, can your checks prove they can fail. For every ❌ it names the exact artifact *a machine would need to see*. Add `--json` for scripts.

Claude Code users can install through the plugin instead of the terminal:

```
/plugin marketplace add connorpham/vteam-harness
/plugin install vteam@vteam-harness
/vteam:setup
```

### What it actually looks like

Three transcripts, captured from a real run — not mockups.

**1. Measure the gap before installing anything.** `audit` reads your repo and scores six dimensions; every ❌ names the artifact a machine would need to see.

```console
$ npx vteam-harness audit
  0/100 · grade F    (A ≥85 · B ≥70 · C ≥55 · D ≥35 · F <35)

GATES          0/20
   ❌ no CI pipeline — nothing can go red off this machine
   ❌ no test entrypoint (package.json test / pytest / Makefile / tests/)
   → a machine would need to see: a CI pipeline that runs the tests on every push
HOOKS          0/15
   ❌ no active git hooks — a push leaves this machine completely unchecked
   ❌ no secret scan in hooks or CI — a leaked token sails through

$ npx vteam-harness init && npx vteam-harness audit
  85/100 · grade A
```

**2. A vague ticket does not reach the developer.** The DoR gate answers with the four things that are missing, not with a shrug.

```console
$ python3 .vteam/scripts/dor_check.py WAL-1
❌ dor_check: WAL-1 is NOT ready — return to the BA lane (raci §2)
   - no Given/When/Then acceptance criteria
   - no spec citation (`spec §x.y` or a docs/specs/ path)
   - no out-of-scope section — the dev will self-expand
   - no original estimate — an unestimated ticket is not created yet (BA debt)
```

**3. A verdict is valid only for the code it examined.** QA passed this ticket, then one commit landed on top — and the pass expired by itself.

```console
$ python3 .vteam/scripts/stale_verdict_check.py
✅ no stale verdicts — examined 1 evidenced tickets

# …one commit later, on the same ticket:
$ python3 .vteam/scripts/stale_verdict_check.py
⚠️  1 tickets were judged, then the CODE CHANGED

  WAL-1  (REPORT pins d576135)
      ↳ e823e9d 2026-08-21 15:29  WAL-1 tweak after the verdict

A verdict is valid only for the code it examined.
```

And the push fence, for completeness: code with no committed review dossier does not leave the machine.

```console
$ git push origin feat/WAL-1-topup-limits
❌ review_check: evd/WAL-1/dev/review.md NOT in commit d5761359a478 — the review
   dossier commits with the code; a file on one machine is a fabricated report
error: failed to push some refs to 'origin'
```

---

**Working in a mature repo with no documentation?** Run `/docs` first. It reads your codebase, asks you one batched round of questions, and writes the spec shards, decision records and known-issues the other lanes assume already exist — marking every sentence `DRAFT-FROM-CODE` or `OWNER-CONFIRMED`, so nothing it inferred can be mistaken for something you confirmed.

**Starting from nothing — no code, no docs, just an idea?** Run `/plan`. It interviews you section by section (Why, Capabilities, Constraints, Non-goals, Success signal — with a one-round steering menu after every drafted section), then writes a brief, a PRD whose requirement rows carry machine-checkable codes, and an architecture spine when the answers earn one. The PRD registers as a source document, so the verbatim gate guards everything `/ba` later shards from it — planning output that is load-bearing, not decorative.

---

**Want proof before belief?** [The 15-minute tour](docs/TUTORIAL.md) — install into a scratch repo and watch every gate refuse you for the right reason, then let you through: DoR red→green, the push fence blocking undossiered code, and a QA verdict that **expires when the code changes after it**. No AI calls, no services.

## Requirements

| Requirement | Why | If missing |
|---|---|---|
| **Node.js ≥ 20** | the installer CLI and the board | `npx` won't run |
| **git** | repo root, hooks, the review fence, verdict anchoring | `init` refuses with one clear line |
| **Python 3** | 11 of the 14 gates are Python | `doctor` diagnoses it and stops — it never crashes on it |
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
| **A gate that has never been red does not exist** | Every checking gate ships a `--selftest` mutation proof: feed it a violating input, watch it fail. `doctor` discovers every selftest-bearing check and runs them all (22 today). An always-green check gets fixed or deleted. |
| **Evidence that only lives in the session isn't evidence** | Screenshots, review cards, verdicts, decisions — everything durable lands in a committed file or the tracker, and every outward write is **read back** to confirm it landed. |
| **A verdict is valid only for the code it examined** | Each QA verdict pins two anchors: `COMMIT:` for the code and `VERIFIED-AT:` for the clock. When the code moves, the verdict expires and the ticket returns to the queue. A verdict that can't be anchored is red — *"cannot verify"* and *"verified clean"* are different answers. |
| **Autonomy is a ladder, not a switch** | `off` → `assisted` → `full`. Quality gates never relax at any level; only *wait-for-human* gates flip, with a labelled, reversible paper trail. Real money, legal, credentials and data deletion are never auto-decided. |
| **Agents don't chat** | One brief → one card → done. Briefs are file paths and scope, never pasted walls of text. Exactly one rebuttal round, and it must be paid for with runnable evidence. Your token bill stays sane. |

---

## What ships

### Workflows (9, rendered for YOUR tool)

<p align="center">
  <img src="https://raw.githubusercontent.com/connorpham/vteam-harness/main/docs/assets/team.svg" alt="The nine workflows and how work moves: /plan and /docs build the oracle; /pm dispatches one coding item at a time; /ba shards specs into tickets; /dev implements and gets reviewed by two fresh agents; /qa verifies from the spec. dor_check guards the BA-to-DEV hand-off, review_check guards the push, evd_check guards Done. /verify and guidelines are shared tools any lane calls." width="100%">
</p>

Each lane is one command in your agent tool. What matters is not the persona — it is **what each one leaves behind in your repo**, and **which gate refuses the hand-off** when it isn't there.

#### Getting an oracle to judge against

**`/plan` — you have an idea, no code, no docs.** It interviews you through five fields (Why · Capabilities · Constraints · Non-goals · Success signal) with a one-round steering menu after each drafted section, then writes a brief, a PRD whose requirement rows carry machine-checkable codes, and an architecture spine when your answers earn one.
*Writes:* `docs/specs/` brief + PRD · *Then:* the PRD registers as a source document, so the verbatim gate guards every shard `/ba` later cuts from it. Planning output that is load-bearing, not decorative.

**`/docs` — you have a mature codebase and no documentation.** It reads the code first (every inference marked `⚠ UNVERIFIED`), then asks you **one batched round** of questions, then writes what the other lanes assume already exists.
*Writes:* spec shards, decision seeds, `known-issues.md`, a **proposed** config patch · *Never:* edits your config itself, or mixes what it guessed with what you confirmed — each sentence is marked `DRAFT-FROM-CODE` or `OWNER-CONFIRMED`.

#### Turning that into shipped work

**`/pm` — the dispatcher.** Reads the tracker, the sprint plan and the decision queue; picks the highest-value item whose blockers are actually Done; funnels everything needing a human into **one** table with proposals and reversal costs attached.
*Writes:* a ledger row per dispatch, the decision queue, session minutes · *Never invents an answer* — a silent spec becomes a question, not a guess.

**`/ba` — spec into a runnable backlog.** Cuts byte-checked verbatim shards from the source documents, writes user stories with *testable* Given/When/Then criteria, and turns every gap into a structured question instead of a guess. A challenger agent reviews the batch before tickets are filed.
*Gated by:* `verbatim_gate` (a shard that drifted from its source is red) and `dor_check` at the hand-off — **a vague ticket does not reach the developer.**

**`/dev` — ticket to reviewed PR.** Claims the ticket, branches, reads the code map instead of walking your tree, writes a task-sheet *before* touching code, implements the minimum, runs `/verify`, self-reviews with machine-measured design fidelity, then spawns **two fresh reviewer agents** (three when the diff touches your declared high-stakes paths or vocabulary) whose approval must carry a "what I tried to break" list.
*Writes:* the branch, the committed review dossier, a 7-part plain-language report on the ticket · *Gated by:* the push fence — **code with no committed dossier does not leave the machine.**

**`/qa` — independent verification.** Derives what to expect **from the spec, never from the ticket prose or the dev's claim**; designs 2–5 test cases; runs them in a real browser as a real user; collects annotated evidence; cross-checks every claim in the ticket against a file that proves it; gets a fresh challenger to try to falsify the verdict; writes a report a non-programmer understands in two minutes.
*Writes:* `evd/<TICKET>/` — see [what a verdict has to carry](#what-a-verdict-has-to-carry) · *Never touches product code.*

#### Running it, and staying honest

**`/team` — a full workday on top of `/pm`.** Clears your decision queue first, then works every unblocked item — dev tickets sequentially (one coding item at a time, by design), BA drafts and architecture records in parallel background lanes, QA between dev tasks — until the only thing left needs *you*. Ends with a one-page desk report.

**`/verify` — the gate, on demand.** Lint → types → unit → build → reality checks → integration → e2e, cheapest-first. A skipped step must declare why; a silent skip is a failure. On a repo with no test suite it prints `GREEN (WEAK — no test suite ran)` instead of a green that lies.

**`guidelines` — the method, not a role.** Behavioural defaults that prevent classic LLM coding mistakes: think before writing, surgical diffs, red-first tests.

### Gates (14 checks that exit non-zero)

The count rule, stated once: a *gate* is a script that exits non-zero on your work. Helper libraries and the resolver/report tools are not counted, and the pre-push fence is listed separately below.

Each one ships a `--selftest` that feeds it a violating input and proves it goes red.

| Gate | Blocks |
|---|---|
| `gate.py` | the verification pipeline itself — runs your stack profile's ordered steps and stops at the first red; a step that can't run without a declared `skip_reason` is a manifest error, not a skip |
| `dor_check.py` | a ticket entering DEV without testable acceptance criteria, a spec citation, an estimate and a declared scope — with a durable waiver path for real exceptions |
| `review_check.py` | a push whose review dossier is missing, malformed, or approves without a "what I tried to break" list |
| `evd_check.py` | evidence that doesn't exist, doesn't open, or whose report skips the template — including every claim in the report that no evidence file backs. Every executed UI test case must also carry its **journey** (`AS:` which account and role · `PRECONDITION:` · `ENTRY:` the screen the user starts on and the control they click — **a bare URL is refused, because typing an address proves the address, not the product** · `AFTER:` what changed, including *survives a reload* · `BACK:` where Back and Cancel land you) and a `*_boxed.png` with a caption on the region that carried the verdict |
| `evd_ui_check.py` | screenshots that are blank, error pages or the wrong region — detected by pixel analysis, not by filename |
| `graph_check.py` | an incoherent work graph — dangling blocked-by edges, dependency cycles (deadlocks), a Done ticket without a PASS verdict (a lane closed outside its rights), byte-identical repeated dispatches, an item dispatched past `team.loop_budget_per_day`, and commits straying outside a ticket's declared `CODE-SCOPE`. Each check names the MAST failure mode it closes (arXiv 2503.13657) |
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

### What a verdict has to carry

A "PASS" is worth exactly as much as the folder behind it. This is that folder — and every field in it is demanded by `evd_check`, not by a style guide.

<p align="center">
  <img src="https://raw.githubusercontent.com/connorpham/vteam-harness/main/docs/assets/evidence.svg" alt="Anatomy of one QA test case: the evidence folder with REPORT.md, per-step screenshots named for what they show, and a boxed verdict screenshot; the journey fields the gate demands — AS which account and role, PRECONDITION, ENTRY the screen and the control clicked, AFTER what changed including survives-a-reload, BACK where Back and Cancel land; and why an ENTRY that is only a URL is refused." width="100%">
</p>

**The journey, not the route.** Every executed UI test case states who was signed in (`AS:` — half of all UI bugs are role-shaped), what had to exist first (`PRECONDITION:`), and **where the user started and what they clicked** (`ENTRY:`). An `ENTRY:` that is only a URL is **refused**: typing a screen's address proves the address, not the product — a menu item missing for that role, a wrong permission, an unreachable row, all three hide behind a deep link. Keep the URL beside the click path if it's useful; it just can't be the only path.

**Finish the motion a person finishes.** `AFTER:` records what actually changed — the confirmation message, the list row behind, and whether the value **survives a reload** (a save that dies on refresh is not a save). `BACK:` records where Back and Cancel land you, and with what state — is the filter preserved, does Cancel actually cancel. Those four moves find more real defects than any boundary table.

**Evidence a stranger can read.** Screenshots are named for what they show (`01_orders_list.png`, not `01.png`). The step that carried the verdict gets a **red box with a caption** — required on every UI case, not just failures, because an unannotated full-page shot makes the reader guess which pixels mattered. And the verdict itself pins two anchors: the `COMMIT:` it examined and the `VERIFIED-AT:` clock — so it can expire.

### The graph

The dependency graph of your project already exists — scattered across `- blocked-by:` lines, the sprint plan, the ledger and the evidence tree. `npx vteam-harness graph` computes what nobody reads together: a **READY table** (tickets whose every blocker is provably Done, with sprint and cost), a **BLOCKED table** (who waits on whom), and the findings a human eye misses — edges pointing at tickets that don't exist, cycles where two tickets block each other forever, Done tickets with no PASS in their evidence. Every panel names the file it was read from. It is read-only and **always exits 0** — the graph is a mirror; the gate that fails the build on the same findings is `graph_check.py`, and the two are held together by a conformance selftest. `--json` for a stable, diffable dump pinned to the commit; `--dot | dot -Tsvg > graph.svg` to see it.

### The board

```bash
npx vteam-harness board          # http://127.0.0.1:4177
```

The proof trail as one local page: ticket columns by status, ledger rows with `done`/`blocked`/`failed` badges and token accounting, evidence per ticket with its verdict and pinned commit, and the decision queue front and centre whenever something needs you.

Read-only **by construction**: it binds `127.0.0.1` only, answers exactly `GET /` and `GET /api/state`, serves no files, and has no mutating endpoint at all — every write attempt gets a 405, because a board that could transition a ticket would be a second write path around the gates. Every panel names the file it read; empty panels tell you which file to create instead of rendering a plausible blank.

### The code map (CPG-lite)

`python3 .vteam/scripts/code_map.py build` walks your `git.code_paths` + `paths.specs` and writes a sorted `.vteam/map.json`: files, symbols, import edges, doc anchors. Then `code_map.py query PROJ-42 wallet topup` ranks the files that actually matter, expands one import hop, and prints a capped table of **paths and line ranges — never file content** — ending in "read THESE, not the tree". `/dev` and `/docs` start there instead of walking the directory tree, which is where most of an agent's context budget quietly goes. It is honest about what it is: Python is really parsed (`ast`), JS/TS symbols come from conservative regexes, markdown contributes headings and ticket keys as doc→code edges. No data-flow, no call graph, not a Joern CPG — a real one needs per-language compiler frontends, and vteam ships zero dependencies. A stale map warns loudly and still answers; `--strict` turns that into exit 1 for CI.

### Cross-model review

You run vteam on Claude, but the code review doesn't have to be. A review card is just a file, so any tool that can write a conforming one can hold a reviewer seat — and two agents on the same model share their blind spots. Point a card id at an external CLI (`review.external.r2: {command: "codex exec", model: "gpt-5-codex"}`) and run `node .vteam/scripts/external_review.mjs <TICKET> R2`: vteam pipes the brief — `review-standard.md` verbatim, the card contract with the gate's real numbers, and the diff — to the tool on stdin, then validates what it prints against `review_check`'s own bar before writing `## R2 — external (gpt-5-codex)` into the dossier. An invalid card is never written: no card means the push fence blocks, exactly as for a missing Claude card. The CLI is yours to install and authenticate — vteam refuses loudly when the binary isn't on PATH rather than silently reviewing with one fewer pair of eyes.

### The paper trail

Your project's memory, all machine-readable: a **decision queue** so nothing needing you is ever scattered, an append-only **dispatch ledger**, session minutes, an **acceptance dossier** (the one file you read to sign off), and a knowledge base with **graduation rules** — lessons don't pile up, they become gates and then get deleted.

### Model routing and cost control

Doctrine speaks in tiers so it never rots — `frontier / workhorse / standard / utility`: expensive models for expensive-if-wrong decisions, cheap models for checklist work, and **never a downgrade at a quality gate**. One data file (`model-routing.data.yaml`) holds role→tier routing, high-stakes overrides (a diff touching money bumps the second reviewer up a tier), prices, and the exact model name each tool expects.

```bash
python3 .vteam/scripts/model_route.py dev-r2 --tool claude-code                 # → sonnet
python3 .vteam/scripts/model_route.py dev-r2 --tool claude-code --high-stakes   # → opus
```

Because the ledger records tokens and tier per ticket, `perf_report.py` answers questions instead of guessing: who did what at what cost, whether the model choice was sane (flagging frontier use without an approved escalation trail, or a cheap model doing DEV work), where the tokens went (outliers above 2× the median, monthly trend, a cost band honestly labelled an estimate). Routing changes get argued from that report, never from vibes.

### Running it 24/7 on a subscription

The "24/7 scheduled sessions" above is not one immortal process — it is short shifts on a clock: open the repo, read the board, run `/team`, print the desk report, exit. The ledger, the In Progress claim with its TTL, and the decision queue are what make a shift resumable from cold, so a spent usage window or a closed laptop costs you a break, not an incident. `docs/team/ops-247.md` (rendered at install) is the copy-paste appendix: a launchd plist plus `caffeinate` for macOS, a systemd user timer plus `systemd-inhibit` for Linux, a cron line plus a lock anywhere — so two shifts can never collide on one repo. It is honest about the limit: a subscription meters usage in rolling windows, so you get *unattended continuity, not unlimited throughput* — and about what never relaxes at 03:00: every gate, the push fence, and the exemptions. Questions still wait for you; the morning ritual is still one desk report.

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
team:
  size: 1                                                 # >1 makes the ledger's Actor column a GATE
  hours_per_day: 8                                        # plan costs accept "1.5d" or "12h"
  loop_budget_per_day: 4                                  # >N dispatches of one item in a day = thrash
specs:
  sources: []                                             # the ORIGINAL docs shards are checked against
review:
  reviewers: 2
  high_stakes_paths: ["prisma/schema.prisma"]             # a diff here gets an extra reviewer
  high_stakes_terms: [wallet, refund, payout]             # your project's risk vocabulary
docs:
  task_context:                                           # what /dev reads before coding
    always: [docs/architecture.md]
    by_label: { payment: [docs/specs/billing.md] }
```

Knobs worth setting deliberately:

- **`git.merge_strategy`** — `squash` and `rebase` discard branch commits when a PR lands, so verdicts anchor by timestamp instead of by sha. Set this to match your repo or the stale-verdict gate will tell you it cannot anchor.
- **`autonomy.self_merge`** — whether an agent may merge its own green PR. Only honoured at `level: full`, and you can keep it `false` there.
- **`review.high_stakes_terms`** — the words that mean money or irreversibility *in your product*. A diff mentioning them gets an extra reviewer at a higher tier.
- **`docs.task_context`** — which background documents `/dev` must read for which kind of ticket. A file listed here but missing is reported loudly, never guessed around.
- **`team.size`** — set it to your real headcount. Above 1, the ledger's `Actor` column becomes mandatory (a gate, not a convention) and reporting splits per person.
- **`team.hours_per_day` / `team.loop_budget_per_day`** — a workday in hours (so estimates can be written `12h`), and the per-item daily dispatch ceiling above which `graph_check` calls thrash what it is.

Supported surfaces: **agent tools** Claude Code (native skills and subagents), Cursor, Windsurf, Codex and Copilot (the last two with a documented sequential-review fallback where subagents don't exist); **trackers** Jira (ADF flattening, attachment read-back, link-direction verification), GitHub Issues (`PROJ-123` ⇄ issue `#123`, labels carry the status machine) or a markdown backlog that needs no external service at all; **design source** Figma (fidelity measured against the design's own node data, because measuring code with code is self-grading) or none.

---

## Command reference

Eight commands, one journey. Gates exit 1; the two mirrors (`board`, `graph`) always exit 0; nothing calls a network except the preflight pings you configured. Every transcript below is captured from a real run — most of them from **this repository**, which installs vteam into itself and keeps its own ledger and evidence (`evd/VT-1/`).

<picture>
  <img src="https://raw.githubusercontent.com/connorpham/vteam-harness/main/docs/assets/commands.svg" alt="Every vteam command end to end: audit grades with no install, init writes config, gates, skills and fence, doctor proves the install with 22 selftests. Daily: the agent tool runs the workday, 14 gates can refuse with exit 1, everything lands in committed files; board and graph mirror those files and never fail the build. resume derives where a dead session stopped; usage measures who ran which model at what cost; update refreshes framework files by manifest hash." width="100%">
</picture>

| Command | What it does |
|---|---|
| [`audit [--json]`](#audit--measure-before-you-believe) | grade any repo's agent accountability 0–100. No install needed, never writes, no network. |
| [`init [--yes]`](#init--install-validated-before-the-first-byte) | install into the current repo. Every flag value is validated before the first byte is written; invalid input exits 1 having written nothing. |
| [`doctor [--json]`](#doctor--prove-the-install) | prove the install: prerequisites, config parse, manifest integrity, hook wiring, every selftest (discovered dynamically — 22 today), live provider pings. |
| [`update`](#update--refresh-without-touching-your-files) | refresh framework files by manifest hash — your edited copies are kept, the new version parked as `*.new`. |
| [`board [--port N]`](#board--the-read-only-dashboard) | the read-only local dashboard on 127.0.0.1. |
| [`graph [--json\|--dot]`](#graph--the-work-graph-made-visible) | ready set, blocked set, dangling edges, cycles. Always exits 0 — the mirror; `graph_check.py` is the gate. |
| [`usage [--sync\|--json\|--since D]`](#usage--measured-not-self-reported) | **measured** AI usage — who ran which model, when, at what token cost — from the agent CLIs' own session logs. |
| [`resume <KEY> [--json]`](#resume--where-a-dead-session-stopped) | where a crashed or paused ticket stopped and the next move — **derived** from committed artifacts, never stored. |
| `doctor --migrate [--apply]` | rewrite legacy pre-vteam markers in existing ledgers and evidence. Dry-run by default. |

### `audit` — measure before you believe

Reads the repo (CI config, hooks, evidence trees, ledgers, anchored verdicts, selftests), writes **nothing**, scores six dimensions 0–100 and names the exact artifact each ❌ needs. The [transcript above](#what-it-actually-looks-like) shows 0→85 on a bare repo; this repository's own score went 62/C → **91/A** the day it adopted itself (PR #38 carries the before/after).

```console
$ npx vteam-harness audit --json | jq '.score, .grade'
91
"A"
```

### `init` — install, validated before the first byte

Reads your repo to derive `code_paths` (never invents them — an empty derivation is a loud warning, and the fence then **fails closed**), writes the config, the `.vteam/` gates with their manifest, the rendered workflows for your agent tools, the push fence and the CI gate. Re-running never clobbers your ledgers, and a repo with its own hooks keeps them — this repo's own fence survived its self-install untouched.

```console
$ npx vteam-harness init --yes --name Shop --key SHOP --profile node --tracker markdown
✓ code_paths derived from this repo: [src/] — review in vteam.config.yaml (the review fence watches ONLY these)
✓ git config core.hooksPath .githooks
✓ claude-code: 11 workflow files

vteam installed. Next steps:
  1. Review vteam.config.yaml (high-stakes paths/terms, code_paths, capacity).
  2. Tickets live in docs/backlog/*.md (markdown tracker — zero services).
  3. Run: npx vteam-harness doctor
  Then start a workday with /team in your agent tool.

  Heads-up: the pre-push fence is active from THIS commit on — even the commit
  that adds vteam reaches the protected branch through a PR, or one deliberate
  ALLOW_PUSH_MAIN=1 git push for this install commit only.
```

### `doctor` — prove the install

Reads everything init wrote and **runs the proof**: python present, config parses in all three parser languages, every manifest hash intact (files someone edited are *named*, not counted), hooks wired, then all 22 discovered selftests — each one feeds its gate a violating fixture and demands RED — then pings the tracker, git remote and hosting CLI for real. From this repository:

```console
$ npx vteam-harness doctor
✅ python3 available (Python 3.9.6)
✅ config parses (version 1)
✅ .vteam runtime complete
✅ manifest verified (55 framework-owned files intact)
✅ core.hooksPath = .githooks
✅ code_paths alive (src/, core/, bin/)
✅ model-routing snapshot fresh (2026-08-17)
✅ gate selftests green (22 discovered checks prove they can red)
  … (14 more green lines)
✅ gate selftests green (22 discovered checks prove they can red)
── preflight ──
✅ Tracker: backlog dir docs/backlog (1 tickets)
✅ Design: no design source configured
✅ Git: remote origin https://github.com/connorpham/vteam-harness.git
✅ Hooks: core.hooksPath = .githooks
✅ GitHub CLI: signed in (PRs possible)
⚠️  Database       no .vteam/db-check.sh declared — DB leg unchecked (declare one if the app needs a DB)
✅ Gate: driver installed (generic profile)
──────────────────────────────────────────
PREFLIGHT: GREEN — the ticket→design→code→git chain runs end-to-end
```

### `update` — refresh, without touching your files

Reads `.vteam/manifest.json` (the hashes of what the framework last wrote), overwrites **only** files that still match, parks the new version of anything you edited as `*.new` next to your copy. Ledgers and config are never candidates.

```console
$ npx vteam-harness update
✓ .vteam runtime refreshed
✓ doctrine refreshed in docs/team
✓ claude-code workflows re-rendered
update done — ledgers and config untouched.
```

### `board` — the read-only dashboard

Reads the same files everything else writes (tickets, ledger, evidence verdicts, decision queue) and serves one page on `127.0.0.1` — read-only **by construction**: GET `/` and GET `/api/state` are the only endpoints, so there is no write to secure.

```console
$ npx vteam-harness board
vteam board — read-only dashboard for /path/to/your-repo
  http://127.0.0.1:4177   (Ctrl-C stops it; --port <n> to move it)
```

### `graph` — the work graph, made visible

Reads `docs/backlog/*.md` (`blocked-by` edges), the plan, the ledger and the evidence verdicts; prints what can start now, what waits on what, and every incoherence — dangling edges, cycles, a Done ticket with no PASS. Always exits 0: it is the mirror, `graph_check.py` is the gate that fails. `--json` is byte-stable per commit (diffable), `--dot` renders with Graphviz. From this repository:

```console
$ npx vteam-harness graph
vteam graph — the implicit work graph, made visible · /Users/connorpham/Documents/vteam

  1 ticket · 0 edges · 0 ready · 0 blocked · 1 done    (commit b269435)

── READY — what a machine says can start now (0) ──
   read from: docs/backlog/<KEY>.md + docs/pm/plan.yaml + docs/pm/log.md + evd/<KEY>/REPORT.md
   nothing is startable: every open ticket is waiting on another (see BLOCKED and FINDINGS)

── BLOCKED — waiting on another ticket (0) ──
   read from: docs/backlog/<KEY>.md (`- blocked-by:` lines)
   nothing is blocked

── FINDINGS (0) ──
   ✅ no dangling blockers, no cycles, every Done ticket carries a PASS verdict

── SOURCES ──
   plan: docs/pm/plan.yaml has no sprint-N blocks yet

graph REPORTS, it never fails the build (always exit 0) — it is a mirror of the files above.
The gates that DO fail are dor_check.py (blocked-by not Done), schedule_check.py (plan) and evd_check.py (verdicts).
```

### `usage` — measured, not self-reported

The ledger's `tok ≈` is written by the agent that did the work. `usage` reads the **agent CLIs' own session logs** on this machine (Claude Code, Codex) for this project only: who ran which model, when, on which branch, at what token cost — counts only, never chat content. The cross-check flags what no self-report can dodge: a *done* ledger day with no recorded session, and a heavy AI day with no ledger row. This repository's real history:

```console
$ npx vteam-harness usage --since 2026-08-17
Measured AI usage — Connor Pham · this project · since 2026-08-17
(from local session logs: counts only — models, tokens, times. Never chat content.)

By model:
  claude-fable-5               3 sessions · in      4k · cache  279.7M · out    789k
  claude-haiku-4-5-20251001    1 sessions · in      10 · cache     24k · out     102

Daily (date × source × model):
  2026-08-17  claude claude-fable-5              1s   17msg · in      32 · out     47k
  2026-08-18  claude claude-fable-5              1s  187msg · in      3k · out    227k
  2026-08-18  claude claude-opus-5               1s   59msg · in     118 · out     74k
  2026-08-19  claude claude-fable-5              1s   81msg · in     162 · out     90k
  2026-08-21  claude claude-fable-5              3s   99msg · in     198 · out    126k
  2026-08-21  claude claude-haiku-4-5-20251001   1s    1msg · in      10 · out     102
  2026-08-21  claude claude-opus-5               1s   97msg · in     194 · out    103k
  2026-08-24  claude claude-fable-5              1s   78msg · in     156 · out     96k
  2026-08-24  claude claude-haiku-4-5-20251001   1s   33msg · in     268 · out     21k
  2026-08-24  claude claude-sonnet-5             1s    5msg · in      10 · out      6k

Sessions (last 4 of 4):
  2026-08-21 04:44  claude claude-haiku-4-5-20251001     0m ·    1msg · out    102 · feat/scale-round
  2026-08-21 04:43  claude claude-fable-5                0m ·    1msg · out    171 · feat/scale-round
  …
Ledger cross-check: claimed tok ≈ 1390k · measured in+out 804k
  ✅ every done day has a session, every heavy day has a ledger row
```

`--sync` writes the counts to `docs/pm/usage/<you>.md` — **one file per person**, so a team never merge-conflicts; commit it and `perf_report` puts every member's *claimed* number next to their *measured* one.

### `resume` — where a dead session stopped

Reads the artifacts that already have one owner each — the claim comment (against `team.claim_ttl_hours`), `feat|fix/<KEY>-*` branches, the tasksheet, the review dossier, the QA verdict, the ledger — and derives the furthest **proven** stage plus the one next dispatch. It stores nothing, so it cannot go stale or lie; run it twice, get the same answer. Against this repository's real ticket:

```console
$ npx vteam-harness resume VT-1
VT-1 — derived from committed artifacts (nothing stored, nothing to go stale)

  claim        ✅ 2026-08-24T04:20:00Z · chore/self-install  (PAST TTL)
  branch       — none matching *VT-1*
  tasksheet    —  evd/VT-1/dev/tasksheet.md
  review       —  evd/VT-1/dev/review.md
  qa verdict   ✅ PASS
  ledger       1 row(s), last: 2026-08-24 QA done

  STAGE  qa-verdict PASS
  NEXT   nothing to resume — QA passed. If the ticket is not Done yet, /qa V7.3b closes it.
```

A ticket that died mid-`/dev` instead answers `STAGE tasksheet written (/dev T1 done)` and tells the PM to re-dispatch `/dev`, which resumes the leftover branch instead of restarting — the recovery lane (`pm.md` P0.1c) runs this first.

---

## What you get out of it

**If you're a solo owner or founder:** the team works while you sleep, and your daily touchpoint is a 15-minute desk report — what got done with live evidence links, what needs you as batched questions with ready-made proposals and stated reversal costs, what's at risk in the next seven days. When the backlog drains you read one acceptance file and sign off in batches.

**If you're a developer:** you stop babysitting the agent. Underspecified tickets bounce back to analysis before you waste a session. Reviews come from fresh agents with empty context held to a written standard, so an approval without a "what I tried to break" list is invalid and a fabricated finding voids the whole card. Your PRs carry committed review dossiers anyone can audit months later.

**If you're leading a team of humans:** every ledger row names its **person** — `VTEAM_ACTOR` env or `git config user.name`, never invented — and with `team.size > 1` that column is a *gate*, not a convention (`log_check` goes red on an unattributed ledger; `doctor --migrate` upgrades old ones). `perf_report` then answers the questions a lead actually has: who did what, in which lanes, at what token cost, with **routing flags per person** — a dev running `frontier` without an approved escalation, a done row with no model recorded, a token outlier worth a look. And because everything above is self-reported, `vteam usage` adds the **measured** side: it reads the agent CLIs' own session logs on each member's machine (Claude Code, Codex), so the report can put *claimed* `tok ≈ 90k` next to *measured* 300k — plus two flags no self-report can fake its way past: a "done" day with **no recorded AI session**, and a heavy AI day with **no ledger row**. Each member syncs one file (`usage --sync`, conflict-free by construction); raw logs never leave their machine. Two people appending to the same ledger merge conflict-free (union merge, set up by init). One honesty note, stated in the report itself: vteam measures artifacts, tokens, models and session times — it never reads anyone's chat. Also: crashed sessions can't orphan tickets (claims carry timestamps and TTLs), and *"we're on schedule"* is a number a script computes.

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
- **One human owner plus agents is the most-tested shape.** `team.size > 1` now has real machinery — the mandatory Actor column, per-person reporting, conflict-free ledger merges, and a claim TTL that is a config knob (`team.claim_ttl_hours`) read by `vteam resume` — but the WIP limit is still doctrine prose the agents follow, not a gate; treat >1 as young.
- **Trackers are markdown, Jira and GitHub Issues.** Linear and Trello are not implemented.
- **The graph's edges come from `blocked-by` only.** `plan.yaml` has no `dependencies` field yet, so sprint-level ordering is not part of the graph — `vteam graph` computes the ready set from ticket blockers, not from a critical path.
- **An external review card proves its shape, not its author.** `graph_check`/`review_check` hold a card written by Codex to the same bar as one written by Claude, but no gate cross-checks the `MODEL:` stamp against your config — provenance rests on the committed trail, as it does for every card.
- **Evidence is committed to git.** If your screenshots would contain regulated or personal data, decide your policy before enabling the screenshot gates — a committed image is permanent.

---

## Status

Working, and the proof ships with it: `npm test` runs [tests/e2e.mjs](tests/e2e.mjs) — **141 checks** (the suite's own last check verifies this number against the run, so it cannot go stale again) plus a 15-fixture parser-conformance suite and a 10-row ledger-grammar fence (the Python, Node and shell config readers must agree byte-for-byte, the Python and Node ledger parsers row-for-row, and configs they must reject must die in all of them) covering fresh repo → `init` → **doctor green**, manifest-guarded `update`, invalid input writing nothing, the board's read-only fence, and the pre-push fence and secret scan actually going red. CI runs it on every push. Also dogfooded against a real project's artifacts: 500+ verbatim spec rows, a 41-row ledger and real review dossiers all pass the ported gates.

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
bin/, src/   the installer CLI (audit · init · doctor · update · board · graph · doctor --migrate)
tests/       the end-to-end suite behind every claim above
```

## Security

The same law as everything else here: a security claim without a machine check is a hope. **Zero runtime dependencies** (`npm ls --all` — empty tree), no network calls beyond the preflight pings you configure, a dashboard that is read-only *by construction*, a secret scan that **fails closed**, and releases published from CI with **npm provenance** (Sigstore) so the tarball is cryptographically tied to its commit. OpenSSF Scorecard re-grades the repo weekly (badge above), CodeQL scans every push. Reporting a vulnerability: [SECURITY.md](SECURITY.md). The full posture, control by control, each with the command that verifies it: [docs/security/](docs/security/README.md).

## License

MIT
