// GitHub Copilot — prompt files + a copilot-instructions pointer; no subagents.
import fs from "node:fs";
import path from "node:path";

export const id = "copilot";
export const marker = ".github/prompts/team.prompt.md";

export function render(wf, ctx) {
  return {
    path: path.join(".github", "prompts", `${wf.name}.prompt.md`),
    text: `---\ndescription: ${wf.description.slice(0, 250)}\n---\n\n` + ctx.noSubagentNote + wf.body,
  };
}

export function pointers(root) {
  const ci = path.join(root, ".github", "copilot-instructions.md");
  const pointer = "\n## vteam\n\nThis repo runs the vteam virtual-team framework. " +
    "Prompt files: .github/prompts/*.prompt.md. Config: vteam.config.yaml.\n";
  if (!fs.existsSync(ci) || !fs.readFileSync(ci, "utf8").includes("## vteam")) {
    fs.mkdirSync(path.dirname(ci), { recursive: true });
    fs.appendFileSync(ci, pointer);
    return [".github/copilot-instructions.md (pointer appended)"];
  }
  return [];
}
