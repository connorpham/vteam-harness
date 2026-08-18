# vteam

**Proof-of-done for AI agents.** Your agent can't say *done* anymore — it has to prove it.

One command puts a whole virtual AI team to work on your repository — a PM, a BA, an architect, a developer, and a QA that ship real tickets with real evidence, on any AI coding tool.

## 60-second start

```bash
npx vteam-harness audit    # grade this repo's AI-agent accountability 0-100 — no install, writes nothing
npx vteam-harness init     # close the gap: the team + 15 machine gates (Claude Code, Cursor, Windsurf, Codex, Copilot)
/team                      # then start a full "workday" in your agent tool
```

`audit` works on any repo, vteam or not: six dimensions (gates, hooks, evidence, review trail, verdicts, self-proof), a letter grade, and for every ❌ the exact artifact *a machine would need to see* to believe your agents. `--json` for scripts. It never writes, never phones home — and like every vteam check, it carries its own `--selftest` mutation proof.

Claude Code users can skip the terminal:

```
/plugin marketplace add connorpham/vteam-harness
/plugin install vteam@vteam-harness
/vteam:setup               # grades the repo, installs, verifies — showing real output at every step
```

vteam belongs to the same family as **BMAD Method, SpecKit, OpenSpec and Superpowers** — but it was not designed on a whiteboard. It was **extracted from a production harness that ran a real project autonomously**: 37+ merged PRs, 113+ confirmed review findings, 24/7 scheduled sessions, a single human owner spending ~15 minutes a day. Every rule in this framework exists because something specific broke without it.

---

## The problem it solves

AI agents are great at writing code and terrible at being **accountable** for it. Left alone, an agent will:

- say *"done"* with nothing to prove it,
- review its own work and approve it,
- invent an answer when the spec is silent,
- quietly skip the step that was inconvenient,
- and produce reports that read well but point at nothing.

Most frameworks solve the *"what to build"* side (specs, plans, task lists). **vteam solves the *"how a team of agents stays honest"* side** — and it does it with machinery, not prose:

| Principle | What it means in practice |
|---|---|
| **A gate that has never been red does not exist** | Every quality check ships with a *mutation self-test*: feed it a violating input, watch it fail, prove it works. An always-green check is deleted or fixed. |
| **Evidence that only lives in the session isn't evidence** | Screenshots, review cards, verdicts, decisions — everything durable goes to a committed file or the issue tracker. Every outward write is **read back** to confirm it landed. |
| **Autonomy is a ladder, not a switch** | `off` → `assisted` → `full`. Quality gates never relax at any level; only *wait-for-human* gates flip — with a documented, reversible, labelled paper trail. Real money, legal, credentials and data deletion are **never** auto-decided. |
| **One rule, one home** | Changing a rule means deleting the old sentence in the same commit. No framework rot, no two files disagreeing about the law. |
| **Agents don't chat** | One brief → one card → done. Briefs are file paths + scope, never pasted walls of text. Exactly one rebuttal round, and it must be paid for with runnable evidence. Your token bill stays sane. |

---

## Who verifies the work?

Every framework in this family tells the agent to be rigorous. The difference is what happens when it isn't:

| | They ship | vteam ships |
|---|---|---|
| **"Done"** | The agent's own claim, styled as a checklist | `gate.sh` exits non-zero until tests, evidence and review dossiers exist — *done* is an exit code, not a sentence |
| **Review** | A prompt asking the agent to review carefully | Committed review dossiers enforced at `git push`; every verdict pins the commit it examined and expires when the code moves |
| **The gates themselves** | Trust — nobody tests the checker | Every checking gate ships `--selftest`: feed it a violating input, watch it go red. A gate that has never been red does not exist |

The full receipts — tool by tool, with sources, star counts, and genuine credit where each one leads: **[docs/COMPARISON.md](docs/COMPARISON.md)**.

---

## What you get after `npx vteam-harness init`

### The team (7 workflows, rendered for YOUR tool)

