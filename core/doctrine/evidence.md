# Evidence — written for the stranger

> `/qa` reads this at V4 (recording) and V7 (closing). The machines behind it:
> `annotate.py box` (exact-fit box + caption below), `evd_index.py` (the folder
> introduces itself), `xlsx_export.py` (the same record as a workbook), and
> `evd_check.py` (the gate that refuses a folder a stranger could not read).
> Ported from the owner's ai-qa framework, 2026-09-08.

Every artefact this lane produces has one audience: **a person with no context,
six months from now, deciding whether to trust a verdict.** Often that person is
you, and you will remember nothing.

## What makes evidence good

**Named for what it shows.** `03_total_after_save.png`, never `03.png`. The
filenames are the first thing a reader sees, and a folder of numbers forces them
to open every file to find the one that matters.

**Annotated.** One box on the region that carried the verdict, with a caption
saying what it proves. A red rectangle with no words explains nothing; a
full-page screenshot with no box makes the reader guess. Both are common, both
are useless.

**Self-contained.** The case manifest says what was done in plain language, so
the images confirm a story the reader already has rather than being a puzzle.

**Honest about what it is not.** Evidence from a different build, a different
account or a previous session is labelled as such — or discarded. Stale evidence
that looks current is worse than none.

**Anchored to an environment.** The report's `ENVIRONMENT: <name — url>` line
says where every verdict came from — `local`, `dev`, `stg`, `prod` — and the
gate refuses a report without it. A bug found on staging is not evidence about
production; a pass on a laptop is not evidence about anything shared. The
`APP: UP … · env: <name>` line quoted into the sheet is the proof the two agree.

## The manifest, per case

```
TITLE:        Changing a quantity and pressing Save recalculates the total
KIND:         acceptance
RESULT:       PASS | FAIL | BLOCKED
AS:           staff@demo (role STAFF)
PRECONDITION: order #4102 exists, status Pending, 2 × item A at 150,000 (checked read-only at 10:02)
ENTRY:        signed in → Orders → filter "Pending" → row #4102 → "Edit"
STEPS:        1. clear "Quantity" · 2. type 3 · 3. press "Save"
EXPECTED:     "Total" reads 450,000 ₫ (spec §3.2)
ACTUAL:       "Total" reads 450,000 ₫; banner "Order #4102 saved" — as expected
AFTER:        list row shows 3 · "Total" 450,000 survives a reload · "Pending" badge unchanged
BACK:         Back returns to Orders with the "Pending" filter kept; Cancel discards the change
PERSONA:      the daily operator — keyboard, Enter to save, 200th time today
OBSERVATIONS: the Pending badge in the sidebar still read 12 after the save until a manual refresh
```

Every field is there because a verification went wrong without it:

- **AS** — half of all interface defects are role-shaped. A verdict with no
  actor cannot be reproduced or trusted.
- **PRECONDITION** — resolved read-only, now. An id from the ticket may not
  exist any more, and an empty list from stale data is "data moved", not a defect.
- **ENTRY** — as a click path. See `red-flags.md`.
- **AFTER** — including the reload. This is where "it works" most often stops
  working.
- **BACK** — Cancel that does not cancel, filters that reset. Cheap to check,
  frequently broken.

## The coverage decision, per pack

The root `manifest.md` carries one more thing the gate will not do without: a
`COVERAGE:` block that states, for the two lenses a verifier skips in silence
more than any other — **security** and **accessibility** — either the case that
covered it or an out-loud waiver with a reason.

```
COVERAGE:
- security: TC_4        (or)  security: n/a — read-only display, no auth/session/write path
- accessibility: TC_6  (or)  accessibility: n/a — backend migration, no UI in this change
```

The gate cannot decide *when* a lens applies — that is judgement — but it refuses
the *silence*, because "nobody wrote it into the ticket" is precisely how a whole
class of defect goes untested while the pack looks finished. A waiver is a
five-second honest answer; a pack that says nothing about security or
accessibility is one that never decided, and never deciding is how the gap hides.
See `competencies/qa/qa-security-probes.md` and the stack profile's fidelity gate (`ui_fidelity.mjs`) and `roles/design.md`.

The fields are the skeleton. How each value is *written* — the title as a
sentence about behaviour, steps with the exact value typed, expected as an
observable fact and actual in the same shape — is `competencies/qa/qa-case-writing.md`, and it is
what lets a stranger read the record in fifteen seconds. The gate refuses an
EXPECTED or ACTUAL that is only a judgement word ("works", "failed"), because
present is not the same as written.

Three more are optional in the gate and expected by the reader:

- **PERSONA** — which of the four people in `competencies/qa/qa-user-mindset.md` you were being,
  so the reader knows why the journey pressed Enter instead of Save, or left
  and came back. A journey with no persona is a route.
- **HEURISTIC** — on an exploratory case, the one heuristic from
  `competencies/qa/qa-heuristics.md` you were applying, and its timebox. A heuristic you ran but
  did not name was a hunch.
- **OBSERVATIONS** — what you saw that is *not* the verdict: the badge that
  did not update, the pause, the label two panels away that now names the
  wrong thing. No severity, no RESULT change. One click to see if it repeats,
  one line here, and it reappears in the report's Observations section. The
  thing you noticed and did not write down is the ticket somebody files next
  week.

## The report

Different audience, different rules. `REPORT.md` is read by people who do not
work in the code: a product owner, a manager, sometimes a customer.

- **The first five lines are the report.** The verdict word, then three
  lines — *Verdict*, *What it means*, *Next step* — that a product owner could
  paste into a chat and the team would know what to do. `competencies/qa/qa-report-writing.md`
  has the template, the section shapes and the language rules; the bullets
  below are the floor it stands on.
- **Black-box voice.** What a user does and what the product does. No file
  paths, no route names, no internal vocabulary — those go in the appendix.
- **The bar:** a non-programmer reads it in two minutes and understands what was
  asked for, what was checked, what happened, and what should happen next.
- **The verdict first**, in a word, at the top. Everything after it is support.
- **Uncertainty stated, not hidden.** "I could not verify the refund path
  because no test account has refund permission" is a useful sentence. Omitting
  it to make the report look complete is a lie of structure.
- **Observations kept apart from findings.** A section of its own, after the
  conclusion, for what was seen but not judged. A reader who wants only the
  verdict stops before it; a reader planning next week's work starts there. Fold
  them into the findings and the severity table lies; drop them and the report
  pretends it saw nothing but what it was asked.

## Evidence and git

Text commits; binaries do not. Reports, manifests, verify sheets, debate cards,
database checks and journey scripts all go into version control — a verdict that
lives on one laptop is not reproducible, and an unreproducible verdict is
indistinguishable from a fabricated one.

Images are attached to the ticket instead, and the manifest records their names
and checksums, so a clean checkout can still tell you what was captured even
when the pixels are gone.
