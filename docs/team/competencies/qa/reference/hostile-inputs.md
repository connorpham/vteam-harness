<!-- Reference table for qa-hostile-inputs. Verbatim from connorpham/ai-qa core/doctrine/hostile-inputs.md
     (read 2026-09-07). The competency is the METHOD for choosing from these; this is the data. -->

# Hostile inputs — what a real user will type by accident

> `/qa` opens this in V2 when it writes the boundary case. `/triage` opens it in
> T3 when varying the data. Pick two or three rows that fit the field in front
> of you; never paste the whole table into a test plan.

This is not a security catalogue — that is `security-probes.md`, the input an
attacker sends on purpose. Every value below is instead produced by ordinary
people doing ordinary work: pasting from a spreadsheet, living in a different
locale, having an apostrophe in their name, being paid in a currency with no
decimals. If the product is used by a thousand people, each of these arrives
this week. (The same character often lives in both files — the apostrophe in
`O'Brien` here, and the apostrophe that starts `' OR '1'='1` there. The value is
the same; the intent, and therefore the case, is different.)

**The oracle rule still applies to every row.** The table says what to try. The
spec says what should happen. Four outcomes need no citation, because no
specification anywhere permits them: **a crash or raw error shown to the user,
silent data loss or corruption, one person seeing another's data, and one
action producing two records.** Everything else — whether spaces are trimmed,
what the error says, whether `1.000` is a thousand — is either cited or written
up as a decision request.

## Text fields

| Try | A real person does this because | What usually breaks |
|---|---|---|
| Empty | They skipped it | Saved as empty string, not null; "required" not enforced on edit, only on create |
| Whitespace only (`   `) | Space bar to "clear" it | Passes `required`; sorts to the top of every list forever |
| Leading or trailing space | Pasted from Excel or a chat | Lookup fails; duplicate check misses; `"abc "` and `"abc"` become two customers |
| Exactly the max length, and max + 1 | Long names are normal | Off-by-one; counter says 0 remaining while the server rejects |
| Very long (5,000 chars) | Pasted the wrong thing | Layout breaks; the database truncates silently; the export row wraps |
| A newline in a single-line field | Pasted from a document | Two lines in the CSV; the name splits across cells |
| `O'Brien`, `Nguyễn Thị Ánh`, `José` | Their name | Apostrophe breaks a query or a display; the accent is stripped on search; the display shows `Nguy?n` |
| Emoji, combining characters, right-to-left text | A phone keyboard; an Arabic address | Counted as two characters; truncated mid-glyph; the layout flips |
| A zero-width space or non-breaking space | Copied from a web page | Looks identical, matches nothing |
| `<b>hello</b>`, `{{name}}`, `=SUM(A1)` | A message about HTML; a template example; a spreadsheet formula | Rendered instead of displayed; runs when the CSV is opened in Excel |
| The words `null`, `undefined`, `NaN`, `None`, `0` | A field that once showed them, copied back | Treated as absent, or as a number |
| A URL | A note field that contains a link | Auto-linked when it should not be, or the reverse |

## Numbers

| Try | Because | Breaks |
|---|---|---|
| `0` | It is a real value | Treated as empty; the discount of 0% becomes "no discount set"; division |
| Blank **and** `0` **and** `-0` | These are three different classes | Only one of them is handled |
| `-1` | A minus was typed, or a refund | Accepted where quantity must be positive; the total goes negative and pays the customer |
| `1.5` where an integer is expected | The unit is not obvious | Rounded silently, truncated silently, or stored as 1.5 items |
| `0.1 + 0.2` shapes: `19.99 × 3` | Every basket | `59.97` becomes `59.970000000000006` and the invoice shows it |
| `1,000` · `1.000` · `1 000` | Their locale | A thousand becomes one, or one thousand becomes one point zero |
| Leading zeros: `007`, `0084` | Codes, phone numbers, postal codes | Stripped, then the code no longer matches |
| The maximum plus one · a 20-digit number · `1e10` | A fat finger; a paste | Overflow; scientific notation in the display; the database rejects with a raw error |
| Eastern Arabic digits `١٢٣`, full-width `１２３` | Their keyboard | Rejected as "not a number" for a number |
| Exactly the boundary | "over 100" and "100 or more" are different products | The spec says one and the code does the other |

## Money

| Try | Because | Breaks |
|---|---|---|
| A currency with 0 decimals (VND, JPY) next to one with 2 (USD) and 3 (KWD) | International customers | `100000.00 ₫`; or the 3rd decimal lost |
| Sum of rounded lines vs rounded sum | Every invoice with tax | The lines add to `100.01`; the total says `100.00`; the accountant rejects it |
| Discount greater than the subtotal | A fixed-amount coupon on a small order | Negative total; the store pays the customer |
| The same coupon applied twice | Double-click, or two tabs | Two discounts |
| Price changed while the item was in the cart | Merchandising happens | The cart shows the old price; the order charges the new one; nobody told the customer |
| A refund larger than the payment · a second refund of the same payment | Support pressure | Accepted |
| Tax on the discounted amount vs on the gross | The rule differs by jurisdiction | Cited in the spec? If not, this is a decision request, not a guess |
| Rounding mode | Half-up, half-even, truncate — all three exist in production systems | `2.5 → 2` in one place and `3` in another |

