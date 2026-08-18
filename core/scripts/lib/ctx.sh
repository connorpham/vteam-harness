#!/usr/bin/env bash
# ctx.sh — the shell leg of the vteam context layer (mirrors lib/ctx.py semantics).
#
# Source it from bash gates:   . "$(dirname "$0")/lib/ctx.sh"
# Provides:
#   vteam_root                 → repo root via `git rev-parse` (exit 1 outside git)
#   vteam_cfg KEY [DEFAULT]    → config value for `key` or `section.key`
#   vteam_load_env             → export .env KEY=VALUE pairs — INERT text parsing,
#                                never `source`d, so values can never execute
#                                (same discipline as ctx.py; os env wins, like
#                                ctx.py's setdefault)
#
# vteam_cfg limitations (documented, not hidden): it is a grep/awk lookup over
# the vteam YAML subset — top-level scalars and two-level `section:` → `  key:`
# scalars only. Comments after values are stripped; surrounding quotes are
# stripped; lists/anchors/multiline are OUTSIDE this helper — a shell gate that
# needs those must call `python3 .vteam/scripts/lib/ctx.py <key>` instead.
# When the key is absent (or no config file exists) the DEFAULT is printed;
# with no DEFAULT the function returns 1 and prints nothing.
#
# Selftest: bash ctx.sh --selftest   (green lookups + a .env fixture carrying a
# command substitution that MUST NOT execute + missing-key red)

vteam_root() {
  git rev-parse --show-toplevel 2>/dev/null || {
    echo "ctx.sh: not inside a git repository (git rev-parse failed)" >&2
    return 1
  }
}

# vteam_cfg <key|section.key> [default]
vteam_cfg() {
  local key="$1" def="${2-}" file val
  file="$(vteam_root 2>/dev/null)/vteam.config.yaml"
  if [ -f "$file" ]; then
    case "$key" in
      *.*)
        local sec="${key%%.*}" leaf="${key#*.}"
        val=$(awk -v sec="$sec" -v leaf="$leaf" '
          /^[A-Za-z_][A-Za-z0-9_-]*:/ { insec = ($0 ~ "^" sec ":") }
          insec && $0 ~ "^  " leaf ":" {
            line = $0
            sub("^  " leaf ":[ ]*", "", line)   # drop "  key: "
            print line; exit
          }' "$file")
        ;;
      *)
        val=$(awk -v k="$key" '
          $0 ~ "^" k ":" { line = $0; sub("^" k ":[ ]*", "", line); print line; exit }
          ' "$file")
        ;;
    esac
    # strip trailing comment, then surrounding quotes — mirrors ctx.py
    val="${val%%[[:space:]]#*}"
    val="${val%"${val##*[![:space:]]}"}"
    case "$val" in
      \"*\") val="${val#\"}"; val="${val%\"}" ;;
      \'*\') val="${val#\'}"; val="${val%\'}" ;;
    esac
    if [ -n "$val" ]; then printf '%s\n' "$val"; return 0; fi
  fi
  if [ $# -ge 2 ]; then printf '%s\n' "$def"; return 0; fi
  return 1
}

# vteam_load_env [file] — parse KEY=VALUE lines as INERT TEXT and export them.
# Never sources the file: `$(…)`, backticks and `;` in values stay literal data.
# Pre-existing environment variables win (ctx.py setdefault semantics).
vteam_load_env() {
  local file="${1:-.env}" line k v
  [ -f "$file" ] || return 0
  while IFS= read -r line || [ -n "$line" ]; do
    case "$line" in ''|\#*) continue ;; esac
    case "$line" in *=*) ;; *) continue ;; esac
    k="${line%%=*}"
    v="${line#*=}"
    # keys must look like env identifiers — anything else is skipped, not eval'd
    case "$k" in
      [A-Za-z_]*) case "$k" in *[!A-Za-z0-9_]*) continue ;; esac ;;
      *) continue ;;
    esac
    # strip surrounding quotes like ctx.py
    case "$v" in
      \"*\") v="${v#\"}"; v="${v%\"}" ;;
      \'*\') v="${v#\'}"; v="${v%\'}" ;;
    esac
    if [ -z "${!k+x}" ]; then
      export "$k=$v"
    fi
  done < "$file"
}

# ── selftest (only when executed directly, never when sourced) ────────────────
if [ "${BASH_SOURCE[0]:-}" = "$0" ] && [ "${1:-}" = "--selftest" ]; then
  set -u
  tmp=$(mktemp -d)
  trap 'rm -rf "$tmp"' EXIT
  fail() { echo "ctx.sh selftest: FAIL — $1" >&2; exit 1; }

  ( cd "$tmp" && git init -q . )
  cat > "$tmp/vteam.config.yaml" <<'EOF'
version: 1
project:
  name: "Quoted Name"
  key: TST            # trailing comment must be stripped
paths:
  pm: docs/pm
stack:
  profile: generic
EOF
  # green lookups
  ( cd "$tmp"
    [ "$(vteam_cfg project.key)" = "TST" ]        || fail "project.key lookup"
    [ "$(vteam_cfg project.name)" = "Quoted Name" ] || fail "quote stripping"
    [ "$(vteam_cfg paths.pm)" = "docs/pm" ]        || fail "paths.pm lookup"
    [ "$(vteam_cfg version)" = "1" ]               || fail "top-level lookup"
    [ "$(vteam_cfg paths.qa docs/qa)" = "docs/qa" ] || fail "default fallback"
    # mutation: a missing key with no default must RED (return 1, print nothing)
    if vteam_cfg no.such.key >/dev/null; then fail "missing key should return 1"; fi
  ) || exit 1

  # .env inertness: a value carrying $(…) must arrive as LITERAL TEXT.
  # The canary file must not exist after the load — if it does, the value ran.
  canary="$tmp/CANARY"
  printf 'VT_SAFE=hello\nVT_EVIL=$(touch %s)\nVT_QUOTED="a b"\nVT_PRESET=fromfile\n9BAD=x\n' \
    "$canary" > "$tmp/.env"
  ( cd "$tmp"
    export VT_PRESET=fromenv
    vteam_load_env .env
    [ ! -e "$canary" ]               || fail ".env value EXECUTED — parsing is not inert"
    [ "${VT_SAFE:-}" = "hello" ]     || fail "plain value not exported"
    [ "${VT_QUOTED:-}" = "a b" ]     || fail "quoted value not stripped"
    [ "${VT_PRESET:-}" = "fromenv" ] || fail "os environment should win over .env (setdefault)"
    case "${VT_EVIL:-}" in '$(touch'*) ;; *) fail "metachar value not literal: ${VT_EVIL:-unset}" ;; esac
    printenv 9BAD >/dev/null && fail "invalid key exported instead of skipped"
    true
  ) || exit 1

  echo "ctx.sh selftest: OK (config lookups green + missing-key red + inert .env: \$() stayed literal, canary untouched, env wins)"
  exit 0
fi
