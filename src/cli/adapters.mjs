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

/** The Environment block for the lanes that run the product (dev/qa/verify):
 * the app's resolved coordinates + the ONE headed mechanism, so "HEADED" in a
 * rendered workflow names commands instead of a vibe. Built from cfg.app in JS
 * — deliberately NOT a render() template group: an unset `app:` section must
 * produce the "not configured" branch, never a literal `{app.url}` in text. */
const ENV_WORKFLOWS = new Set(["dev", "qa", "verify"]);
function envBlock(cfg) {
  const app = (cfg && typeof cfg.app === "object" && !Array.isArray(cfg.app)) ? cfg.app : {};
  const start = String(app.start ?? "").trim();
  const url = String(app.url ?? "").trim();
  if (!start && !url) {
    return "> **Environment:** `app:` is not configured in vteam.config.yaml — env bring-up is\n" +
      "> manual this session, and `app_check.sh` prints `APP: SKIP`. Set `app.start` +\n" +
      "> `app.url` (+ optional `app.health`, `app.open_files`, `app.headed` — schema:\n" +
      "> DESIGN.md §2) to enable the watchable session: headed Chrome via\n" +
      "> `.vteam/scripts/browser.mjs`, health probe via `.vteam/scripts/app_check.sh`,\n" +
      "> editor opening via `.vteam/scripts/open_files.sh`.\n\n";
  }
  return `> **Environment** (from \`app:\` in vteam.config.yaml — start: \`${start || "<unset>"}\` · url: ${url || "<unset>"}):\n` +
    "> - **Bring-up:** run `app.start` in a BACKGROUND terminal (a gate never starts servers\n" +
    ">   — it probes), then `bash .vteam/scripts/app_check.sh --wait 60` and QUOTE its\n" +
    ">   `APP: UP` line as the bring-up proof (`--url <base>` overrides `app.url` for one run).\n" +
    "> - **HEADED = a real Chrome window the owner can watch:** drive journeys through\n" +
    ">   `launch`/`shot` from `.vteam/scripts/browser.mjs` (Playwright, the OS Chrome,\n" +
    ">   `headless: false`). Preflight it: `node .vteam/scripts/browser.mjs check` — missing\n" +
    ">   Playwright is a loud BLOCKED with the install command, never a silent headless run.\n" +
    ">   `app.headed: never` (unattended shifts) drops only the visibility, NEVER a screenshot.\n" +
    "> - **Work visibly:** open the files being edited in the owner's editor —\n" +
    ">   `bash .vteam/scripts/open_files.sh <file[:line]> …` (config `app.open_files`:\n" +
    ">   auto|code|cursor|none; a missing editor CLI skips with one line, never blocks).\n\n";
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
      // guidelines is method-only — no agents spawned, no routing block needed;
      // dev/qa/verify additionally get the Environment block (the lanes that
      // must bring the app up and run it headed)
      body: (name === "guidelines" ? "" : routing) +
        (ENV_WORKFLOWS.has(name) ? envBlock(cfg) : "") + render(raw.body, cfg),
    };
    const out = adapter.render(wf, ctx);
    write(out.path, out.text);
    written.push(out.path);
  }
  if (adapter.pointers) written.push(...adapter.pointers(root));
  return written;
}
