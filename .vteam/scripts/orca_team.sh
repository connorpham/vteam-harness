#!/usr/bin/env bash
# orca_team.sh — the /team parallel-mode coordination transport (Claude Code + Orca).
#
# A TOOL, not a gate: the PM coordinator calls it to run parallel DEV on the Orca
# orchestration bus (a real, persistent, addressable mailbox — unlike the
# subagent SendMessage/ListAgents path, which is disabled for spawned agents).
# It degrades cleanly when Orca is absent: it prints the tool-neutral fallback
# (agents return their result as TEXT to the PM, who integrates) and exits 0.
#
# The guards are unchanged and live elsewhere: parallel_check (disjoint file
# scope) and coord_check (a chat handoff must become real CODE-SCOPE). This
# script only carries messages; it never merges and never writes the ledger —
# those stay the PM's single hand.
#
# Usage:
#   orca_team.sh status                 transport reachable? (exit 0 either way)
#   orca_team.sh open-run <objective>   create a Run + ensure coordination.md; print RUN=<id>
#   orca_team.sh wait <run_id>          block for worker_done/escalation/question
set -uo pipefail
cd "$(git rev-parse --show-toplevel 2>/dev/null || echo .)"

# --- resolve the Orca CLI (per the orchestration skill's rules) --------------
resolve_cli() {
  # An explicit override is the caller's responsibility (it is honored as-is,
  # even on Linux); the no-bare-orca guard below is for the AUTO path only.
  if [ -n "${ORCA_CLI_COMMAND:-}" ]; then echo "$ORCA_CLI_COMMAND"; return; fi
  if [ -n "${ORCA_DEV_REPO_ROOT:-}" ] && command -v orca-dev >/dev/null 2>&1; then echo orca-dev; return; fi
  if [ "$(uname -s)" = "Linux" ]; then
    # On Linux, bare `orca` is the GNOME screen reader — NEVER run it. Use orca-ide
    # or nothing (empty → caller treats the transport as unavailable → fallback).
    command -v orca-ide >/dev/null 2>&1 && echo orca-ide || echo ""
    return
  fi
  echo orca   # macOS / Windows: `orca` is the Orca CLI
}
ORCA="$(resolve_cli)"

# paths.pm from config (scalar subset), default docs/pm
PM="docs/pm"
if [ -f .vteam/scripts/lib/ctx.sh ]; then
  # shellcheck disable=SC1091
  . .vteam/scripts/lib/ctx.sh 2>/dev/null && PM="$(vteam_cfg paths.pm 2>/dev/null || echo docs/pm)"
fi
COORD="$PM/coordination.md"

fallback() {
  echo "⚠ Orca transport unavailable — parallel DEV falls back to TEXT relay."
  echo "  Each worktree DEV agent returns its result (ledger row + report + any"
  echo "  contract handoff) as TEXT to the PM; the PM writes coordination.md +"
  echo "  the ledger and merges serially. parallel_check + coord_check still gate."
}

transport_up() {
  [ -n "$ORCA" ] || return 1                 # no safe CLI resolved (e.g. Linux, no orca-ide)
  command -v "$ORCA" >/dev/null 2>&1 || return 1
  # Parse the JSON properly (not a literal grep that a whitespace/key change breaks).
  "$ORCA" status --json 2>/dev/null | python3 -c '
import sys, json
try:
    d = json.load(sys.stdin)
except Exception:
    sys.exit(1)
sys.exit(0 if d.get("result", {}).get("runtime", {}).get("reachable") is True else 1)
' || return 1
  return 0
}

ensure_coord() {
  mkdir -p "$PM"
  [ -f "$COORD" ] || printf '# Coordination log — peer handoffs between parallel DEV agents\n\n| Round | From | To | Path/Contract | What/why |\n|---|---|---|---|---|\n' > "$COORD"
}

case "${1:-}" in
  status)
    if transport_up; then
      echo "✅ Orca transport reachable via '$ORCA' — parallel DEV agents coordinate on the Run mailbox."
    else
      echo "ℹ️  Orca transport not reachable via '$ORCA'."
      fallback
    fi
    exit 0 ;;
  open-run)
    obj="${2:-/team parallel session}"
    ensure_coord
    if ! transport_up; then fallback; echo "COORD=$COORD"; exit 0; fi
    out="$("$ORCA" orchestration run-create --objective "$obj" --json 2>/dev/null)"
    rid="$(printf '%s' "$out" | python3 -c '
import sys, json
try:
    print(json.load(sys.stdin).get("result", {}).get("run", {}).get("id", ""))
except Exception:
    print("")
')"
    if [ -z "$rid" ]; then echo "⚠ could not create a Run (see: $ORCA orchestration run-create)"; fallback; exit 0; fi
    echo "RUN=$rid"
    echo "COORD=$COORD"
    echo "→ dispatch each DEV agent bound to this Run (see docs/team/parallel-transport.md);"
    echo "  agents coordinate via 'orca orchestration send/check/ask'; PM: 'orca_team.sh wait $rid'."
    exit 0 ;;
  wait)
    rid="${2:?usage: orca_team.sh wait <run_id>}"
    transport_up || { fallback; exit 0; }
    exec "$ORCA" orchestration check --run "$rid" --wait --types worker_done,escalation,question --timeout-ms "${3:-600000}" --json ;;
  *)
    echo "usage: orca_team.sh {status | open-run <objective> | wait <run_id>}"; exit 2 ;;
esac
