# VT-8 — what I did, in plain words

## Scenario: An AI report can now be written so anyone understands it
Given the team only had free-form or code-heavy reports
When a lane writes its account as Given/When/Then scenarios in a .bdd.md file
Then a product owner reads it in about a minute and knows what happened

## Scenario: A report that hides behind jargon is refused
Given a scenario whose step mentions a file path or a function call
When the gate checks the report
Then it is rejected and names the code-speak to move into the appendix

## Scenario: An empty-sounding outcome is refused
Given a scenario whose Then only says the work "works"
When the gate checks it
Then it is rejected and asks for the outcome a person would actually see

## Scenario: A rambling report is refused
Given a step longer than thirty words or a scenario taller than fifteen lines
When the gate checks it
Then it is rejected as too long-winded so reports stay scannable

## Appendix (for technical readers)
Gate: core/scripts/bdd_report_check.py (structure + FILLER set + CODE_SPEAK patterns
+ MAX_STEP_WORDS=30 / MAX_SCENARIO_LINES=15). Scans {paths.evidence}/**/*.bdd.md.
