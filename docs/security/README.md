# Security posture — what is machine-verified, and how to check it yourself

vteam's security story follows the project's one law: **a claim without a
machine check is a hope.** This file lists every security control, who
enforces it, and the command or URL that proves it right now.

## The certifications this package carries (or is registered for)

| Credential | What it proves | Where to verify |
|---|---|---|
| **npm provenance** (Sigstore/SLSA) | every release tarball is cryptographically linked to the exact commit + CI workflow that built it — nobody published from a laptop | the **Provenance** section on <https://www.npmjs.com/package/vteam-harness> (from the first release published by `.github/workflows/release.yml`) |
| **OpenSSF Scorecard** | 18 automated supply-chain checks, re-scored weekly, results signed and published | <https://scorecard.dev/viewer/?uri=github.com/connorpham/vteam-harness> |
| **CodeQL** | static analysis (JS + Python) on every push and weekly | the repo's Security → Code scanning tab |
| **OpenSSF Best Practices badge** | the bestpractices.dev criteria, self-certified with evidence | owner registration required — the complete answer sheet is [openssf-best-practices.md](openssf-best-practices.md) |

## Controls in the code itself (each with its proof)

| Control | Proof |
|---|---|
| **Zero runtime dependencies** — no install scripts, no transitive tree, nothing to typosquat | `npm ls --all` on an install → empty tree; `package.json` has no `dependencies` key |
| **No network calls** except configured preflight pings | grep the source: the only `fetch`/socket use is the board's loopback server and provider pings the adopter configures |
| **Board is read-only by construction** | `board.mjs` serves GET `/` and GET `/api/state` on `127.0.0.1` only — there is no write endpoint to secure; e2e asserts it |
| **Secret scan fails closed** | `.githooks/pre-push`: no diff base → scans the FULL outgoing content; e2e section 10 proves a planted `ghp_` token blocks the push |
| **Install validated before the first byte** | invalid `init` input exits 1 having written nothing — e2e section 6 |
| **Update cannot clobber user files** | `.vteam/manifest.json` hash guard; edited files are kept and the new version parked as `*.new` — e2e section 5, and this repo's own fence survived its self-install exactly this way |
| **Every gate proves it can fail** | 22 discovered `--selftest`s feed each gate a violating fixture and demand RED — `npx vteam-harness doctor` runs them all |
| **CI least privilege + pinned actions** | every workflow declares `permissions: contents: read` (plus per-job grants) and pins actions by full SHA, refreshed by Dependabot |

## Reporting

See [SECURITY.md](../../SECURITY.md) — private vulnerability reporting is
enabled on the repository; response SLOs are stated there.

## Owner runbook — one-time actions (each is one command or one form)

0. **Two repo settings** (API mutations only the owner should fire):

   ```bash
   # accept private vulnerability reports (the SECURITY.md link goes live)
   gh api -X PUT repos/connorpham/vteam-harness/private-vulnerability-reporting

   # server-side branch protection: PRs must pass e2e + gate before merging
   # (the local fence already forbids direct pushes; this makes it server-truth)
   gh api -X PUT repos/connorpham/vteam-harness/branches/main/protection \
     --input - <<'EOF'
   {"required_status_checks":{"strict":false,"contexts":["e2e (20)","e2e (22)","gate"]},
    "enforce_admins":false,"required_pull_request_reviews":null,"restrictions":null}
   EOF
   ```


1. **npm Trusted Publishing** (turns on the Provenance badge):
   npmjs.com → package `vteam-harness` → Settings → *Trusted Publisher* →
   GitHub Actions · repository `connorpham/vteam-harness` · workflow
   `release.yml`. From then on: draft a GitHub release on the version tag —
   CI publishes with `--provenance`; no token exists to leak, and the
   prepublish guard still runs inside the job.
2. **OpenSSF Best Practices badge**: sign in at
   <https://www.bestpractices.dev> with GitHub, add the project, and answer
   the questionnaire from [openssf-best-practices.md](openssf-best-practices.md)
   — every answer there is pre-written with its evidence link. Then put the
   badge markdown (shown on your project page) into README.md next to the
   Scorecard badge.
