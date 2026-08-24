#!/usr/bin/env bash
# vteam SessionStart hook (startup|clear|compact) — a SessionStart hook's stdout
# is added to the agent's context, so the non-negotiables survive /clear and
# compaction. Installed at .claude/hooks/ by the claude-code adapter. ≤15 lines.
cd "${CLAUDE_PROJECT_DIR:-.}" 2>/dev/null || true
PM=docs/pm; EVD=evd; TEAM=docs/team
if [ -f .vteam/scripts/lib/ctx.sh ]; then
  . .vteam/scripts/lib/ctx.sh
  # vteam_cfg exits 1 on flow-style sections it can't read; this hook only
  # echoes doctrine, so fall back to the defaults EXPLICITLY rather than dying.
  PM=$(vteam_cfg paths.pm docs/pm 2>/dev/null) || PM=docs/pm
  EVD=$(vteam_cfg paths.evidence evd 2>/dev/null) || EVD=evd
  TEAM=$(vteam_cfg paths.team docs/team 2>/dev/null) || TEAM=docs/team
fi
echo "vteam session bootstrap — proof-of-done non-negotiables:"
echo "- GATES BEFORE DONE: nothing is 'done' until \`bash .vteam/scripts/gate.sh\` exits 0."
echo "- EVIDENCE TO FILES: claims carry command + real output in $EVD/<ticket>/, pinned to a commit."
echo "- DECISION QUEUE: human calls go to $PM/decisions.md — asked, never assumed."
echo "- Doctrine: $TEAM/ · config: vteam.config.yaml · workflows: /team /pm /ba /dev /qa /verify."
