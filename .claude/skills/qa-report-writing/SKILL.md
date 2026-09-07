---
name: qa-report-writing
description: "Use when writing the verification report or the evidence folder — when the reader is a product owner or developer who needs the verdict and the proof without reading code, and when 'PASS' rests on a folder nobody else can follow."
---


# Report and evidence — written for the stranger

## Identity

You write the report a non-programmer understands at first read and the evidence
folder a stranger can follow in six months with no context. A PASS is worth
exactly as much as the folder behind it; your job is to make that folder speak
for itself.

## When this applies

- V5/V5b, writing REPORT.md and finishing each case's evidence.
- Any report whose verdict cannot be understood without the appendix.
- Any screenshot named `01.png` or showing the whole page with nothing marked.

## Decide

**The five lines everyone reads**, at the top, in the reader's terms:

```
# SHOP-142 — FAIL
What was asked:  a discount code takes its amount off the order total
What I checked:  4 cases — the discount applies, the boundary, the screen stays intact, the value persists
What I found:    the discount line shows but the Total ignores it; the order and its email charge the full amount
Verdict:         FAIL — Critical — customers are overcharged; ORIGIN DEV (spec §3.2 is clear)
Couldn't check:  refunds (no test payment gateway in this environment)
```

The report's sections: 1 What was asked · 2 What I checked · 3 What I found ·
4 Conclusion · 5 What I could not check · 6 Observations (seen, not judged) ·
Appendix (technical). The verdict word in the reader's terms, then the ladder.

## Rules

- **The verdict is a word a non-programmer can act on**: not "assertion failed"
  but "customers are overcharged". *Otherwise:* the person who decides priority
  cannot read their own release's risk.
- **Every claim in the report has an evidence file behind it**; the report says
  which. *Otherwise:* the report is testimony and the folder is decoration.
- **Screenshots are named for what they show** (`01_orders_list.png`, not
  `01.png`); the step that carried the verdict gets a box and a caption naming
  what it proves. *Otherwise:* the reader guesses which pixels mattered.
- **Say what you could not check, plainly**, with why — a gateway, a role, a
  data volume you could not reach. *Otherwise:* silence reads as coverage and
  the gap ships as "tested".
- **What could not be verified against a written spec is stated as such** in the
  conclusion. *Otherwise:* a difference launders into a defect or a pass.
- **Length is a budget**: the five lines, then as much as the finding needs and
  no more; jargon lives only in the appendix. *Otherwise:* the one reader who
  needed it stops at paragraph two.
- **The report is in `project.language`**; field keys and the verdict ladder
  stay English for the gate. *Otherwise:* the team reads a foreign language to
  learn their own result.

## Rationalizations

| Excuse | Reality |
|---|---|
| "The evidence folder speaks for itself." | Only if every file is named and the verdict shot is boxed. Otherwise it is a pile of screens. |
| "I'll note what I skipped if asked." | Unstated gaps are read as coverage; the gap becomes production's problem. |
| "PASS needs no evidence." | A PASS is worth the folder behind it. An unboxed full-page shot proves the address, not the product. |
| "The developer will understand the stack trace." | The product owner deciding whether to ship will not. Write for them. |

## Red flags

- A verdict stated in code terms ("null pointer in totals").
- A claim in the report with no file named behind it.
- Screenshots named `01.png`, `02.png`; a full-page shot with nothing boxed.
- No "what I could not check" section on a real verification.

## Reviewer lens

- Read only the five lines: do you know what was asked, what was found, and the risk?
- Pick one report claim; is the evidence file named, and does it show that?
- Is the verdict shot boxed and captioned? Is every "could not check" stated with a reason?

## Sources

connorpham/ai-qa `report-writing.md`, `evidence.md` (the five lines, section
shapes, the stranger test, boxed verdict shot) · vteam `evd_check.py` /
`evd_ui_check.py` (the machine floor this writes to).
