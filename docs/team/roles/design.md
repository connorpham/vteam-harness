# DESIGN playbook — flow and interface locked BEFORE code is written

> The design lane and the DEV workflow's UI phase read this file before touching
> any screen.

## Why this role exists

Without a locked design, the dev invents the interface — and everything invented
gets reworked at acceptance, the most expensive stage to change. DESIGN guarantees
every UI ticket has a **design oracle** (a design-tool frame or an approved mockup)
before DEV starts, and that the shipped look matches that oracle measurably, by
machine.

## The oracle split (house of record, per `ops.md` §4)

**The design source owns the LOOKS; the spec owns the BEHAVIOR.** On conflict, the
spec wins behavior, the design source wins appearance. Colors/spacing/typography
come from the design source's machine-readable data (node JSON, tokens), never
estimated by eye from screenshots.

## Professional sources

| Standard | What it contributes |
|---|---|
| **Design source = visual oracle** | Measured values from data, not eyes |
| **UI quality rules** (the framework's UI intelligence layer) | Laws that sit ABOVE the design: touch targets ≥44px, WCAG AA contrast 4.5:1, focus states — when the design draws it wrong, the law wins, with a written record |
| **Design system before individual screens** | Tokens (color, type, spacing) live in one place; new screens use existing tokens before inventing new ones |

## Core thinking

1. **No oracle, no screen.** A UI ticket with neither a design link nor an approved
   mockup goes back to the design lane — DEV never draws from imagination (a
   temporary approved mockup is acceptable; invention is not).
2. **Fidelity is measured by machine, not by eye.** Computed styles compared
   against the design source's data; a side-by-side design-vs-app image is required
   evidence.
3. **States are part of the design.** A screen without empty / error / loading
   states is an unfinished design — DEV is entitled to demand them.
4. **A deviation from the design source is a decision, never a whim.** Deviating
   for accessibility or technical reasons → written record (change request or
   fidelity note); silent deviation is a defect.

## Per-UI-ticket checklist

- [ ] The ticket carries a design node reference or an approved mockup
- [ ] Empty / error / loading states exist in the oracle or are recorded as
      "per the shared pattern"
- [ ] Color/type tokens checked against WCAG AA — where they fail, accessibility
      wins, with a record
- [ ] Every oracle-vs-app difference after build gets one line of justification

## Anti-patterns

- Dev inventing layout because "the ticket is urgent" — the exact thing this role
  exists to prevent
- Copying colors from screenshots instead of design data
- Changing the design in code without updating the design record
