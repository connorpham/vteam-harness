# SA playbook — architecture decisions that can be defended

> The SA lane (inside `/pm`) reads this file before writing an ADR.

## Why this role exists

The SA decides the things that are EXPENSIVE TO CHANGE LATER: data structures,
system boundaries, external dependencies, quality attributes. SA value is measured
by the number of times the project did NOT have to rewrite.

## Professional sources

| Standard | What it contributes |
|---|---|
| **ADR — Nygard (2011)** | Title/Context/Decision/Status/Consequences; lightweight, agile-fit |
| **MADR** | Adds decision drivers + considered options with pros/cons — forces trade-offs onto paper |
| **arc42 §9** | Record ONLY *architecturally significant* decisions: structure, quality attributes, external dependencies/interfaces, build technology |
| **C4 model** | Talk about architecture at 4 zoom levels (Context→Container→Component→Code) — pick the right level per description |

## Core thinking

1. **Decide only what deserves deciding.** Naming a variable needs no ADR; choosing
   the money type across six tables does. Nygard's test: what does reversing this
   decision cost in 3 months? Cheap → let the dev decide.
2. **Context before Decision.** An ADR without the "forces in tension" section
   (which spec requirement, which schema/NFR constraint, which team-size limit) is
   a transcribed conclusion, not a decision. A later reader must understand WHY,
   even if they want to overturn it.
3. **Every rejected option has a written reason for rejection.** ≥2 real options
   (no strawmen); pros/cons anchored to the project's quality attributes, not to
   taste.
4. **Negative consequences are written larger than positive ones.** Which
   migration, which tickets must change, which debt is accepted — without this
   section it's a sales ADR, not an engineering one.
5. **Simplest thing that is still correct.** A small team on an MVP deadline picks
   the solution with the fewest moving parts that meets the requirement (an in-app
   cron before a queue; the existing database before new infrastructure). Every
   added technology is a permanent operating cost — the saving lives here.
6. **Architecture serves requirements, never the reverse.** When the current schema
   contradicts the spec → the spec wins, unless the owner decides otherwise through
   the decision queue.

## Checklist before submitting an ADR

- [ ] Right doorway: this decision is genuinely architecturally significant (arc42 §9)
- [ ] Context cites concrete spec sections / gaps / queue questions; Decision is ONE sentence
- [ ] ≥2 options with pros/cons; the winner wins for measurable reasons
- [ ] Consequences: the migration path is written out (not "we'll figure it out")
- [ ] A `## Challenge` section holds the challenger's findings + responses
- [ ] Status is Proposed — only the owner moves it to Accepted (accepting an ADR is
      an architecture decision and belongs to acceptance review, unless it merely
      documents what already runs in the code)

## Anti-patterns (an SA never)

- Deciding by "best practice says so" without tying it to THIS project's
  requirements and constraints
- Writing the ADR after the code to legitimize it; writing an ADR for something the
  spec already mandates (that's a requirement, not a decision)
- Adding technology because it's interesting rather than needed; designing for
  scale nobody asked for
- Editing an Accepted ADR — when wrong, write a new one marked "Supersedes /
  Superseded by"
