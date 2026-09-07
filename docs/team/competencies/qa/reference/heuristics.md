<!-- Reference table for qa-heuristics. Verbatim from connorpham/ai-qa core/doctrine/heuristics.md
     (read 2026-09-07). The competency is the METHOD for choosing from these; this is the data. -->

# Heuristics — the working toolbox of a senior tester

> `/qa` reads this in V2 when it chooses the exploratory case and when a
> boundary case needs a sharper edge. `/triage` reads it in T3 to decide what
> to vary. `/regress` reads RCRCRC in R2.

Scripted cases confirm what someone already thought of. Heuristics find what
nobody did. A heuristic is a fallible rule of thumb: it tells you **where to
look and what to try**, and it is allowed to be wrong. It never tells you what
the correct answer is — that is still the spec, or still unknown.

Every heuristic below is used the same way: **name it, timebox it, record what
you tried even when you found nothing.** A heuristic you ran and did not write
down was a hunch, not a test.

## Consistency oracles — HICCUPPS

The single most useful set in this file, because it answers the question this
lane hears every day: *"there is no spec for this — so I can say nothing?"*
No. You cannot call it a defect against a spec. You can report that the product
is **inconsistent with something it should be consistent with**, name which,
and send it back as a decision request. That is a real finding with a real
owner.

| Consistent with… | The question | Example finding |
|---|---|---|
| **History** | Does it behave as it did in the previous release? | The list used to keep its filter after an edit; it no longer does. Nobody asked for that. |
| **Image** | Does it match the image the organisation wants to project? | A stack trace on the checkout page of a bank. |
| **Comparable products** | Does it work the way users' other tools work? | Every spreadsheet on earth treats Enter as "commit the cell". Here it deletes the row. |
| **Claims** | Does it match what the product itself says — the tooltip, the help text, the ticket, the marketing page? | The button says "Save draft"; the record is published. |
| **User expectations** | Would a reasonable user be surprised? | A 30-second wait with no spinner. A Delete with no confirmation. |
| **Product** | Is it consistent with itself? The same thing on the next screen? | Dates are `dd/mm` on the list and `mm/dd` on the detail. Currency has decimals on one screen and not the other. |
| **Purpose** | Does it serve the purpose the feature obviously exists for? | A search that finds "Nguyen" but not "Nguyễn" in a Vietnamese product. |
| **Statutes and standards** | Does it obey the law, the tax rule, the accessibility standard, the ISO date format it claims? | VAT rounded per line where the tax authority requires rounding on the total. |

**How to report a consistency finding.** Not `FAIL — defect`. Write: *"Inconsistent
with <which oracle>: <the two things that disagree>. No written specification
decides which is correct. Decision requested from <owner>."* Severity is set by
consequence as usual — an inconsistency that loses money is still Critical —
and ORIGIN is `SPEC`, because the missing decision is the defect.

Two of these need no decision request. **A crash, a raw error shown to a user,
silent data loss, or one role seeing another's data** violates every one of the
eight at once; no specification anywhere permits them. Report those as defects
with the consequence-based severity and move on.

## Product coverage — SFDIPOT

When you are not sure you have looked everywhere, walk the seven letters. One
question each, one line in the sheet each.

| | Ask | Typical miss |
|---|---|---|
| **Structure** | What is it made of — files, services, jobs, third parties? | The nightly job that recalculates the thing the screen shows. |
| **Function** | What does it do — including the error handling, the logging, the undo? | The audit log that should have a row and does not. |
| **Data** | What goes in, comes out, is stored, is derived? Cardinality, lifetime, ownership? | The derived total that is stored, then not recalculated when a line changes. |
| **Interfaces** | Every way in and out — UI, API, import, export, email, webhook, print. | The export still carries the old field name. The PDF disagrees with the screen. |
| **Platform** | What it depends on — browser, OS, device, locale, timezone, screen size. | Works in Chrome with `en-US`; the date parser fails in `vi-VN`. |
| **Operations** | How it is really used — by whom, how often, in what environment, with what data volume. | Fine with 12 rows, unusable with the 40,000 the client has. |
| **Time** | Anything that depends on when — timeouts, sessions, schedules, month-end, DST, "today". | The report that is right every day except the first of the month. |

## Data heuristics — the shapes of a value

