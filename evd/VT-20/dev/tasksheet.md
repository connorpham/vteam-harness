# VT-20 — DEV tasksheet

CODE-SCOPE: core/scripts/ core/workflows/ core/doctrine/competencies/ profiles/ .claude/skills/ CHANGELOG.md

`CHANGELOG.md` was added to the scope on the third red of the day from this same rule, and it
belongs: this ticket's job includes correcting figures that were **published** there, and the
changelog is not an always-legal process home the way `docs/` and `evd/` are. D12 ruled that
`ALWAYS_LEGAL` stays as it is — the gate asking for a deliberate widening is the point — so the
scope line moves, not the rule.

Four homes because the finding was a chain, not a file: the workflow that loads, the competency
that is loaded, the checker that should have noticed, and the profile that runs the checker.
`.claude/skills/` is declared for D12's reason — it is generated from the doctrine, so any doctrine
ticket touches it.

## Steps

- **T0** — audit by construction, not by reading: extract every lane's step vocabulary, every
  competency's role and `loads`, and cross them. That is what surfaced the P-prefix collision and
  the 3 unreachable skills in one table.
- **T1** — before fixing anything, ask what would have caught each finding. For all seven the
  answer was "nothing", and for three of them a cheap check exists. That set the fix list.
- **T2** — fix the reachability first: it is the one where a shipped rule was doing nothing at all.
- **T3** — then the instrument, because every number published this week was computed with it, and
  correct the published figures in place rather than restating them.
- **T4** — then the guard, and prove each new rule reds on the exact bug it was written for.
- **T5** — file what needs a decision (D15) instead of renaming a vocabulary unilaterally.
