# VT-15..VT-22 — review dossier

Two fresh reviewers on the branch, given different halves and told to break it. **Both returned
REQUEST-CHANGES.** Seventeen findings; every blocker was reproduced before it was accepted, and
every one is fixed in this branch. The cards are summarised below with the traces that made them
checkable.

## R1 — the checker scripts

VERDICT: **REQUEST-CHANGES**

**Tried to break it:**
- Built a pack whose REPORT cites three cases and whose folder holds one — the exact TB-8 failure
  VT-17 exists to catch — and swept it under each declared status. `Done` → red. **`Closed` →
  GREEN. `Resolved` → GREEN.** Ticket file absent → GREEN. The config declares
  `done_statuses: [Done, Closed, Resolved]`; the code hardcoded `("done",)`.
- Closed a ticket with no QA verdict by writing "Q2" in it. Accepted for `Closed won't-fix
  (decision Q2)` and **equally accepted** for "We will revisit the rest in Q2 next year" and
  "Out of scope: unrelated to Q2". `decision_settled()` also returned True for `⏳ UNDECIDED`.
- Hid a missing decision behind the string "UTF-8": a row citing an absent `D99` reds, and the
  same row plus `encoding=UTF-8` only warns. Same for `SHA-256`, `RFC-9457`, `PR-63`.
- Measured one backlog twice and got a fifth and sixth number: absolute `--backlog` → 10 files;
  the identical directory by a relative path → 9, with every `profile:` match silently gone.
- Ran the selftests: five of six pass, and **`route_check` has no `--selftest` at all**
  (`error: unrecognized arguments`). Four new gate-affecting branches shipped with no coverage.
- Verified the consumer-layout path for `competency_check` **holds** — `.claude/skills/<lane>/SKILL.md`
  resolves, a role with no workflow is a skip. No finding there.
- Removed Pillow and watched a clean pack turn into a hard red on a closed ticket.

**Traces:** `core/scripts/graph_check.py:164` (`return "DECIDED" in row.upper()`);
`core/scripts/evd_check.py:413` (`strict_statuses=("done",)`); `core/scripts/route_check.py:96`
(the `\b`-prefix regex) and `:172` (the `is_absolute()` branch).