Reach for these when designing the boundary case, and pair them with the
concrete values in `hostile-inputs.md`.

- **Zero, One, Many.** Every list, every count, every relation. Empty is a different program from one, and one is a different program from many. The page-size-plus-one is where Many usually breaks.
- **Goldilocks.** Too small, too big, just right. The minimum minus one; the maximum plus one; exactly the limit, because "over 100" and "100 or more" are different products.
- **Some, None, All.** Select none of the checkboxes. Select all of them. Select all then deselect one.
- **First, Last, Middle.** The first row on the page, the last, and one in the middle after sorting the other way. Off-by-one lives at the ends.
- **Before, During, After.** Act before the record exists, while it is being saved, and after it has been closed. "During" is where double-submits and races live.
- **CRUD.** Every entity: create it, read it everywhere it appears, update it, delete it — and then read it everywhere again. Then try to delete something that is still referenced.
- **Same again.** Do the exact same action twice. The second time is a different test: the duplicate, the idempotency, the "already in that state".

## Interruptions

At every step of a journey, not only at the end, ask what happens if the person
is interrupted **right now**:

```
cancel · back · refresh · close the tab · timeout / session expiry · log out in
another tab · network drops for 10 seconds · switch user · the phone rings and
they return in 40 minutes · the record is changed by someone else meanwhile
```

Pick two per journey, at the step where interruption would hurt most — usually
between "the user pressed the button" and "the confirmation appeared".

## Follow the data

Enter a value in one place. Then find **every place it appears** and check that
they agree: the list, the detail, the header total, the badge, the search index,
the export, the report, the email, the audit log, the API response, the PDF. A
value that is right on the screen where it was typed and wrong two screens away
is the classic fix-one-place defect, and nobody's happy path visits the second
screen.

## Tours — a way in when a screen is new to you

Choose a tour, walk it for its timebox, write what you saw. One paragraph each;
the names are the memory aid.

| Tour | What you do |
|---|---|
| **Money tour** | Follow everything the customer pays for or the business earns from. Every number that is money gets read back and re-added by hand. |
| **Landmark tour** | Visit every major screen once, from the menu, as each role. Is anything missing, misnamed, or reachable by a role that should not have it? |
| **Back-alley tour** | The features nobody uses — the import, the bulk action, the settings page. Least used means least tested. |
| **Bad-neighbourhood tour** | Wherever defects clustered before (`known-issues.md`, closed bugs). They cluster again. |
| **Garbage-collector tour** | Create things and then delete or cancel every one of them. Watch what is left behind: orphans, counts that do not go down, emails that still go out. |
| **Couch-potato tour** | Do the least possible. Accept every default. Leave every optional field empty. Press the one obvious button. |
| **Obsessive-compulsive tour** | Do everything twice. Save twice, submit twice, add the same item twice, apply the same coupon twice. |
| **Supermodel tour** | Look only. Alignment, truncation, wrapping at 150% zoom, a long name, a long number, a missing translation. Cosmetic — record as Minor, but record it. |
| **Intellectual tour** | Ask the product the hardest questions it claims to answer: the largest order, the oldest customer, the report across a year boundary. |

## RCRCRC — what to regress when you cannot regress everything

Used by `/regress` to rank, and by `/qa` to choose the whole-screen case:

**R**ecent (what changed) · **C**ore (what the business cannot run without) ·
**R**isky (what is fragile, tangled, or touches money) · **C**onfiguration-sensitive
(what behaves differently per role, locale, plan, or flag) · **R**epaired (what
was fixed recently — fixes break neighbours) · **C**hronic (what keeps breaking).

## Using a heuristic inside the case budget

The budget is two to five cases, and one of them may be `KIND: exploratory`.
That case is where a heuristic gets its own manifest:

```
KIND:       exploratory
HEURISTIC:  interruptions — refresh between Pay and the confirmation
TIMEBOX:    20 minutes
STEPS:      1. … 2. press Pay 3. refresh at once 4. read the order list and the payment record back
EXPECTED:   one order, one payment, one email — the spec (§4.1) says an order is created once
ACTUAL:     …
```

`EXPECTED` still cites the spec when it can. When it cannot, the case records a
difference and the report says which consistency oracle it leans on. What the
heuristic buys you is not permission to guess — it is a **reason to look where
the happy path does not go.**
