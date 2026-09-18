#!/usr/bin/env bash
# stop_state.sh — write down the state a lane leaves behind when a session ends mid-ticket.
#
# Why: the 2026-09-03 benchmark arm stopped with 11 uncommitted files, a red unit suite and
# no closing entry — the next reader had to reconstruct the stop from `git status`. A stop
# is not a failure; an UNRECORDED stop is. The claude-code adapter runs this from a
# SessionEnd hook; other tools run it by hand (workflows/dev.md, "Stopping mid-ticket").
#
# Contract: never fails the session (exit 0 always), never commits, idempotent — the file
# is rewritten, the tasksheet line is replaced, not duplicated.
#   bash .vteam/scripts/stop_state.sh            # records if there is anything to record
#   VTEAM_TICKET=PROJ-7 bash …/stop_state.sh     # key override when the branch has none
#   bash .vteam/scripts/stop_state.sh --selftest
# Writes {paths.evidence}/<KEY>/dev/STOP-STATE.md when the tree is dirty OR the branch is
# ahead of the base branch, and a ticket key can be derived from `feat|fix/<KEY>-…` or
# $VTEAM_TICKET. Nothing to record → prints why and exits 0.
set -uo pipefail
SELF="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/$(basename "${BASH_SOURCE[0]}")"
LIB="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/lib/ctx.sh"

record() {
  cd "${CLAUDE_PROJECT_DIR:-.}" 2>/dev/null || { echo "stop_state: no project dir — nothing recorded"; return 0; }
  git rev-parse --show-toplevel >/dev/null 2>&1 || { echo "stop_state: not a git repository — nothing recorded"; return 0; }
  cd "$(git rev-parse --show-toplevel)" || return 0
  local branch key evd dirty base ahead head_line now file sheet
  branch=$(git branch --show-current 2>/dev/null || echo "")
  key="${VTEAM_TICKET:-}"
  if [ -z "$key" ]; then
    key=$(printf '%s' "$branch" | sed -nE 's#^(feat|fix)/([A-Za-z][A-Za-z0-9]*-[0-9]+)-.*#\2#p')
  fi
  key=$(printf '%s' "$key" | tr '[:lower:]' '[:upper:]')
  if [ -z "$key" ]; then
    echo "stop_state: no ticket key (branch '${branch:-detached}', VTEAM_TICKET unset) — nothing recorded"
    return 0
  fi
  dirty=$(git status --porcelain 2>/dev/null | wc -l | tr -d ' ')
  base=$(git symbolic-ref -q --short refs/remotes/origin/HEAD 2>/dev/null || true)
  if [ -z "$base" ]; then
    for b in main master; do
      if git show-ref -q --verify "refs/heads/$b"; then base="$b"; break; fi
    done
  fi
  ahead=0
  if [ -n "$base" ] && [ "$branch" != "${base#origin/}" ]; then
    ahead=$(git rev-list --count "$base..HEAD" 2>/dev/null || echo 0)
  fi
  if [ "$dirty" -eq 0 ] && [ "$ahead" -eq 0 ]; then
    echo "stop_state: $key — tree clean and nothing ahead of ${base:-<no base>} — nothing to record"
    return 0
  fi
  evd=evd
  if [ -f "$LIB" ]; then
    # shellcheck disable=SC1090
    . "$LIB"
    evd=$(vteam_cfg paths.evidence evd 2>/dev/null) || evd=evd
  fi
  now=$(date -u +%Y-%m-%dT%H:%M:%SZ)
  head_line=$(git log -1 --format='%h %s' 2>/dev/null || echo "(no commits)")
  file="$evd/$key/dev/STOP-STATE.md"
  mkdir -p "$evd/$key/dev"
  {
    echo "# STOP-STATE — $key"
    echo
    echo "Written by stop_state.sh when the session ended with work in flight. Finish it, or set the"
    echo "ticket to Blocked with a one-line reason; a stop state older than 7 days is a gate violation."
    echo
    echo "- recorded: $now"
    echo "- branch: ${branch:-detached}"
    echo "- head: $head_line"
    echo "- base: ${base:-<no base branch found>} (+$ahead commits ahead)"
    echo "- uncommitted: $dirty files"
    echo
    echo "## git status --short"
    echo '```'
    git status --porcelain 2>/dev/null | head -200
    echo '```'
    echo
    echo "## last gate"
    if [ -f .review-scratch/gate.log ]; then
      echo '```'; grep -E "^GATE:" .review-scratch/gate.log | tail -1; echo '```'
    else
      echo "no gate log at .review-scratch/gate.log — run \`bash .vteam/scripts/gate.sh\` before trusting this tree"
    fi
    echo
    echo "## failing tests"
    if [ -f .review-scratch/test.log ]; then
      echo '```'; grep -E "✗|✘|FAIL|failed|RED" .review-scratch/test.log | head -20; echo '```'
    else
      echo "no test log at .review-scratch/test.log"
    fi
  } > "$file"
  sheet="$evd/$key/dev/tasksheet.md"
  if [ -f "$sheet" ]; then
    local line tmp
    line="- stop-state: $now — $dirty uncommitted files, +$ahead ahead of ${base:-<no base>}, see STOP-STATE.md"
    tmp=$(mktemp)
    grep -v '^- stop-state: ' "$sheet" > "$tmp"; printf '%s\n' "$line" >> "$tmp"; mv "$tmp" "$sheet"
  fi
  echo "stop_state: wrote $file ($dirty uncommitted, +$ahead ahead of ${base:-<no base>})"
  return 0
}

