<!-- Reference table for qa-checklists. Verbatim from connorpham/ai-qa core/doctrine/checklists.md
     (read 2026-09-07). The competency is the METHOD for choosing from these; this is the data. -->

# Checklists — the reflex checks, by the shape of the feature

> `/qa` opens this in V2 to give the whole-screen case teeth, and in V4 while
> walking. `/triage` opens it in T3 to size the blast radius. Find the shape
> the ticket touches; walk that list; ignore the others.

A seasoned tester does not think about these. They see a table and their eyes
go to the empty state, the sort arrows, the page count. They see a form and
their hand goes to Enter. This file is that reflex, written down, so that a
whole-screen case is a set of specific looks rather than "the rest of the page
still renders."

Every line is phrased as what a real person will do, because that is who finds
it otherwise. Every line still needs the oracle for what *should* happen — except
the four that never do: a crash, lost data, another person's data, or one action
that became two.

## Any form

- Required fields are marked, and the marking matches what the server enforces — on **edit** as well as on create.
- **Enter** submits, or deliberately does not; either way the same thing happens as clicking Save.
- **Tab order** follows the eye; the new field is in it.
- The error appears **next to the field**, says what to do, and **goes away when fixed**. A stale error is a defect people report as "it won't let me save".
- A failed submit **keeps everything typed**. Nothing is retyped.
- **Submit twice** — double-click, or Enter then click — creates **one** record.
- **Cancel discards**, and does not save a draft nobody asked for. Escape and clicking outside the modal behave the same as Cancel.
- Navigating away with changes **warns**, and does not warn when there is nothing to lose.
- Every **default** is the one the spec names; the daily operator relies on it without looking.
- **Browser autofill** lands values in the right fields.
- The success message **names what happened** — "Order #4102 saved", not "Success".
- The list or detail behind the form shows the new value **without a manual refresh**.

## Any list or table

- **Empty state** says so in words and offers the next action. A blank white area is not an empty state.
- **One row** renders correctly — singular labels, no "1 items", pagination hidden or sane.
- **A full page plus one** — the pagination appears, the count is right, the last row is reachable.
- **Sort every column both ways**, with ties and with empty values. Order is stable across refreshes.
- **Filter, sort and page survive** a refresh, a Back, and an edit-and-return. Losing the filter after every edit is the most common "it works but I hate it".
- The **row count** matches the badge, the header, and the export.
- An **edited or deleted row updates in place**; the user is not sent to page 1.
- **Long text truncates** without hiding the action buttons; a long number does not wrap.
- **Bulk select** — is "all" the page or the whole table? The spec says which; the UI must say the same.
- **Two users**: a row deleted by someone else while this list was open — what happens when it is clicked?

## Search

- **No results** is a state with words, not a blank.
- Partial match, **case**, **accents** (`Nguyen` finds `Nguyễn` — or the spec says it does not), leading and trailing spaces, a quote, a hyphen.
- A **single letter** and a very common word — does it return in reasonable time, or lock the screen?
- The result **opens the right record** when two share a display name.
- Search inside a **filtered** list searches the filter, or clears it — one of the two, on purpose.

## Sign-in, roles and permissions

- **Each action as each role** — including the roles that must be refused. Test the denied side as carefully as the granted one.
- The **direct URL** to a forbidden screen, as the wrong role: a clear refusal, not a blank page, not a raw error, and not the data.
- **Someone else's id** in the URL, as this role. This is the line that goes to the top of the report if it fails.
- **Session expiry mid-form**: the work is preserved, or the user is warned before it is lost — and the return after login lands where they were going.
- **Log out in another tab**, then act in this one.
- A **password change or a role change** takes effect in the sessions that are already open — or the spec says it does not.
- The **menu** hides what the role cannot do, **and** the action is refused if reached another way. Hiding is not preventing.

## Money

