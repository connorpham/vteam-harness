#!/usr/bin/env bash
# lane_env.sh — one worktree, one port, one database, one scratch directory.
#
# Why: in the first parallel benchmark run (field finding E13, 2026-09-04) the DEV
# lane and three review agents shared ONE SQLite file, ONE dev server and ONE
# scratch directory. Their fixture-restoring hooks raced; all three reviewers
# reported failures that did not reproduce (3, 2 and 14), one reviewer's eslint
# reddened on another's scratch file, and a fabricated CONFIRMED was one tired
# reviewer away. Worktrees share vteam.config.yaml, so `app.url` alone cannot
# separate them. This helper DERIVES a lane's environment from the worktree it
# runs in, and every lane sources it before starting a server, a test suite or
# a review:
#
#   eval "$(bash .vteam/scripts/lane_env.sh)"              # the DEV lane of this worktree
#   eval "$(bash .vteam/scripts/lane_env.sh --lane R1)"    # a reviewer: same tree, own env
#   bash .vteam/scripts/lane_env.sh --print                # look, do not export
#   bash .vteam/scripts/lane_env.sh --selftest
#
# Exports: PORT, APP_URL (app_check.sh honours it), DATABASE_URL (sqlite
# datasources only — an absolute `file:` URL under the scratch dir; other
# providers get a hint, not a guess), VTEAM_SCRATCH, VTEAM_LANE.
#
# Port = 3100 + fnv1a(realpath of the worktree [+ "#lane"]) % 800 — the SAME scheme
# `vteam init` uses for `app.url`, so a plain checkout's DEV lane lands on the port
# init already wrote, and every other worktree/lane lands on its own.
#
# It also writes a MARKER, <scratch>/lane.env, keyed by the same hash; parallel_check
# reads the markers to prove two in-flight worktrees are not on one port/database.
# Override the scratch root with VTEAM_LANES_ROOT (default $TMPDIR/vteam-lanes).
set -uo pipefail

lanes_root() {
  if [ -n "${VTEAM_LANES_ROOT:-}" ]; then printf '%s' "${VTEAM_LANES_ROOT%/}"; else printf '%s/vteam-lanes' "${TMPDIR:-/tmp}"; fi | sed 's#//*#/#g'
}
root_dir() {
  local r; r="$(git rev-parse --show-toplevel 2>/dev/null)" || return 1
  (cd "$r" && pwd -P)
}
# fnv1a-32 over the UTF-8 bytes, identical to src/cli/init.mjs derivePort()
derive() { # <realpath> <lane> → "<port> <hash8>"
  python3 - "$1" "$2" <<'PY'
import sys
path, lane = sys.argv[1], sys.argv[2]
key = path if lane == "main" else f"{path}#{lane}"
h = 0x811c9dc5
for b in key.encode("utf-8"):
    h ^= b
    h = (h * 0x01000193) & 0xFFFFFFFF
print(3100 + (h % 800), f"{h:08x}")
PY
}
sqlite_datasource() { # 0 only when prisma/schema.prisma declares sqlite
  local schema="$1/prisma/schema.prisma"
  [ -f "$schema" ] && grep -Eq 'provider[[:space:]]*=[[:space:]]*"sqlite"' "$schema"
}

# 3100..3899 is 800 buckets, so two lanes WILL hash to one port eventually — with a
# handful of lanes it is a coin flip, and CI found it the day after the helper shipped
# ("reviewer lane R1 derived the author's port 3724"). A collision here is precisely
# the failure this helper exists to prevent, so the derived port is a STARTING POINT:
# step forward until no other lane's marker claims it. Still deterministic for a given
# set of lanes, and the marker records where the lane actually landed.
claimed_by_others() { # <slug> → ports claimed in markers that are not this lane's
  local mine="$1" f
  for f in "$(lanes_root)"/*/lane.env; do
    [ -f "$f" ] || continue
    case "$f" in */"$mine"/lane.env) continue ;; esac
    sed -n 's/^PORT=//p' "$f"
  done
}
free_port() { # <start> <slug> → the first port from <start> no other lane claims
  local port="$1" slug="$2" taken tries=0
  taken="$(claimed_by_others "$slug" | tr '\n' ' ')"
  while [ "$tries" -lt 800 ]; do
    case " $taken " in *" $port "*) ;; *) printf '%s' "$port"; return 0 ;; esac
    port=$(( port + 1 )); [ "$port" -ge 3900 ] && port=3100
    tries=$(( tries + 1 ))
  done
  printf '%s' "$1"   # 800 lanes on one machine: give the derived port back, loudly
}

