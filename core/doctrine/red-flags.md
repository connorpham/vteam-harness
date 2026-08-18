# Red flags — the 12 excuses

> An agent that wants to skip a step never says "I'm skipping a step". It says one
> of the sentences below. Each one is listed with the rule it violates and the gate
> that catches it — because rebutting an excuse in prose only works until the next
> session, and a gate works every time.
> (Pattern credit: Superpowers' red-flags table. Theirs answers each excuse with
> better prose; ours answers with the machinery that fires anyway.)

If a step feels skippable, find your sentence here first. If it's here, the answer
is already no. If it's genuinely not here, that is a decision-queue question
(`{paths.pm}/decisions.md`), never a unilateral skip.

| # | The excuse | The rule | The gate that catches it |
|---|---|---|---|
| 1 | "The test is flaky anyway." | /verify runs its steps in the fixed cheapest-first order; a skipped step DECLARES itself and why — silent skips are failures. Flaky = a finding to report, not a step to drop. | `gate.sh` (profile manifest owns the step list) — exit ≠ 0 blocks done |
| 2 | "This change is too small to need review." | The fence does not measure size. Code reaches the protected branch only with a committed review dossier behind it. | `review_check` at the pre-push hook; the only bypass is a named hatch (`ALLOW_PUSH_NOREVIEW=1`) appended to `{paths.pm}/hatch-log.md` |
| 3 | "I'll add evidence after merging." | Evidence exists BEFORE the verdict — files a stranger can open, not intentions. A claim without recorded output is not a claim. | `evd_check` / `evd_ui_check` red without manifest + screenshots that open, are readable, and are not blank |
| 4 | "The gate is misconfigured — bypassing it." | Agents do not adjudicate gates. A gate believed wrong gets a red `--selftest` proving it, or it stands. Bypass = named hatch + hatch-log entry; the secret scan has no hatch at all. | `doctor` (17 selftests); pre-push hatch logging; `gates.yaml` is a trust boundary the agent doesn't edit |
| 5 | "It passed locally." | Local memory is not a record. The verify gate's exact result lines are recorded, and CI re-runs them where nobody's shell history can vouch for anything. | /verify recorded results + CI workflow; `review_check` voids cards whose findings trace to nothing executed |
| 6 | "Renaming the command fixed CI." | The step list lives in the profile manifest, not in the agent's hands — a step is present or loudly skipped, never redefined. And every checker has proven it can fail: an always-green pipeline is itself a red flag. | `gate.sh` manifest + `--selftest` mutation proofs (a gate that has never been red does not exist) |
| 7 | "The spec obviously means X." | The spec is the spec. Shards are verbatim and byte-checked; a gap becomes a 3-condition question in the decision queue, never a guess baked into code. | `verbatim_gate`; `dor_check` bounces tickets built on guesses |
| 8 | "QA already passed this last week." | A verdict is valid only for the commit it examined. Code moved after judgment → the verdict is stale and the ticket re-queues. | `stale_verdict_check` (pinned-COMMIT-first) |
| 9 | "I reviewed my own work — it's fine." | Self-review is self-grading. Approval comes from fresh reviewer agents with empty context, and an APPROVE without a "what I tried to break" list is invalid. | `review_check` (card form: traces, tried-to-break list, verdict vocabulary) |
| 10 | "Bookkeeping later — the code is the point." | Work without a ledger row does not exist. The ledger is append-at-end, schema-checked, single-writer, committed before any branch switch. | `log_check` (schema + monotonic dates + token accounting format) |
| 11 | "These old files are clutter — cleaning up." | Bookkeeping and evidence shrink by accident more often than by intent. A shrink >20% in guarded paths blocks the commit unless intent is declared. | `docs_shrink_check` |
| 12 | "The PR speaks for itself." | The ticket is not done without the plain-language report comment — all seven parts, posted to the tracker, read back to confirm it landed. | `comment_check` ([R1]..[R7] markers + tracker read-back) |

Two standing corollaries:

- **Every excuse above was once used successfully.** The gates exist because the
  prose version of each rule was measured being skipped (see `provenance.md`). New
  excuse observed in the wild → it goes in this table, and the framework review
  (ops §6) decides whether it needs a new gate or an existing one's mutation added.
- **This table binds humans too.** The owner can waive a wait-for-human gate through
  the autonomy ladder (ops §3) — with a paper trail. Nobody, human or agent, waives
  a quality gate: those never relax at any autonomy level.