**Findings:** nine. Blocking: the `done`-only closure set, the substring `DECIDED`, the free-text
won't-fix scan, and the Pillow-dependent hard step. Non-blocking: the `log_check` config path and
foreign-key regex, the six-token semantics review (prefix matching, `label:` case-sensitive while
`type:` is not, `type:` inert on this repo's own tickets because none declares `- type:`), the
inverted `--strict` docstring, one-for-four selftest coverage, and the `owned`↔`loads` coupling.

## R2 — the gate driver, the profile manifests, the installer

VERDICT: **REQUEST-CHANGES**

**Tried to break it:**
- Made an advisory failure **upgrade** a weak green: the field-trial-#19 shape printed
  `GREEN (WEAK — only bookkeeping steps ran, ZERO verification of the code)` before, and
  `GREEN (WEAK — no test suite ran…)` after — the strongest banner and its remediation sentence
  gone, because the new steps land in `ran` and are absent from `BOOKKEEPING`. The
  `— ADVISORY FAILED` tail is also built in only one of three branches.
- Turned a hard step non-blocking with one line: `unit: {run: "exit 1", advisory: true}` →
  `GATE: GREEN`, exit 0. `advisory: "false"` (quoted) does the same, because the value is read as
  bare truthiness.
- Adopted vteam into a repo with one closed ticket and pre-standard screenshots:
  **`GATE: RED at evd-ui`** on `missing manifest.md` and a name that breaks `NN_<description>.png`.
  The legacy hatch covered only the subfolder shape.
- Attacked `owned` six ways. A declared-owned **unmodified** file is silently overwritten, because
  the check sits below the refresh branch. A directory matches nothing, silently. A bare string is
  character-split **and written back over the user's manifest**. `../` is inert; an object throws
  cleanly. **Could not find a path where a user loses work** — the carried-forward hash is the
  framework's, so a fork can never be mistaken for framework content.
- Confirmed no masking: an advisory failure followed by a hard failure still reds.

**Traces:** `core/scripts/gate.py:128` (`ran.append` in the advisory branch) with `:143`
(`BOOKKEEPING`) and `:157` (the tail built in the `else` arm); `src/cli/manifest.mjs:89` (the
owned branch, reached only after `:81` has already overwritten) and `:42` (the unvalidated Set).

**Findings:** eight. Blocking: `evd-ui` reddening a repo for its history; the advisory/WEAK
interaction; `owned` not applying to an unmodified file; `requires: "evd"` hardcoded while both
checkers resolve `paths.evidence`, which makes two hard steps permanently skipped with a false
reason on any repo that renames that path. Non-blocking: `owned` validation, `advisory`
undocumented in the file that documents the grammar, `doctor`'s wrong story about owned files, and
no test covering `owned` at all.

## Round 1 — answered

Every blocker is fixed and every non-blocking finding is either fixed or recorded with a reason:

| finding | outcome |
|---|---|
| closure set hardcoded to `done` | reads `tracker.done_statuses`; unreadable status = declared skip. Verified: Done/Closed/Resolved red, In Review passes |
| substring `DECIDED` | matches the declared `✅ DECIDED` marker; `UNDECIDED` no longer settles |
| free-text won't-fix | structured `closed-by:` field, unknown key reds. TB-7 in the field repo was updated to declare it |
| Pillow hard red | `requires_cmd: python3 -c "import PIL"` on all six profiles |
| `evd-ui` reds on history | legacy predicate widened to "no `manifest.md`" — both shapes reported, not failed |
| advisory upgrades WEAK | four steps added to `BOOKKEEPING`; tail note built before all three banners; non-boolean `advisory` reds |
| `owned` skips unmodified files | check moved above the refresh branch; validated; malformed declaration reported and left on disk |
| `requires: "evd"` | dropped from both steps — the sweeps already handle a missing root |
| `term:` prefix matching | both boundaries, plural allowed. Same nine tickets: **98 → 94 files** |
| `profile:` relative path | `resolve()` first |
| `--strict` documented backwards | docstring corrected |
| `log_check` config path + UTF-8 | `pm_dir` passed through; foreign-key test is letters-only with a non-ticket exclusion list |
| `doctor` wrong about owned | owned paths reported separately, and truthfully |
| coverage | `route_check --selftest` added (9 assertions); cases added for both sweeps, the chain rule, the citation rule, three advisory branches, and `owned` in e2e. **171/171** |
| `label:`/`type:` case asymmetry | **recorded, not changed** — changing either is a routing-semantics decision and D13 is the place for it |
| `type:` inert on this repo | **recorded** — vteam's own tickets declare no `- type:` line; the token is exercised on the field repo |
| `owned` ↔ `loads` coupling | **recorded** in VT-22's out-of-scope: a repo pinning a lane workflow reds when a competency ships a new `loads:` |

**Remaining dissent:** none on the blockers. Two reviewer observations are deliberately unresolved
and written down instead: the forced-colors ratio is a two-valued outcome dressed as a measurement
(true, and it is what the mode permits), and `advisory:` remains a one-line additive edit with a
large blast radius — the boolean check narrows the typo case, not the deliberate case. A reviewer
suggested a driver-side allowlist; that is a design change, and it is D-queue work rather than a
fix smuggled into a review round.

## Round 2 — both reviewers re-ran their own attacks, and both found more

Sent back with the fixes and an explicit instruction: re-run the bypasses you built, then attack
the NEW code. Both returned **REQUEST-CHANGES** again. Every round-1 blocker was confirmed closed
by the reviewer who found it; everything new below is a defect the round-1 *fixes* introduced.

**R1 round 2 — what the fixes broke**
- **Deleting one file became a passport past every rule.** The legacy exemption was keyed on "no
  `manifest.md`" — the artefact rule #1 of this checker requires. A closed ticket's failing pack
  flipped to a warning by deleting it. *Fixed:* legacy is now keyed on evidence of the old layout
  (no image matching `NN_*.png` **and** no manifest), which a pack cannot shed without renaming
  every image back.
- **`DEVIATION: WRONG` walked past the gate.** The `needs --oracle` downgrade matched errors that
  only fire when the oracle IS on disk — the opposite of "a declaration a sweep cannot make" — so
  a pack whose own fidelity report said the implementation was wrong passed. The `--bug` half
  could never fire at all. *Fixed:* the branch is deleted; round-1 behaviour was right.
- **`closed-by:` split on whitespace**, so `- closed-by: Q2 — the owner declined` manufactured five
  phantom decisions; and the error message still taught the free-text form that no longer works.
  *Fixed:* commas only, like `blocked-by`, and the message now names the field.
- **`closure_statuses()` crashed on a scalar and disarmed itself on an empty string.** *Fixed:*
  seven config shapes exercised, no crashes, empty falls back to the documented default.
- **The `(?:s|es)?` boundary traded a known false positive for unmeasured false negatives.** *Fixed
  by measurement rather than intuition:* three suffix sets counted across both real backlogs —
  `(?:s|es)?` recovers nothing, `(?:s|es|ly)?` recovers one TRUE match ("concurrently" → VT-5), and
  `(?:s|es|d|ed|ing|ly)?` recovers that one plus **four false** ("form" → "formed"). `-ed`/`-ing`
  is rejected on evidence, with the table in the code so the next reader does not re-derive it.
  The reviewer's verb-form cases are real English and occur in neither backlog; widen the day one
  appears, publishing the same split.
- `npm test` was RED because the changelog moved to 0.19.0 while `package.json` said 0.18.0.

**R2 round 2 — what the fixes broke**
- **A duplicate `skip_reason` under `evd-ui` in all six profiles**, and the parser is last-wins, so
  the shipped skip line blamed a missing `evd/` directory when the real cause was a missing
  Pillow. Identical defect class to round-1 finding 5, reintroduced one line below the comment
  calling it out. *Fixed* in all six, with a repeated-key scan to prove none remain.
- **The new "matched no framework file" warning lied about every in-sync owned path**, because
  `ownedMatched` was set only inside the owned branch, below the two fast paths — so it fired in
  the most ordinary steady state, and right after the hand merge the feature exists for. *Fixed:*
  the match is recorded before the fast paths; a seventh e2e check covers the in-sync case, which
  the first six shared the code's blind spot about.
- **`advisory` was reported documented and was not.** The module docstring — the file that opens
  "read before editing gates.yaml" — did not mention it. *Fixed,* and verified with
  `ast.get_docstring` rather than by eye, which is how it was missed the first time.
- Small ones fixed: the dead `curHash !== newHash` in the owned branch, and the partial-drop case
  now says "N entries ignored" instead of claiming the whole declaration was.

**Both reviewers agreed on one thing worth recording:** recording the allowlist suggestion rather
than implementing it was the right call. R2 argued against its own idea — the TRUST BOUNDARY
already settles deliberate misuse, and hardcoding a set of advisory-eligible step names would put
profile policy inside the driver. The piece worth keeping belongs to `review_check`: a diff that
adds `advisory:` to an existing step should be visible to review.

**Still open, and deliberately:** `log_check`'s foreign-key test is a denylist of acronyms, broken
twice in two rounds (`UTF-8`, then `AES-256`/`IEEE-754`). A denylist has no closing condition —
filed as **D16** to invert it into a declared list of foreign project keys, rather than extend it
one incident at a time.
