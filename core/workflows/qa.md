---
name: qa
command: /qa
description: VERIFY-ONLY QA pipeline for a ticket a dev claims done (the spec is the oracle). Reads the ticket + spec + schema to derive expected behavior → designs 2–5 test cases (exact repro, boundary, whole-screen sanity, read-only DB verify for writes) → self-provisions missing data through the REAL UI flow (write-gated) → runs them HEADED in the browser → collects evidence (named screenshots, annotated images with in-image captions) → cross-checks every ticket claim against an evidence file → machine gate (evd_check.py) → challenger sign-off → plain-language REPORT.md anyone can read → tracker comment posted once both machine gates are green, ticket transition per the full-auto policy. NO code change, NO fix — verification only.
args: "<TICKET: {project.key}-nnn | tracker URL> [assignee=<name>] [base=<app URL>]"
---

# /qa — verify a delivered ticket against the spec (QA lane, no code)

**What this workflow is NOT:** it never edits product code, never fixes anything,
never expands the dev's scope. It answers ONE question with evidence: **does the
app now behave the way the spec says it should, for the requirement this ticket
describes — without breaking the rest of the screen?**

**Immutable principles** (violation = the verification does not count):
1. **The spec is the oracle.** "Done" means the app matches the spec (+ the schema
   for data rules), NOT "matches the ticket prose" and NOT "no error appears".
   Every expected value cites its spec section / schema line. Ticket contradicts
   spec → spec wins; report the contradiction. Spec silent/self-contradictory →
   that TC is BLOCKED and **goes to the BA lane for arbitration** (the BA opens a
   3-condition gap question; per `raci.md` the BA is R for "bug or intended", the
   owner only A when the BA can't answer from the spec either); never invent an
   expected value.
2. **Real test, no shortcuts, no lying.** Every verdict comes from a browser run
   actually performed THIS session against the running app — never from reading
   code, never from an HTTP status, never from a previous run. A step that could
   not run is BLOCKED with a reason + unblock path — never inferred.
3. **Reading code is allowed only to know WHERE to look** (which route, which
   role gate), never to derive the expected value.
4. **Data through the REAL flow only.** Missing data → create it via the app UI
   (login → screen → action). Direct SQL/ORM writes are forbidden as a test path;
   the DB is read-only, used to VERIFY writes/rollbacks. Every write on a shared
   env follows the write gate: **user present in the session → ask before each
   write**; scheduled session with the user absent (at `autonomy.level: full`) →
   proceed without waiting, with the full record: the write block (screen +
   action + values + cleanup path) into the session minutes BEFORE writing, rows
   marked `ZZTEST`, cleaned through the app's reverse flow after V4. No reverse
   flow to clean with → that TC is BLOCKED, nothing is written.
5. **Evidence a stranger understands.** Per TC: `manifest.md` in plain language +
   per-step named screenshots + a box drawn on the exact region with an in-image
   caption (`annotate.py box --label`). `evd_check.py` must be green before
   reporting.
6. **Cross-check before reporting.** Re-read the ticket line by line; map every
   claim → the evidence file that proves it. An unmapped claim = verification
   incomplete.
7. **A fresh challenger signs off.** Before the verdict is final, spawn one fresh
   agent (empty context) briefed with the ticket + verify-sheet + evidence paths,
   whose job is to FALSIFY (wrong account/role? data-shaped diff? boundary
   missed? stale evidence? jargon in REPORT.md?). Record both cards in
   `{paths.evidence}/<TICKET>/debate.md`.
8. **Visible, human-readable process.** One plain-language `▶` line at every
   phase transition. REPORT.md and the final summary pass the bar: **a
   non-programmer reads 2 minutes and understands everything.**

Tempted to infer a verdict instead of running the step? Your excuse is catalogued in `red-flags.md`, next to the gate that catches it.

Tracker recipes: the configured tracker provider. Evidence tooling:
`.vteam/scripts/annotate.py` (box + side-by-side diff) and
`.vteam/scripts/evd_check.py` (machine gate) — use them, don't hand-roll.
External payment/integration environments are SANDBOX — never a real transaction.

---

## V0 — RESOLVE + ANNOUNCE THE TICKET

1. Fetch issue + ALL comments + attachments. Env vars missing → STOP, ask.
2. **Assignee filter.** Default from config (`assignee=` overrides). Different
   assignee → STOP and ask before verifying someone else's ticket.
3. **Status must be verifiable.** In Review / Ready for QA / Done-claimed = the
   target. To Do / In Progress = not delivered yet → STOP: `BLOCKED (not
   delivered)`. Closed → ask whether to re-verify.
4. **ANNOUNCE before any work** (one block); auto-picked ticket → wait for the go:
   ```
   ▶ Verifying <TICKET> — <summary>
     assignee: <name> | status: <status> | screen/feature: <what>
     target: <app URL> (branch: <protected|PR branch — say which>)
   ```
5. **Pin WHAT code is being verified.** Dev's PR merged → verify the protected
   branch. Not merged → check out the PR branch (read-only) and say so. Unclear →
   ask.

## V1 — READ: ticket + spec + schema (understand as QA, not as dev)

**Role playbook:** read `{paths.team}/roles/qa.md` first.

**KB preflight (index-only):** `{paths.qa}/knowledge-base.md` §0 + INDEX BEFORE
designing anything; open ONLY tag-matching lessons and answer them in the
verify-sheet (cite by TITLE). Scan `{paths.qa}/known-issues.md` headings — any
divergence found later is deduped against it before being called a bug.

**Read the change ledger BEFORE the shard:** `{paths.specs}/changes.md` — filter
CH-nn rows touching this ticket's shard/screen. An expected value that ignores a
decided CH is a wrong expected value.

Write `{paths.evidence}/<TICKET>/verifysheet.md` (REPORT.md points to it in the
appendix; it commits with the V7.4 dossier so the link outlives the session):
- Requirement + AC as the ticket states them; the dev's claimed delivery (PR
  link, comment) verbatim.
