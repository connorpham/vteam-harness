---
name: dev
command: /dev
description: Ticket-driven DEV pipeline, end-to-end — preflight (tracker/design-source/git/DB pinged for real) → fetch the ticket → read spec + schema (the ticket is a claim, the spec is the spec) → UI tickets pull the design from the ticket's design link (design source = visual oracle; exact colors/spacing/text from node data) → implement on a feature branch → /verify gate + evidence → self-review with machine-measured design fidelity → {review.reviewers} fresh review agents must approve (+1 on high-stakes diffs; committed review trail enforced at pre-push) → push + PR → mandatory 7-part plain-language report comment on the ticket, then transition to In Review (Done belongs to /qa). Runs the machine DoR gate and claims the ticket before coding.
args: "<TICKET: {project.key}-nnn | tracker URL> [assignee=<name>] [branch=feat|fix]"
---

# /dev — implement a ticket, prove it before delivering

**Immutable principles** (violation = the task is not done):
1. **The spec is the spec, the ticket is a claim.** Expected behavior comes from
   the spec shard (`{paths.specs}/<feature>.md`) and the schema — never from
   ticket prose alone. Ticket contradicts spec/schema → STOP and ask before coding.
2. **No code before understanding.** T1's task-sheet (requirement, acceptance
   criteria, touched models/routes, cited sources) must exist before the first
   edit. Ambiguous ticket → ask, do not guess.
3. **Minimal, surgical change** (the `guidelines` workflow is the method authority
   — load it). No drive-by refactors, no scope expansion; a side finding gets its
   own note/ticket (T5), never smuggled into this branch.
4. **Never commit on the protected branch.** Branch `feat/<TICKET>-<slug>` (or
   `fix/…`) from its up-to-date tip.
5. **"Done" is machine-checked AND peer-checked.** The /verify gate must be green
   with exact result lines recorded, AND every review card T4b requires (R1 + R2,
   plus R3 when triggered) must approve BEFORE any commit/push/PR/comment. UI
   change → headed browser evidence under `{paths.evidence}/<TICKET>/dev/` (the
   root layer `{paths.evidence}/<TICKET>/` belongs to the QA lane). A claim
   without recorded output is not a claim.
6. **The ticket is not done without the report comment.** Closing requires posting
   the 7-part report comment to the tracker — always print the exact posted text
   in the final summary. After the comment + PR merge, T6.3 transitions the ticket
   to In Review (at `autonomy.level: full`); moving to Done is /qa's call after a
   PASS verdict.
7. **Visible, human-readable process.** One plain-language checkpoint line at
   EVERY phase transition — `▶ [T3/T6] <what's happening, in plain words>`. Every
   report/summary must pass the bar: **a non-programmer understands it** (jargon
   goes in an appendix, never the body).

Tempted to skip a step? Find your excuse in `red-flags.md` first — if it's listed, the answer is already no, and a gate fires anyway.

Method authority: the `guidelines` workflow. Tracker recipes: the configured
tracker provider (`providers/tracker/<name>`). Schema: read the project's schema
file for real field names — never guess. Framework docs: read the in-repo
framework guide before writing code when the project declares one (the installed
version may differ from training data).

---

## T0 — RESOLVE + ANNOUNCE THE TICKET

1. **Preflight the whole chain first**: `bash .vteam/scripts/preflight.sh` — pings
   tracker, design source, git, DB, test infra for real. Non-UI ticket → add
   `--backend` so the design-source legs only warn. RED → show the misses +
   unblock steps; continue only with green parts. Never print tokens.
2. Fetch the issue + ALL comments + attachments. No ticket key given → list the
   assignee's open tickets and ask the user to pick.
3. **Assignee filter.** Default assignee comes from config (`assignee=<name>`
   overrides). Ticket assigned to someone else → STOP and ask.
4. **Status must be workable — In Progress is a CLAIM, not an invitation.**
   To Do / Open = OK. **In Progress → another session's until proven otherwise**:
   read the latest claim comment + `git branch -a --list '*<TICKET>*'`
   (`npx vteam-harness resume <TICKET>` reads all these signals in one shot and
   names the furthest proven stage). A claim
   younger than the claim TTL, or a branch someone is pushing → STOP, pick other
   work. A claim past TTL with no remote branch and no fresh worklog → ORPHANED
   (previous session died): take over, write one `failed: previous session died
   mid-work` row to the ledger so loop guards count crashed sessions, and resume
   the leftover local branch if one exists instead of restarting. Done/Closed →
   tell the user. In Review → ask whether this is rework. The `reopen` label =
   QA returned it — read QA's REPORT.md BEFORE re-reading the spec.
