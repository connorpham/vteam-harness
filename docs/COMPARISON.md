# BMAD vs Spec Kit vs OpenSpec vs Superpowers vs Task Master vs vteam: who verifies the work?

Every comparison of AI-agent development frameworks asks the same questions — spec
format, tool coverage, install friction, star count. None of them asks the question
that decides whether the code is actually done: **when the agent claims "done", what
happens if it's lying?**

This document compares on that axis. It tries hard to be fair: every framework here
does something genuinely well, vteam borrows from several of them (and says so), and
vteam's own limits are listed at the bottom with the same bluntness. All star counts
and download numbers were verified against the GitHub/npm/PyPI APIs on **2026-08-18**;
every criticism of a tool links to that tool's own issue tracker, docs, or a named
third-party review.

---

## The enforcement axis

There are three ways a framework can "enforce" its process, and they are not the same:

1. **Prompted** — the agent is *told* to be rigorous ("you MUST write tests",
   "review adversarially"). Compliance is whatever the agent self-reports. This is
   where most of the category lives.
2. **Structurally validated** — a script checks that artifacts have the right
   *shape*: the spec file exists, the markdown has the right headers, the task graph
   has no cycles. Real machinery — but it validates the paperwork, not the work.
3. **Machine-failed** — a script runs against the *work itself* and exits non-zero
   when the claim doesn't hold: the tests didn't run, the evidence file doesn't
   exist, the approval points at a commit that has since changed. Nothing proceeds
   until it's green, and bypasses leave a paper trail.

One more level matters, and almost nobody talks about it: **who checks the checker?**
A gate that has never been red is indistinguishable from a gate that doesn't work.
(vteam learned this the hard way — its source harness shipped two always-green gates
without noticing. See [provenance](../core/doctrine/provenance.md).) The honest
version of level 3 is a gate that ships with a *mutation proof*: feed it a violating
input, watch it fail, in the same PR that ships it.

With that vocabulary, here is the field.

---

## The tools, honestly

### BMAD Method — the planning heavyweight

