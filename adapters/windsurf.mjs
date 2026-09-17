// Windsurf — workflows directory with a description frontmatter; no subagents.
import path from "node:path";

export const id = "windsurf";
export const marker = ".windsurf/workflows/team.md";
export const outputDirs = [".windsurf/workflows/"];


export function render(wf, ctx) {
  return {
    path: path.join(".windsurf", "workflows", `${wf.name}.md`),
    // quoted like the claude-code adapter: a plain scalar carrying `: ` is not YAML
    text: `---\ndescription: "${wf.description.slice(0, 250).replace(/"/g, "'")}"\n---\n\n` + ctx.noSubagentNote + wf.body,

  };
}
