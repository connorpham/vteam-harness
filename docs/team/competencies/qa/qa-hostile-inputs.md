---
name: qa-hostile-inputs
description: "Use when choosing the concrete values for a boundary case — text, numbers, money, dates, files, emails, ids — and when a field has only ever been tested with the value the developer typed."
role: qa
loads: V2
applies: always
---

# Hostile inputs — what a real user will type by accident

## Identity

You know that if a thousand people use the product, every awkward value arrives
this week: the trailing space pasted from Excel, the name `Nguyễn Thị Ánh`, the
`1.000,00` from another locale, the coupon applied twice, the file renamed to
the wrong extension. None of it is an attack (that is `qa-security-probes` —
same characters, different intent); all of it is Tuesday.

## When this applies

- V2, writing the boundary case for whichever field the ticket touches.
- Any input the pack has only tested with one, convenient, valid value.

## Decide

**Pick, never sweep** — for the field in front of you, choose exactly three:

1. **One value the spec explicitly refuses** — the boundary case's spine.
2. **One value a real user produces this week** — from the field type's table in
   `reference/hostile-inputs.md` (text · numbers · money · dates/time ·
   selections/search · files · contact data/ids).
3. **One from the no-citation set, if the surface can reach it** — the double
   action, someone else's id.

The highlights per type, from the reference tables:

| Type | The three that pay most |
|---|---|
| Text | trailing space (lookup misses, duplicates split) · exactly max and max+1 · `O'Brien` / `Nguyễn` / emoji (query, search, display) |
| Numbers | `0` vs blank vs `-0` (three classes) · `-1` where positive is assumed · `1,000` vs `1.000` (locale) |
| Money | 0-decimal currency next to 2-decimal · sum-of-rounded-lines vs rounded-sum · discount > subtotal · the same coupon twice |
| Dates | 23:59/00:01 on a boundary day · 31 Jan + 1 month · a user timezone that is a different date from UTC |
| Lists/search | 0 · 1 · page-size+1 · sort with ties and nulls · `Nguyen` finding `Nguyễn` |
| Files | 0 bytes · one byte over the limit · right extension wrong content · the same file twice · cancel at 90% |
| Ids | someone else's id as this role · a deleted record's id · leading zeros stripped |

## Rules

- **The oracle rule applies to every row**: the table says what to *try*; the
  spec says what should happen. *Otherwise:* the table becomes a defect list and
  half of it is opinion.
- **Four outcomes need no citation** — a crash or raw error shown to a user ·
  silent data loss or corruption · one person seeing another's data · one action
  producing two records. No specification anywhere permits these. *Otherwise:*
  the obvious catastrophe waits for a spec paragraph while the customer screams.
- **Record the value exactly as typed in STEPS** — `type "SHOP-142 " — note the
  trailing space` — and the rule it tests in EXPECTED with its citation.
  *Otherwise:* the FAIL cannot be reproduced and dies in triage.
- **Whether spaces are trimmed, what the error says, whether `1.000` is a
  thousand — cited, or a decision request.** *Otherwise:* you are legislating
  locale policy from the test chair.

## Reviewer lens

- Which three values were chosen, and from which rows? Was any chosen for convenience?
- Does one case exercise the no-citation set on this surface — and is its outcome written as the floor, not as a cited rule?
- Take one field the ticket touches and one row the pack skipped: would it have hit?

## Sources

connorpham/ai-qa `hostile-inputs.md` — full tables mirrored at
`reference/hostile-inputs.md` (kept verbatim; this file is the method for
choosing from them) · Ministry of Testing Test Heuristics Cheat Sheet (data
type attacks).

Rationalizations, red flags and a worked example live in `reference/qa-hostile-inputs.md` — opened when needed, never loaded by default.
