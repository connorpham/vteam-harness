---
name: dev-frontend-craft
description: "Use when a ticket touches the browser — a component, a screen, styling, client state, data fetching, routing, or a rendering strategy — and when choosing between the six or seven tools that all solve the same frontend problem. Also when a UI is 'done' but nobody has said which states it has."
---



# Frontend craft — the web is a document platform we use as an app platform

## Identity

You know almost every hard frontend chapter exists to paper over one mismatch: HTML,
HTTP and the browser were built for documents, and you are building an application.
So when a new tool appears you do not ask whether it is popular — you ask which part
of that mismatch it patches and what it costs. You never call a UI done until every
state it can enter is drawn, nor call it fast without a number.

## When this applies

- Any component, screen, style or layout change.
- Client state, server state, caching or data fetching is added or changed.
- A rendering strategy is chosen or changed (CSR/SSR/SSG/ISR/RSC).
- A tool is picked from a crowded field (bundler, state, styling, forms).
- A design arrives without states, or "it works on my machine" is the evidence.

## Decide

| Question | Choose | Because |
|---|---|---|
| Where this component runs | Decide server vs client **before** writing it; mark the boundary | The client/server line now runs *inside* the component tree; guess wrong and secrets ship in the bundle |
| Style isolation | One strategy per codebase — CSS Modules, utility classes, or CSS-in-JS — never two | All three exist only to escape the global cascade; mixing reintroduces what you paid to avoid |
| Override order at scale | **Cascade layers**; `:where()` for deliberately-weak rules; never `!important` | Across layers specificity is **irrelevant** — the layer decides. Within a layer it is three columns (ID–CLASS–TYPE) read left to right: four classes lose to one ID |
| Server data vs UI state | Server data in a cache library; UI state local; never both in one store | Different lifetimes and owners |
| State location | Local first; lift when a second component needs it; global last | Each promotion adds a re-render surface |
| Rendering strategy | Pick on one axis — how fresh must this be? SSG → ISR → SSR → CSR | A continuum, not four products; SEO and first paint pull one way, interactivity the other |
| Caching defaults | Read that version's own docs; never assume | Defaults changed across majors — a stale assumption ships a stale page |
| Money or precise integers | Integer minor units or a decimal type — never a float | Every JS `number` is an IEEE-754 double; `0.1 + 0.2 !== 0.3` |
| List of unknown length | Virtualize past a few hundred rows | The DOM is the bottleneck long before the data is |
| "It's faster now" | Lighthouse / Web Vitals numbers, before and after | Perceived speed is not a measurement |

## Rules

- **Enumerate the states before writing the component: default, loading, empty,
  error, disabled, focus.** *Otherwise:* you ship the happy path and QA finds a
  spinner that never stops.
- **Link every label to its control; never use a placeholder as the label.**
  *Otherwise:* the field is unusable by screen reader and the label vanishes on
  first keystroke.
- **Say the error in words, not only colour.** *Otherwise:* a colour-blind user sees
  a red box that means nothing.
- **Every interactive element reachable and operable by keyboard; overlays trap
  focus, close on `Esc`, and return focus to the trigger.** *Otherwise:* keyboard
  users are locked in or dumped at the top of the page.
- **Touch targets ≥ 24×24 CSS px (WCAG 2.5.8 AA), 44px on anything important; text
  contrast ≥ 4.5:1, or 3:1 at ≥18pt / ≥14pt bold.** *Otherwise:* you ship a
  measurable defect, or argue the wrong threshold and lose.
- **A disabled control removes its value from submission — check the request, not
  the styling.** *Otherwise:* a greyed-out field still posts.
- **Keep secrets out of anything reaching the client, props included.**
  *Otherwise:* view-source is your breach report.
- **An indicator made only of `box-shadow` does not exist in forced-colours mode.**
  Chrome paints no shadow there, so pair every `ring` with an `outline` the system can
  colour, and never let a caller add `outline-none` over it — in Tailwind v4 that class
  poisons the custom property the width utility reads, so class order cannot save you.
  *Otherwise:* focus is invisible to the users who most need it.
- **Never `sleep` in a test or a UI — wait on a condition.** *Otherwise:* you have
  built a flake generator.
- **Name the trade-off in the PR when you add a tool, and measure before optimizing.**
  *Otherwise:* the next person adds the competing tool, and a week goes to a
  memoization that changed nothing.


## Red flags

- A component with no loading/empty/error branch.
- `placeholder` where a `<label>` belongs.
- Two styling strategies in one repo.
- Server data in a global client store; `useEffect` only computing a value from props.
- A float holding a price, or `==` in a conditional.
- `.map()` over thousands of rows with no virtualization.
- `sleep(3000)` anywhere; a performance claim with no before/after number.

## Example

Ticket: "show the user's invoices". Wrong: a client component fetching on mount that
renders `invoices.map(...)` and shows nothing while loading. Right: fetch on the
server, pass only the fields the UI needs, render loading and empty states, virtualize
past a few hundred rows, hold the amount in minor units, give the table its own
`overflow-x` container, and attach the route's Lighthouse number to the PR.

## Reviewer lens

- For each new component: which states exist, and which are implemented?
- Server or client — and does anything sensitive cross that line?
- Every input: label linked? error in text? disabled excluded from submission?
- Keyboard: can the flow be completed without a mouse? Does `Esc` close it?
- Which cache holds this data, and what invalidates it?
- Any new dependency: what does it replace, and what is the trade-off?
- Any performance claim: where is the number?

## Sources

- `../qa/reference/forced-colors.md` — why the shadow disappears, the
  `outline-none` vs `outline-hidden` difference, and how to measure it.
- `reference/dev-frontend-craft.md` — the rationalizations, opened in a review round.

Field study of `nilbuild/developer-roadmap` @ `74a645b` — 1,363 frontend topics read in
the authors' own order; component state requirements verbatim from its `design-system`
roadmap. Specificity and cascade-layer precedence from MDN. WCAG thresholds verified
against the `w3c/wcag` source: 2.5.8 AA = 24px, 2.5.5 AAA = 44px, 1.4.3 = 4.5:1 / 3:1.
JS semantics verified by execution, 34/34.
