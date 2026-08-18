#!/usr/bin/env bash
# lockfile_check.sh — one repo, one package manager.
#
# Why this is a script and not an inline gates.yaml one-liner: the original
# inline form (`ls a b c && exit 1 || true`) could NEVER go red — `ls` exits
# non-zero unless ALL listed files exist, so a pnpm lockfile sailed through a
# gate whose whole job was to flag it (found on a real pnpm repo in the
# 2026-08-18 field trials, issue #18). An always-green gate shipped inside the
# framework whose own law is "a gate that has never been red does not exist" —
# and it slipped precisely because inline step commands carry no selftest.
# Logic now lives here, WITH the selftest, and doctor re-runs it on every install.
#
# Behavior: reads stack.package_manager from vteam.config.yaml (default npm).
# The expected manager's lockfile is welcome; any OTHER manager's lockfile at
# the repo root is RED — two managers means two dependency truths.
#
#   bash lockfile_check.sh            # check the repo
#   bash lockfile_check.sh --selftest # prove green AND red in a temp dir
set -u

check_dir() { # <dir> <package_manager> → 0 clean / 1 foreign lockfile found
  local dir="$1" pm="$2" fail=0 f mgr
  local pairs="npm:package-lock.json pnpm:pnpm-lock.yaml yarn:yarn.lock bun:bun.lockb bun:bun.lock"
  for pair in $pairs; do
    mgr="${pair%%:*}"; f="${pair#*:}"
    [ "$mgr" = "$pm" ] && continue
    if [ -e "$dir/$f" ]; then
      echo "❌ $f present but stack.package_manager is '$pm' — one repo, one package manager"
      fail=1
    fi
  done
  return $fail
}

if [ "${1:-}" = "--selftest" ]; then
  td="$(mktemp -d)"; trap 'rm -rf "$td"' EXIT
  # green path: only the declared manager's lockfile
  : > "$td/package-lock.json"
  check_dir "$td" npm >/dev/null || { echo "lockfile_check selftest: FAIL (own lockfile flagged)"; exit 1; }
  # red path 1: a single foreign lockfile alone (the exact hole from issue #18)
  rm -f "$td/package-lock.json"; : > "$td/pnpm-lock.yaml"
  check_dir "$td" npm >/dev/null && { echo "lockfile_check selftest: FAIL (lone pnpm-lock passed an npm repo)"; exit 1; }
  # red path 2: right manager, plus a stray second one
  : > "$td/package-lock.json"
  check_dir "$td" npm >/dev/null && { echo "lockfile_check selftest: FAIL (npm+pnpm mix passed)"; exit 1; }
  # green path 2: pnpm repo with only pnpm-lock
  rm -f "$td/package-lock.json"
  check_dir "$td" pnpm >/dev/null || { echo "lockfile_check selftest: FAIL (pnpm repo with own lockfile flagged)"; exit 1; }
  echo "lockfile_check selftest: OK (2 green paths + 2 red paths — including the lone-foreign-lockfile hole)"
  exit 0
fi

cd "$(git rev-parse --show-toplevel)"
PM="$(python3 .vteam/scripts/lib/ctx.py stack.package_manager 2>/dev/null || echo npm)"
if check_dir . "$PM"; then
  echo "✅ lockfile: single package manager ($PM)"
else
  echo "   Remove the foreign lockfile(s), or fix stack.package_manager in vteam.config.yaml."
  exit 1
fi
