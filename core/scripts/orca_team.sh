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
#   orca_team.sh trust <path>           pre-accept Claude's trust dialog for a worktree
#   orca_team.sh --selftest             offline proof (fake orca, temp HOME) — see the block below

#
# Why `trust` exists: `orca orchestration worker-start --worktree new-child`
# creates a directory Claude Code has never seen, so Claude opens its "Do you
# trust the files in this folder?" dialog FIRST and eats the injected prompt —
# the worker sits at the dialog and the run reports agent_prompt_stalled. Marking
# the folder trusted before dispatch is the whole fix.
set -uo pipefail
# The caller's cwd, captured BEFORE we move to the repo root: `trust` takes a path
# from the caller, and resolving a relative one against the repo root instead of
# where it was typed is exactly the silent mis-target this script warns about.
ORIG_PWD="$PWD"
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

# ── selftest: offline, in a temp repo — a fake `orca` on PATH, HOME in a temp dir ──
# The tool talks to a bus and edits the user's ~/.claude.json; neither may be touched
# by a test, so both are stand-ins. Green paths + the refusals that protect the
# user's own config (VT-25 — this script had no test of any kind).
if [ "${1:-}" = "--selftest" ]; then
  SELF="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/$(basename "${BASH_SOURCE[0]}")"
  td="$(mktemp -d)"; trap 'rm -rf "$td"' EXIT
  fail() { echo "orca_team selftest: FAIL — $1" >&2; exit 1; }
  mkdir -p "$td/repo" "$td/bin" "$td/home" "$td/wt" "$td/wt2" "$td/wt3"
  ( cd "$td/repo" && git init -q . )
  cat > "$td/bin/orca" <<'FAKE'
#!/bin/sh
case "$*" in
  "status --json") echo "{\"result\":{\"runtime\":{\"reachable\":${FAKE_REACHABLE:-true}}}}" ;;
  orchestration\ run-create*) echo '{"result":{"run":{"id":"run-42"}}}' ;;
  orchestration\ check*) echo "CHECK $*" ;;
  *) echo "fake orca: unexpected $*" >&2; exit 9 ;;
esac
FAKE
  chmod +x "$td/bin/orca"
  run() { ( cd "$td/repo" && PATH="$td/bin:$PATH" HOME="$td/home" ORCA_CLI_COMMAND=orca bash "$SELF" "$@" ); }
  # status: reachable → ✅; unreachable → the TEXT-relay fallback, still exit 0
  out="$(run status)" || fail "status must exit 0"
  case "$out" in *"transport reachable"*) ;; *) fail "reachable status not reported: $out" ;; esac
  out="$(FAKE_REACHABLE=false run status)" || fail "unreachable status must still exit 0"
  case "$out" in *"falls back to TEXT relay"*) ;; *) fail "fallback not printed when unreachable: $out" ;; esac
  # open-run: the Run id comes from the transport, coordination.md is created with the header
  out="$(run open-run demo)" || fail "open-run must exit 0"
  case "$out" in *"RUN=run-42"*) ;; *) fail "run id not surfaced: $out" ;; esac
  [ -f "$td/repo/docs/pm/coordination.md" ] || fail "coordination.md not created"
  grep -q "^| Round | From | To |" "$td/repo/docs/pm/coordination.md" || fail "coordination.md lacks the handoff header"
  out="$(FAKE_REACHABLE=false run open-run demo)" || fail "open-run without transport must exit 0"
  case "$out" in *"COORD="*"coordination.md"*) ;; *) fail "fallback open-run must still name COORD: $out" ;; esac
  # wait: exec's the transport's check with the run id
  out="$(run wait run-42 5)" || fail "wait must pass the transport's exit 0"
  case "$out" in "CHECK orchestration check --run run-42 --wait"*) ;; *) fail "wait did not call check with the run id: $out" ;; esac
  # trust: creates ~/.claude.json 0600 with the flag, idempotent on the second run
  key="$(cd "$td/wt" && pwd)"
  out="$(run trust "$td/wt")" || fail "trust on an existing dir must exit 0"
  python3 - "$td/home/.claude.json" "$key" <<'PY' || fail "trust did not record the flag as 0600"
import json, os, stat, sys
d = json.load(open(sys.argv[1]))
assert d["projects"][sys.argv[2]]["hasTrustDialogAccepted"] is True, d
assert stat.S_IMODE(os.stat(sys.argv[1]).st_mode) == 0o600, oct(os.stat(sys.argv[1]).st_mode)
PY
  [ ! -e "$td/home/.claude.json.vteam-bak" ] || fail "a config we CREATED must not be backed up"
  out="$(run trust "$td/wt")" || fail "second trust must exit 0"
  case "$out" in *"already trusted"*) ;; *) fail "second trust is not idempotent: $out" ;; esac
  # a PRE-EXISTING config: other keys kept, mode 0600 kept, backed up exactly once
  printf '{"oauthAccount":{"x":1},"projects":{}}' > "$td/home/.claude.json"; chmod 600 "$td/home/.claude.json"
  run trust "$td/wt2" >/dev/null || fail "trust over an existing config must exit 0"
  [ -f "$td/home/.claude.json.vteam-bak" ] || fail "existing config was not backed up"
  grep -q '"oauthAccount"' "$td/home/.claude.json" || fail "existing keys were lost"
  mode="$(stat -f %Lp "$td/home/.claude.json" 2>/dev/null || stat -c %a "$td/home/.claude.json")"
  [ "$mode" = "600" ] || fail "mode 0600 not preserved (got $mode)"
  bak1="$(cat "$td/home/.claude.json.vteam-bak")"
  run trust "$td/wt3" >/dev/null || fail "third trust must exit 0"
  [ "$(cat "$td/home/.claude.json.vteam-bak")" = "$bak1" ] || fail "the backup was overwritten on a later run"
  # mutations: a path that does not exist, a config that is not JSON, an unknown subcommand
  if run trust "$td/nope" >/dev/null 2>&1; then fail "trust must refuse a non-existent path"; fi
  printf 'not json' > "$td/home/.claude.json"
  if run trust "$td/wt" >/dev/null 2>&1; then fail "trust must refuse to overwrite a non-JSON config"; fi
  [ "$(cat "$td/home/.claude.json")" = "not json" ] || fail "a REFUSED run modified the config"
  if run bogus >/dev/null 2>&1; then fail "an unknown subcommand must exit non-zero"; fi
  echo "orca_team selftest: OK (status reachable/unreachable, open-run with and without the transport, wait → check, trust: create 0600 + idempotent + backup-once + mode kept + bad path/bad JSON refused, unknown subcommand red)"
  exit 0
