# Changelog

What changed in each released version, newest first. Dates are the npm publish date.

Every entry is derived from the commit that bumped `package.json` — not written from
memory. Two versions below were bumped in git but **never reached npm**; they are kept
here because the version numbers are spent and skipping them silently would be a lie.

The current version always has an entry: `tests/e2e.mjs` fails if the newest heading here
does not match `package.json`.

---

## 0.15.4 — unreleased

The README finally describes what the last three releases actually shipped.

- **The specialists have a section.** The seven deep-skill subagents from 0.14.0 were
  installed by `init` and mentioned nowhere in the README — zero occurrences of the word
  "specialist". They now have their own section with a diagram
  (`docs/assets/specialists.svg`), a dispatch table, and the rule that matters: they work
  inside the same `/dev` pipeline, the same evidence rules, the same gates. Specialists
  advise; the lane decides.
- **Watchable dev and QA sessions have a section.** The `app:` capabilities from 0.15.0
  and 0.15.2 — `APP: UP` bring-up proof, a real headed Chrome window per QA journey,
  `/dev` opening the files it edits — were one dense line inside a config table. They are
  now described where someone deciding whether to adopt vteam will actually read them.
- **This changelog exists.** 22 versions shipped before it did.
- Two more guards: the README's selftest count must equal what `doctor` discovers (it
  said 25 in two places and 22 in four *at the same time*), and the newest entry here must
  be the shipping version. Suite total 156 → 157.

## 0.15.3 — 2026-09-03

The README npm actually serves, and a guard on the count that drifted.

- Nine relative links (`LICENSE`, `docs/TUTORIAL.md`, `docs/DESIGN.md`, `SECURITY.md`, …)
  only resolved on GitHub. On npmjs.com and in any `node_modules` copy they pointed
  nowhere. All are absolute now — the README is one file serving two surfaces.
- The selftest count said **22** in four places; `doctor` discovers and runs **25**. Fixed
  in the prose, the pasted `doctor` transcript and both text layers of `commands.svg`.
- The transcript is a real captured run again, which also corrected `55`→`59`
  framework-owned files, `1`→`2` tickets, and removed a duplicated line left by an old
  elision.
- New machine check: the README's selftest count must equal what discovery finds. The
  suite already guarded its own `N checks` claim for the same reason; this number had no
  guard and drifted the same way. Suite total 155 → 156.

## 0.15.2 — 2026-09-02

Watchable dev & QA sessions (VT-2).

- App environment config, headed Chrome by default, and editor opening — so a `/dev` or
  `/qa` session is something a human can sit and watch rather than infer from logs.

## 0.15.1 — 2026-09-02

Maintenance release.

## 0.15.0 — 2026-08-30

Ship the headed-by-default UI evidence to npm installs.

## 0.14.0 — 2026-08-30

Ship the specialist subagents to npm installs.

- The backend, frontend/mobile, DevOps, data, AI/data, QA-automation and security
  specialist agents now land in a fresh install instead of living only in this repo.

## 0.13.1 — 2026-08-24

Ship the command-reference README to npm.

## 0.13.0 — 2026-08-24

Close the 2026-08-24 review holes.

- A TTL knob for verdict expiry, a ledger fence, and the first README truth guard — the
  suite began machine-checking a number the README states about itself.

## 0.12.0 — 2026-08-24

`resume` is a READER, not a store.

- Checkpoint-resume reworked per ops doctrine: it derives the furthest proven stage from
  claim, branch, tasksheet, review dossier, QA verdict and ledger. It stores nothing, so
  nothing can go stale or lie.

## 0.11.0 — never published

`vteam usage` — measured AI-usage history per person, model and day. The version was
bumped in git (`e5066e86`) but no tarball was published under it.

## 0.10.1 — 2026-08-21

Ship the explanatory README and its three diagrams to npm.

## 0.10.0 — 2026-08-21

Evidence a stranger can read, and a tester who behaves like a person.

- QA evidence gained the journey fields (`AS:`, `PRECONDITION:`, `ENTRY:`, `AFTER:`,
  `BACK:`), named screenshots and the boxed verdict shot. An `ENTRY:` that is only a URL
  is refused: typing an address proves the address, not the product.

## 0.9.2 — 2026-08-21

Ship the visuals to npm, and stop the stale-README trap.

## 0.9.1 — 2026-08-21

Ship the reshaped README to npm.

## 0.9.0 — 2026-08-21

The graph round — the work graph made visible, and the four MAST holes closed.

- `vteam graph` renders READY/BLOCKED work and findings; `graph_check` is its gate twin,
  catching dangling edges, dependency cycles, Done tickets without a PASS verdict,
  repeated dispatches and commits straying outside a ticket's declared scope. Each check
  names the MAST failure mode it closes (arXiv 2503.13657).

## 0.8.0 — never published

The scale round — 8h workdays, 24/7 shifts, cross-model review, code map, conflict-free
knowledge files. Bumped in git (`1f687fde`) but no tarball was published under it.

## 0.7.0 — 2026-08-19

Team accountability — the Actor column makes `team.size` real.

- Every ledger row names the human whose session dispatched it. With `team.size > 1` the
  column is machine-mandatory: `log_check` reds a legacy header and any empty Actor cell.

## 0.6.1 — 2026-08-19

One rule, one home — the consistency round.

## 0.6.0 — 2026-08-18

Field-trial findings #17–#20, plus the 15-minute tour.

- Finding #17 is why `code_paths` is derived from the repo's real layout at init: a
  hardcoded `[src/, prisma/]` default silently lost the review fence on repos whose code
  lives elsewhere.

## 0.5.0 — 2026-08-18

The greenfield intake release — `/plan`.

- Interviews the owner section by section, writes a BRIEF then a PRD whose requirement
  rows carry gate-compatible codes, and registers the PRD as a source document so the
  verbatim gate guards everything sharded from it.

## 0.4.1 — 2026-08-18

Ship the rewritten README to npm.

## 0.4.0 — 2026-08-18

Per-project customization; record the compatibility debt.

## 0.3.0 — 2026-08-18

The proof-of-done release.

## 0.2.0 — 2026-08-18

The audit-hardening release.

## 0.1.0 — 2026-08-17

First published version — LICENSE, repository metadata, packaging manifest.

---

## A note on provenance

`release.yml` publishes with npm provenance (Sigstore) when a GitHub release is drafted on
the version tag. Versions from 0.13.0 onward were published from a workstation instead, so
they carry npm's registry signature but **no provenance attestation**. Publishing through
the release workflow is what makes the README's provenance claim true.
