# VT-21 — DEV tasksheet

CODE-SCOPE: core/scripts/ core/workflows/ profiles/ src/cli/ .claude/skills/

`src/cli/` is in scope because D14's fix is in the installer's manifest guard, not in a gate.
`.claude/skills/` for D12's reason — generated from the doctrine, so any doctrine or workflow
ticket touches it.

## Steps

- **T0** — before gating either checker, run it and see what it does to a real repo. That is what
  separated them: `schedule_check` exits 1 today for true reasons that have nothing to do with any
  change, and `evd_ui_check` finds a real evidence-layout gap. One of those may block a commit; the
  other must not.
- **T1** — rather than bend a checker to fit the gate, give the driver the missing concept:
  `advisory`. Guard it with selftests in four directions, including that it never softens a hard red.
- **T2** — `--sweep` for the UI checker, carrying VT-17's legacy policy so a repo is not reddened
  for evidence written before the standard.
- **T3** — the lens goes where each lane can actually use it: a challenger prompt in `/ba`, a
  self-check in `/pm`, which has no challenger for the ordering.
- **T4** — D14 in the manifest guard, proven by declaring the field repo's fork and watching the
  `.new` stop appearing while the signal survives.
