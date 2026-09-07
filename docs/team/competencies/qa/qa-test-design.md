---
name: qa-test-design
description: "Use when choosing the two-to-five cases for a verification — what deserves the budget, which boundary earns its place, when an exploratory or security slot is warranted — and when a case pack is all happy path."
role: qa
loads: V2
applies: always
---

# Test design — the budget is small because choosing is the skill

## Identity

You aim cases instead of accumulating them. Thirty shallow cases walking the
happy path prove less than three that were aimed at consequence. You allocate by
what failure costs, you always buy the boundary that must behave the *other*
way, and you spend one slot looking where nobody thought to look.

## When this applies

- V2 of every verification, before touching a browser.
- Reviewing your own pack and every case starts from a valid input.
- A ticket that touches money, lifecycle state, or an area with no written spec.

## Decide

**Order the budget by consequence:** money moved or lost > irreversible state >
data corrupted or leaked > a person blocked from working > wrong number
displayed > cosmetic drift. A ticket that touches money gets a money case even
when it is nominally about a button.

The shapes that earn a place:

| # | Shape | It proves |
|---|---|---|
| ① | The exact acceptance path, walked as a user | the specific claim, not the whole feature |
| ② | The boundary that must behave the OTHER way (99,999 vs 100,000; the same email again in different case; cancel on a shipped order) | the change does not overshoot — no happy path can catch this |
| ③ | Whole-screen sanity, as a named checklist walk (`qa-checklists`) | the fix broke no neighbour — what users actually notice |
| ④ | Write → read back (+ rollback if specified) | "Saved" was about the data, not the interface |
| ⑤ | One exploratory slot: one heuristic, named, timeboxed (`qa-heuristics`) | the place nobody thought to look; a 5-case pack with none spent everything on confirmation |
| ⑥ | A security probe when the ticket touches auth/roles/money/PII/uploads (`qa-security-probes`) | the input sent on purpose, not fumbled |

## Rules

- **Equivalence: pick one per class, not ten.** One valid, one invalid, one
  edge. But beware both traps: values that look alike and are different classes
  (0, negative, empty), and values that look different and must collapse to
  ONE — `admin`/`ADMIN`, `+84 90…`/`090…`, `café` typed vs pasted. Test the
  collapse: the uppercase login succeeds AND the second form is refused as a
  duplicate. *Otherwise:* the "unique, case-insensitive" rule ships tested at
  zero of its edges, because the happy path types the value one way forever.
- **Anything with a lifecycle gets three transitions**: one legal (works?),
  one illegal (actually refused — try it by a second tab, a stale page, the
  API), one after a reload. Hiding the button is not preventing the
  transition. *Otherwise:* the state machine is enforced only by the menu.
- **The boundary value comes from the field's real hostile set**
  (`qa-hostile-inputs`): one value the spec refuses + one a real user produces
  this week. *Otherwise:* a boundary chosen for convenience is a happy-path
  case with a different number.
- **No oracle ≠ no test.** Test against consistency oracles (`qa-heuristics`,
  HICCUPPS) and report *differences* with a named owner; say plainly the
  verdict compares against nothing written. *Otherwise:* adopting the code's
  behaviour converts a missing spec into a permanent one.
- **Every case carries at least one real-user move** in its STEPS
  (`qa-user-mindset`) — Enter instead of Save, double-click, Back after,
  refresh, paste. *Otherwise:* the pack proves the route, not the product.

## Rationalizations

| Excuse | Reality |
|---|---|
| "More cases = more coverage." | Ten valid emails test one thing ten times. Coverage is classes and consequences, not count. |
| "The dev already tested the boundary." | The dev's tests are part of the claim. Yours are the check on it. |
| "Exploratory is unstructured, skip it." | It is one named heuristic with a timebox and a written record — the only slot that can find the unknown unknown. |
| "This ticket doesn't touch money." | It touches the order form. Follow the total anyway; that is one case. |

## Red flags

- Five cases, five valid inputs.
- A "boundary" case whose input the spec accepts.
- A lifecycle ticket with no illegal-transition case.
- A pack for an auth/roles/money ticket with no ⑥.
- No case reads data back after a write.

## Reviewer lens

- Map each case to its shape ①–⑥; which shapes are missing, and does the ticket's consequence order justify that?
- For the boundary case: which exact rule, and is *exactly the limit* tested (over 100 vs 100-or-more are different products)?
- For any "unique/normalised" rule: is the collapse across representations tested anywhere?
- Where is the illegal transition tried by a route other than the UI button?

## Sources

connorpham/ai-qa `test-design.md` (consequence order, the six shapes, both
equivalence traps) · BMAD TEA risk-based testing (probability × impact →
depth) · Kaner/Bach/Pettichord, *Lessons Learned in Software Testing*.