if [ "${1:-}" = "--selftest" ]; then
  fail() { echo "stop_state selftest: FAIL — $1" >&2; exit 1; }
  td=$(mktemp -d); trap 'rm -rf "$td"' EXIT
  ( cd "$td" && git init -q . && git config user.email t@t.t && git config user.name t \
      && printf 'version: 1\npaths:\n  evidence: evd\n' > vteam.config.yaml \
      && mkdir -p evd/PROJ-1/dev && printf '# tasksheet PROJ-1\n' > evd/PROJ-1/dev/tasksheet.md \
      && git add -A && git commit -qm init && git branch -M main ) || fail "fixture"
  run() { ( cd "$td" && CLAUDE_PROJECT_DIR="$td" VTEAM_TICKET="${VTEAM_TICKET:-}" bash "$SELF" ); }
  f="$td/evd/PROJ-1/dev/STOP-STATE.md"
  # 1) ticket branch + dirty tree → recorded with the right fields, tasksheet line appended
  ( cd "$td" && git checkout -q -b feat/PROJ-1-thing && echo wip > wip.txt )
  out=$(run) || fail "must exit 0 (dirty)"
  [ -f "$f" ] || fail "dirty ticket branch must write STOP-STATE.md (got: $out)"
  grep -q '^- branch: feat/PROJ-1-thing$' "$f" || fail "branch field"
  grep -q '^- uncommitted: 1 files$' "$f" || fail "uncommitted count"
  grep -q '^- recorded: 20[0-9][0-9]-' "$f" || fail "recorded timestamp"
  grep -q '^?? wip.txt$' "$f" || fail "git status block"
  [ "$(grep -c '^- stop-state: ' "$td/evd/PROJ-1/dev/tasksheet.md")" -eq 1 ] || fail "tasksheet line appended once"
  # 2) idempotent: a second run replaces, never duplicates
  run >/dev/null
  [ "$(grep -c '^- stop-state: ' "$td/evd/PROJ-1/dev/tasksheet.md")" -eq 1 ] || fail "second run must not duplicate the tasksheet line"
  # 3) committed-ahead but clean tree still records (+1 ahead of main) — the file is rewritten
  ( cd "$td" && git add -A && git commit -qm "wip(PROJ-1): x" )
  run >/dev/null
  grep -q '^- base: main (+1 commits ahead)$' "$f" || fail "ahead-of-base must record (+1)"
  grep -q '^- uncommitted: 0 files$' "$f" || fail "clean tree count 0"
  # 4) clean tree, nothing ahead → nothing written
  ( cd "$td" && git checkout -q -- . && git checkout -q main && rm -f evd/PROJ-1/dev/STOP-STATE.md )
  out=$(VTEAM_TICKET=PROJ-1 run)
  case "$out" in *"nothing to record"*) ;; *) fail "clean+not-ahead must record nothing (got: $out)";; esac
  [ ! -f "$f" ] || fail "clean run must not write a file"
  # 5) dirty but no ticket key (branch main, no override) → nothing written
  ( cd "$td" && echo x > stray.txt )
  out=$(run)
  case "$out" in *"no ticket key"*) ;; *) fail "keyless run must say so (got: $out)";; esac
  [ ! -f "$f" ] || fail "keyless run must not write a file"
  # 6) VTEAM_TICKET override records on a keyless branch, key upper-cased
  out=$(VTEAM_TICKET=proj-1 run)
  [ -f "$f" ] || fail "VTEAM_TICKET override must record (got: $out)"
  grep -q '^# STOP-STATE — PROJ-1$' "$f" || fail "key upper-cased from the override"
  echo "stop_state selftest: OK (dirty ticket branch recorded + fields · idempotent tasksheet line · ahead-only recorded · clean+level skips · keyless skips · VTEAM_TICKET override)"
  exit 0
fi

record
exit 0
