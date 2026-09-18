# Review dossier — VT-31 (init prefills app.* for Next repos)

**Provenance, stated plainly:** both cards were written by the implementing session, not by
spawned reviewers. Every bullet is a command that was run on 2026-09-18 with the output it gave;
the RED/GREEN transcript is in `evd/VT-31/dev/proof.md` §2.

## R1 — implementation review (mutation probes)
APPROVE

Tried to break:
- forced the detection off at src/cli/init.mjs:143 (`false && detectNextApp(root)`), kept the five new checks, ran `node tests/e2e.mjs` — RED on exactly the three behaviour checks (url+port, start+health, summary line), 201/204. Restored: 204/204.
- asked whether the port survives a symlinked spelling of the same checkout: `node /tmp/vt31/probe-b.mjs` → `/var/tmp` and `/private/var/tmp` both 3297. This was a real defect in the first cut, caught by the suite (the test hashed `/var/folders/…`, init hashed `/private/var/…`); fixed at src/cli/init.mjs:479.
- checked the empty-app path is byte-identical for non-Next repos: the template writes `start: "${app.start}"` at src/cli/init.mjs:220, which renders `start: ""` when the block is empty — e2e §14c's `.replace('  start: ""', …)` still matches (the whole suite is green), and the `noNext` fixture check asserts `start: ""` and `url: ""`.
- checked the documented config block is untouched: `node tests/conformance.mjs` → 17 fixtures OK, including "README documented config (verbatim)".

Traces: src/cli/init.mjs:143, src/cli/init.mjs:479, src/cli/init.mjs:220, tests/e2e.mjs:345, `node tests/e2e.mjs`, `node tests/conformance.mjs`

## R2 — adversarial read: can the prefill mislead a lane the way the empty block did?
APPROVE

Tried to break:
- two checkouts on one machine: `derivePort` at src/cli/init.mjs:475 is fnv1a over the realpath, range 3100–3899; three fixed paths gave 3660, 3717, 3698. A collision is possible (1 in 800 for two arbitrary paths) and is then visible: `app_check.sh` probes the URL and the owner sees the pinned port in init's summary — not silent, and cheaper than the E7 failure it replaces. Verifying the listener's owner at gate time is VT-30's job and is named in Out of scope.
- a repo that declares `next` but has no `prisma/schema.prisma` (profile `node`): detection at src/cli/init.mjs:464 reads dependencies + devDependencies, not the profile, so it is prefilled too — the arm's problem was "no app to drive", which does not depend on Prisma.
- an unparseable package.json: `detectNextApp` returns false in its catch, so init keeps the empty block instead of crashing — the same posture `detectProfile` already takes.
- looked for a second place the empty block is assumed: `grep -rn 'start: ""' tests src core` → four hits: tests/e2e.mjs:356 (this ticket's non-Next check), tests/e2e.mjs:553 (§14c's replace, still matching), src/cli/init.mjs:147 (the empty-app object itself), core/templates/vteam.config.example.yaml:42 (the shipped example, a conformance fixture — left as is, its comment already says "e.g. npm run dev"). No consumer parses the block for emptiness; the GUIDE bullet at docs/GUIDE.md:367 now documents the prefill, and its fenced config block (the other conformance fixture) is unchanged.

Traces: src/cli/init.mjs:475, src/cli/init.mjs:464, docs/GUIDE.md:367, `grep -rn 'start: ""' tests src core`
