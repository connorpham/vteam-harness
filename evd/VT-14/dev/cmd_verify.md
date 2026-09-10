# VT-14 — DEV evidence: progressive disclosure + one routing fix

BASE-COMMIT: dfa10f1 (VT-13 merged) · the change itself is UNCOMMITTED at capture time
CAPTURED-AT: 2026-09-10T08:37:08Z

Everything below was RUN against the working tree that holds this change.

## 1. The gate still passes, and the six required sections survive

```
$ python3 core/scripts/competency_check.py
✅ competency_check: 31 competencies well-formed and indexed under /Users/connorpham/Documents/vteam/docs/team/competencies

$ grep -E "^## " docs/team/competencies/dev/dev-testing-craft.md
## Identity
## When this applies
## Decide
## Rules
## Reviewer lens
## Sources

$ tail -1 docs/team/competencies/dev/dev-testing-craft.md
Rationalizations, red flags and a worked example live in `reference/dev-testing-craft.md` — opened when needed, never loaded by default.
```

Rationalizations / Red flags / Example are absent from the body and present in
the reference file — they are the three sections `REQUIRED_SECTIONS` does not
list, which is what makes the move gate-legal.

## 2. What moved, per file

```
  ROLE   COMPETENCY                     BEFORE  AFTER  MOVED
  ba     ba-acceptance-criteria           1083    876    207
  ba     ba-story-slicing                 1072    820    252
  dev    dev-codebase-design               732    587    145
  dev    dev-error-handling                742    566    176
  dev    dev-identity                      807    674    133
  dev    dev-security-basics               815    641    174
  dev    dev-testing-craft                 801    628    173
  pm     pm-prioritisation                1076    837    239
  qa     qa-case-writing                   822    732     90
  qa     qa-heuristics                     766    656    110
  qa     qa-hostile-inputs                 747    625    122
  qa     qa-identity                       848    708    140
  qa     qa-report-writing                 685    550    135
  qa     qa-requirement-smells             811    703    108
  qa     qa-test-design                    821    689    132
  qa     qa-user-mindset                   867    744    123

  TOTAL MOVED: 2459 words ≈ 3319 tokens out of the default load path
```

## 3. Reference files created, one per competency

```
$ ls docs/team/competencies/*/reference/ | wc -l
20
  ba   2 file
  dev  5 file
  pm   1 file
  qa   12 file

$ head -6 docs/team/competencies/dev/reference/dev-testing-craft.md
<!-- Reference detail for dev-testing-craft. Moved out of the competency body so the
     lane spends its context on the ticket, not on the rulebook. The competency is
     the METHOD; this is the argument, the smell list and the worked case. -->

# dev-testing-craft — rationalizations, red flags, example

```

## 4. The routing fix, and why only one

Each `always` QA competency was judged against its own description — is the
stated trigger matchable from a ticket (labels, paths, profile, text)?

```
  qa-identity            "any ticket"                        → always is correct
  qa-requirement-smells  "reading a ticket or spec"           → always is correct
  qa-test-design         "choosing the 2–5 cases"             → always is correct
  qa-case-writing        "writing a test case record"         → always is correct
  qa-report-writing      "writing the verification report"    → always at V5, correct
  qa-user-mindset        "any UI verification"                → CONDITION → routed
  qa-heuristics          "when the spec is silent"            → discovered mid-work,
                                                                NOT matchable → left always
  qa-hostile-inputs      "choosing values for a boundary case" → every input → left always
```

One file changed, not the two-to-three first estimated. The estimate was wrong
and is corrected here rather than quietly met.

## 5. The gate

```
$ bash .vteam/scripts/gate.sh
```
