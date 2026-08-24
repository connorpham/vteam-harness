# OpenSSF Best Practices badge — the complete answer sheet (passing level)

Owner: sign in at <https://www.bestpractices.dev> with GitHub → *Add project* →
`https://github.com/connorpham/vteam-harness`. Answer the questionnaire with
the rows below; each answer names its evidence so the entry survives an audit.
Statuses: **Met** unless stated. When done, copy the badge markdown from your
project page into README.md.

## Basics

| Criterion | Answer | Evidence |
|---|---|---|
| Project website | Met | https://github.com/connorpham/vteam-harness (README is the site) |
| Description of what it does | Met | README first screen: proof-of-done harness, 14 machine gates |
| How to obtain / provide feedback / contribute | Met | npm install line in README; GitHub issues; PRs via branch+fence workflow described in README |
| FLOSS license | Met | MIT — `LICENSE` at repo root, `license` field in package.json |
| License posted in standard location | Met | `/LICENSE` |
| Basic documentation | Met | README (per-command, end-to-end with transcripts), docs/TUTORIAL.md, docs/DESIGN.md, docs/ROADMAP.md |
| HTTPS for all project sites | Met | github.com + npmjs.com only |
| Discussion mechanism | Met | GitHub issues/PRs |
| English documentation | Met | all docs are English |
| Maintained | Met | commit history; ledger `docs/pm/log.md` shows dated releases |

## Change control

| Criterion | Answer | Evidence |
|---|---|---|
| Public version-controlled source repo | Met | GitHub, full history |
| Unique version numbering | Met | semver in package.json; every npm release immutable |
| Release notes | Met | PR descriptions per release + `docs/ROADMAP.md` phase log; ledger rows date each release |
| Interim versions available for review | Met | every change lands as a PR before merge (repo's own pre-push fence forbids direct pushes to main) |

## Reporting

| Criterion | Answer | Evidence |
|---|---|---|
| Bug reporting process | Met | GitHub issues |
| Vulnerability reporting process | Met | `SECURITY.md` — GitHub private vulnerability reporting, URL given |
| Vulnerability response ≤ 14 days | Met | SLOs stated in SECURITY.md (ack 3d, assess 7d, fix/mitigate 14d) |
| Bug reports acknowledged/archived | Met | GitHub issues history is public and permanent |

## Quality

| Criterion | Answer | Evidence |
|---|---|---|
| Working build system | N/A (justify) | pure interpreted JS/Python CLI — no build step exists; `files:` in package.json ships sources verbatim |
| Automated test suite | Met | `npm test`: 141 e2e checks + 15 parser-conformance fixtures + 10 ledger-grammar fence rows; CI on Node 20 & 22 |
| New functionality adds tests | Met | policy enforced in practice — recent PRs #34–#39 each added e2e sections/selftests; the suite's last check even verifies the README's stated test count |
| Warning flags enabled | Met | `set -euo pipefail` in shell, strict argparse in Python, ESM strict mode in Node; CodeQL runs as the linter of record |
| Tests invoked by continuous integration | Met | `.github/workflows/ci.yml` on every push/PR |

## Security

| Criterion | Answer | Evidence |
|---|---|---|
| Secure development knowledge | Met | maintainer statement; the project's own doctrine (`core/doctrine/ops.md`, TRUST BOUNDARY notes in gate configs) documents the threat model of repo-write = execute |
| Basic good cryptographic practices | N/A (justify) | the project implements NO cryptography; hashing for the manifest uses Node's crypto (SHA-256) only for change detection |
| Secured delivery mechanism | Met | npm over HTTPS; releases published from CI with npm provenance (Sigstore) — `.github/workflows/release.yml` |
| No unpatched vulnerabilities of medium+ severity | Met | zero dependencies; CodeQL + Scorecard green; no open advisories |
| No leaked credentials | Met | pre-push secret scan (fails closed) + `.gitignore` on `.env`; e2e proves a planted token blocks the push |
| Input validation | Met | `init` validates every flag before writing a byte (e2e §6); config parsers reject malformed YAML identically in 3 languages (conformance suite) |
| Memory-safe languages | Met | JavaScript + Python only |

## Analysis

| Criterion | Answer | Evidence |
|---|---|---|
| Static code analysis | Met | CodeQL (JS + Python), every push + weekly — `.github/workflows/codeql.yml` |
| Dynamic analysis | Met | the e2e suite IS dynamic analysis: it installs into fresh repos and exercises every command and failure path (141 checks), including hostile fixtures (torn JSONL, malformed configs, planted secrets) |
| Fix vulnerabilities found by analysis | Met | policy in SECURITY.md; CodeQL alerts triaged via the Security tab |

## Notes for the two commonly-questioned rows

- **"Working build system — N/A"**: bestpractices.dev accepts N/A with
  justification; an interpreted zero-build CLI is the textbook case.
- **"Crypto — N/A"**: same; do not claim Met for crypto you do not implement.
