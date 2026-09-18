# VT-41 · proof — commands run on 2026-09-18

## 1. Why two of the three could never be green
```
$ gh pr checks 69   → fail=2 (analyze javascript-typescript, analyze python)  pass=6
$ gh pr checks 70   → fail=2                                                  pass=6
$ gh pr checks 71   → pass=9
```
#69 bumps `init`, #70 bumps `analyze`, and the two must run on the same version of
github/codeql-action. Either PR alone creates the mismatch, so the analyze jobs fail. #71
touches `upload-sarif` in a different workflow, which is why it alone was green.

## 2. The new pin, verified upstream rather than trusted
```
$ gh api repos/github/codeql-action/commits/b96794f015dfd88f77b49b1c93e0fa7110f94c63
commit: b96794f015df  2026-09-09T14:02:30Z  Merge pull request #4131 from github/update-v4.38.0-7e08580a
$ gh api repos/github/codeql-action/tags --paginate | (tags containing that sha)
v4.38.0
v4
$ (the pin being replaced)
commit: cdf488f595d8  2026-08-26T14:39:15Z
```
The SHA exists, is reachable from both `v4.38.0` and `v4`, and is 14 days newer than the pin
it replaces — so the `# v4` comment beside it stays true.

## 3. The change
```
   .github/dependabot.yml          | 9 +++++++++
   .github/workflows/codeql.yml    | 4 ++--
   .github/workflows/scorecard.yml | 2 +-
   3 files changed, 12 insertions(+), 3 deletions(-)

  .github/workflows/codeql.yml:25:      - uses: github/codeql-action/init@b96794f015dfd88f77b49b1c93e0fa7110f94c63 # v4
  .github/workflows/codeql.yml:27:      - uses: github/codeql-action/analyze@b96794f015dfd88f77b49b1c93e0fa7110f94c63 # 
  .github/workflows/scorecard.yml:26:      - uses: github/codeql-action/upload-sarif@b96794f015dfd88f77b49b1c93e0fa7110f
```
And the root cause, closed: `.github/dependabot.yml` now groups `github/codeql-action*`, so
the next bump of the family arrives as ONE pull request instead of three that fight each other.

## 4. CI on the combined change (PR #91, commit 22fdffe)
```
$ gh pr checks 91
CodeQL:pass  analyze (javascript-typescript):pass  analyze (python):pass
e2e (20):pass  e2e (20):pass  e2e (22):pass  e2e (22):pass  gate:pass  gate:pass
```
The two `analyze` jobs are the ones that were RED on #69 and #70. Green here, on a change that
moves `init` and `analyze` together, is the diagnosis confirmed rather than argued.
