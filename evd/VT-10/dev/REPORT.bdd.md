# VT-10 — what changed, in plain words

Background, in one paragraph: the framework can put several AI developers to work
at the same time. Each one gets its own private copy of the project folder so they
cannot tread on each other. The safety checks that police this were written before
anyone had actually tried it. The first real attempt, with two developers, hit five
separate problems within minutes — every one of them a check that refused honest
work. This ticket fixes all five and writes down the rules the run learned the hard
way.

## Scenario: Two developers working side by side stop being accused of overlapping

Given two AI developers are each working on their own ticket in their own private
copy of the project
And each has written down which folders their ticket is allowed to touch
When the safety check asks whether their two lists of folders overlap
Then it finds both lists and reports that the two developers are clear to carry on
And it no longer claims one developer has written down nothing at all

## Scenario: A developer who has not yet published their plan gets told exactly that

Given one developer has written down which folders they will touch but has not yet
published it for the others to see
When the safety check runs
Then it stops the work and says the plan is not published yet, naming the file to
publish
And it no longer pretends the developer left the plan blank, which sent the last run
looking for the wrong problem

## Scenario: Handing a shared piece of work to a colleague is accepted as real

Given one developer has formally handed a shared piece of work to the other
And the receiving developer has added it to their own written plan
When the check that keeps handovers honest runs from the giver's copy of the project
Then the handover is accepted as genuinely done
And it is no longer rejected because the receiver's plan sits in a folder the giver
cannot see

## Scenario: The shared logbook everyone must write in stops counting as private ground

Given both developers were told to record their handover in the team's shared logbook
And both therefore listed that logbook among the files they would touch
When the overlap check runs
Then it sets the shared logbook aside, says out loud that it has done so, and lets
both carry on
And two developers who really do overlap on the same product code are still stopped

## Scenario: Finished work stops being counted as work in progress

Given an earlier ticket was completed and folded into the main project, but its
leftover working copy is still lying around
And the team is allowed at most two developers at a time
When the safety check counts how many are actually working
Then it counts two, not three, and allows the next ticket to start
And it no longer blocks new work on the strength of work that already finished

## Scenario: A ticket is no longer blamed for a note that merely mentions it

Given a manager saved a note whose description happens to mention a developer's
ticket by name, while changing files belonging to nobody in particular
When the check that watches for developers quietly widening their own remit runs
Then that note is recognised as somebody else's and the ticket is left alone
And a change that genuinely leads with the ticket's own name, touching the very same
files, is still caught

## Scenario: A new working copy no longer swallows the instructions sent to it

Given a fresh private copy of the project has just been created for a new developer
And the assistant has never seen that folder, so it asks the human whether the folder
can be trusted
When the team runs the new one-line command that answers that question in advance
Then the folder is marked trusted, the human's own settings are backed up first, and
running it twice changes nothing
And the developer receives its instructions instead of waiting at a dialog nobody is
watching

## Scenario: The rules are written down where the next run will read them

Given these five problems were found only by trying, and cost a live run its first
hour
When someone opens the team's guidance for running several developers at once
Then they find three rules stated plainly, each with the reason it exists, and the
developer's own guide repeats the two that bind them at the moment they bind

## Appendix (for technical readers)
Gates: parallel_check (sibling CODE-SCOPE via `git show <branch>:<path>`;
split_bookkeeping over paths.pm/evidence/qa; `--merged` filter), coord_check
(tasksheet_text, newest-branch-first), graph_check (attributes: the key must LEAD
the subject). Helper: `orca_team.sh trust <path>` sets
projects["<abs>"].hasTrustDialogAccepted in ~/.claude.json. Doctrine:
parallel-transport.md + dev.md T1 + team.md T2. Proof: cmd_probe.md (live
three-worktree fixture, 7 mutation proofs), cmd_verify.md (gate GREEN, 32 selftests,
e2e 164/164). No screenshots: a CLI framework's outcome is an exit code.
