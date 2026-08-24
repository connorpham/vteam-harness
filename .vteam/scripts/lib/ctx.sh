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
# stripped. Flow mappings `{a: b}` are OUTSIDE this subset and are REFUSED
# loudly (stderr + return 1) — never misread into a wrong scalar or a silent
# default; single-line `[a, b]` lists are returned as the RAW bracket text;
# anchors/multiline are outside too — a shell gate that needs any of those
# must call `python3 .vteam/scripts/lib/ctx.py <key>` instead.
# A key that is PRESENT but EMPTY returns the empty value (exit 0) — the
# DEFAULT applies only when the key is ABSENT (or no config file exists);
# absent with no DEFAULT returns 1 and prints nothing.
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
# awk exit codes: 0 = key found (value printed, possibly empty) · 1 = key
# absent · 2 = the section itself is a flow mapping `{…}` (unreadable here).
vteam_cfg() {
  local key="$1" def="${2-}" file val rc
  file="$(vteam_root 2>/dev/null)/vteam.config.yaml"
  if [ -f "$file" ]; then
    case "$key" in
      *.*)
        local sec="${key%%.*}" leaf="${key#*.}"
        val=$(awk -v sec="$sec" -v leaf="$leaf" '
          /^[A-Za-z_][A-Za-z0-9_-]*:/ {
            insec = ($0 ~ "^" sec ":")
            if (insec) {                        # flow-style section: the leaf IS
              line = $0                         # configured but unreadable here —
              sub("^" sec ":[ ]*", "", line)    # refuse, never default silently
              sub(/[ \t]*#.*$/, "", line)
              if (line ~ /^\{/) { flow = 1; exit }
            }
          }
          insec && $0 ~ "^  " leaf ":" {
            line = $0
            sub("^  " leaf ":[ ]*", "", line)   # drop "  key: "
            print line; found = 1; exit
          }
          END { if (found) exit 0; if (flow) exit 2; exit 1 }' "$file")
        rc=$?
        ;;
      *)
        val=$(awk -v k="$key" '
          $0 ~ "^" k ":" { line = $0; sub("^" k ":[ ]*", "", line); print line; found = 1; exit }
          END { exit found ? 0 : 1 }' "$file")
        rc=$?
        ;;
    esac
    if [ "$rc" -eq 2 ]; then
      echo "ctx.sh: section '${key%%.*}' is a flow mapping — vteam_cfg cannot read '$key'; use \`python3 .vteam/scripts/lib/ctx.py $key\`" >&2
      return 1
    fi
    if [ "$rc" -eq 0 ]; then
      # strip trailing comment + trailing whitespace — mirrors ctx.py
      val="${val%%[[:space:]]#*}"
      val="${val%"${val##*[![:space:]]}"}"
      case "$val" in
        \{*)   # flow mapping value: outside the subset — never a wrong scalar
          echo "ctx.sh: config key '$key' is a flow mapping — outside vteam_cfg's scalar subset; use \`python3 .vteam/scripts/lib/ctx.py $key\`" >&2
          return 1 ;;
        \[*\]) # single-line inline list: returned as RAW bracket text (documented)
          printf '%s\n' "$val"; return 0 ;;
        \[*)   # opening bracket without a close on the same line
          echo "ctx.sh: config key '$key' is an unterminated inline list — outside vteam_cfg's scalar subset; use \`python3 .vteam/scripts/lib/ctx.py $key\`" >&2
          return 1 ;;
      esac
      case "$val" in
        \"*\") val="${val#\"}"; val="${val%\"}" ;;
        \'*\') val="${val#\'}"; val="${val%\'}" ;;
      esac
      printf '%s\n' "$val"; return 0   # present-but-empty prints "" — NOT the default
    fi
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
  motto: ''
paths:
  pm: docs/pm
stack:
  profile: generic
flowsec: { a: b }
git:
  code_paths: [src/, prisma/]
docs:
  by_label: { x: [a.md] }
EOF
  # green lookups
  ( cd "$tmp"
    [ "$(vteam_cfg project.key)" = "TST" ]        || fail "project.key lookup"
    [ "$(vteam_cfg project.name)" = "Quoted Name" ] || fail "quote stripping"
    [ "$(vteam_cfg paths.pm)" = "docs/pm" ]        || fail "paths.pm lookup"
    [ "$(vteam_cfg version)" = "1" ]               || fail "top-level lookup"
    [ "$(vteam_cfg paths.qa docs/qa)" = "docs/qa" ] || fail "default fallback"
    # present-but-EMPTY value: return the empty value, NOT the default (M14)
    [ "$(vteam_cfg project.motto FALLBACK)" = "" ] || fail "empty value must not fall through to default"
    vteam_cfg project.motto >/dev/null             || fail "empty value must still be exit 0 (found)"
    # single-line inline list: returned as RAW bracket text (documented)
    [ "$(vteam_cfg git.code_paths)" = "[src/, prisma/]" ] || fail "inline list raw passthrough"
    # mutation: a missing key with no default must RED (return 1, print nothing)
    if vteam_cfg no.such.key >/dev/null; then fail "missing key should return 1"; fi
    # mutation: a flow-mapping SECTION must be refused loudly, never defaulted
    if vteam_cfg flowsec.a fallback >/dev/null 2>"$tmp/err1"; then fail "flow section should return 1"; fi
    grep -q "flow mapping" "$tmp/err1"             || fail "flow section refusal must explain itself on stderr"
    # mutation: a flow-mapping VALUE must be refused loudly, never a wrong scalar
    if vteam_cfg docs.by_label >/dev/null 2>"$tmp/err2"; then fail "flow value should return 1"; fi
    grep -q "flow mapping" "$tmp/err2"             || fail "flow value refusal must explain itself on stderr"
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

  echo "ctx.sh selftest: OK (config lookups green + empty-value kept + list raw + flow-map refused loudly + missing-key red + inert .env: \$() stayed literal, canary untouched, env wins)"
  exit 0
fi