- Every **total equals the sum of the lines shown**, re-added by hand from the screen, not from the API.
- **Rounding**: per line or on the total, and which mode — as the spec says; the invoice and the screen agree to the last unit.
- **Tax** on the discounted or the gross amount, per the spec; the receipt shows the same figure as the screen.
- The **currency** symbol, position and decimal count match the currency — VND has no decimals; a `.00` on it is a defect.
- **Zero** and **negative** — a free item, a full refund, a discount larger than the subtotal.
- **The email, the PDF, the export and the screen show the same numbers.** Follow the data.
- A **refund cannot exceed the payment**, and the second refund of the same payment is refused.
- A price that changed while the item sat in the cart — which price is charged, and does the customer see it before paying?

## Anything with a lifecycle (order, subscription, document, ticket)

- **Each legal transition** works and is recorded — in the status, the history, the audit log.
- **Each illegal transition** is refused when attempted, not merely hidden in the UI. Try it by another route: a second tab, a stale page, the API.
- **The same transition twice** — cancel a cancelled order, approve an approved request.
- A transition **after a reload**, and **after a wait** longer than the session.
- **Two users** transitioning the same record at the same moment: one wins, the other is told.
- The **side effects** of the transition happened — the email, the stock movement, the invoice — once.

## Dates and time

- Displayed in the **user's** timezone and named as such where it matters; stored consistently.
- "Today" at **23:59 and 00:01**; a range **crossing a month or year** end.
- The **calendar picker and the typed date agree**, and the typed date follows the user's locale, not the developer's.
- Relative labels ("2 hours ago") and absolute times agree.
- Month arithmetic: **31 Jan + 1 month** is whatever the spec says it is, every time.
- The scheduled job and the report agree on which day an event at 23:30 belongs to.

## Notifications and email

- Sent to the **right person**, **once**, with the **same names and amounts** as the screen.
- The **link** lands on the right record, as the right role, and survives a login in between.
- **Not sent** when the action failed or was cancelled.
- Respects **unsubscribes** and the recipient's language.
- The badge or inbox count **updates** when it is read, and only then.

## Files, imports and exports

- The export contains **what the filtered list shows**, not the whole table — or the spec says otherwise, and the button's label agrees.
- **Headers** are the labels the user sees; Vietnamese characters survive a round trip through **Excel**.
- **Zero rows** exports a valid empty file, or a message — not a crash.
- The **filename** says what it is and when it was made.
- The **download works in the browser**, not only as an API call.
- An import **reports every rejected row with a reason**, imports the rest or none — per the spec — and does the same on re-import (no duplicates).

## Delete

- The **confirmation names the thing** being deleted, and how many.
- **Soft or hard**, per the spec; a soft-deleted record disappears from every list, count and search, and reappears from none.
- What happens to **children and references** — orphaned, cascaded, or refused — is what the spec says.
- The **list updates**; the **count goes down**; the **undo** works if one is promised.
- Deleting something **in use** — a category with products, a user with open orders — is refused with a reason, or handled as specified.

## Small screens and touch (when mobile is a surface)

- The **primary action is within thumb reach** and not covered by the keyboard.
- The **keyboard type** matches the field — numeric for numbers, email for email.
- **Rotation**, **background and return**, **an incoming call** mid-form: the state survives.
- **Permission denied** — camera, location, notifications — has a path, not a dead end.
- A **slow connection**: the spinner appears, the button disables, and one tap is one action.

## Performance, as a person feels it

- Something **visible happens within a second** of every click — a spinner, a disabled button, a skeleton.
- While it loads, **a second click does nothing** extra.
- The result shown is the result of **the last** click, not the previous one arriving late.
- With **the client's data volume** — thousands of rows, not the twelve in the seed — the screen is still usable. Ask the dossier what the real volume is.

## Using a checklist

Pick the one or two shapes the ticket touches. Walk them as part of the
whole-screen case — they *are* the whole-screen case — and record what you
looked at in STEPS even when it was fine, so the next reader knows the list was
walked and not merely cited. A line that fails becomes a finding with a
severity; a line that made you pause becomes an OBSERVATION. A line that does
not apply is skipped without comment.