emit() { # <root> <lane> → the export lines on stdout, and the marker on disk
  local root="$1" lane="$2" port hash slug scratch app db_line derived
  read -r derived hash < <(derive "$root" "$lane")
  slug="$(basename "$root")-${hash}"; [ "$lane" != "main" ] && slug="${slug}-${lane}"
  port="$(free_port "$derived" "$slug")"
  scratch="$(lanes_root)/$slug"
  mkdir -p "$scratch" || { echo "lane_env: cannot create $scratch" >&2; return 1; }
  app="http://127.0.0.1:$port"
  if sqlite_datasource "$root"; then
    db_line="export DATABASE_URL=\"file:$scratch/dev.db\""
  else
    db_line="# DATABASE_URL: no sqlite datasource in prisma/schema.prisma — give this lane its OWN database (name it $slug); not derived here"
  fi
  {
    echo "export PORT=$port"
    echo "export APP_URL=\"$app\""
    echo "$db_line"
    echo "export VTEAM_SCRATCH=\"$scratch\""
    echo "export VTEAM_LANE=\"$lane\""
    echo "# lane '$lane' of $root → port $port · scratch $scratch (E13: one worktree, one port, one database, one scratch dir)"
    if [ "$port" != "$derived" ]; then
      echo "# port $derived was already claimed by another lane; stepped to $port (800 buckets collide)"
    fi
  }
  {
    echo "WORKTREE=$root"
    echo "LANE=$lane"
    echo "PORT=$port"
    echo "APP_URL=$app"
    case "$db_line" in export*) echo "DATABASE_URL=file:$scratch/dev.db" ;; *) echo "DATABASE_URL=" ;; esac
    echo "VTEAM_SCRATCH=$scratch"
    echo "RECORDED=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  } > "$scratch/lane.env"
}