5. **Definition-of-Ready gate (machine-checked):**
   `python3 .vteam/scripts/dor_check.py <TICKET>` must be GREEN — G/W/T AC + spec
   citation + out-of-scope section + design link (if UI) + original estimate + not
   blocked by an un-Done ticket. RED → the ticket returns to the BA lane
   (`raci.md` §2); do NOT start coding. Sole exception: the user orders ad-hoc
   work that skipped /ba — the waiver must become a DURABLE trace: a ticket
   comment `DoR waived by <user> — reason` (a scratchpad dies with the session; a
   comment doesn't).
6. **CLAIM the ticket here**: transition to In Progress **+ comment
   `claimed <timestamp> · branch feat/<TICKET>-<slug>`** — a claim without a
   timestamp leaves the next session unable to tell working from orphaned.
7. **ANNOUNCE before any work** (one block); if the ticket was auto-picked, wait
   for the go:
   ```
   ▶ Task <TICKET> — <summary>
     assignee: <name> | status: <status> | type: <Story|Bug|Task> | priority: <p>
     branch plan: feat|fix/<TICKET>-<slug>
   ```

## T1 — READ: ticket + spec + schema + code (build the task-sheet)

**Role playbook:** read `{paths.team}/roles/dev.md` first — the professional
baseline this lane is held to.

**KB preflight (index-only — never read the whole file):** read
`{paths.qa}/knowledge-base.md` §0 + its INDEX table, open ONLY lessons whose tags
match this ticket's area, and answer them in the task-sheet (cite by TITLE). Same
for `{paths.qa}/known-issues.md` headings. Over the cleanup threshold (§0) →
propose a consolidation pass.

**Read the change ledger BEFORE the shard:** `{paths.specs}/changes.md` — filter
CH-nn rows touching this ticket's shard/screen. The shard is VERBATIM source; all
decided requirement deltas live in the change ledger. A NEW spec contradiction
discovered mid-work → add a CH-nn row with status `proposed` (PM/BA arbitrate
later); don't just narrate it in the task-sheet.

**Context via the code map — BEFORE reading the directory tree:**
`python3 .vteam/scripts/code_map.py query <TICKET> <2-4 domain terms>` (e.g.
`query PROJ-42 wallet topup balance`). It prints PATHS + line ranges only — read
those files plus `docs.task_context` below, and let the returned paths fill the
task-sheet's **Code map** bullet. It says `MAP IS STALE` or `NO CODE MAP` → run
`python3 .vteam/scripts/code_map.py build` first (one command, seconds) and
re-query. The map is **advisory and lexical** (python is really parsed; js/ts
symbols come from regexes, and there is no data-flow) — a file you know matters
but the map missed gets read anyway **and named in the task-sheet** as
`code map MISSED: <path> — <why it matters>`, so the next session (and the map's
scan roots, `git.code_paths`) can be corrected. Reading the whole tree "to be
safe" is the behavior this step exists to replace.

**Task context (only when config `docs.task_context` exists):** read the files it
maps for THIS ticket — `always:` first, then the `by_label:` lists matching the
ticket's labels and its issue type. This is the project background the owner
already wrote down (created by `/docs` on undocumented repos); reading it is
cheaper than rediscovering it in review. **A listed file that does not exist is
said LOUDLY in the task-sheet** — one line, `task context MISSING: <path> (mapped
by <always|label:<name>>)` — never silently skipped and never replaced by a
guess: a stale mapping means either the config or the repo moved, and the owner
needs to know which.

Write `{paths.evidence}/<TICKET>/dev/tasksheet.md` BEFORE touching code (it
carries Impact + assumptions + self-review results; it commits with the code so
the next session can resume the work):
- **Requirement** in one paragraph, plus acceptance criteria as the ticket states them.
- **`CODE-SCOPE:`** one line, the paths this ticket may touch (e.g.
  `CODE-SCOPE: src/auth/ src/lib/session.ts`) — graph_check reds any commit
  naming this ticket that strays outside them (MAST 2.3: self-expansion).
  Scope grew mid-ticket? Widen the line DELIBERATELY in the same commit and
  say why in the task-sheet — or split the ticket.
- **Spec check**: the governing spec sections — quote them. Spec silent on a
  detail → list it under "assumptions to confirm" and ask.
- **Design check (UI tickets)**: the design oracle, in priority order — ① design
  link on the ticket (record file + node ids) → ② search the project's design
  index / frame matcher and attach the matching frame to the ticket, then use it
  as ①. Neither exists → report to /pm (design lane / decision queue); don't
  design ad-hoc inside a dev ticket. **The design source rules the looks, the
  spec rules behavior** — on conflict, spec text (verbatim messages/validation)
  wins over the picture; note the correction.
- **Data model**: exact models/fields touched (read the schema — never assume
  names). Schema change needed → plan the migration + client regeneration per the
  stack profile.
- **Code map**: routes/components/lib files involved; what exists vs what's new.
- **Impact**: who else uses what I'll change (search each touched symbol),
  auth/role implications, external sandbox notes if relevant.

## T2 — PLAN (minimal change, stated out loud)

**Load the `guidelines` workflow NOW, before writing the plan** — its defaults
(think first, surgical diff, surface assumptions, verifiable success criteria)
govern T2–T4; planning without it is a pipeline violation.

In the task-sheet, before editing: the minimal file-by-file change list ·
migration yes/no · test plan (which tests prove the AC — expected values cite
spec/schema) · what is explicitly OUT of scope. Present the plan to the user only
when a decision is genuinely theirs (schema change, new dependency, ambiguous
spec); otherwise proceed.

## T3 — IMPLEMENT

- `git fetch && git switch -c <type>/<TICKET>-<slug> origin/<protected>` (never
  commit on the protected branch).
- **UI work — design from the design source, consistency from the design
  language, quality from the UI rules:**
  0. Read the design language FIRST ({paths.design}/design-language.md —
     generated from the design source at install; if absent, say so in the
     task sheet rather than inventing tolerances). Write
     `{paths.evidence}/<TICKET>/dev/fidelity.json` AS you build the layout
     (selectors + expected values from the design node data) — know what the
     screen will be measured on before coding it.
  1. Download the ticket's design frames to `{paths.evidence}/<TICKET>/design/`
     and read the node data for exact values — colors/spacing/fonts/text come
     from the API data, never eyeballed from a screenshot.
  2. Read `{paths.design}/design-language.md` (tokens generated from the
     project's own design source at install/refresh time): shared colors /
     type-scale / radii / components. Anything your screen needs that the frame
     doesn't specify comes from HERE, not from taste. Where the design source
     provides no spacing system, spacing has exactly one source: the frame's node
     data.
  3. Apply the framework's UI quality rules (a11y, touch targets ≥44px, WCAG AA
     contrast, responsive) ON TOP of both — a design drawn with 3px touch targets
     still ships with 44px.
  Skipping any of these on a UI ticket is a pipeline violation; API/backend
  tickets skip all three.
- Follow repo conventions (aliases, generated-code locations, auth mechanism,
  styling system — from the project docs). Match surrounding style; comments only
  for constraints the code can't show.
- Schema change: edit the schema → run the profile's migration command → 
  regenerate the client. Commit the migration with the code. Hand-naming a
  migration folder → timestamps in **UTC** (local-time timestamps have reordered
  migrations and killed clean-DB replays).
- Side finding (unrelated bug/dead code) → note it in the task-sheet + report at
  T6; do NOT fix it here.

## T4 — VERIFY with the /verify gate

- Run the /verify workflow (or its gate directly). Record the exact closing lines
  in the task-sheet. New behavior needs a new test whose expected value cites
  spec/schema.
- **UI change → PROPER EVIDENCE, machine-guarded:**
  1. Start the dev server, capture with `node .vteam/profiles/nextjs-prisma/scripts/ui-evidence.mjs` —
     it signs in through the app's REAL auth flow (the profile's auth strategy),
     no forged cookies, so the images show what a real user sees. The run is
     **HEADED by default** — the browser visibly opens and walks each screen at
     a human-followable pace, so the owner can WATCH the app being used like a
     real user (the same standard the QA lane holds). Pass `--headless` only on
     machines with no display (CI sets it automatically). Images go to
     `{paths.evidence}/<TICKET>/dev/` — the root layer belongs to QA; two lanes,
     two directories, so their gates never red each other. One image per
     criterion, named `NN_<description>.png`.
  2. Ticket has a design oracle → add `design_vs_app.png` (design beside app) with
     a line stating what matches and what differs **intentionally**.
  3. `manifest.md` must contain a **CRITERION → IMAGE** table.
  4. **Mandatory:** `python3 .vteam/scripts/evd_ui_check.py <TICKET>` GREEN. It
     checks images open / are big enough / are **not blank or error pages**
     (dominant-color ratio) / follow naming / are referenced in the manifest /
     `design_vs_app.png` exists when the ticket has a design oracle. Red = not
     done, non-negotiable.
  5. **Images per STATE, not only per criterion:** with data, empty, error (and
     loading if skeletons exist) — the manifest carries a `STATE:` line listing
     captured states; inapplicable states say `N/A because <reason>`.