[github.com/bmad-code-org/BMAD-METHOD](https://github.com/bmad-code-org/BMAD-METHOD) —
52,003 stars / 5,938 forks (2026-08-18) · npm `bmad-method` 18,523 downloads for the
week 2026-08-09→15 · latest v6.11.0

**What it's genuinely great at:** the front of the lifecycle. Idea → brief → PRD →
architecture → context-rich stories is BMAD's core value and nothing else in the
category does it as thoroughly. Scale-adaptive planning (right-sizing ceremony from
weekend prototype to enterprise brownfield) is a real answer to "too much process".
Its Test Architect module (TEA) has the best *vocabulary* for quality decisions in
the category — PASS / CONCERNS / FAIL / WAIVED is memorable, human language. 42
supported agent platforms is the broadest reach anywhere. And its v6.11 changelog
("skills read evidence instead of guessing") shows its instincts pointing the right
way.

**Where the enforcement axis finds it:** those TEA gate decisions are markdown
produced by agent self-evaluation — the official TEA docs show no CI script, exit
code, or blocking mechanism anywhere. Nothing fails red when the process is violated.
BMAD's own issue tracker states it plainly:
[issue #2003](https://github.com/bmad-code-org/BMAD-METHOD/issues/2003) — *"there is
no safety mechanism (safeguard) that forces the developer agent to reread the
original code, understand the real nature of the problem, or verify that the fix is
actually effective"* — with documented cases of agents checking off tasks via renamed
commands, useless assertions, and TODO stubs, and the summary claim that BMAD
*"lack[s] the necessary quality controls (safeguards) to prevent development agents
from bypassing the controls themselves."* Its one hard review rule — a prompted
"minimum 3 issues per review" — backfires into nitpick-manufacturing and endless
review cycles ([issue #1332](https://github.com/bmad-code-org/BMAD-METHOD/issues/1332)).
Prompt rules don't just fail to bind; when they're rigid, they distort.

### GitHub Spec Kit — the category's distribution king

[github.com/github/spec-kit](https://github.com/github/spec-kit) — 129,868 stars /
11,626 forks (2026-08-18) · PyPI `specify-cli` 94,973 downloads/month

**What it's genuinely great at:** reach and legitimacy. It coined "spec-driven
development" into common usage, ships under the github/ org with Microsoft Learn
training behind it, and supports 30+ agent integrations with bash/PowerShell/Python
parity. The *constitution* pattern (one non-negotiable principles file injected into
every downstream command) is a genuinely good idea, and `/speckit.taskstoissues`
(plan → GitHub issues in one command) is the kind of pragmatic bridge the category
needs more of.

**Where the enforcement axis finds it:** the only scripts that can fail check that
artifact *files exist* (`check-prerequisites.sh` — existence, not content).
`/speckit.analyze` is declared "STRICTLY READ-ONLY"; constitution violations get an
LLM-assigned "CRITICAL" label in a report, and nothing exits non-zero.
`/speckit.converge` "assesses" code against spec via LLM judgment — it never runs
tests, never diffs, never blocks. Wavect's production review says it outright:
*"Crucially: no machine verification exists. The review process remains entirely
human-dependent."* And the repo's top discussion,
[#1784](https://github.com/github/spec-kit/discussions/1784), calls the result the
*"illusion of work"* — kilobytes of generated instructions that drown the agent in
its own documentation. The spec chain is excellent; nothing checks the code kept its
promises.

### OpenSpec — the lightweight change manager

[github.com/Fission-AI/OpenSpec](https://github.com/Fission-AI/OpenSpec) — 65,242
stars / 4,497 forks (2026-08-18) · npm `@fission-ai/openspec` 261,760 downloads/week,
1,417,163/month · YC W26

**What it's genuinely great at:** being light and honest about scope. Sub-1-minute
setup, plain markdown, no API keys. Delta specs merged into living specs is real
change management — nobody else maintains a spec-of-record over time. `--json` on
every CLI command turns the tool into a proper state API for agents (a pattern worth
copying, and vteam did: `audit --json`, `doctor --json`). Even its upgrade check is
honest — it asks the installed binary its version instead of trusting npm's exit
code.

**Where the enforcement axis finds it:** level 2, deliberately. `openspec validate`
checks markdown structure — requirement headers, SHALL/MUST placement, scenario
blocks. "DONE" state means *the file exists*. Config errors "generate warnings"
rather than blocking; `/opsx:verify` is an agent instruction, not a script. A
hands-on review (ypyl.github.io, June 2026) found *"zero references to OpenSpec
enforcing constraints, blocking invalid specs, or preventing downstream errors."*
OpenSpec validates the shape of the plan better than anyone. Everything after
`tasks.md` is trust-the-agent.

### Superpowers — the best prose in the business

[github.com/obra/superpowers](https://github.com/obra/superpowers) — 273,275 stars /
24,448 forks (2026-08-18) · v6.3.0 (2026-08-12) · in Anthropic's, OpenAI's and xAI's
official plugin marketplaces

**What it's genuinely great at:** methodology craft. The skills are the most
carefully engineered prompts in the category — pressure-tested against persuasion
scenarios, regression-tested in a public eval harness, refined across named major
versions. RED-GREEN-REFACTOR TDD, plans written for "an enthusiastic junior engineer
with poor taste" (a bar vteam's brief-writing credits by name), and the SessionStart
hook that re-injects the methodology after `/clear` and compaction — cheap machinery
that solves a real failure mode, and which vteam's own installer now imitates. Its
"Red Flags" table enumerating the exact rationalizations agents use to skip process
directly inspired vteam's [red-flags doctrine](../core/doctrine/red-flags.md).

**Where the enforcement axis finds it:** everything is level 1 — by admission. The
launch post documents that subagents *"would skip the gates under pressure"*, and
the fix was stronger wording, not machinery. "Critical issues block progress" means
the orchestrating agent is *told* not to proceed. Review verdicts live in chat
context; nothing is pinned to commits; the human can verbally waive any workflow
with no record of the waiver. The eval harness that machine-tests things tests the
*vendor's skill wording*, in the vendor's repo — nothing runs in yours. It is the
strongest possible version of the prompted approach, which makes it the clearest
demonstration of the ceiling.

### Task Master — the task graph that trusts the agent

[github.com/eyaltoledano/claude-task-master](https://github.com/eyaltoledano/claude-task-master)
— 28,004 stars / 2,627 forks (2026-08-18) · npm `task-master-ai` 13,334
downloads/week, down from a 276,211/month peak in Dec 2025 · last push 2026-04-28

**What it's genuinely great at:** PRD → dependency-aware task backlog, and `next` —
a deterministic "what should the agent do now" oracle. That single-entry-point
pattern is exactly right for driving agents, and the one-click Cursor/MCP install paths
set the category's bar for time-to-first-value.

**Where the enforcement axis finds it:** this one is instructive, because Task
Master *built* level-3-shaped machinery and then didn't connect it to reality. Its
`autopilot` has a real RED/GREEN/COMMIT state machine with a TestResultValidator
(RED requires ≥1 failing test, GREEN requires 0) — but the test results arrive as
**agent-supplied JSON** (`autopilot complete --results '{"total":10,"passed":9,...}'`),
and the validator checks only that the arithmetic is consistent. It never executes
the suite. A fabricated result passes the gate. Likewise `loop` completion is a
regex matching the agent's own `<loop-complete>` marker, and `set-status done` is a
claim, not a proof. The shape of verification without the substance is arguably more
dangerous than no verification: it *looks* audited. (The OSS is also effectively
frozen — no push since April 2026 — as the team's energy moved to the commercial
Hamster workspace.)

### Also on the map

- **Agent OS** (5,289 stars, 2026-08-18; last push 2026-05-05) deserves a note for
  intellectual honesty: v3 (Jan 2026) deliberately **retired** its implementation,
  orchestration, and verification phases, betting that frontier models plus Plan
  Mode handle execution. Its `/discover-standards` (reverse-engineering a codebase's
  real conventions into persistent files) is a great onboarding idea. But the
  retreat means the back of the lifecycle isn't just unenforced — it's explicitly
  out of scope.
- **Ruflo** (formerly Claude Flow; 68.1k stars, 2026-08-18) is the one tool here
  that ships real cryptographic verification — of *itself*. `ruflo verify` checks
  Ed25519-signed witness manifests proving your installed bytes match the audited
  release: genuine supply-chain integrity, worth stealing. But as sublimecoding's
  May 2026 deep dive puts it, *"the only substantive verification mechanism is
  Ed25519-signed release manifests… security plugins operate at the prompt/guard-rail
  level, not as machine-verifiable proofs."* It proves the tool is untampered; it
  never proves your code is done.

---

## The verification table

"Machine-fails" means: a script exits non-zero against the work itself, and the
failure blocks progress. Assessed from each tool's own docs, source, and issue
tracker (links above), 2026-08-18.

| | What actually machine-fails | What is prompt- or report-only | Is the checker itself tested? |
|---|---|---|---|
| **BMAD** | Installer dependency checks (Node/Python versions) | TEA gate decisions (PASS/CONCERNS/FAIL/WAIVED), review scores, "minimum 3 issues", the entire dev loop ([#2003](https://github.com/bmad-code-org/BMAD-METHOD/issues/2003)) | No |
| **Spec Kit** | Artifact-file *existence* (`check-prerequisites`), CLI arg validation | analyze / checklist / converge verdicts, constitution "CRITICAL" labels, hook execution | No |
| **OpenSpec** | Markdown structure of specs (`openspec validate`), workflow-schema shape | `/opsx:verify`, code-vs-spec conformance, "DONE" (= file exists) | No |
| **Superpowers** | Nothing in your repo (SessionStart hook re-injects prose; vendor evals test skill wording in the vendor's repo) | TDD, review verdicts, "verification before completion", blocking on critical issues | Vendor-side only |
| **Task Master** | tasks.json graph integrity (cycles, dangling refs); arithmetic consistency of *agent-supplied* test JSON | Whether tests actually ran; loop completion (regex on the agent's own marker); `set-status done` | No |
| **Agent OS** | Nothing (bash installers only; v3 retired verification by design) | Standards compliance, spec adherence | No |
| **Ruflo** | Its own supply chain (Ed25519 witness manifests); federation PII blocking | Reviewer agents, consensus votes, SPARC "quality gates", merge checklist | Tool integrity yes; work gates n/a |
| **vteam** | 13 checking gates: review dossiers at `git push`, evidence files (images must open and not be blank — pixel-checked), ledger schema + append-only shape, verdicts pinned to commits with staleness re-queue, verbatim spec shards (byte-checked), DoR, report comments read back from the tracker, fail-closed secret scan, docs-shrink guard | Card *content* truth (the machine checks card form; the standard says so honestly — content rests on the committed trail and QA's independent re-run) | **Yes — every checking gate ships `--selftest` mutation proof; `doctor` discovers and runs every selftest (19 today)** |

The last column is the one vteam considers non-negotiable, and the one nobody else
fills: a gate you've never seen red is a decoration.

---

## Where vteam fits — including what it isn't

vteam is not a planning framework, and using it does not mean abandoning the tools
above. Its position is the **back of the lifecycle**: once a spec exists — from
BMAD's PRD chain, Spec Kit's `/speckit.specify`, OpenSpec's change folders, or a
markdown file you wrote by hand — nothing ships without proving itself against it.
Machine DoR before work starts, adversarial review with committed dossiers enforced
at push, evidence files a gate validates, verdicts that expire when the code moves,
and a `--selftest` on every one of those checks. It composes *with* the front-of-
lifecycle tools; it competes with the assumption that prompting is enough.

**Now the other side of the ledger.** In the spirit of the table above:

- **It's young.** Pre-1.0 (`vteam-harness@0.2.0`), one production project of
  provenance, a tiny community next to the six-figure star counts above. Every rule
  was extracted from real incidents — but from *one* harness's incidents.
- **Solo-owner sweet spot.** The design center is one human owner with a virtual
  team. Multi-human teams get best-effort support (`team.size > 1`), not the
  first-class treatment BMAD and Spec Kit aim at organizations.
- **Tracker coverage is Jira, GitHub Issues, and markdown.** No Linear. GitHub's
  provider is honest about API limits (no file attachments — the committed evidence
  dir is the attachment of record), which also means: not every tracker feature
  everywhere.
- **Evidence capture is web-only** (headed Playwright). Mobile/desktop capture is an
  open interface, not a shipped feature.
- **The gates check what machines can check.** Card form, file existence and
  content shape, pixel-level blank detection, commit pinning. A sufficiently
  determined agent colluding with a careless human can still merge bad work — vteam
  narrows that path and logs every escape hatch (`ALLOW_PUSH_*` uses append to a
  hatch log; the secret scan has no hatch at all), it does not eliminate judgment.

If you want the best planning artifacts in the business, start with BMAD or Spec
Kit. If you want the lightest spec-of-record loop, OpenSpec. If you want the finest
prompted methodology, Superpowers. **If you want the moment your agent says "done"
to be a machine's verdict instead of the agent's — that is the one job vteam exists
to do.**

---

*Numbers verified 2026-08-18 against the GitHub, npm, and PyPI APIs. Quotes link to
their sources inline. Corrections welcome — file an issue; this page holds itself to
the same standard it measures others by.*
