#!/usr/bin/env bash
# app_check.sh — env bring-up proof for the dev/qa lanes: is the app UP?
#
# Why this is a script and not workflow prose: qa.md V2b said "dev server up →
# health check returns 200/3xx" for months with no command behind it, so the
# check was performed by vibes. This names the command, and its output line is
# what the QA verify-sheet must quote (`APP: UP …`).
#
# Reads the `app:` section of vteam.config.yaml (schema: docs/DESIGN.md §2):
#   app.url    — where the running app answers (e.g. http://localhost:3000)
#   app.health — health endpoint: a path (/api/health) or a full URL; empty = probe app.url
#   app.start  — the command that runs the dev server (NAMED in the red output;
#                this gate never runs it — gates probe, they do not mutate)
#
#   bash app_check.sh [--wait <seconds>] [--url <override>]   # e.g. /qa's base= arg
#   bash app_check.sh --selftest
#
# Output contract (machine-quotable):
#   APP: UP <url> (HTTP <code>)      exit 0
#   APP: DOWN <target> after <n>s — start it with: <app.start>   exit 1
#   APP: SKIP — app.url not set …    exit 0 (a repo with no web app must not red)
set -u

probe() { # <target> <wait_s> → sets CODE; 0 = 2xx/3xx within budget
  local target="$1" budget="$2" waited=0
  while :; do
    CODE="$(curl -sS -o /dev/null -m 5 -w '%{http_code}' "$target" 2>/dev/null || echo 000)"
    case "$CODE" in 2??|3??) return 0 ;; esac
    [ "$waited" -ge "$budget" ] && return 1
    sleep 2; waited=$((waited + 2))
  done
}

run_check() { # <url> <health> <start> <wait_s> — the whole check, selftest-callable
  local url="$1" health="$2" start="$3" wait_s="$4" target
  if [ -z "$url" ]; then
    echo "APP: SKIP — app.url not set in vteam.config.yaml (set app.start/app.url to enable env bring-up)"
    return 0
  fi
  case "$health" in
    http://*|https://*) target="$health" ;;
    "")                 target="$url" ;;
    *)                  target="${url%/}/${health#/}" ;;
  esac
  if probe "$target" "$wait_s"; then
    echo "APP: UP $url (HTTP $CODE)"
    return 0
  fi
  echo "APP: DOWN $target after ${wait_s}s — start it with: ${start:-<set app.start in vteam.config.yaml>}"
  return 1
}

if [ "${1:-}" = "--selftest" ]; then
  command -v curl >/dev/null || { echo "app_check selftest: FAIL — curl not on PATH"; exit 1; }
  td="$(mktemp -d)"
  srv_pid=""
  trap '[ -n "$srv_pid" ] && kill "$srv_pid" 2>/dev/null; rm -rf "$td"' EXIT

  # green path 1: no app.url configured → SKIP, exit 0 (repos without a web app)
  out="$(run_check "" "" "" 0)" || { echo "app_check selftest: FAIL (unset url must exit 0)"; exit 1; }
  case "$out" in "APP: SKIP"*) ;; *) echo "app_check selftest: FAIL (expected SKIP, got: $out)"; exit 1 ;; esac

  # green path 2: a real server answers → UP (python prints the bound ephemeral port)
  # -u: unbuffered, or the "Serving HTTP on … port N" line sits in a block
  # buffer and the port never reaches srv.log while the server runs
  ( cd "$td" && exec python3 -u -m http.server 0 --bind 127.0.0.1 ) >"$td/srv.log" 2>&1 &
  srv_pid=$!
  port=""
  for _ in $(seq 1 50); do
    port="$(sed -n 's/.*port \([0-9]*\).*/\1/p' "$td/srv.log" | head -1)"
    [ -n "$port" ] && break
    sleep 0.1
  done
  [ -n "$port" ] || { echo "app_check selftest: FAIL (http.server never reported its port)"; exit 1; }
  out="$(run_check "http://127.0.0.1:$port" "" "npm run dev" 4)" \
    || { echo "app_check selftest: FAIL (live server should be UP): $out"; exit 1; }
  case "$out" in "APP: UP http://127.0.0.1:$port (HTTP 2"*) ;; *)
    echo "app_check selftest: FAIL (UP line malformed: $out)"; exit 1 ;; esac
  # …and a health PATH joins onto the url ('/' serves the dir listing → 200)
  out="$(run_check "http://127.0.0.1:$port" "/" "npm run dev" 0)" \
    || { echo "app_check selftest: FAIL (health path probe): $out"; exit 1; }
  kill "$srv_pid" 2>/dev/null; wait "$srv_pid" 2>/dev/null; srv_pid=""

  # red path: the port is now closed → DOWN, exit 1, unblock path names app.start
  if out="$(run_check "http://127.0.0.1:$port" "" "npm run dev" 0)"; then
    echo "app_check selftest: FAIL (closed port must red)"; exit 1
  fi
  case "$out" in *"start it with: npm run dev"*) ;; *)
    echo "app_check selftest: FAIL (DOWN line must name app.start: $out)"; exit 1 ;; esac

  # red path: a trailing flag with no value must refuse, not spin the arg loop
  # forever (shift 2 on one remaining arg fails silently under set -u alone)
  if out="$(bash "$0" --wait 2>&1)"; then
    echo "app_check selftest: FAIL (trailing --wait must exit 1)"; exit 1
  fi
  case "$out" in *"--wait needs a value"*) ;; *)
    echo "app_check selftest: FAIL (trailing --wait must say why: $out)"; exit 1 ;; esac

  echo "app_check selftest: OK (SKIP on unset url + UP on a live server + health path joined + DOWN red naming app.start + trailing flag refused)"
  exit 0
fi

. "$(cd "$(dirname "$0")" && pwd)/lib/ctx.sh"
cd "$(vteam_root)" || exit 1
command -v curl >/dev/null || { echo "APP: DOWN — curl not on PATH (install curl)"; exit 1; }

WAIT=0 URL_OVERRIDE=""
while [ $# -gt 0 ]; do
  case "$1" in
    --wait) [ $# -ge 2 ] || { echo "app_check: --wait needs a value"; exit 1; }
            WAIT="$2"; shift 2 ;;
    --url)  [ $# -ge 2 ] || { echo "app_check: --url needs a value"; exit 1; }
            URL_OVERRIDE="$2"; shift 2 ;;
    *) echo "usage: app_check.sh [--wait <seconds>] [--url <override>] | --selftest"; exit 1 ;;
  esac
done
case "$WAIT" in ''|*[!0-9]*)
  echo "app_check: --wait takes a whole number of seconds (got '$WAIT')"; exit 1 ;;
esac

URL="${URL_OVERRIDE:-$(vteam_cfg app.url "")}"
HEALTH="$(vteam_cfg app.health "")"
START="$(vteam_cfg app.start "")"
run_check "$URL" "$HEALTH" "$START" "$WAIT"