- **API/backend change → its own evidence standard, not "some curl":**
  `{paths.evidence}/<TICKET>/dev/api.md` with one REAL request→response pair per
  criterion — full command (token masked), status code, body, and one line
  "proves which AC". Plus at least one failing case (401/403/422) per
  write endpoint. No images needed.
- **Bug ticket (fix/) → BEFORE–AFTER evidence mandatory:** reproduce on the old
  code (`before_*`), same steps on the fix branch (`after_*`), side by side in
  the manifest. A fix that can't reproduce the original bug proves nothing.
  Machine check: `evd_ui_check.py <TICKET> --bug` — missing pair = RED.
- Any red → fix or report honestly; never deliver on a red gate.

## T4a — SELF-REVIEW (reviewer #0 is the author)

Most review findings are things the author could have caught by putting their
screen next to the design and re-reading the diff as a stranger (provenance: one
ticket burned 6 review rounds mostly on self-catchable findings). Do all 3 —
NOT DONE = NO REVIEWERS YET:

1. **Re-read your own diff as a reviewer:** `git add -A && git diff --cached`
   (an unstaged diff is a diff reviewers can't see — same protocol as T4b), hunk
   by hunk — every hunk answers "which AC does this serve?"; a hunk with no
   answer is scope creep, remove it. Quick sweep: dead code / debug prints /
   forgotten TODOs / rushed names.
2. **UI ticket — measure fidelity by machine, not by eye** (proportionality: a
   diff touching ≤1 component or copy-only may declare `NARROW-SCOPE:` in the
   manifest instead of paying the full measurement tax):
   - `fidelity.json` — key elements' selectors + expected values **taken from the
     design node data** (never from your own code — measuring code with code is
     self-grading).
   - `node .vteam/profiles/nextjs-prisma/scripts/ui_fidelity.mjs <TICKET>` → generates `fidelity.md`.
     WRONG deviations → fix code, re-measure. Justified deviations → declare an
     `intent` from the CLOSED list (`a11y:` / `spec:` / `responsive:` + reason) —
     the tool rejects intents outside the list.
   - Put `design_vs_app.png` beside the frame and walk the measurable-beauty
     checklist (spacing rhythm, alignment, hierarchy, empty/error/loading). What
     you can see wrong, fix NOW — don't save it for reviewers.
3. **Record self-review results at the end of the task-sheet** (3–6 lines): what
   you caught and fixed, what deviates intentionally and why — reviewers read
   this to NOT re-dig measured ground.

## T4b — TWO-AGENT REVIEW (mandatory gate BEFORE commit/push/PR/comment)

No delivery until {review.reviewers} fresh agents (config `review.reviewers`;
spawned in the SAME message — parallel, empty context, never forked) have all
reviewed the diff and approved. **Model routing
(`{paths.team}/model-routing.md`):** R1 = `workhorse`, R2 = `standard`; if the
diff matches `review.high_stakes_terms` → BOTH `workhorse`. **Every reviewer
brief MUST include `{paths.team}/review-standard.md`**: findings are
CONFIRMED-with-evidence or QUESTION; APPROVE carries a tried-to-break list; a
CONFIRMED that doesn't reproduce voids the card and spawns a replacement.

Brief reviewers with the SELF-REVIEW results (T4a) + `fidelity.md` if UI —
reviewers verify measured numbers instead of re-measuring, and focus where the
machine can't measure.

- **R1 — spec reviewer:** briefed with task-sheet + diff + spec/schema citations.
  Checks: does the change do exactly what the spec says (each AC → code), is it
  MINIMAL (flag any unrelated edit), migrations/regenerated client consistent?
- **R2 — challenger:** briefed with the diff + repo map, NOT the task-sheet
  reasoning. Job: FALSIFY — bugs, edge cases (empty/duplicate/unauthorized role),
  regressions in callers of changed code, security (auth gates, input
  validation), UI a11y if applicable.
- **R3 — architecture & future (CONDITIONAL — only when the diff touches
  `review.high_stakes_paths` or matches `review.high_stakes_terms`; skip for
  screen-only tickets):** `workhorse`, briefed with the diff + roadmap + ADRs +
  sprint plan. Its card must answer: optimal or merely working? will it survive
  the features already planned? and for every major design point: **"option A
  (as built) vs option B — why A"** — an approve-only card without comparisons is
  INVALID, send it back.

Each returns a verdict card (APPROVE / REQUEST-CHANGES + findings with file:line;
major findings as A-vs-B comparisons). Record all cards in
`{paths.evidence}/<TICKET>/dev/review.md` — this file COMMITS with the code, and
`review_check.py` at pre-push demands it: valid R1+R2 APPROVE cards
(tried-to-break ≥3 bullets, ≥2 command/file:line traces), plus R3 when triggered.
Any REQUEST-CHANGES → fix, re-run the T4 gate, then re-submit to the SAME concern
(a targeted re-review, not a fresh full pass). Only when ALL required cards say
APPROVE does the pipeline proceed to T5. Unresolvable disagreement → the user.

**Cross-model reviewers — `review.external.<card>`.** A card is a FILE, so any
tool that can write a conforming one can hold that seat — and two agents on the
same model share their blind spots. When `review.external.r2` is configured (any
card id), that card comes from the external CLI instead of a spawned agent:

```
node .vteam/scripts/external_review.mjs <TICKET> R2
```

The runner pipes the brief (`{paths.team}/review-standard.md` verbatim + the card
contract + the diff) to the tool on stdin, validates what it prints against
review_check's own bar, and only then writes `## R2 — external (<model>)` into
the dossier — stamped `MODEL:` / `TOOL: external`, replacing that card and no
other. Exit 0 = APPROVE filed, 2 = REQUEST-CHANGES filed (round still open),
1 = nothing written and stdout says what was missing.

Then **STILL run `review_check.py`** — the gate does not care who wrote the card.
Everything else is unchanged: the reviewer COUNT is still `review.reviewers`,
high-stakes still adds R{N+1}, any REQUEST-CHANGES still reopens the round, and
the remaining cards are still fresh Claude agents spawned in one message. An
external card that fails validation is NOT written — no card, so the push fence
blocks exactly as it does for a missing Claude card. The external CLI is
installed and authenticated by YOU; a missing binary is a RED run, never a
silent skip to one fewer reviewer.

**Answering a reviewer — before typing any sentence containing "fixed":**
1. `git add -A` then `git status --porcelain` filtered for unstaged changes —
   must be **0 lines**; reviewers read `git diff --cached`, a fix outside staging
   means they approved the old version.
2. Every finding closes with ONE command proving it closed, **output pasted into
   the message** — never a bare "fixed".
3. **Checks must be as WIDE as the change:** renamed an identifier → grep the OLD
   name repo-wide and classify every hit; changed shared behavior → find every
   caller, not just the one you edited.

## T5 — DELIVER: commit + PR

1. Commit on the branch: code + migration + tests + **the text layer of the
   evidence dir (review.md, manifest.md, fidelity.json/md — images/binaries stay
   out of git)** — pre-push blocks if review.md is missing on a code diff.
   Message: `<type>(<TICKET>): <what>` — follow the project's commit-authorship
   rules in its own instructions file.
2. Push and open the PR into the protected branch, titled
   `<type>(<TICKET>): <what>`, ticket key + summary + test-result lines in the
   body.
3. **Self-merge (only at `autonomy.level: full`):** when ALL 4 machine-checkable
   conditions hold — every review card APPROVE + the PR's CI green + the /verify
   gate green + **no unanswered human comment on the PR** (a human comment is
   priority input: handle it via /pm's PR-FEEDBACK protocol FIRST, then merge) —
   merge per `git.merge_strategy` without waiting (on squash/rebase the
   VERIFIED-AT anchor keeps the QA verdict alive — qa workflow V5b). Any
   condition missing (or autonomy below full)
   → leave the PR open + record why in the session minutes.
   `git switch <protected> && git pull` after merging.
4. List every side finding from T3 and what was done with it.

## T6 — TRACKER CLOSE LOOP (report comment is REQUIRED)

1. Write the **7-part report comment** — sentinel-tagged sections
   `[R1] What was done · [R2] Impact scope · [R3] Technical · [R4] Tested ·
   [R5] Evidence · [R6] Notes for QA · [R7] Open issues` — plain language,
   readable by a non-programmer (jargon only inside the evidence lines). Impact
   scope copies the task-sheet's Impact section, never rewritten from memory.
   **UI tickets: attach images by command, not by hand:**
   `python3 .vteam/scripts/evd_ui_check.py <TICKET> --attach` — it re-validates
   the images, uploads them, then **re-reads the ticket's attachment list to
   confirm every filename actually landed** — attaching without read-back doesn't
   count as attached.
2. **Post it** — the ticket is NOT done until this comment is on the tracker.
   **Then machine-verify:** `python3 .vteam/scripts/comment_check.py <TICKET>` —
   re-reads the comment from the tracker and checks all 7 markers; posting
   without read-back doesn't count as posted. Print the exact posted text in the
   final summary. Tracker unreachable → say so, deliver the text locally, mark
   the close-out PENDING.
3. **Status transition (at `autonomy.level: full`):** after comment + PR merged →
   transition to **In Review** (QA verify next; Done belongs to /qa after a PASS
   verdict).
3b. **Time tracking is part of closing** (when the tracker supports worklogs):
   post a worklog with real elapsed session time, and verify the ticket carries
   an original estimate. A closed ticket without worklog + estimate is not closed
   — if the provider lacks worklog support, the gate skips LOUDLY with a note in
   the summary.
4. Final summary — plain language first (what a non-dev needs), then the
   technical block: gate results, review cards, PR link, side findings,
   task-sheet path.
5. **Close the learning loop** — append a lesson (+ one INDEX line) to
   `{paths.qa}/knowledge-base.md` or state "no new lesson". Prefer GRADUATION
   over accumulation (§0): machine-checkable → into a gate; unconditional → into
   this workflow; recurring env pattern → known-issues — then delete from KB.

## Definition of Done
- [ ] T0: ticket announced; assignee = configured person (or user overrode)
- [ ] T0: `dor_check.py <TICKET>` GREEN (or a waiver commented on the ticket —
      durable trace); ticket claimed (In Progress + `claimed <timestamp> · branch`)
      before coding
- [ ] `{paths.evidence}/<TICKET>/dev/tasksheet.md` exists with spec/schema
      citations BEFORE the first edit, and COMMITS with the code
- [ ] T1: change ledger filtered for this ticket's shard/screen; a newly found
      spec contradiction got a `proposed` CH-nn row
- [ ] T1: `docs.task_context` files read (`always:` + this ticket's labels/type)
      when configured; any missing mapped file named loudly in the task-sheet
- [ ] Work on a `feat|fix/<TICKET>-*` branch — zero commits on the protected branch
- [ ] Schema change (if any) has a committed migration + regenerated client
- [ ] /verify gate green, exact result lines recorded
- [ ] UI ticket: the UI quality rules were applied before designing/coding
- [ ] T4a self-review ran: own diff re-read; UI has `fidelity.json` (expecteds
      from design node data) + `ui_fidelity.mjs` GREEN (0 wrong deviations;
      intentional ones carry closed-list intents); results recorded in task-sheet
- [ ] UI: `evd_ui_check.py <TICKET>` GREEN (images in `…/dev/`, correctly named,
      no blank pages, manifest complete, `design_vs_app.png` + `fidelity.md`
      when a design oracle exists)
- [ ] UI: manifest has the `STATE:` line (data/empty/error/loading — N/A with reason)
- [ ] API/backend: `api.md` — one real request→response pair per AC + ≥1 failing case
- [ ] Bug ticket: `evd_ui_check.py <TICKET> --bug` GREEN (`before_*`/`after_*` pair)
- [ ] UI: images attached via `--attach` and the read-back confirmed all names
- [ ] T4b: all required cards APPROVED (R1+R2, +R3 when triggered); cards in
      `review.md` COMMITTED — pre-push runs `review_check.py`
- [ ] PR opened with ticket key; side findings reported, not smuggled in
- [ ] 7-part report comment POSTED and `comment_check.py <TICKET>` GREEN (or
      explicitly PENDING with reason); exact text shown to the user
- [ ] Status transition: In Review after comment + merge (full autonomy); Done is /qa's
- [ ] Every phase narrated with a ▶ line; final summary passes the plain-language bar
- [ ] KB read at T1; lesson appended at T6 (or "no new lesson" stated)
- [ ] T1: code map queried BEFORE the tree read; any map miss named in the task-sheet
- [ ] T1: tasksheet declares `CODE-SCOPE:` (arms the derailment gate)
