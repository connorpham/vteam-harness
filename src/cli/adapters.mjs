// Thin loader over adapters/<tool>.mjs — the per-tool renderers live THERE
// (one module per tool; contract: adapters/README.md). This file only:
// loads workflows, substitutes config vars, prepends the resolved model-routing
// block, delegates to the tool module, and writes the results.
import fs from "node:fs";
import path from "node:path";
import { pathToFileURL } from "node:url";
import { spawnSync } from "node:child_process";
import { pkgRoot, render, parseFrontmatter, writeFile } from "./util.mjs";

export const TOOLS = ["claude-code", "cursor", "windsurf", "codex", "copilot"];

const NO_SUBAGENT_NOTE = `> **Adapter note:** this tool has no native subagent spawning. Where the
> workflow says "spawn a fresh agent" (reviewers, challengers, background
> lanes), run each pass in a FRESH conversation/context with only the brief's
> paths, and paste the returned card into the dossier file. Background lanes
> run sequentially. Every gate and card requirement holds unchanged.

`;

async function loadAdapter(tool) {
  if (!TOOLS.includes(tool)) throw new Error(`unknown tool ${tool}`);
  // file:// URL, not a bare absolute path — plain C:\… specifiers crash Node's
  // ESM loader on Windows (ERR_UNSUPPORTED_ESM_URL_SCHEME).
  return import(pathToFileURL(path.join(pkgRoot, "adapters", `${tool}.mjs`)).href);
}

export async function adapterMarker(tool) {
  return (await loadAdapter(tool)).marker;
}

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
    return { meta, body };
  });
}

/** Render all workflows for one tool into the target repo. Returns written
 * paths. `write(relPath, text)` lets init/update route output through the
 * manifest guard; the default writes directly. */
export async function renderTool(tool, root, cfg,
  write = (rel, text) => writeFile(path.join(root, rel), text)) {
  const adapter = await loadAdapter(tool);
  const routing = routingBlock(tool, root);
  const ctx = { root, cfg, noSubagentNote: NO_SUBAGENT_NOTE };
  const written = [];
  for (const raw of workflows()) {
    const name = raw.meta.name;
    const wf = {
      name,
      description: render(raw.meta.description || "", cfg),
      args: render(raw.meta.args || "", cfg), // frontmatter args carry {project.key} too
      // guidelines is method-only — no agents spawned, no routing block needed
      body: (name === "guidelines" ? "" : routing) + render(raw.body, cfg),
    };
    const out = adapter.render(wf, ctx);
    write(out.path, out.text);
    written.push(out.path);
  }
  if (adapter.pointers) written.push(...adapter.pointers(root));
  return written;
}
