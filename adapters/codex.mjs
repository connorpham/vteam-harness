// Codex — prompt files + an AGENTS.md discovery pointer; no subagents.
import fs from "node:fs";
import path from "node:path";

export const id = "codex";
export const marker = ".codex/prompts/team.md";

export function render(wf, ctx) {
  return {
    path: path.join(".codex", "prompts", `${wf.name}.md`),
    text: ctx.noSubagentNote + wf.body,
  };
}

export function pointers(root) {
  const agents = path.join(root, "AGENTS.md");
  const pointer = "\n## vteam\n\nThis repo runs the vteam virtual-team framework. " +
    "Workflows: .codex/prompts/ (team, pm, ba, dev, qa, docs, plan, verify, guidelines). Config: vteam.config.yaml. " +
    "Doctrine: the team docs directory named in the config.\n";
  if (!fs.existsSync(agents) || !fs.readFileSync(agents, "utf8").includes("## vteam")) {
    fs.appendFileSync(agents, pointer);
    return ["AGENTS.md (pointer appended)"];
  }
  return [];
}
