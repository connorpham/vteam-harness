# DRAFT — awesome-claude-code submission

> **DRAFT — the owner posts this, not an agent.** Submission is ONLY via the
> automated GitHub issue form ("Recommend a Resource") at
> https://github.com/hesreallyhim/awesome-claude-code/issues/new/choose — human PRs
> are rejected. One resource per issue.

## Attempt 1 — rejected 2026-08-18 (eligibility, not quality)

Issue [#2560](https://github.com/hesreallyhim/awesome-claude-code/issues/2560) was
closed as `not planned` by the `github-actions` bot with the generic CONTRIBUTING
pointer. The cause is the ground rule, and it is arithmetic, not judgment — a
resource must satisfy **at least one** of:

- **≥14 days old** (since the first commit on the default branch) **and** commits
  after day one, or
- **≥100 stars**.

On submission day the repo was **1 day old** (first commit on `main`:
2026-08-17T07:03Z) with **2 stars** — both conditions failed, so the bot closed it
before any human read the description. Nothing about vteam was assessed.

**Resubmit on or after 2026-08-31** (14 days after the first commit). The
"commits after day one" half is already satisfied and keeps accruing. Do not
resubmit earlier: CONTRIBUTING warns that non-compliant submissions "risk being
restricted from interacting with this repository temporarily", and a second
auto-close costs the one thing this list rewards — a clean record.

**Second fix, applied below:** the rejected description was five lines and read as
a pitch. CONTRIBUTING is explicit — "Resource descriptions should be written as
_descriptions_ - not a sales pitch. Don't address the reader... Keep it formatted
to one line. Don't use any emojis." The description in this draft is now one
factual line about mechanism.

Fields below map 1:1 to the issue form (`recommend-resource.yml`, fetched
2026-08-18).

---

**Title (issue title):**

```
[Resource]: vteam
```

**Display Name:**

```
vteam
```

**Category** (dropdown — single choice):

```
Agent Orchestration
```

*(Rationale: the list has no verification/QA category. vteam is a PM/BA/SA/DEV/QA
orchestration harness, so Agent Orchestration is the honest fit; "Security" would
oversell the secret-scan angle.)*

**Link:**

```
https://github.com/connorpham/vteam-harness
```

**Author Name:**

```
connorpham
```

**Author Link:**

```
https://github.com/connorpham
```

**Description** — ONE line, descriptive, no emojis, 10–500 chars:

```
A virtual PM/BA/SA/DEV/QA team for Claude Code and other agent tools in which completion is machine-checked: review dossiers are enforced at git push, evidence files are validated by scripts, QA verdicts are pinned to the commit they examined, and every checking gate carries a mutation self-test.
```

*(295 characters, single line. States what the software does; no second-person
address, no emojis, no superlatives — the three things the rejected version got
wrong on top of the eligibility gate.)*

**Checklist** — check the five required boxes truthfully (visit the repo first;
links working; Claude Code-specific; CONTRIBUTING.md read). **Leave the final
trap checkbox UNCHECKED** — the template plants a "do not check this box" item to
catch people who don't read.