| Command | Role | What it does |
|---|---|---|
| `/team` | Everyone | A full **workday**: clears your decision queue first, then works every unblocked item — dev tickets sequentially, BA drafts and architecture records in parallel background lanes, QA between dev tasks — until only *you* can move things forward. Ends with a one-page desk report. |
| `/pm` | Project manager | Reads the tracker + sprint plan + decision queue, picks the highest-value unblocked work, dispatches it, and funnels everything that needs a human into ONE table. Never invents answers. |
| `/ba` | Business analyst | Turns your spec into a runnable backlog: verbatim spec shards (byte-checked), user stories with *testable* Given/When/Then criteria, every gap becoming a structured question instead of a guess. Challenger-reviewed before tickets are filed. |
| `/dev` | Developer | Ticket → branch → minimal implementation → verification gate → **self-review with machine-measured design fidelity** → two fresh reviewer agents (three on high-stakes diffs) → PR → a 7-part plain-language report on the ticket. |
| `/qa` | QA engineer | Verify-only: derives expectations from the SPEC (never the ticket prose), runs 2–5 test cases headed in a real browser, collects annotated evidence, cross-checks every claim, gets a challenger sign-off, writes a report a non-programmer understands in 2 minutes. Never touches product code. |
| `/verify` | The gate | Lint → types → unit → build → reality checks → integration → e2e, in a fixed cheapest-first order. Skipped steps must declare why — silent skips are a failure. |
| `guidelines` | Method | Behavioral defaults that prevent classic LLM coding mistakes (think first, surgical diffs, red-first tests). |

### The machinery (15 gates that can actually fail)

Definition-of-Ready checks, review-dossier enforcement at `git push`, evidence validation (images must open, be readable, and **not be a blank/error page** — detected by pixel analysis), ledger schema checks, stale-verdict detection (*a verdict is valid only for the code it examined*), verbatim-spec guards, report-comment read-back, and secret scanning with **no** escape hatch that **fails closed** (no diff base → the full outgoing content is scanned). Every checking gate carries `--selftest` mutation proof — `doctor` runs all 17 (python, shell and node, context libraries included) — and the two live-environment gates (the pre-push fence and preflight) are driven to red for real by the e2e suite.

### The paper trail (your project's memory)

A decision queue (nothing needing you is ever scattered), a dispatch ledger (machine-checked, append-only), session minutes, an acceptance dossier (the ONE file you read to sign off), and a knowledge base with **graduation rules** — lessons don't accumulate, they turn into gates and then get deleted.

### Performance & cost management (who did what, on which model, at what price)

The ledger convention pays off because a machine reads it. `perf_report.py` turns it into answers:

- **Who did what** — per-lane items, outcomes, token totals and medians.
- **Was the model choice sane** — tier usage checked against the routing table, with flags: `frontier` used without an owner-approved escalation trail · a cheap lookup model doing DEV work · finished work with no model recorded. History written before vteam still reads (legacy model names are mapped; pre-adoption rows are grandfathered, never flagged unfairly).
- **Where the tokens went** — outliers >2× the median (usually extra review rounds), a monthly trend, and a rough cost band priced from the model data file — honestly labelled an estimate.

Flags land in every desk report; the full report is a mandatory input of the 14-day framework review — **routing changes get argued from this report, never from vibes**.

### Model routing that reaches your tool

Doctrine speaks in abstract tiers so it never rots (`frontier / workhorse / standard / utility` — expensive brains for expensive-if-wrong decisions, cheap brains for checklist work, and **never a downgrade at a quality gate**). One data file, `model-routing.data.yaml`, is the machine home: role→tier routing, high-stakes overrides (a diff touching money bumps the second reviewer up a tier), prices, and **the exact model name each tool wants**.

Every rendered workflow carries the resolved table for *its* tool — a Claude Code agent knows exactly what to pass as the subagent `model` parameter; Cursor/Windsurf users get "switch your model picker to X for this pass"; tools you haven't configured show a visible SET-ME banner instead of a silently wrong default. Runtime resolution:

```bash
python3 .vteam/scripts/model_route.py dev-r2 --tool claude-code                # → sonnet
python3 .vteam/scripts/model_route.py dev-r2 --tool claude-code --high-stakes # → opus
```

When providers change models or prices, you edit ONE data file and run `vteam update` — doctrine, workflows and reports all follow.

---

## What's in it for your project

**If you're a solo owner / founder:** the team runs while you sleep. Your daily touchpoint is a 15-minute desk report: what got done (with live evidence links), what needs you (batched questions with ready-made proposals and reversal costs), what's at risk in the next 7 days. When the backlog drains, you read one acceptance file and sign off in batches.

**If you're a developer:** you stop being the agent's babysitter. The DoR gate bounces underspecified tickets back to analysis before you waste a session. Reviews come from *fresh* agents with empty context, held to a written standard — an APPROVE without a "what I tried to break" list is invalid, and a fabricated finding voids the whole card. Your PRs carry committed review dossiers anyone can audit later.

**If you're a team:** work-in-progress is limited by design (one coding item at a time — Little's Law is enforced, not quoted), crashed sessions can't orphan tickets (claims have timestamps and TTLs), two sessions can't grab the same work, and the sprint plan is a structured file a script measures — *"we're on schedule"* is a computed number, never a hand-written sentence.