fi

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
  trust)
    # Set projects["<abs path>"].hasTrustDialogAccepted = true in ~/.claude.json so a
    # worker dispatched into a NEW worktree gets its prompt instead of a trust dialog.
    # Idempotent; backs the file up ONCE (never overwrites an existing backup, so the
    # pre-vteam original survives repeated runs); refuses a path that does not exist,
    # because trusting a typo silently leaves the real worktree untrusted.
    tgt="${2:?usage: orca_team.sh trust <path>}"
    case "$tgt" in /*) ;; *) tgt="$ORIG_PWD/$tgt" ;; esac   # relative → the CALLER's cwd
    [ -d "$tgt" ] || { echo "❌ trust: '$tgt' is not an existing directory (create the worktree first)"; exit 1; }
    # `cd` can fail on a directory that EXISTS but cannot be entered (mode 000,
    # a dead symlink target). Unchecked, the command substitution yielded "" and
    # we cheerfully trusted projects[""] and exited 0 — the exact silent
    # mis-target the -d guard above is meant to prevent.
    abs="$(cd "$tgt" 2>/dev/null && pwd)" || abs=""
    [ -n "$abs" ] || { echo "❌ trust: '$tgt' exists but cannot be entered (permissions?) — nothing was changed"; exit 1; }
    TRUST_PATH="$abs" python3 -c '
import json, os, shutil, sys
from pathlib import Path

target = os.environ["TRUST_PATH"]          # via env: never interpolated into code
cfg = Path.home() / ".claude.json"
existed = cfg.exists()
indent = 2
if existed:
    try:
        raw = cfg.read_text(encoding="utf-8")
        data = json.loads(raw)
    except (OSError, ValueError) as e:
        # This is the users own live Claude Code state. A config we cannot parse
        # gets refused loudly - never "repaired" by replacing it with ours.
        sys.exit(f"trust: cannot read {cfg} ({e}) - fix or move it, then retry")
    if not isinstance(data, dict):
        sys.exit(f"trust: {cfg} is not a JSON object - refusing to overwrite it")
    # Keep the file in the shape we found it. This config can be megabytes of
    # history; re-indenting a compact one would balloon it and noise up any
    # diff the owner takes of their own settings.
    indent = 2 if raw.startswith("{\n") else None
else:
    data = {}

projects = data.setdefault("projects", {})
if not isinstance(projects, dict):
    sys.exit(f"trust: {cfg} has a non-object projects key - refusing to overwrite it")
entry = projects.get(target)
if not isinstance(entry, dict):
    entry = {}
if entry.get("hasTrustDialogAccepted") is True:
    # Idempotent: nothing to write, so nothing to back up either.
    print(f"already trusted: projects[{target!r}].hasTrustDialogAccepted = true in {cfg}")
    sys.exit(0)

entry["hasTrustDialogAccepted"] = True
projects[target] = entry
tmp = Path(str(cfg) + ".vteam-tmp")        # write-then-rename: never a torn config
try:
    # About to write. Preserve the PRE-EXISTING config once - never overwrite an
    # earlier backup, or a second run would replace the users original with ours.
    if existed:
        bak = Path(str(cfg) + ".vteam-bak")
        if not bak.exists():
            shutil.copy2(cfg, bak)
            print(f"   backed up {cfg} -> {bak}")
    else:
        print(f"   {cfg} did not exist - creating it")
    tmp.write_text(json.dumps(data, indent=indent), encoding="utf-8")
    # KEEP THE ORIGINAL FILE MODE. os.replace installs a brand-new file, so
    # without this a 0600 config holding oauthAccount came back 0644 -
    # widening a credential file is not an acceptable side effect of a
    # convenience helper. A config we create ourselves starts private.
    os.chmod(tmp, (cfg.stat().st_mode & 0o7777) if existed else 0o600)
    os.replace(tmp, cfg)
except OSError as e:
    # read-only HOME, full disk, vanished parent - report it in this blocks own
    # voice and leave no half-written temp file behind
    try:
        tmp.unlink()
    except OSError:
        pass
    sys.exit(f"trust: could not write {cfg} ({e}) - nothing was changed")
print(f"trusted: set projects[{target!r}].hasTrustDialogAccepted = true in {cfg}")
print("   a worker dispatched into this worktree now gets its prompt, not a dialog")
' || exit 1
    exit 0 ;;
  *)
    echo "usage: orca_team.sh {status | open-run <objective> | wait <run_id> | trust <path>}"; exit 2 ;;
esac
