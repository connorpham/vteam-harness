<!-- Reference for qa-accessibility-verification. Moved out of the competency body when the
     forced-colors rule landed and the competency hit its word ceiling: these are the arguments
     you meet AFTER a finding is filed, so they are needed at rebuttal time, not at design time.
     Deep material on the second rendering mode is in reference/forced-colors.md. -->

# Accessibility verification — the excuses, and what answers them

> `/qa` opens this when a finding is pushed back on, not when designing the pass.
> Each row is a sentence you will actually hear; the right column is the reply that
> ends the argument, because it is a measurement rather than an opinion.

## Rationalizations

| Excuse | Reality |
|---|---|
| "The scanner says zero violations." | It cannot see focus order, focus return, or a meaningless label. Those are the expensive ones. |
| "It's not in the acceptance criteria." | WCAG is the oracle when the spec is silent. Cite it. |
| "Our users don't use screen readers." | You do not know that, and contrast, font scale and target size affect everyone. |
| "The designer chose that grey." | Then they chose a measurable defect. Give them the ratio. |
| "Focus is clearly visible, I can see the ring." | In one of two rendering modes. Turn High Contrast on and count the pixels again. |

## Two more that arrive later in the argument

| Excuse | Reality |
|---|---|
| "That's the component library's default, not our code." | A default you shipped is a decision you made. File it against the wrapper you own. |
| "No customer has complained." | People who cannot use a screen leave without filing tickets. Absence of complaint is absence of data. |
| "We'll do an accessibility pass before launch." | Focus order and names are structural. A pass at the end is a rewrite, which is why it never happens. |
