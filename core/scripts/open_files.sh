#!/usr/bin/env bash
# open_files.sh — open the files being worked on in the owner's editor, so a
# /dev session is watchable like a real developer's screen.
#
# Why a script and not workflow prose: "open it in the editor" written as prose
# gets improvised per session (wrong CLI, silently skipped, blocking errors).
# This is one deterministic helper: detect the CLI, open at the line, NEVER
# block the pipeline — a missing editor is one honest line and exit 0.
#
# Config: app.open_files (vteam.config.yaml, schema docs/DESIGN.md §2)
#   auto   — prefer `cursor -g`, else `code -g` (VS Code), else skip loudly
#   code   — only the `code` CLI          cursor — only the `cursor` CLI
#   none   — never open anything (unattended 24/7 shifts)
#
#   bash open_files.sh [--dry-run] <file[:line]> [<file[:line]> …]
#   bash open_files.sh --selftest
set -u

pick_editor() { # <mode> → prints the CLI to use, or nothing (skip)
  case "$1" in
    none)   return 0 ;;
    # a forced mode whose CLI is absent prints nothing (→ the one-line skip),
    # it never propagates a nonzero status — opening files must not block work
    code)   if command -v code   >/dev/null; then echo code;   fi ;;
    cursor) if command -v cursor >/dev/null; then echo cursor; fi ;;
    auto|"")
      if   command -v cursor >/dev/null; then echo cursor
      elif command -v code   >/dev/null; then echo code
      fi ;;
    *) echo "open_files: unknown app.open_files value '$1' (auto|code|cursor|none)" >&2; return 1 ;;
  esac
}

open_all() { # <mode> <dry> <file…> — the whole behavior, selftest-callable
  local mode="$1" dry="$2"; shift 2
  local cli
  cli="$(pick_editor "$mode")" || return 1
  if [ "$mode" = "none" ]; then
    echo "open_files: SKIP (app.open_files: none)"
    return 0
  fi
  if [ -z "$cli" ]; then
    echo "open_files: no editor CLI on PATH for '$mode' (cursor/code) — files not opened, pipeline continues"
    return 0
  fi
  local f
  for f in "$@"; do
    if [ "$dry" = "1" ]; then
      echo "WOULD RUN: $cli -g $f"
    else
      "$cli" -g "$f" >/dev/null 2>&1 \
        || echo "open_files: '$cli -g $f' failed — continuing (opening files never blocks work)"
    fi
  done
  return 0
}

if [ "${1:-}" = "--selftest" ]; then
  td="$(mktemp -d)"; trap 'rm -rf "$td"' EXIT
  fail() { echo "open_files selftest: FAIL — $1"; exit 1; }
  mkdir "$td/bin"
  printf '#!/bin/sh\necho "cursor $*" >> "%s/calls"\n' "$td" > "$td/bin/cursor"
  printf '#!/bin/sh\necho "code $*" >> "%s/calls"\n'   "$td" > "$td/bin/code"
  chmod +x "$td/bin/cursor" "$td/bin/code"

  # auto prefers cursor when both exist, and passes -g file:line through
  ( PATH="$td/bin:$PATH" open_all auto 0 src/a.ts:12 ) || fail "auto with both CLIs errored"
  grep -q "^cursor -g src/a.ts:12$" "$td/calls" || fail "auto did not run cursor -g file:line: $(cat "$td/calls")"
  # auto falls back to code when cursor is gone
  rm "$td/bin/cursor" "$td/calls"
  ( PATH="$td/bin:$PATH" open_all auto 0 src/a.ts:12 ) || fail "auto with code-only errored"
  grep -q "^code -g src/a.ts:12$" "$td/calls" || fail "auto did not fall back to code: $(cat "$td/calls")"
  # forced mode uses exactly that CLI; dry-run prints instead of running
  out="$(PATH="$td/bin:$PATH" open_all code 1 lib/b.py)" || fail "dry-run errored"
  [ "$out" = "WOULD RUN: code -g lib/b.py" ] || fail "dry-run line wrong: $out"
  # none → SKIP line, nothing invoked
  rm -f "$td/calls"
  out="$(PATH="$td/bin:$PATH" open_all none 0 src/a.ts)" || fail "mode none errored"
  case "$out" in *"SKIP"*) ;; *) fail "mode none must say SKIP: $out" ;; esac
  [ ! -e "$td/calls" ] || fail "mode none still invoked an editor"
  # no CLI at all → one honest line, exit 0 (never blocks the pipeline)
  out="$(PATH="$td/bin-empty" open_all auto 0 src/a.ts)" || fail "missing CLIs must exit 0"
  case "$out" in *"no editor CLI on PATH"*) ;; *) fail "missing-CLI line wrong: $out" ;; esac
  # …and a FORCED mode whose CLI is absent also skips with exit 0 (the hole:
  # `cmd && echo` propagates status 1 out of the case arm)
  out="$(PATH="$td/bin-empty" open_all cursor 0 src/a.ts)" || fail "forced mode with missing CLI must exit 0"
  case "$out" in *"no editor CLI on PATH"*) ;; *) fail "forced-missing line wrong: $out" ;; esac
  # mutation: an unknown mode is refused loudly
  if out="$(open_all typo 0 src/a.ts 2>&1)"; then fail "unknown mode must exit 1"; fi
  case "$out" in *"unknown app.open_files"*) ;; *) fail "unknown-mode message wrong: $out" ;; esac

  echo "open_files selftest: OK (auto→cursor + fallback→code + forced/dry-run + none skip + no-CLI exit 0 + unknown mode red)"
  exit 0
fi

. "$(cd "$(dirname "$0")" && pwd)/lib/ctx.sh"
cd "$(vteam_root)" || exit 1

DRY=0
if [ "${1:-}" = "--dry-run" ]; then DRY=1; shift; fi
if [ $# -eq 0 ]; then
  echo "usage: open_files.sh [--dry-run] <file[:line]> [<file[:line]> …] | --selftest"
  exit 1
fi
MODE="$(vteam_cfg app.open_files auto)"
[ -n "$MODE" ] || MODE=auto
open_all "$MODE" "$DRY" "$@"
