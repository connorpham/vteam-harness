// Claude Code — native skills with subagent spawning (the reference adapter).
import path from "node:path";

export const id = "claude-code";
export const marker = ".claude/skills/team/SKILL.md";

export function render(wf, ctx) {
  const hint = wf.args ? `argument-hint: "${wf.args.replace(/"/g, "'")}"\n` : "";
  return {
    path: path.join(".claude", "skills", wf.name, "SKILL.md"),
    text: `---\nname: ${wf.name}\ndescription: "${wf.description.replace(/"/g, "'")}"\n${hint}---\n\n${wf.body}`,
  };
}