## Dates and time

| Try | Because | Breaks |
|---|---|---|
| Today · yesterday · tomorrow | The obvious three | "Today" is computed on the server, in a different day from the user |
| 23:59 and 00:01 on a boundary day | Month-end reports; deadlines | The order at 23:59 falls into next month; the deadline "today" expired an hour early |
| 29 Feb · 30 Feb · 31 Apr | A date picker that allows them, or a typed date | Accepted, then crashes on save; or silently moved to 1 Mar |
| 31 Jan + 1 month | Subscriptions | 3 Mar, or 28 Feb, or an error — which one does the spec say? |
| The DST switch day (the missing hour, the doubled hour) | Twice a year | A 1-hour meeting is 0 or 2 hours long; the daily job runs twice or not at all |
| A user timezone that is a different date from UTC | Anyone east of London at breakfast | The birthday, the deadline, the "created today" filter are off by one |
| End before start · end equals start | A slip | Accepted; a negative duration; a zero-length booking is charged |
| Year 1900 · 1970 · 2038 · 9999 · a two-digit year | Legacy data, a typo | Epoch zero shows as "1 Jan 1970"; `31/12/99` |
| `dd/mm/yyyy` typed into a `mm/dd/yyyy` field | The locale of the user, not the developer | 4 July becomes 7 April, and both are valid dates so nothing complains |
| A relative label ("2 hours ago") next to the absolute time | Both are shown | They disagree because one uses the server clock |

## Selections, lists, and search

| Try | Because | Breaks |
|---|---|---|
| Nothing selected · everything selected · everything minus one | Bulk actions | "Select all" acts on the page, or on the whole table — which did the spec say? |
| The option that was deleted after the page loaded | Two people, one list | Saved with a dangling reference, or a raw error |
| A list of 0 · 1 · page-size · page-size + 1 · 10,000 | Real data volume | Empty state missing; pagination off by one; the export times out |
| Sort with ties · sort with nulls | Names repeat; fields are optional | Order changes on every refresh; nulls first on one screen, last on another |
| Filter that matches nothing | Typo | Blank page with no message |
| Search: `Nguyen` for `Nguyễn` · uppercase · a trailing space · a quote · a single letter | Ordinary searching | No match on accents; a crash on the quote; the single letter returns everything and times out |
| The result that opens | Clicking it | Opens the wrong record when two share a name |

## Files

| Try | Because | Breaks |
|---|---|---|
| 0 bytes | An empty export from another system | Accepted, then unreadable |
| Exactly the size limit · one byte over | Photos are big | The error names the wrong limit, or arrives after the whole upload |
| Right extension, wrong content · wrong extension, right content | Renamed files | Accepted and later crashes a viewer; or rejected although it is fine |
| A filename with spaces, Vietnamese characters, 200 characters, no extension | Real filenames | Download link broken; the name mangled |
| The same file twice | Retrying | Two attachments, or the second silently replaces the first |
| Cancel at 90% | Impatience | An orphan on the server; a record that says it has a file |
| A CSV with a UTF-8 BOM · without one · with `;` as the separator | Excel in Europe and Vietnam | The first header is `ï»¿id`; everything lands in one column |

## Contact data and identifiers

| Try | Because | Breaks |
|---|---|---|
| `First.Last+tag@Example.COM` · an IDN domain · a trailing dot | Valid emails | Rejected; or lower-cased on one screen and not the other, so the same person is two accounts |
| Phone with spaces, dashes, `+84` vs `0`, an extension | Every human writes phone numbers differently | Duplicate customers; the SMS goes nowhere |
| A postal code with a leading zero | Half the world | Stripped to an integer |
| An id that does not exist · a deleted record's id · **someone else's id, as this role** | A stale link; a curious user | A raw error; a soft-deleted ghost; **another customer's order** — the one that goes to the top of the report |
| An id with a different case, or with whitespace | Copied from a chat | Two records, or none |

## How to use this file in a case

Pick, do not sweep. For the field the ticket touches, choose:

1. **one value the spec explicitly refuses** — that is the boundary case's spine,
2. **one value a real user will produce this week** — from the row that fits,
3. **one value from the "no citation needed" set** — the double action, the
   other person's id — if the ticket's surface can reach it.

Record the value exactly as typed in STEPS, and the rule it tests in EXPECTED
with its citation. A boundary case whose input was chosen because it was
convenient is a happy-path case with a different number.
