# vteam

[![npm](https://img.shields.io/npm/v/vteam-harness?color=%23C03B2B&label=npm)](https://www.npmjs.com/package/vteam-harness)
[![ci](https://github.com/connorpham/vteam-harness/actions/workflows/ci.yml/badge.svg)](https://github.com/connorpham/vteam-harness/actions/workflows/ci.yml)
[![node](https://img.shields.io/node/v/vteam-harness)](https://nodejs.org)
[![license](https://img.shields.io/npm/l/vteam-harness)](https://github.com/connorpham/vteam-harness/blob/main/LICENSE)
[![OpenSSF Scorecard](https://api.scorecard.dev/projects/github.com/connorpham/vteam-harness/badge)](https://scorecard.dev/viewer/?uri=github.com/connorpham/vteam-harness)
[![codeql](https://github.com/connorpham/vteam-harness/actions/workflows/codeql.yml/badge.svg)](https://github.com/connorpham/vteam-harness/actions/workflows/codeql.yml)

**Your AI agent says "done". vteam makes it prove it — and shows you the gap in ten seconds, before you install anything.**

```bash
npx vteam-harness audit        # grades this repo 0–100. No install, no writes, no network. Node only.
```

```console
  0/100 · grade F    (A ≥85 · B ≥70 · C ≥55 · D ≥35 · F <35)

GATES          0/20
   ❌ no CI pipeline — nothing can go red off this machine
   ❌ no test entrypoint (package.json test / pytest / Makefile / tests/)
HOOKS          0/15
   ❌ no active git hooks — a push leaves this machine completely unchecked
   ❌ no secret scan in hooks or CI — a leaked token sails through
EVIDENCE       0/20
   ❌ no evidence tree (evd/, docs/qa, …) — QA results die with the session
VERDICTS       0/15
   ❌ no mechanism ties an approval to a commit — every verdict is "trust me, it was this version"
SELF-PROOF     0/15
   ❌ no check can demonstrate it fails — green that cannot go red is decoration
```

Every ❌ is a claim an agent can make today without proof. That score is the whole product: six things a machine would need to see before it believes "done". Closing them is two commands.

## Install — two minutes

```bash
npx vteam-harness init --yes   # the team, the gates, the push fence — validated before the first byte is written
npx vteam-harness doctor       # every selftest (39 today) + provider preflight — GREEN, or it names what is missing
```

Then open your agent tool and type `/team` for a workday, or `/dev PROJ-12` for one ticket. Works with **Claude Code, Cursor, Windsurf, Codex, Copilot** — same gates, rendered for each. Needs git, Node ≥ 20, Python 3.9+ (`audit` needs only Node).

Claude Code can also install it as a plugin: `/plugin marketplace add connorpham/vteam-harness` · `/plugin install vteam@vteam-harness` · `/vteam:setup`.

## What changes on day one

<p align="center">
  <img src="https://raw.githubusercontent.com/connorpham/vteam-harness/main/docs/assets/fence-demo.svg" alt="A real terminal transcript: audit grades the repo F; after init, a push straight to main is refused, a push of product code without a committed review dossier is refused, and audit grades the repo A." width="860">
</p>

Three things, all real transcripts (no mockups — [more in the guide](docs/GUIDE.md#what-it-actually-looks-like)):

- **Done is an exit code.** A gate exits non-zero; the push is refused; the hatch that lets you through writes a line in a log. There is nothing to argue with.
- **A verdict dies when the code moves.** QA passed a ticket, one commit landed on top — the pass expired by itself and the ticket came back.
- **Every gate proves it can fail.** Each of the 35 checks ships a `--selftest` that feeds it a violating input and watches it go red. A gate that has never been red does not exist.

## Who it is for — and who it is not

- **A developer running one agent tool.** You stop babysitting: vague tickets bounce back before you burn a session, reviews come from a fresh context with a fixed card, and nothing reaches `main` without evidence you can open in a year.
- **A lead handing work to agents (or to people plus agents).** Every ledger row names its human, every verdict names its commit, every decision that needed you sits in one queue. `/team` runs the day; you read a 15-minute desk report.
- **Not for you (yet)** if your repo will not commit evidence and ledgers, if you want zero process, or if your app is a pnpm/Turborepo monorepo on the `nextjs-prisma` profile (workable, but by hand — see [known limits](docs/GUIDE.md#known-limits)).

## What ships

9 workflows (`/team /pm /ba /dev /qa /verify /docs /plan /guidelines`) · 18 gate steps that exit non-zero · 7 specialist agents · 31 competencies each ending in a reviewer lens · trackers: markdown (zero services), Jira, GitHub Issues · design: Figma · four read-only mirrors (`board`, `graph`, `usage`, `resume`) · cross-model review (a Codex or Gemini card held to the same bar) · parallel DEV in worktrees. All of it in [the guide](docs/GUIDE.md); the 15-minute hands-on version is [the tutorial](docs/TUTORIAL.md).

## Proof, not promises

- `npm test` runs [tests/e2e.mjs](tests/e2e.mjs) — **236 checks** (the suite's last check verifies this number against itself) plus a 17-fixture parser-conformance suite and a 10-row ledger-grammar fence. CI runs it on every push, on Linux and macOS.
- **It has been run on itself.** A line-by-line read of all 64 framework files (18,602 lines) on 2026-09-17 found 13 defects — including three gates the workflows named and no profile ran. Every fix carries a test that was red before it and a mutation probe that reds when it is reverted: [`evd/VT-24/dev/`](evd/VT-24/dev/), [`evd/VT-25/dev/`](evd/VT-25/dev/).
- **It has been run on a second repo.** A full `/team` day on a pnpm/Turborepo Next 15 + Prisma app — four tickets merged, four QA verdicts with challengers — and every gap that day found is a ticket here, not a footnote.
- **It was measured against BMAD** on one frozen login spec with a held-out 39-probe judge, and **lost: BMAD 100 %, vteam 92.3 %** (the three "contradicted" claims turned out to be probe defects, see the erratum; the speed findings stand).
 The scorecard, the repairs the judge needed and what changes because of it are in [docs/BENCHMARK.md](docs/BENCHMARK.md).
 [How it compares on the enforcement axis](docs/COMPARISON.md) is written up separately.

## Where things are

| | |
|---|---|
| [docs/GUIDE.md](docs/GUIDE.md) | everything: transcripts, workflows, gates, evidence pack, configuration, command reference, limits |
| [docs/TUTORIAL.md](docs/TUTORIAL.md) | the 15-minute tour — watch the gates go red, then green, in a scratch repo |
| [docs/COMPARISON.md](docs/COMPARISON.md) | BMAD · Spec Kit · OpenSpec · superpowers · Task Master · vteam — who verifies the work? |
| [CHANGELOG.md](CHANGELOG.md) · [docs/DESIGN.md](docs/DESIGN.md) · [docs/ROADMAP.md](docs/ROADMAP.md) | what changed, why it is built this way, what is next |
| [core/doctrine/provenance.md](core/doctrine/provenance.md) · [red-flags.md](core/doctrine/red-flags.md) | the incidents behind every rule, and the excuses agents use to route around gates |

## Status

Pre-1.0 — sharp edges are listed in [known limits](docs/GUIDE.md#known-limits), plainly. Published on npm as **`vteam-harness`** (the name `vteam` was blocked for similarity); the command is `vteam`. One human owner plus agents is the most-tested shape; `team.size > 1` and parallel DEV have real machinery and one live run each.

## Security

`init` and `update` write only under `.vteam/`, the rendered tool directories, `.githooks/`, `.github/workflows/vteam-gate.yml`, `docs/team/` and the ledgers — every framework-owned file is recorded in `.vteam/manifest.json` with its hash, and `update` never overwrites a file you changed. Gates read `.env` as inert text; nothing is ever `source`d. Report a vulnerability privately via [docs/security](docs/security/).

## License

MIT — see [LICENSE](LICENSE).