if [ "${1:-}" = "--selftest" ]; then
  SELF="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/$(basename "${BASH_SOURCE[0]}")"
  fail() { echo "lane_env selftest: FAIL — $1" >&2; exit 1; }
  command -v python3 >/dev/null || fail "python3 not on PATH"
  td="$(mktemp -d)"; trap 'rm -rf "$td"' EXIT
  export VTEAM_LANES_ROOT="$td/lanes"
  mk() { mkdir -p "$1/prisma" && git -C "$1" init -q && printf 'datasource db {\n  provider = "sqlite"\n  url = env("DATABASE_URL")\n}\n' > "$1/prisma/schema.prisma"; }
  mk "$td/a"; mk "$td/b"
  a1="$(cd "$td/a" && bash "$SELF")" || fail "repo a: helper exited non-zero"
  a2="$(cd "$td/a" && bash "$SELF")" || fail "repo a: second run exited non-zero"
  b1="$(cd "$td/b" && bash "$SELF")" || fail "repo b: helper exited non-zero"
  [ "$a1" = "$a2" ] || fail "the same worktree must derive the same environment twice"
  pa="$(printf '%s\n' "$a1" | sed -n 's/^export PORT=//p')"; pb="$(printf '%s\n' "$b1" | sed -n 's/^export PORT=//p')"
  [ -n "$pa" ] && [ -n "$pb" ] || fail "PORT missing from the output: $a1"
  [ "$pa" != "$pb" ] || fail "two worktrees derived the SAME port $pa — that is E13"
  [ "$pa" -ge 3100 ] && [ "$pa" -lt 3900 ] || fail "port $pa outside 3100..3899"
  da="$(printf '%s\n' "$a1" | sed -n 's/^export DATABASE_URL=//p')"; db="$(printf '%s\n' "$b1" | sed -n 's/^export DATABASE_URL=//p')"
  [ -n "$da" ] && [ "$da" != "$db" ] || fail "two worktrees must get two databases: $da vs $db"
  case "$da" in '"file:/'*) ;; *) fail "DATABASE_URL must be an absolute sqlite file URL: $da" ;; esac
  # a reviewer lane in the SAME worktree gets its own port and database
  r1="$(cd "$td/a" && bash "$SELF" --lane R1)" || fail "--lane R1 exited non-zero"
  pr="$(printf '%s\n' "$r1" | sed -n 's/^export PORT=//p')"
  [ "$pr" != "$pa" ] || fail "reviewer lane R1 derived the author's port $pa"
  printf '%s\n' "$r1" | grep -q 'export VTEAM_LANE="R1"' || fail "VTEAM_LANE must name the lane: $r1"
  # the marker parallel_check reads: keyed by the same hash, carries the port
  m="$(ls "$td"/lanes/a-*/lane.env 2>/dev/null | grep -v -- '-R1/' | head -1)"
  [ -n "$m" ] || fail "marker lane.env not written under $VTEAM_LANES_ROOT"
  grep -q "^PORT=$pa$" "$m" || fail "marker must record the port: $(cat "$m")"
  grep -q "^WORKTREE=$(cd "$td/a" && pwd -P)$" "$m" || fail "marker must record the worktree realpath"
  # the same scheme as init: derivePort(root) for lane main equals ours
  INIT="$(cd "$(dirname "$0")/../.." 2>/dev/null && pwd)/src/cli/init.mjs"
  if [ -f "$INIT" ]; then
    want="$(cd "$td/a" && node -e "import(process.argv[1]).then(m => console.log(m.derivePort(process.cwd())))" "$INIT" 2>/dev/null)"
    [ -z "$want" ] || [ "$want" = "$pa" ] || fail "init's derivePort says $want, lane_env says $pa — the two schemes drifted"
  fi
  # no sqlite datasource → a hint, never a guessed DATABASE_URL
  rm "$td/b/prisma/schema.prisma"; b2="$(cd "$td/b" && bash "$SELF")" || fail "repo b without schema exited non-zero"
  printf '%s\n' "$b2" | grep -q '^export DATABASE_URL=' && fail "a non-sqlite repo must not get a derived DATABASE_URL"
  printf '%s\n' "$b2" | grep -q '^# DATABASE_URL: no sqlite datasource' || fail "the non-sqlite hint is missing: $b2"
  # a FORCED collision must be stepped over, not shared: plant a marker on the port a
  # third lane is about to derive, and it has to land somewhere else
  r2_derived="$(cd "$td/a" && bash "$SELF" --lane R2 | sed -n 's/^export PORT=//p')"
  rm -rf "$td/lanes"/*-R2
  mkdir -p "$td/lanes/squatter"
  printf 'WORKTREE=%s\nLANE=squatter\nPORT=%s\n' "$td/z" "$r2_derived" > "$td/lanes/squatter/lane.env"
  r2="$(cd "$td/a" && bash "$SELF" --lane R2)" || fail "--lane R2 exited non-zero after a planted collision"
  pr2="$(printf '%s\n' "$r2" | sed -n 's/^export PORT=//p')"
  [ "$pr2" != "$r2_derived" ] || fail "a port another lane already claims must be stepped over, got $pr2"
  [ "$pr2" -ge 3100 ] && [ "$pr2" -lt 3900 ] || fail "stepped port $pr2 outside 3100..3899"
  printf '%s\n' "$r2" | grep -q "already claimed by another lane" || fail "the step must be said out loud"
  rm -rf "$td/lanes/squatter"
  rm -rf "$td/lanes"/*-R2
  echo "lane_env selftest: OK (stable per worktree + distinct ports/dbs across worktrees and lanes + marker written + parity with init.derivePort + non-sqlite hint + a planted collision stepped over and said out loud)"
  exit 0
fi

LANE="${VTEAM_LANE:-main}"
while [ $# -gt 0 ]; do
  case "$1" in
    --lane) [ $# -ge 2 ] || { echo "lane_env: --lane needs a name" >&2; exit 1; }; LANE="$2"; shift 2 ;;
    --print) shift ;;
    *) echo "usage: eval \"\$(bash .vteam/scripts/lane_env.sh [--lane <name>])\" | --print | --selftest" >&2; exit 1 ;;
  esac
done
case "$LANE" in *[!A-Za-z0-9_-]*|"") echo "lane_env: lane name must be [A-Za-z0-9_-]+ (got '$LANE')" >&2; exit 1 ;; esac
ROOT="$(root_dir)" || { echo "lane_env: not inside a git repository" >&2; exit 1; }
emit "$ROOT" "$LANE"
