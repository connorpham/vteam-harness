# Knowledge base — lessons in transit, not in residence

## §0 — Reading and graduation rules

- Pipelines read ONLY this section + the INDEX table, then open just the lessons
  whose tags match the current work. Never read the whole file.
- **Graduation over accumulation.** A lesson's destiny is to LEAVE this file:
  machine-checkable → into a gate script (with mutation proof); unconditional →
  into the workflow's own text; recurring environment pattern → into
  known-issues.md (KI-nnn). After graduating, delete it here.
- Cleanup thresholds: INDEX > 25 rows or file > 250 lines → a consolidation pass
  becomes due work.
- A rule that cannot go RED gets skipped — if a lesson keeps being violated,
  it isn't a lesson, it's a missing gate.

## INDEX

| Title | Tags | Where it graduates to |
|---|---|---|

## KB-R1 · Verify a claim against HEAD, not against the edit you just made

**Tag:** review-conduct · evidence · self-report
**Found:** VT-22, across four review rounds, 2026-09-11.

**The pattern.** Four claims in four consecutive review replies did not survive a check the
reviewer could run in under a minute:

1. "the docstring now documents `advisory`" — it did not; the reviewer ran `ast.get_docstring`.
2. "the selftest print now names the new branches" — it did not; the string was never written.
3. "gate GREEN" — measured on the working tree **before** the commit, so `graph_check` had not
   yet seen the commit whose CODE-SCOPE it judges. True of the tree, false of the branch.
4. The same selftest print, reported fixed a second time, **quoting text that existed nowhere in
   the repo**. A multi-line `print(...)` had been the target of a single-line `str.replace` that
   matched nothing, and the reply was composed from the intent of the edit.

**Why it happens.** Each of these was written from what the edit was *meant* to do, not read back
off the artefact. A `.replace()` that matches nothing is silent; a script that prints "done" after
it is lying politely. The failure is invisible to the person who made it and free to catch for
anyone else, which is the worst possible split.

**The rule.** Before writing "now reads…", "is now documented", or "gate is green" into a report,
run the check against the thing the reader will open:

    git show HEAD:<path> | grep -c "<the exact string you are about to quote>"

and for a gate, run it **after** the commit, never before. For a structured artefact, parse it
(`ast.get_docstring`, `json.load`, the repo's own config parser) rather than eyeballing it.

**Cheapest guard for a script that edits files:** assert the replacement happened.
`assert s.count(old) == 1` before writing turns a silent no-op into a stack trace — this session
used it in most places and every miss above is where it did not.

**Addendum, found the round after this entry was written.** "The tree is clean" is a claim like any
other, and `git status --porcelain` is its `grep -c`. This entry's four instances are all about
reading back a *file*; the fifth was about reading back the *tree*. The report said "clean tree: 0
dirty files" — true when the command ran, and then `vteam update` rewrote the deployed mirror and
nobody looked again. `HEAD` shipped with the fix in `core/scripts/gate.py` and the old driver in
`.vteam/scripts/gate.py`, which is the copy this repo actually executes, and `doctor` could not see
it because it compares the mirror against the manifest and both were stale together.

So the round-3 diagnosis — *"true of the working tree, false of the branch"* — runs in both
directions. That time the commit was missing from the check; this time the check was missing a
commit. **Produce a state report by running the command at the moment you write it**, not by
remembering that you saved everything.

