<!-- Reference for qa-accessibility-verification (verify side) and dev-frontend-craft (build side).
     Every number and every compiled-CSS line below was MEASURED in the vteam field trial
     (~/Documents/testbed-base, tickets TB-6 and TB-8, 2026-09-09/10), not read off a blog:
     evd/TB-6/dev/focus_measure.md, evd/TB-8/dev/manifest.md, evd/TB-8/qa/focus_journey.verify.json.
     The competency is WHEN to look; this is what to look at and what the answers looked like. -->

# The second rendering mode — forced colours / High Contrast

> `/qa` opens this in V2 when a ticket touches a focus indicator, a border, a
> shadow or a status colour. `/dev` opens it in T2 before building any indicator.
> It answers one question: *does the thing you are about to certify still exist
> when the operating system, not the stylesheet, picks the colours?*

## Why a normal pass misses it

Windows High Contrast (and `forced-colors: active` generally) hands colour choice
to the user agent. Chrome, in that mode, **does not paint `box-shadow` at all**,
but it does paint `outline` and `border`, substituting a system colour. So an
indicator built only from a shadow — which is what `ring-*` in Tailwind compiles
to — is fully visible in the default pass and **completely absent** for the people
who turned the setting on because they cannot see low-contrast edges.

Measured, on the same button, same build, same browser (headed Chrome 152):

| rendering mode | `box-shadow` | `outline-style` | pixels changed on focus |
|---|---|---|---|
| default | the ring, painted | `solid` (transparent) | 256 |
| `forced-colors: active` | `none` — dropped by the browser | `none` | **0** |

Zero changed pixels is not a subtle regression. It is no indicator.

## The trap that produced two tickets

A shared component may carry a correct two-layer indicator — a `box-shadow` ring
for the default mode plus a transparent `outline-2` that only the forced-colors
substitution makes visible — and a **caller** can still erase it with one class.
In Tailwind v4:

```
.outline-none  { --tw-outline-style: none; outline-style: none }
.outline-2     { outline-style: var(--tw-outline-style); outline-width: 2px }
@property --tw-outline-style { initial-value: solid }
```

`outline-none` does not merely win the `outline-style` declaration — it poisons
the custom property the width utility reads. So **reordering classes or raising
specificity cannot rescue it**, and `tailwind-merge` will not drop the conflict
because width and style are different conflict groups. The observable fingerprint
is an outline that is fully specified and never drawn:

```
outlineWidth: "2px"                  ← the width utility applied
outlineColor: "rgba(5, 0, 73, 0.8)"  ← forced colours supplied a system colour
outlineStyle: "none"                 ← nothing paints
--tw-outline-style: "none"           ← because the variable is poisoned
boxShadow: "none"                    ← the browser dropped the ring
```

**`outline-hidden` is not a synonym for `outline-none`.** It emits the same pair
*plus* a later `outline: 2px solid #0000` shorthand, and a shorthand resets
`outline-style`, so the element keeps a 2px outline the user agent can colour.
Measured on a dialog close button using it: `--tw-outline-style: none` yet
`outline-style: solid`, `outline-width: 2px`, `outline-color: rgb(0, 0, 0)`.
When a designer really wants no visible focus box in the default mode,
`outline-hidden` is the class that keeps High Contrast users covered;
`outline-none` is the one that does not.

## How to measure it, in about twenty lines

Playwright takes `forcedColors` as a **context** option, so make a context rather
than reusing a launched page:

```js
const context = await browser.newContext({ forcedColors: "active" });
```

Then, per control: reach it with the **real Tab key** (never `element.focus()` — a
programmatic focus is not what a keyboard user does), assert `:focus-visible`,
read `getComputedStyle` for `outlineStyle` / `outlineWidth` / `outlineColor` /
`boxShadow` and the `--tw-outline-style` property, and photograph the same clip
twice — unfocused and focused. Count a pixel as changed when any channel differs
by more than **8/255**. Two numbers make the verdict: the computed style says what
the browser intends, the pixel delta says what a person would see. Report both,
because either alone has a failure mode — a style read cannot tell you the outline
is the same colour as the background, and a pixel count cannot tell you whether
what changed was the indicator or a neighbour.

## What such a measurement does *not* prove

Everything above comes from Chromium's **emulation** of forced colours. The system
colour it substitutes is the emulator's, not a Windows theme's, and a real High
Contrast theme can pick differently. Emulation is enough to prove *absence* — zero
changed pixels is zero on any theme — and not enough to certify a particular
colour or ratio. Say which one you ran.

Under forced colours a contrast ratio is usually the **wrong** check: the user
agent picks both colours, so the answer is "the theme's", not the product's. The
testable question is whether the indicator is painted at all. Keep WCAG 1.4.11
(3:1 for the information that identifies a component and its state) for the
default rendering, where the product does choose the colours.
