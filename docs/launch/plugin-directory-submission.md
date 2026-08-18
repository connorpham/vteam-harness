# DRAFT — Anthropic plugin directory submission

> **DRAFT — the owner posts this, not an agent.** Submit at the official form:
> **https://clau.de/plugin-directory-submission** (the funnel behind
> anthropics/claude-plugins-official and claude-plugins-community). Submissions go
> through automated security scanning; acceptance into the official list is
> curated at Anthropic's discretion.
>
> **Pre-flight before submitting:**
> 1. The marketplace must be live on the default branch:
>    `.claude-plugin/marketplace.json` at the repo root and
>    `plugins/vteam/.claude-plugin/plugin.json` — both already pass
>    `claude plugin validate` (one advisory warning: optional `version` omitted on
>    purpose so git-sourced installs track the resolved commit).
> 2. Test the install path yourself, from a clean machine if possible:
>    `/plugin marketplace add connorpham/vteam-harness` then
>    `/plugin install vteam@vteam-harness` then `/vteam:setup`.
> 3. Note the community list already contains plugins named "adversarial-review" /
>    "adversarial-spec" — the verification-framework position is worth claiming
>    promptly.

Paste-ready field content (adapt to the form's actual labels):

---

**Plugin name:**

```
vteam
```

**Marketplace / repository:**

```
https://github.com/connorpham/vteam-harness
```

**Marketplace name (as declared in marketplace.json):**

```
vteam-harness
```

**Install commands:**

```
/plugin marketplace add connorpham/vteam-harness
/plugin install vteam@vteam-harness
```

**Short description:**

```
Proof-of-done for AI agents: a virtual PM/BA/SA/DEV/QA team plus 15 machine gates
that fail red when an agent claims work it can't prove.
```

**Longer description (if the form has one):**

```
vteam installs a virtual AI team into any repo and makes "done" a machine's
verdict instead of the agent's claim: committed review dossiers enforced at git
push, evidence files validated by scripts (blank screenshots detected by pixel
analysis), QA verdicts pinned to the commit they examined and expired when the
code moves, a fail-closed secret scan, and a --selftest mutation proof on every
checking gate — a gate that has never been red does not exist.

The plugin itself is deliberately small: one skill (/vteam:setup) that grades the
repo (npx vteam-harness audit, 0-100, works with no install), installs the harness
(npx vteam-harness init), and verifies it (npx vteam-harness doctor — all 17 gate
selftests must pass). It ships no plugin-level hooks on purpose: a plugin hook
would fire in every repo you open, so vteam's SessionStart doctrine re-injection
is wired per-repo by init instead. The gates are tool-agnostic — the same install
drives Cursor, Windsurf, Codex, and Copilot.
```

**Category / tags (pick what the form offers):**

```
agent orchestration · quality gates · code review · QA / verification
```

**Author:**

```
connorpham — https://github.com/connorpham
```

---

If accepted, announce it (X thread + README badge) — marketplace acceptance was
its own news cycle for Superpowers (~Jan 2026).
