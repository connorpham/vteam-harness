#!/usr/bin/env bash
# gate.sh — muscle-memory wrapper for the verification gate driver.
# Usage: bash .vteam/scripts/gate.sh [e2e]
set -uo pipefail
cd "$(git rev-parse --show-toplevel)"
exec python3 .vteam/scripts/gate.py "$@"
