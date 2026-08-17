// Cursor — commands directory; no native subagent spawning.
import path from "node:path";

export const id = "cursor";
export const marker = ".cursor/commands/team.md";

export function render(wf, ctx) {
  return {
    path: path.join(".cursor", "commands", `${wf.name}.md`),
    text: ctx.noSubagentNote + wf.body,
  };
}
