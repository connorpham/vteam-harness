# Provenance — the scars behind the rules

vteam was not designed on a whiteboard. It was extracted from a harness that ran a
real production project — 37+ PRs, six audited working sessions, 113+ confirmed
review findings — and most of its rules exist because something specific broke.
Doctrine files state the rules undated and unadorned; this file keeps the
incidents, so the rules keep their teeth without dragging their history into every
brief. Nothing here is normative — when this file and a doctrine file disagree, the
doctrine file wins.

## Why "a gate that has never been red does not exist" (verify workflow, principle)

The source harness shipped TWO always-green gates without noticing. A docs-shrink
guard compared `git diff --cached` in contexts where nothing was ever staged — green
at both of its call sites, always. A stale-verdict checker's first version measured
a gitignored directory — nothing to measure, always green. The knowledge base
already contained the lesson "a rule that cannot go RED gets skipped" — the harness
just hadn't applied it to its own gates. Hence the shipping rule: every new or
changed gate must be run against a violating input in the same PR, red output
pasted.

## Why the supersession law (ops §4)

An autonomy upgrade was PATCHED ON TOP of existing files instead of REPLACING the
old sentences. An audit later counted **7 pairs of self-contradicting rules living
side by side for weeks** (frontmatter and DoD said "wait for the user", phase text
said "proceed autonomously") — all three worker pipelines had Definitions of Done
that could not be satisfied without violating their own file. One rule, one home;
delete the old sentence in the same commit.

## Why the review investment is non-negotiable

Two-reviewer review was the highest-yield line item in the source project: ~113
CONFIRMED findings across 11 PRs, including bugs no code-reading would catch — 3
data-exposure cases where the HTTP layer returned a correct 403 but the payload
still leaked, and 5 bugs on one ticket that only surfaced when run against a
database with realistic volume. The rule "the second reviewer needs a different
lens, not equal IQ" (model routing) came from the same data.

## Why review cards must point at commands

A review round produced findings that could not be traced to anything executed.
The counter-rule: every CONFIRMED carries its reproducing command + output; every
tried-to-break item names the exact command; fewer than 2 traces voids the card.
The machine checks card FORM only — and the standard says so honestly; content
truth rests on the committed trail and QA's independent re-run.

## Why evidence namespaces have exactly one owner

DEV and QA lanes were once pointed at the SAME manifest file — while their two
gates demanded two different schemas for it. Whichever lane ran second turned the
other lane's gate red; the evidence directory ended up with three layouts, one of
which no gate understood. Now: `evd/<KEY>/` belongs to QA, `evd/<KEY>/dev/` to DEV;
one directory, one owner.

## Why verdicts pin a commit

Tickets marked Done kept being edited afterward (pre-merge fixups, review follow-ups)
— making the QA verdict silently apply to code nobody had examined. The verdict
file now records the exact commit examined, and a stale-verdict gate re-queues any
Done ticket whose code moved after judgment. Corollary learned the hard way: the
pinned SHA beats the tracker's changelog, because changelogs get washed by
post-verdict commits.

## Why the ledger is single-writer and committed immediately

Two lanes once wrote the same bookkeeping file concurrently — rows vanished. An
uncommitted ledger edit was destroyed by a branch checkout and had to be rewritten
from memory. Hence: background lanes return TEXT; only the main track writes the
ledger/minutes/decisions; bookkeeping commits before any branch switch.

## Why the oracle must arrive before the pipeline runs

One ticket ran the ENTIRE pipeline twice (≈620k + ≈780k tokens) because its mockup
was replaced by the real design frame mid-flight — while the question that would
have surfaced this sat unanswered in the decision queue the whole time, and
preflight didn't yet check that the design source was configured. Preflight now
pings every oracle the ticket depends on before work starts.

## Why prose-only rules get machine teeth or die

Measured over six sessions: an architecture-review rule ("mandatory when the diff
touches schema/lib") ran once in its lifetime — the next three qualifying diffs
skipped it. QA verified 1 of 11 delivered PRs. Token accounting appeared on 7 of 20
ledger rows. Two knowledge-base size-threshold breaches went uncleaned. Every one
of those rules was prose; none could go red. The extraction's standing bias: a rule
worth having is worth a gate, a challenger prompt, or deletion.

## Why briefs are paths, not pasted content

Pasting spec sections and diffs into subagent prompts doubled token spend and
produced agents that argued with stale excerpts. Briefs now carry paths + scope +
measurable expectations + forbidden moves ("a brilliant engineer with poor
judgment" is the audience — credit: Superpowers). One brief → one card → done.

## Why the question bar exists

A question sat open for three days blocking a group of screens — while its answer
had been sitting in the upstream spec since before the question was asked. The
3-condition bar (prove you searched / two-sided proposal with reversal cost / what
it blocks by when) turns questions into confirmations and outsources nothing.

## Why append-at-end, and why docs-shrink is guarded

A bookkeeping file was once reduced from 81 lines to 1 by an errant write; 18+
evidence images evaporated in a cleanup. The ledgers are append-at-end (machine-
checkable monotonic dates) and a shrink of >20% in bookkeeping paths blocks the
commit unless intent is declared.

## Reference keep-awake setup (macOS)

The source project ran 24/7 on a MacBook: a LaunchAgent running `caffeinate -is`
(blocks system sleep, display may sleep; `RunAtLoad` + `KeepAlive` so launchd
revives it after reboot or kill). Physical conditions no software fixes: the lid
must stay open (lid-close sleeps regardless, absent external display + power),
power connected, and the agent app running — a closed app means missed schedules
run late, not lost. Remove with `launchctl bootout` + deleting the plist.

## Working-balance warning

At one audit, ~27 of the previous 60 commits were harness/process work against ~12
of product code. Some of that is legitimate foundation cost — but the curve must
bend down after setup. vteam inherits the watch: the framework review (ops §6)
tracks process-vs-product commit ratio, and a rising process share is a finding.
