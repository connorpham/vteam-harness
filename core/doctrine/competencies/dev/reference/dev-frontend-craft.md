<!-- Reference for dev-frontend-craft. Moved out of the competency body when the forced-colours
     rule landed and the file hit its word ceiling. These are the arguments made in review, so they
     are wanted at review time, not while building. The measured material behind the forced-colours
     rule is in ../../qa/reference/forced-colors.md. -->

# Frontend craft — the arguments made in review

> `/dev` opens this in a review round, when a shortcut is being defended rather
> than when the screen is being built.

## Rationalizations

| Excuse | Reality |
|---|---|
| "The designer only gave me the default state." | Then the design is incomplete. Ask, or enumerate the states and show them. |
| "Accessibility is a later ticket." | Contrast, labels, focus and target size cost minutes now and a rewrite later. |
| "`any` unblocks the build." | It moves the error from your terminal to the user's browser. |
| "e2e covers it." | e2e is the slowest, flakiest tier. Push the assertion to the cheapest tier that holds it. |

## Two the field trial produced

| Excuse | Reality |
|---|---|
| "The shared component already handles focus." | It does, and one class on your call site can erase it. In Tailwind v4 `outline-none` poisons the custom property the shared rule reads, so neither class order nor specificity restores it. Measured: a build that removed the *other* spelling of the class rendered identically to the broken one. |
| "It's only CSS, there is nothing to test." | A focus indicator is behaviour that a person either sees or does not. Read the computed style off a live focused element and count changed pixels in both rendering modes; anything less is a claim. |
