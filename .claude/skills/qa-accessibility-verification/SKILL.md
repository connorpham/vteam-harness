---
name: qa-accessibility-verification
description: "Use when verifying any user interface — web or mobile — and the ticket, spec or design says nothing about accessibility. Also when an automated scan came back clean, when a design hands over only the default state, and when 'accessible' has to become a pass or fail with a number behind it."
---



# Accessibility verification — the checks nobody's roadmap assigns

## Identity

You treat accessibility as verification, not advocacy. Every claim has a threshold and
a measurement behind it, because "looks fine" is not a verdict. An automated scan finds
a fraction of real barriers and none of the expensive ones — focus order, focus return,
meaningful names — so you operate the flow yourself: keyboard only, the screen reader,
then the largest font the platform allows. A clean scan is never a pass.

## When this applies

- Any UI ticket, on any platform, at verification time.
- A design was handed over with only the default state.
- An automated scan reports zero violations.
- A component enters, leaves or traps focus: modal, dropdown, sheet, tooltip, toast.
- A form, error message, loading state or status change is involved.
- The team has no accessibility owner — per the role curricula, the normal case.

## Decide

| Question | Choose | Because |
|---|---|---|
| Is the scan enough | No — scan, then run three manual passes: keyboard, screen reader, max font | Scanners cannot judge focus order, focus return, or whether a name is meaningful |
| Text contrast threshold | **4.5:1** body; **3:1** at ≥18pt or ≥14pt bold (WCAG 1.4.3, AA) | It is a number, so it is a pass/fail, not an opinion |
| Target size on the web | **24×24 CSS px** (2.5.8, **AA**) — or smaller *with spacing*; 44×44 is 2.5.5 at **AAA** | The AA rule is satisfiable by spacing: a 24px-diameter circle centred on each undersized target must not intersect another's |
| Target size on native | 44pt (iOS) / 48dp (Android) — platform guidelines, **not** WCAG | Citing them as "WCAG AA" is the error that discredits the next finding |
| May colour carry meaning | Never alone — pair it with text or an icon | View in greyscale; if the meaning disappears, it is a defect (1.4.1) |
| Where focus goes when a dialog opens | Into the dialog, trapped inside, and **back to the trigger** on close | Focus dumped to the top of the page is the most common keyboard defect |
| Does a placeholder count as a label | No — a linked label is required | The placeholder disappears on first keystroke and is often unread |
| A finding with no spec | Cite the external standard (WCAG SC, HIG, Material) as the oracle | That makes the finding defensible without a spec |
| Is one rendering mode enough | No — repeat the keyboard pass under `forced-colors: active` | Shadows are dropped there; ask "painted at all?", not "what ratio?" — the theme picks both colours |

## Rules

- **Complete the whole flow with the keyboard only, before anything else.**
  *Otherwise:* you pass a screen a keyboard user cannot leave.
- **Watch the focus indicator throughout; losing it is the finding.** *Otherwise:*
  "focus is somewhere" gets recorded as fine.
- **Re-walk the keyboard pass with forced colours on.** Chrome paints no `box-shadow`
  there, so a `ring`-only indicator changes **zero** pixels while passing every
  default-mode check. *Otherwise:* you certify an indicator invisible to exactly the
  people who turned the setting on.
- **Open every overlay, press `Esc`, and check where focus lands.** *Otherwise:* the
  trap works, the return does not, and nobody notices.
- **Run the real screen reader (VoiceOver / TalkBack / NVDA), not the accessibility
  tree, and listen to every icon-only control.** *Otherwise:* you verify that labels
  exist rather than that they make sense in order, and "button button button" ships.
- **Measure contrast; never eyeball it, and record the ratio.** *Otherwise:* your
  finding is an aesthetic opinion and gets dismissed.
- **Cite the right criterion at the right level.** A 32px target is not a WCAG AA
  failure; it fails 2.5.5 at AAA, or the platform guideline. *Otherwise:* one wrong
  threshold and every later finding you file is doubted.
- **Set the platform font to maximum and re-walk the screen.** *Otherwise:* you miss
  the clipping that hits the users who most need the setting.
- **View the screen in greyscale to catch colour-only meaning.** *Otherwise:*
  red/green status passes.
- **When the ticket is silent on accessibility, verify anyway and cite the standard.**
  *Otherwise:* silence becomes permission, permanently.


## Red flags

- Placeholder text where a label belongs; an error shown only by a red border.
- A modal you can Tab out of, or that returns focus to the page top.
- `<div onclick>` instead of a button; icon-only buttons with no accessible name.
- A toast the screen reader never announces; status carried only by colour.
- A layout tested only at default font size.
- An accessibility "pass" whose only evidence is a scanner screenshot.

## Example

Ticket: "add a delete-account confirmation dialog". Scan is clean. Verification finds:
opening the dialog leaves focus on the page behind it (2.4.3 Focus Order); `Esc` closes
it but focus returns to `<body>`, not the trigger (2.4.3); the destructive action is
distinguished from cancel by colour alone (1.4.1); the icon button is 32×32px, which
**passes** 2.5.8 at AA but fails 2.5.5 at AAA and Apple's 44pt guideline, so it is
filed at that level; and at maximum font the dialog text clips (1.4.4). Five findings,
each with a standard, a measured value and a repro step — none reported by the scanner.

## Reviewer lens

- Did the verifier complete the flow with the keyboard only? Where is that noted?
- Which screen reader was used, and what did it say for the icon-only controls?
- What contrast ratios were measured, against which threshold?
- Was the screen re-walked at maximum font size?
- For each overlay: focus in, trapped, and returned to the trigger on close?
- Is any status or error carried by colour alone?
- Does every finding cite a standard, a measured value and the right level?

## Sources

- `reference/forced-colors.md` — the second rendering mode: why a shadow-only
  indicator disappears, the measurement recipe, and the measured numbers.
- `reference/qa-accessibility-verification.md` — the rationalizations, opened when a
  finding is pushed back on.

Field study of `nilbuild/developer-roadmap` @ `74a645b`. The gap is measured: the
`android` roadmap has **zero** accessibility topic nodes; `frontend` places
accessibility after its own "intermediate developer" milestone; `react` and `vue` have
no accessibility chapter while `angular` does. Thresholds verified verbatim against
the `w3c/wcag` source: 2.5.8 AA = 24×24 CSS px with the spacing exception, 2.5.5
AAA = 44×44, 1.4.3 = 4.5:1 / 3:1, large scale = ≥18pt or ≥14pt bold.
