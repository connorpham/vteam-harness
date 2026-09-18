#!/usr/bin/env bash
# vteam SessionEnd hook — when a session ends with a ticket in flight (dirty tree or
# commits ahead of the base branch on a feat|fix/<KEY>-… branch), record the stop
# state to {paths.evidence}/<KEY>/dev/STOP-STATE.md so the next reader does not
# reconstruct it from git. Never fails the session. Installed at .claude/hooks/ by
# the claude-code adapter; the script itself ships in .vteam/scripts/.
cd "${CLAUDE_PROJECT_DIR:-.}" 2>/dev/null || exit 0
[ -f .vteam/scripts/stop_state.sh ] && bash .vteam/scripts/stop_state.sh 2>/dev/null
exit 0
