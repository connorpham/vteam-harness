<!-- Reference detail for dev-codebase-design. Moved out of the competency body so the
     lane spends its context on the ticket, not on the rulebook. The competency is
     the METHOD; this is the argument, the smell list and the worked case. -->

# dev-codebase-design — rationalizations, red flags, example

> `/dev` opens this at the review step, and whenever an excuse for skipping a
> rule appears. Read the row that fits the change in front of you; never paste
> the whole file into a report.

## Rationalizations

| Excuse | Reality |
|---|---|
| "We'll need this abstraction later." | Then add it later, with the second caller in hand and a real shape. |
| "It's cleaner as a separate service." | Separate is not clean; a seam with one adapter is decoration. |
| "I'll export the internals just for the test." | Then the internals are the interface and every refactor breaks the test. |

## Red flags

- A new file whose only job is to call one other function.
- `utils.ts` gained a function this ticket; which feature owns it?
- An interface with more methods than the implementation has branches.
- `import` from a sibling feature.

## Example

Ticket: "apply member tier discount at checkout". Shallow: `DiscountHelper`
with `getTier()`, `getRate()`, `applyRate()`, `formatDiscount()` used from the
checkout page. Deep: `priceOrder(order, tierPolicy): PricedOrder` in
`features/pricing/`; the page calls one function, the test passes a fake
`tierPolicy`, and the tier lookup lives behind the seam.
