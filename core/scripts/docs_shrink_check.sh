#!/usr/bin/env bash
# docs_shrink_check.sh — block bookkeeping documents from shrinking by accident.
#
# Why: a decision queue was once cut from 81 lines to 1 by an errant doc-editing
# script (a ternary swallowed the else branch). No gate went red — docs live in
# no lint, no tsc, no test, no build — and it nearly reached the protected branch
# inside a refactor PR. Losing that file loses the whole decision queue.
#
# Law: the project's ledgers only GROW or get edited in place. Shrinking >20% of
# lines in one change signals an accidental overwrite, not editing. Real deletions
# declare intent:  ALLOW_DOCS_SHRINK=1 bash .vteam/scripts/docs_shrink_check.sh
set -uo pipefail
cd "$(git rev-parse --show-toplevel)"

PM_DIR=$(python3 .vteam/scripts/lib/ctx.py paths.pm 2>/dev/null || echo docs/pm)
ADR_DIR=$(python3 .vteam/scripts/lib/ctx.py paths.adr 2>/dev/null || echo docs/adr)
WATCH="^(${PM_DIR}|${ADR_DIR})/.*\.md$"
THRESHOLD=20
fail=0

# Pick the comparison baseline by environment. The first version compared
# `git diff --cached` — always green in BOTH places the gate really runs (nothing
# staged locally; CI index equals HEAD). Correct baselines:
#   · CI on a PR (GITHUB_BASE_REF set): HEAD vs the base branch — catches every
#     shrink across the whole PR.
#   · Local: WORKTREE vs HEAD — catches it the moment the gate runs, pre-stage.
#   · CI on a push to the protected branch (no base ref): the PR already checked
#     it → nothing to compare, pass.
if [[ -n "${GITHUB_BASE_REF:-}" ]]; then
  git fetch --no-tags --depth=1 origin "$GITHUB_BASE_REF" >/dev/null 2>&1
  base="FETCH_HEAD"
  after_lines() { git show "HEAD:$1" 2>/dev/null | wc -l | tr -d ' '; }
  changed() { git diff "$base" HEAD --name-only --diff-filter=M | grep -E "$WATCH" || true; }
else
  base="HEAD"
  after_lines() { wc -l < "$1" 2>/dev/null | tr -d ' '; }
  changed() { git diff HEAD --name-only --diff-filter=M | grep -E "$WATCH" || true; }
fi

while IFS= read -r f; do
  [[ -z "$f" ]] && continue
  git cat-file -e "$base:$f" 2>/dev/null || continue
  before=$(git show "$base:$f" | wc -l | tr -d ' ')
  after=$(after_lines "$f")
  [[ "$before" -eq 0 ]] && continue
  drop=$(( (before - after) * 100 / before ))
  if [[ "$drop" -gt "$THRESHOLD" ]]; then
    echo "❌ $f: $before → $after lines (lost ${drop}%)"
    fail=1
  fi
done < <(changed)

if [[ "$fail" -eq 1 ]]; then
  if [[ "${ALLOW_DOCS_SHRINK:-}" == "1" ]]; then
    echo "⚠️  ALLOW_DOCS_SHRINK=1 — passing because intent was declared"
    exit 0
  fi
  echo ""
  echo "Ledgers only grow or get edited in place. A >${THRESHOLD}% shrink is usually an overwrite."
  echo "Inspect with: git diff $base -- <file>"
  echo "Deliberate deletion: re-run with ALLOW_DOCS_SHRINK=1."
  exit 1
fi
echo "✅ ${PM_DIR} + ${ADR_DIR} ledgers show no abnormal shrink"
