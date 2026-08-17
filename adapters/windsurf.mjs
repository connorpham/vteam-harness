// Windsurf — workflows directory with a description frontmatter; no subagents.
import path from "node:path";

export const id = "windsurf";
export const marker = ".windsurf/workflows/team.md";

export function render(wf, ctx) {
  return {
    path: path.join(".windsurf", "workflows", `${wf.name}.md`),
    text: `---\ndescription: ${wf.description.slice(0, 250)}\n---\n\n` + ctx.noSubagentNote + wf.body,
  };
}