- **EXPECTED (from the spec, cited)** — quote the governing sections. Data rules
  from the schema (cite model:field).
- **UI EXPECTED (from the design oracle)** — ① design link on the ticket:
  download frames to `{paths.evidence}/<TICKET>/design/`, exact values from node
  data; ② else look the frame up by screen code in the design index. A UI TC
  compares the real screen against it (`annotate.py diff` → `design_vs_app.png`),
  judged at block/color/text level. The dev submitted a committed `fidelity.md`
  → READ it: re-run `node .vteam/scripts/ui_fidelity.mjs <TICKET>` to confirm the
  numbers still hold on the build being verified, and audit the INTENTIONAL
  deviation lines — does the declared reason stand (real a11y/spec, or an
  excuse)? QA still designs its own boundaries — never take TCs from the dev's
  spec. Design oracle contradicts the spec (verbatim messages/validation) → spec
  wins; record the design deviation.
- **CLAIM (from ticket + dev comment)** — what they say now works.
- Accounts/roles needed per criterion, data needed.
- Ambiguity → ask the user BEFORE spending effort.

## V2 — DESIGN THE VERIFICATION (before touching a browser)

Plan in the verify-sheet — usually 2–5 TCs:
- ① **Exact acceptance path** — the criterion as the ticket/spec states it.
- ② **Boundary pair** — the adjacent input that must behave the OTHER way
  (empty/duplicate identifier, insufficient balance, cancelled record…). A
  delivery that overshoots is a bug.
- ③ **Whole-screen sanity** — the rest of the screen/flow still behaves per
  spec, not only the new spot.
- ④ **Write → read-only DB verify** — if the feature writes, verify the row via
  a read-only query AFTER the UI action; and the rollback path if the spec
  defines one.
- Per TC: account + role, exact URL/steps/inputs, the spec-cited expected, the
  region to box.
- **Data check (read-only):** does the needed data exist? Never trust values in
  the ticket to still exist — resolve a currently-valid key; an empty list from
  stale data = "data moved", not a bug.

## V2b — ENV BRING-UP

