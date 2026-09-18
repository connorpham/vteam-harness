# vteam vs BMAD — one frozen login spec, one held-out judge

**Result, scored 2026-09-17: BMAD 100 %, vteam 92.3 %. vteam lost, and three of its "done"
claims were contradicted by the judge.** One run, one sample, published as promised whichever
way it went. Full scorecard: [docs/benchmark/2026-09-03/SCORECARD.md](benchmark/2026-09-03/SCORECARD.md).
Every repair made to the judge before scoring, and why: [JUDGE-REPAIRS.md](benchmark/2026-09-03/JUDGE-REPAIRS.md).

## Setup

Same spec (`SPEC-LOGIN.md`, sha256 `2e310e67…`, 39 acceptance criteria, weight 91), same Next 16 +
Prisma 6 + SQLite scaffold, same agent (Claude Code, Claude Opus 5), same single opening prompt,
no human input after it. The only variable is the framework installed in the repo. A held-out
judge of 39 black-box Playwright probes was written before either arm ran, calibrated to 0 % on
the empty scaffold and 100 % on a reference solution, and re-calibrated to 100 % after the one
probe repair made on scoring day (J3 below).

## Headline

| Metric | arm-a · vteam | arm-b · BMAD 6.11 |
|---|---|---|
| **AC coverage (weighted)** | **84 / 91 = 92.3 %** | **91 / 91 = 100 %** |
| Criteria passed | 36 / 39 | 39 / 39 |
| Own verification green at stop (lint · types · unit · build) | **no** — unit suite red | yes |
| Claims contradicted by a probe | **3** (weight 7) | 0 |
| Claim accuracy | 92.1 % | 100 % |
| Mutation score (unit + typecheck, 5 planted bugs) | skipped — unit suite already red | 4 / 5 |
| Commits after the framework-install commit | 25 (+1 operator commit, see below) | 11 |
| Commit span | 09-03 12:28 → 09-04 16:33, with a 21 h gap and no commits in it | 09-03 12:28 → 14:56 (2 h 28 min) |
| Time to first feature commit | 4 h 29 min (2 h 05 min of it before the backlog existed) | 1 h 44 min |
| Diff vs baseline | 114 files, +13 667 / −72 | 52 files, +6 850 / −61 |
| Test files written | 20 | 13 |
| Tokens / active minutes | not recorded | not recorded |

### Coverage by spec area

| Area | vteam | BMAD |
|---|---|---|
| 4.A Core login | 26 / 28 | 28 / 28 |
| 4.B Security (rate limit, lockout, CSRF, fixation, enumeration, timing, redirect) | 24 / 24 | 24 / 24 |
| 4.C Forgot / reset password | 21 / 21 | 21 / 21 |
| 4.D A11y · responsive · dark mode | 13 / 18 | 18 / 18 |

## What vteam failed — and had claimed

All three failures were declared **done** in the arm's `CLAIMS.md`, each pointing at one of its own
end-to-end tests as evidence. The judge, running the production build, disagreed:

| AC | W | Requirement | Judge's error |
|---|---|---|---|
| AC-A07 | 2 | client-side validation shows an inline field error and sends no request | `expect(locator).toBeVisible() failed` — no `[role=alert] / [aria-live] / [data-error]` appeared |
| AC-D02 | 3 | every error linked via `aria-describedby` and announced by a live region | `no live region announces the error` |
| AC-D07 | 2 | dark mode uses only the §6 tokens, no colour literal in own CSS | `colour literals outside globals.css: app/auth.css:8, :164–167` |

This is the exact failure vteam exists to prevent: a claim of done that the work does not support.
Why the arm's own e2e tests passed while the probes fail has **not been investigated yet** — that
is VT-28, and the answer will be published here whether it points at the arm, the framework or
the probe's reading of the spec.

## How the two runs went

- **vteam (arm-a)** spent its first 2 h 05 min wiring the framework to the repo and sharding the
  spec into a backlog (three challenger rounds on the backlog draft), and 4 h 29 min before the
  first feature commit. Its `RUNLOG.md` records **16 environment findings** before and during
  feature work (gate crashing on the App Router layout, a hardcoded `src/`, `node_modules`
  deleted mid-gate by something outside the arm, four lanes sharing one database and dev server,
  a red-proof that proved nothing because `next start` served a stale build). One ticket (ZK-2)
  took three review rounds and ~2.5 h; the arm cut its own reviewer count mid-run to keep
  moving. The run stopped without a closing entry: the last commit closes ZK-5's review round,
  ZK-4's throttle migration and 10 other files were left uncommitted, and that throttle had
  turned an earlier integration test red (`auth-endpoints.test.ts:214` now receives the
  rate-limit message where it expects the invalid-credentials one).
- **BMAD (arm-b)** wrote a PRD and story breakdown in 1 h 27 min, then shipped all four spec
  areas in the next hour with two `step-04` adversarial review rounds. Its `RUNLOG.md` resolved
  eight BMAD human checkpoints on its own and records them. One planted bug survived its unit
  suite and typecheck (a rejected login answering 200) — its end-to-end tests are outside the
  mutation harness.

## Caveats that belong next to every number above

1. **One sample.** Agent runs vary; a few points of coverage is noise. Failing three criteria
   while claiming them, and a 2.8× longer commit span, are signal.
2. **arm-a is scored at its stop state.** PROTOCOL §3 says the operator commits everything the
   arm produced after it stops; that step was missed on 09-04 and done on 09-17 (`356bfcc`, no
   content change). The tree as committed on 09-04 does not even seed, so it was not scored.
3. **Cost was not captured.** Both arms ran as agent teammates; no Claude Code session log
   exists under either arm directory and neither `RUNLOG.md` carries token figures. The cost
   row is empty rather than estimated.
4. **The judge needed five repairs on scoring day** (broken `node_modules` in arm-b and in the
   judge, one ambiguous probe locator, stale Prisma clients, and an iCloud-evicted scaffold that
   hung every copy). All were applied before either arm was scored, to both arms identically,
   and are listed with evidence in JUDGE-REPAIRS.md. The locator repair (J3) was followed by a
   full re-calibration: 91 / 91.
5. **Framework-native scores are excluded.** `vteam audit` would score BMAD on not being vteam.
6. **The harness stays out of this repository.** Probes are the held-out exam; only the
   scorecard and the repairs record are published.

## What changes in vteam because of this

| Finding | Action | Ticket |
|---|---|---|
| Three "done" claims stood against a failing production build | Reproduce against arm-a's stop state; find what let the arm's e2e pass; fix the gate or the doctrine, not the arm | VT-28 |
| 2 h before a backlog, 4.5 h before a feature, 16 environment findings | Time-to-first-value work already under way (front page, `audit` first) — the setup tax inside a real repo is the next target | VT-26 · D17 |
| Three review rounds on one ticket, reviewers cut mid-run | The reviewer count and round limit are config today; the default was wrong for a small spec | to be filed after VT-28 |

Harness, protocol, probes and calibration evidence: `~/Documents/vteam-vs-bmad/` on the owner's
machine (`PROTOCOL.md`, `results/_reference`, `results/2026-09-03/`), deliberately not published.
