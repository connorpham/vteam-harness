# Security policy

vteam is a CLI that writes files into your repository and runs local checks.
It is **zero-dependency by doctrine** (Node built-ins and Python stdlib only —
`npm ls --all` shows an empty tree), makes **no network calls** except the
preflight pings you configure (your tracker, your git remote), and its
dashboard binds to `127.0.0.1` with **no write endpoint at all**.

## Supported versions

| Version | Supported |
|---|---|
| latest minor on npm | ✅ fixes land here |
| anything older | ⬆️ upgrade — `npm i -g vteam-harness@latest`, then `npx vteam-harness update` in each repo |

## Reporting a vulnerability

**Please do not open a public issue for a vulnerability.**

Use GitHub's private vulnerability reporting:
**[Report a vulnerability](https://github.com/connorpham/vteam-harness/security/advisories/new)** —
it opens a private thread between you and the maintainer.

What to expect (working days):

- **Acknowledgement within 3 days.**
- **Assessment within 7 days** — severity, affected versions, and whether we
  agree it is exploitable, with reasoning either way.
- **Fix or documented mitigation within 14 days** for confirmed reports, a
  patched release on npm, and credit in the advisory unless you prefer none.

## Scope — what counts as a vulnerability here

- Anything that makes a **gate pass when it should fail** (the product IS the
  refusal — a bypass of `evd_check`, the push fence, the secret scan, or the
  manifest guard is a security bug, not a nuisance).
- Command injection through config values, ticket titles, file names or any
  other repo-controlled input reaching a shell.
- The board serving anything writable, binding beyond loopback, or leaking
  file contents outside the repo root.
- `init`/`update` writing outside the target repository, or following
  symlinks out of it.
- Secrets handled wrongly: tokens logged, written to tracked files, or the
  pre-push secret scan being escapable.

Out of scope: vulnerabilities in the AI agent tools vteam orchestrates
(report those to their vendors), and findings that require the attacker to
already have write access to the repository (repo write access = shell
access by design; the gates' TRUST BOUNDARY notes state this).

## What the project itself runs

- CI on every push: the full test suite (141 e2e checks, parser-conformance
  fences) on Node 20 and 22, plus the repo's own gate pipeline.
- CodeQL static analysis (JavaScript + Python) and OpenSSF Scorecard, both on
  every push to `main` and weekly.
- The pre-push fence scans every outgoing diff for token patterns and **fails
  closed** when it cannot compute a diff base.
- Releases are published from CI with **npm provenance** (Sigstore), so the
  npm page cryptographically links each tarball to the exact commit and
  workflow that built it.