**If you care about cost:** token discipline is a first-class rule set. Model routing sends expensive models only to expensive-if-wrong decisions (architecture, money logic, first reviewer) and cheap models to checklist work — resolved to concrete model names per tool, not left as prose. The ledger records tokens and the tier per ticket, and `perf_report.py` turns that into per-lane spend, routing-violation flags, outliers and a cost estimate — so the routing gets tuned with data, and overspend has nowhere to hide.

---

## Works with your stack, not against it

Everything project-specific lives in **one config file** — the framework itself contains zero assumptions about your project (that's a standing rule: adaptation is configuration, never forking).

```yaml
# vteam.config.yaml (generated by init, edited by you)
project:  { name: My Project, key: PROJ, language: en }   # reports in en/vi/…
stack:    { profile: nextjs-prisma }        # or node / python / generic
tracker:  { provider: jira }                # or github / markdown (markdown = zero external services)
design:   { provider: figma }               # or none
autonomy: { level: assisted }               # off / assisted / full
review:   { high_stakes_paths: [...], high_stakes_terms: [wallet, refund] }
```

- **Agent tools:** Claude Code (native skills + subagents), Cursor, Windsurf, Codex, Copilot (with a documented sequential-review fallback for tools without subagents).
- **Trackers:** Jira (every Atlassian quirk handled: ADF, attachment read-back, link-direction verification), **GitHub Issues** (`PROJ-123` ⇄ issue `#123`; labels carry the status machine, every write is read back, and it's honest about what the API can't do — attachments stay in the committed evidence dir, named on the issue), or a **markdown backlog** — tickets as files, so the whole framework runs with *no external service at all*.
- **Design source:** Figma (fidelity measured in numbers against the design's own node data — expected values come from the design, never from your code, because *measuring code with code is self-grading*) or none.
- **Languages:** the framework speaks English internally; every owner-facing report speaks *your* language (`language: vi`, etc.). Machine-checked markers are locale-neutral sentinels, so gates work in any language.

```bash
npx vteam-harness doctor    # python3 check, config parse, manifest verify, hooks, 17 selftests, live provider pings
                            # --json for machine-readable {ok, checks}
npx vteam-harness update    # refresh framework files — .vteam/manifest.json makes "never touches
                            # your files" checkable: only hash-unmodified files are overwritten,
                            # anything you edited is kept (new version parked as *.new)
```

---

## How is this different from BMAD / SpecKit / OpenSpec / Superpowers?

Those frameworks are strongest at the **front** of the lifecycle: turning an idea into specs, plans and tasks. vteam borrows gratefully where they lead (a change-ledger idea from OpenSpec, a scale-adaptive light path from BMAD, brief-writing and red-first testing standards from Superpowers) — and adds the part none of them enforce:

> **the back of the lifecycle** — proof of done, adversarial review with teeth, evidence that survives the session, verdicts pinned to commits, autonomy with an audit trail, and a learning loop where every incident becomes a gate.

Use them together if you like: vteam doesn't care where your spec came from, only that once it exists, nothing ships without proving itself against it. The detailed, sourced comparison lives in [docs/COMPARISON.md](docs/COMPARISON.md).

---

## Status

Working and end-to-end tested — and the test ships in the repo: `npm test` runs [tests/e2e.mjs](tests/e2e.mjs) (fresh repo → init → **doctor green**, manifest-guarded update, invalid input writes nothing, the pre-push fence and secret scan actually go red), wired to CI on every push. Also dogfooded against the source project's real artifacts: 500+ verbatim spec rows, a 41-row ledger and real review dossiers all pass the ported gates. Published as `vteam-harness` (npm blocked the name `vteam` for similarity; the command is still `vteam`). Pre-1.0: expect sharp edges. The GitHub Issues tracker provider shipped with the proof-of-done campaign; Linear and deeper multi-human team support are next.

- Architecture & design decisions: [docs/DESIGN.md](docs/DESIGN.md)
- Build history & roadmap: [docs/ROADMAP.md](docs/ROADMAP.md)
- The incidents behind the rules: [core/doctrine/provenance.md](core/doctrine/provenance.md)

## Layout

```
core/        tool-agnostic source: doctrine, workflows, gates, templates, locales
adapters/    one renderer module per tool (claude-code, cursor, windsurf, codex, copilot) — see adapters/README.md to add yours
profiles/    stack profiles for the verification gate (nextjs-prisma, node, python, generic)
providers/   tracker + design-source adapters (jira, github, markdown / figma, none)
plugins/     the Claude Code plugin (/plugin marketplace add connorpham/vteam-harness)
bin/, src/   the npx installer CLI (audit · init · doctor · update · doctor --migrate)
```

## License

MIT
