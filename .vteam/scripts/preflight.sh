#!/usr/bin/env bash
# preflight.sh — is the ticket→design→code→git chain ready to run end-to-end?
# Every link is PINGED FOR REAL (provider ping methods), never just "var exists".
# Runs at /dev T0, /pm P0, /ba B0 — and by hand any time.
#
# --backend: a ticket with no UI → the design-source legs only WARN, never block.
# Exit 0 = all green; 1 with the misses + unblock steps. Never prints tokens.
set -u
. "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/lib/ctx.sh"
cd "$(vteam_root 2>/dev/null || pwd)"
# .env is parsed as INERT TEXT (ctx.sh), never sourced — a value carrying $(…)
# or backticks is data here, exactly as in ctx.py. Sourcing .env would hand
# code execution to anything that can write that file.
vteam_load_env .env

BACKEND=0
[ "${1:-}" = "--backend" ] && BACKEND=1

MISS=0
ok()   { printf "✅ %s\n" "$1"; }
miss() { printf "❌ %-14s %s\n" "$1" "$2"; MISS=1; }
design_miss() { # design leg: red for UI tickets, yellow for backend tickets
  if [ "$BACKEND" = "1" ]; then printf "⚠️  %-14s %s (backend ticket — not blocking)\n" "$1" "$2"
  else miss "$1" "$2"; fi
}

# 1. Tracker — provider ping (asserts real API JSON, not a 200 HTML lookalike)
TRK=$(python3 - <<'PY' 2>&1
import sys; sys.path.insert(0, ".vteam/scripts/lib")
from ctx import Ctx
import tracker as trk
ok, msg = trk.load(Ctx()).ping()
print(("OK " if ok else "NO ") + msg)
PY
)
case "$TRK" in
  OK*) ok "Tracker: ${TRK#OK }" ;;
  *)   miss "Tracker" "${TRK#NO }" ;;
esac

# 2. Design source — provider ping (the `none` provider always passes with a note)
DSG=$(python3 - <<'PY' 2>&1
import sys; sys.path.insert(0, ".vteam/scripts/lib")
from ctx import Ctx
import design as dsg
ok, msg = dsg.load(Ctx()).ping()
print(("OK " if ok else "NO ") + msg)
PY
)
case "$DSG" in
  OK*) ok "Design: ${DSG#OK }" ;;
  *)   design_miss "Design" "${DSG#NO }" ;;
esac

# 3. Git + hosting CLI — push code, open PRs
# The printed URL strips userinfo (user:token@) — remotes cloned with embedded
# PATs are common in CI, and this script promises to never print tokens.
git remote get-url origin >/dev/null 2>&1 \
  && ok "Git: remote origin $(git remote get-url origin | sed -E 's#(://)[^/@]+@#\1#')" \
  || miss "Git" "no origin remote"
HOOKS=$(git config core.hooksPath || true)
if [ "$(python3 .vteam/scripts/lib/ctx.py git.hooks 2>/dev/null || echo managed)" = "managed" ]; then
  [ "$HOOKS" = ".githooks" ] && ok "Hooks: core.hooksPath = .githooks" \
    || miss "Hooks" "run once per clone: git config core.hooksPath .githooks (silent hooks turn law into prose)"
fi
if command -v gh >/dev/null 2>&1; then
  gh auth status >/dev/null 2>&1 && ok "GitHub CLI: signed in (PRs possible)" \
    || miss "GitHub CLI" "run: gh auth login"
else
  printf "⚠️  %-14s %s\n" "Hosting CLI" "gh not installed — PRs must be opened another way"
fi

# 4. Database — only when the project declares a check (profiles may not need one)
if [ -x .vteam/db-check.sh ]; then
  if bash .vteam/db-check.sh >/dev/null 2>&1; then ok "Database: reachable (db-check.sh)"
  else miss "Database" "db-check.sh failed — bring the DB up (see your compose/service docs)"; fi
else
  printf "⚠️  %-14s %s\n" "Database" "no .vteam/db-check.sh declared — DB leg unchecked (declare one if the app needs a DB)"
fi

# 5. Test infra — the gate must have steps to run
if python3 .vteam/scripts/gate.py --help >/dev/null 2>&1 || [ -f .vteam/scripts/gate.py ]; then
  ok "Gate: driver installed ($(python3 .vteam/scripts/lib/ctx.py stack.profile 2>/dev/null || echo '?') profile)"
else
  miss "Gate" "gate driver missing — broken install, re-run npx vteam init"
fi

echo "──────────────────────────────────────────"
if [ "$MISS" = "0" ]; then
  echo "PREFLIGHT: GREEN — the ticket→design→code→git chain runs end-to-end"
else
  echo "PREFLIGHT: RED — clear the ❌ items above, then re-run"
  exit 1
fi
