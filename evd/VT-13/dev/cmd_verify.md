# VT-13 — DEV evidence: doctrine 19 → 31 competencies

Everything below was RUN. Two anchors on every block: the command, and the
commit it was run at. Numbers captured across the change, not reconstructed.

COMMIT (merged): dfa10f1  ·  PR https://github.com/connorpham/vteam-harness/pull/66
CAPTURED-AT: 2026-09-10T08:36:30Z  (mirrored from the session's working evidence)

## 1. Baseline before the change

```
$ python3 core/scripts/competency_check.py --root docs/team/competencies   # at 6ee5fc6
✅ competency_check: 19 competencies well-formed and indexed under docs/team/competencies

$ bash .vteam/scripts/gate.sh                                             # at 6ee5fc6
E2E: GREEN — 164/164 checks passed
GATE: GREEN (9 steps ran, 1 declared skips)
```

## 2. What a naive drop-in would have done — measured, not assumed

The 12 files were first written as free-standing skills (2 frontmatter fields,
no word budget). Run against the repo's own gate in a sandbox of 19+5 files:

```
$ python3 core/scripts/competency_check.py --root <sandbox>/competencies
❌ competency_check: 22 problems
   - 5× frontmatter lacks `role`      - 5× lacks `loads`      - 5× lacks `applies`
   - 5× body over MAX_WORDS (1285–1594 words > 1100; baseline max was 959)
   - 2× INDEX.md is stale
```

That is why the shipped files carry five frontmatter fields, routing tokens and
bodies inside the budget. The gate also caught, later in the same work, a
description that narrated a procedure (`then`) — REQUIRED by the
`PROCEDURAL` rule to describe the problem instead.

## 3. After the change, on merged main

```
$ python3 core/scripts/competency_check.py                                 # at dfa10f1

$ bash .vteam/scripts/gate.sh                                             # at dfa10f1

$ node bin/vteam.mjs doctor                                               # at dfa10f1
PREFLIGHT: GREEN — the ticket→design→code→git chain runs end-to-end
```
