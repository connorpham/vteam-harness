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
#
# Selftest: --selftest (temp repo: grown ledger green + 2 shrink mutations red
# + declared-intent hatch).
set -uo pipefail
. "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/lib/ctx.sh"

if [[ "${1:-}" == "--selftest" ]]; then
  SELF="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/$(basename "${BASH_SOURCE[0]}")"
  tmp=$(mktemp -d); trap 'rm -rf "$tmp"' EXIT
  fail() { echo "docs_shrink_check selftest: FAIL — $1" >&2; exit 1; }
  ( cd "$tmp" && git init -q . && git config user.email t@t.t && git config user.name t )
  mkdir -p "$tmp/docs/pm" "$tmp/docs/adr"
  seq 1 30 | sed 's/^/decision line /' > "$tmp/docs/pm/decisions.md"
  seq 1 20 | sed 's/^/adr line /'      > "$tmp/docs/adr/0001.md"
  ( cd "$tmp" && git add -A && git commit -qm init )
  # green: a ledger that GROWS passes
  seq 1 35 | sed 's/^/decision line /' > "$tmp/docs/pm/decisions.md"
  ( cd "$tmp" && env -u GITHUB_BASE_REF bash "$SELF" ) >/dev/null \
    || fail "grown ledger should pass"
  # mutation 1: 30 → 5 lines in the pm ledger must RED
  seq 1 5 | sed 's/^/decision line /' > "$tmp/docs/pm/decisions.md"
  if ( cd "$tmp" && env -u GITHUB_BASE_REF bash "$SELF" ) >/dev/null; then
    fail "83% shrink of the pm ledger should RED"
  fi
  ( cd "$tmp" && git checkout -q -- docs/pm/decisions.md )
  # mutation 2: shrink in the ADR ledger must RED too
  seq 1 2 | sed 's/^/adr line /' > "$tmp/docs/adr/0001.md"
  if ( cd "$tmp" && env -u GITHUB_BASE_REF bash "$SELF" ) >/dev/null; then
    fail "90% shrink of the adr ledger should RED"
  fi
  # declared intent: the hatch passes LOUDLY
  ( cd "$tmp" && env -u GITHUB_BASE_REF ALLOW_DOCS_SHRINK=1 bash "$SELF" ) >/dev/null \
    || fail "ALLOW_DOCS_SHRINK=1 should pass on declared intent"
  echo "docs_shrink_check selftest: OK (grow green + 2 shrink mutations red + declared-intent hatch)"
  exit 0
fi

cd "$(vteam_root)"

PM_DIR=$(vteam_cfg paths.pm docs/pm)
ADR_DIR=$(vteam_cfg paths.adr docs/adr)
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