- DB up → migrations clean → dev server up → health check returns 200/3xx.
- Resolve test accounts per role (seed data or existing rows, read-only). No
  usable account → V3 (create via the app's real sign-up flow, write-gated).
- Browser: HEADED — a run the user could watch.

## V3 — PROVISION DATA VIA THE REAL UI FLOW (only if V2 found gaps)

- Trace the producing flow (sign-up → login → the screen that creates the
  record). Drive it in the browser like a real user.
- **Write gate (principle 4): user present → ask first, one block per write**
  (screen + action + exact values + cleanup action); **user absent (scheduled
  session)** → write the block into the session minutes BEFORE acting, then
  proceed. Both paths: capture the run under
  `{paths.evidence}/<TICKET>/data_prep/`, mark rows `ZZTEST`, verify by read-only
  SELECT, clean up via the app's reverse action after V4. No reverse flow → that
  TC = BLOCKED, nothing written.
- Producing flow impossible (feature not built, external dependency) → that TC =
  `BLOCKED (missing data)` with what was tried; never fake it.

## V3b — TICKETS WITH NO SCREEN (the non-UI verify branch)

Activates when the ticket **produces no screen**: a migration, a model, a shared
library function, a background process. Without this branch such tickets are
unverifiable by a browser pipeline — and they are the foundation everything else
stands on, where errors are most expensive.

Unchanged principle: **the spec is still the oracle, and QA still RUNS things
itself — never reads the dev's report as proof.** Only the viewport changes: from
screenshots to database state and command output.

Every TC on this branch needs all four, recorded in
`{paths.evidence}/<TICKET>/TC_n/`:

1. **Migrations run on a CLEAN database, not only the dev's.** Create a scratch
   DB → deploy migrations → status clean. A migration that only works on the dev
   machine (old data masking the flaw) is a broken migration.
2. **Spec-mandated data invariants, checked by read-only SELECT.** Cite the exact
   rule id. Record the statements and real results in `db_verify.md`.
3. **The dev's tests must go RED when the behavior is flipped.** Pick one core
   constraint of the ticket, temporarily break it, run the tests, confirm they
   RED, restore, and `git diff` confirms clean. A green test proves nothing; a
   test that reds in the right place does.
4. **A boundary pair QA invents itself, not taken from the dev's tests.** The dev
   tested their understanding; QA probes exactly where that understanding could
   be wrong.

`evd_check.py` accepts a TC without images when its `manifest.md` declares
`TYPE: NON-UI` — but then `db_verify.md` is MANDATORY. No images and no data
check is not verification.

## V4 — RUN THE VERIFICATION, HEADED (the actual test)

Announce each run in one line (TC / account / what it proves). For each TC from
V2: drive the steps in the browser, screenshot each meaningful step as
`01_<what>.png`, `02_<what>.png`… then annotate the verdict region:

```bash
python3 .vteam/scripts/annotate.py box \
  --img {paths.evidence}/<TICKET>/TC_<n>/03_result.png --rect X,Y,W,H \
  --label "TC_<n>: <what this proves / what diverges>" \
  --out {paths.evidence}/<TICKET>/TC_<n>/03_result_boxed.png
```

Evidence layout (one folder per TC):
```
{paths.evidence}/<TICKET>/
├── manifest.md            # plain language: the requirement, TC list, per-TC verdict
├── debate.md              # V6 cards (verifier + challenger)
├── data_prep/             # V3 runs, if any
└── TC_<n>/
    ├── manifest.md        # what it verifies, steps, expected (spec §), actual, RESULT: PASS|FAIL|BLOCKED
    ├── 01_*.png …         # per-step screenshots (+ *_boxed.png on the verdict step)
    └── db_verify.md       # write TCs only: the read-only SELECT + rows after the action
```

Gate: `python3 .vteam/scripts/evd_check.py --evd {paths.evidence}/<TICKET>
--expect-tcs <N from V2>` green — pass the PLANNED TC count, so "planned 5, ran
1" can go red — before V5.

## V5 — CROSS-CHECK AGAINST THE TICKET

Table in the verify-sheet — one row per claim in the ticket AND the dev's
delivery comment: `claim → TC → evidence file → matches spec?`. Rules:
- A claim with no evidence row = INCOMPLETE — back to V2/V4; do not report.
- Criterion met but a NEW divergence appeared nearby → verdict `NEW-BUG` for that
  finding; describe it with evidence. A finding to report, never to fix here.
- Ticket misdescribed the behavior but the app still diverges from spec →
  verdict on the REAL divergence, note the correction.

## V5b — DRAFT REPORT.md (plain language, so V6 can grade it)

Write `{paths.evidence}/<TICKET>/REPORT.md` — in `project.language`, black-box
voice, ZERO jargon in the body (no file:line, route names, "oracle" — appendix
only). Bar: **a non-programmer reads 2 minutes and understands everything.**
Fixed template:

```markdown
# Verification report <TICKET> — <verdict, large: PASS / FAIL / PARTIAL / NEW-BUG / BLOCKED / UNCLEAR>
COMMIT: <sha verified — HEAD of the code the TCs ran on; the verdict binds to the code, evd_check requires it>

## 1. What does this ticket ask for? (told as a user)
On screen <name>, when <the user does what>, the system must <the right outcome —
per the spec>. The dev reports it done (PR <link>).

## 2. How did I check?
| # | What I did (account, screen, action, data) | Expected (per spec) | Actual | Match? |
(plus: where test data came from / how it was UI-created, if applicable)

## 3. Evidence — what to look at, where?
One line each: file path → what that file SHOWS (covering every TC_<n>).

## 4. Conclusion
1–3 sentences: requirement met or not · new findings or none · recommendation
(move to Done / return to dev).
FAIL / NEW-BUG verdicts → one extra line per finding:
**Severity:** Blocker / Critical / Major / Minor (definitions: roles/qa.md) ·
**Origin:** DEV stage (code diverges from AC) or BA/spec stage (AC/spec wrong or
missing — work returns to the BA lane).

## 5. If BLOCKED / UNCLEAR — why, and what's needed?
**Could not verify <what>** because <reason> · **Tried:** <…> · **To unblock:** <who/what>.

## Appendix (for technical readers)
verify-sheet · spec §/schema citations · debate.md · remaining evidence files.
```

## V6 — CHALLENGER SIGN-OFF

1. Write YOUR verdict card into `debate.md` FIRST (verdict + strongest evidence +
   `MY WEAK SPOT:` the one thing most likely to be wrong).
2. Spawn ONE fresh agent (never forked; model `standard` per model-routing) with:
   ticket verbatim + verify-sheet + evidence paths + REPORT.md + this
   instruction: "FALSIFY this verification: wrong role/account? data-shaped
   difference? boundary untested? evidence stale or not showing what the caption
   says? any REPORT.md sentence a non-technical reader can't follow? Return your
   own card."
3. Challenger found a hole → run the decisive experiment (a re-run, a SELECT),
   never argue in prose. Append the resolution + `Remaining dissent:` line.
4. Consensus without a run that actually executed = UNCLEAR, never PASS.

## V7 — REPORT + CLOSE THE LOOP

1. Finalize REPORT.md (challenger's readability fixes applied). Re-run
   `evd_check.py` — must be green.
2. **Summary to the user** = REPORT.md content (verdict + V5 table + evidence
   paths + new findings + remaining dissent).
3. **Tracker comment — self-posted (full autonomy):** 3 parts (result + attached
   evidence + notes/recommendation), posted right after both machine gates are
   green (`evd_check.py` + challenger V6). Print the comment verbatim into the
   session minutes.
3a. **Attach QA images to the tracker — mandatory, with read-back** (images live
   outside git, so the tracker is the only place they survive the session):
   `python3 .vteam/scripts/evd_check.py --evd {paths.evidence}/<TICKET> --attach <TICKET>`
   — uploads every TC image, re-reads the attachment list to confirm each
   filename, and writes a `## TRACKER ATTACHMENTS` section (name · md5 · url)
   into the root manifest. That pointer is what lets a clean checkout reproduce
   the verdict when images are gone from disk.
3b. **Ticket-closing policy (FULL-AUTO at `autonomy.level: full`):** verdict
   **PASS** + PR merged + CI green → transition the ticket to **Done**. Verdict
   FAIL / NEW-BUG → return the ticket to **To Do + `reopen` label** (distinguishes
   returned work from new work — /dev's DoR gate reads this label and points at
   REPORT.md first) with a comment linking REPORT.md + severity.
   **Blocker/Critical** findings → recorded in the minutes as the NEXT dev item,
   before any new ticket (SLA per roles/qa.md). BLOCKED/UNCLEAR → keep In Review +
   record in the minutes. Every closed ticket is listed in the minutes for the
   owner's acceptance review.
4. **Commit the verification dossier (a verdict must be reproducible):**
   REPORT.md, manifest.md (with TRACKER ATTACHMENTS), verifysheet.md, debate.md,
   TC_*/manifest.md, db_verify.md commit via the light path — a docs branch + PR,
   self-merged when CI is green (images stay out of git). QA never touches
   product code, but its own text dossier MUST reach git — a verdict living on
   one machine is a fabricated report.
5. **Cleanup**: reverse V3 `ZZTEST` data via the app; record any residue in the
   manifest.
6. **A finding OUTSIDE the ticket's scope that deserves its own ticket → QA files
   the Bug ticket itself** (full autonomy; the exemption list still waits for the
   owner). Bug template — missing sections make the DoR gate red:
   ```
   [Environment]  <app URL> — branch, test account
   [Steps to reproduce]  1. … 2. … 3.
   [Expected]  per spec §x.y ({paths.specs}/<feature>.md)
   [Actual]  what happened
   [Severity]  Blocker / Critical / Major / Minor (roles/qa.md)
   [EVD]  {paths.evidence}/<TICKET>/TC_n/… (boxed image, db_verify if a write is involved)
   ```
   Labels: `qa-found` + area; estimate left for BA refinement (noted in the
   ticket). Dedup against known-issues BEFORE filing (principle from V1).
7. **Close the learning loop** — append a lesson (+ INDEX line) to
   `{paths.qa}/knowledge-base.md`, even for FAIL/BLOCKED runs (or state "no new
   lesson"). Prefer GRADUATION (§0): gate-shaped → `evd_check.py`; cross-screen →
   known-issues; unconditional → this workflow — then delete from KB.

## Definition of Done
- [ ] V0: assignee matches; status verifiable; announced (incl. WHICH code:
      protected branch or PR branch)
- [ ] Expected derived from spec/schema with citations (never from ticket prose or code)
- [ ] Every TC ran HEADED this session against the running app; blocked TCs carry
      reason + unblock path
- [ ] Boundary TC + whole-screen sanity TC ran (not only the happy path)
- [ ] Writes verified via read-only DB checks; all test data UI-created, per the
      write gate (ask when present / minutes-first when absent), ZZTEST-marked,
      cleaned up
- [ ] V5 table: every ticket/dev claim mapped to an evidence file
- [ ] `evd_check.py --expect-tcs <N>` green; REPORT.md follows the template
      (with the COMMIT: line), jargon-free body
- [ ] QA images attached with read-back + TRACKER ATTACHMENTS section in the manifest
- [ ] V1: change ledger filtered for this ticket's shard/screen
- [ ] Failing verdict: every finding carries Severity + Origin (DEV / BA-spec) —
      evd_check blocks otherwise; ticket returned To Do + `reopen`
- [ ] Out-of-scope findings: deduped, Bug ticket filed per template (labels
      `qa-found` + area) or explicitly judged not ticket-worthy
- [ ] The text dossier COMMITTED via the light path — the verdict reproducible from git
- [ ] debate.md has both cards + resolution; the challenger was a real fresh agent
- [ ] NO product code changed; findings reported, not fixed
- [ ] Tracker comment posted after both machine gates; transition per V7.3b
- [ ] KB preflight done at V1; lesson appended at V7
- [ ] Every phase narrated with a ▶ line; all user-facing output passes the
      plain-language bar
