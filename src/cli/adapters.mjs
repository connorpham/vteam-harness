import fs from "node:fs";
import path from "node:path";
import { spawnSync } from "node:child_process";
import { pkgRoot, render, parseFrontmatter, writeFile } from "./util.mjs";

export const TOOLS = ["claude-code", "cursor", "windsurf", "codex", "copilot"];

const NO_SUBAGENT_NOTE = `> **Adapter note:** this tool has no native subagent spawning. Where the
> workflow says "spawn a fresh agent" (reviewers, challengers, background
> lanes), run each pass in a FRESH conversation/context with only the brief's
> paths, and paste the returned card into the dossier file. Background lanes
> run sequentially. Every gate and card requirement holds unchanged.

`;

/** The tier→model table for this tool, resolved by model_route.py from the
 * data file — so every rendered workflow tells its agent EXACTLY which model
 * each role runs on, instead of leaving "workhorse" abstract. */
function routingBlock(tool, root) {
  const script = [path.join(root, ".vteam/scripts/model_route.py"),
                  path.join(pkgRoot, "core/scripts/model_route.py")].find(fs.existsSync);
  if (!script) return "";
  const r = spawnSync("python3", [script, "--table", "--tool", tool],
    { cwd: root, encoding: "utf8" });
  if (r.status !== 0) {
    console.log(`⚠ ${tool}: model routing table unavailable (${(r.stderr || "").trim().slice(0, 120)}) — ` +
      `set this tool's models in model-routing.data.yaml, then re-run vteam update`);
    return "";
  }
  const usage = tool === "claude-code"
    ? "> Spawning a subagent: pass the resolved name as the Agent tool's `model` parameter.\n"
    : "> This tool has no subagent spawning: before each reviewer/challenger pass, switch\n" +
      "> your model picker to the resolved name, run the pass in a fresh chat, then switch back.\n";
  return r.stdout.trimEnd() + "\n" + usage + "\n";
}

function workflows() {
  const dir = path.join(pkgRoot, "core", "workflows");
  return fs.readdirSync(dir).filter((f) => f.endsWith(".md")).map((f) => {
    const { meta, body } = parseFrontmatter(fs.readFileSync(path.join(dir, f), "utf8"));
    return { file: f, meta, body };
  });
}

/** Render all workflows for one tool into the target repo. Returns written paths. */
export function renderTool(tool, root, cfg) {
  const written = [];
  const routing = routingBlock(tool, root);
  for (const wf of workflows()) {
    const name = wf.meta.name;
    // guidelines is method-only — no agents spawned, no routing block needed
    const body = (name === "guidelines" ? "" : routing) + render(wf.body, cfg);
    const desc = render(wf.meta.description || "", cfg);
    let out, text;
    switch (tool) {
      case "claude-code":
        out = path.join(root, ".claude", "skills", name, "SKILL.md");
        text = `---\nname: ${name}\ndescription: "${desc.replace(/"/g, "'")}"\n` +
          (wf.meta.args ? `argument-hint: "${wf.meta.args.replace(/"/g, "'")}"\n` : "") +
          `---\n\n${body}`;
        break;
      case "cursor":
        out = path.join(root, ".cursor", "commands", `${name}.md`);
        text = NO_SUBAGENT_NOTE + body;
        break;
      case "windsurf":
        out = path.join(root, ".windsurf", "workflows", `${name}.md`);
        text = `---\ndescription: ${desc.slice(0, 250)}\n---\n\n` + NO_SUBAGENT_NOTE + body;
        break;
      case "codex":
        out = path.join(root, ".codex", "prompts", `${name}.md`);
        text = NO_SUBAGENT_NOTE + body;
        break;
      case "copilot":
        out = path.join(root, ".github", "prompts", `${name}.prompt.md`);
        text = `---\ndescription: ${desc.slice(0, 250)}\n---\n\n` + NO_SUBAGENT_NOTE + body;
        break;
      default:
        throw new Error(`unknown tool ${tool}`);
    }
    writeFile(out, text);
    written.push(path.relative(root, out));
  }
  // pointer files so agents discover the framework
  if (tool === "codex") {
    const agents = path.join(root, "AGENTS.md");
    const pointer = "\n## vteam\n\nThis repo runs the vteam virtual-team framework. " +
      "Workflows: .codex/prompts/ (team, pm, ba, dev, qa, verify). Config: vteam.config.yaml. " +
      "Doctrine: the team docs directory named in the config.\n";
    if (!fs.existsSync(agents) || !fs.readFileSync(agents, "utf8").includes("## vteam")) {
      fs.appendFileSync(agents, pointer);
      written.push("AGENTS.md (pointer appended)");
    }
  }
  if (tool === "copilot") {
    const ci = path.join(root, ".github", "copilot-instructions.md");
    const pointer = "\n## vteam\n\nThis repo runs the vteam virtual-team framework. " +
      "Prompt files: .github/prompts/*.prompt.md. Config: vteam.config.yaml.\n";
    if (!fs.existsSync(ci) || !fs.readFileSync(ci, "utf8").includes("## vteam")) {
      fs.appendFileSync(ci, pointer);
      written.push(".github/copilot-instructions.md (pointer appended)");
    }
  }
  return written;
}
