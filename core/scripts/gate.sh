#!/usr/bin/env bash
# gate.sh — the one entrypoint. The full transcript is ALSO written to a file:
# field finding E10 — a gate piped through grep/tail and then moved to the
# background blocks forever once a step writes more than a pipe buffer, because
# nothing drains the pipe. A file always drains, and a RED can be re-read after
# the terminal scrolled away. Override the path with VTEAM_GATE_LOG.
set -uo pipefail
cd "$(git rev-parse --show-toplevel)"
LOG="${VTEAM_GATE_LOG:-${TMPDIR:-/tmp}/vteam-gate-$(basename "$PWD").log}"
mkdir -p "$(dirname "$LOG")" 2>/dev/null
python3 .vteam/scripts/gate.py "$@" 2>&1 | tee "$LOG"
rc=${PIPESTATUS[0]}
echo "📝 transcript: $LOG"
exit "$rc"
