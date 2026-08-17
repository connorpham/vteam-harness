import fs from "node:fs";
import path from "node:path";
import { execSync } from "node:child_process";
import { pkgRoot, repoRoot, ask, askChoice, copyDir, writeIfAbsent, writeFile, render } from "./util.mjs";
import { TOOLS, renderTool } from "./adapters.mjs";

const PROFILES = ["generic", "node", "python", "nextjs-prisma"];
const TRACKERS = ["markdown", "jira"];
const DESIGNS = ["none", "figma"];
const AUTONOMY = ["off", "assisted", "full"];

export async function init(flags) {
  const root = repoRoot();
  const cfgFile = path.join(root, "vteam.config.yaml");
  if (fs.existsSync(cfgFile)) {
    console.log("vteam.config.yaml already exists — use `vteam update` to refresh the install.");
    process.exit(1);
  }

  const yes = !!flags.yes;
  const get = async (flag, q, def) => flags[flag] ?? (yes ? def : await ask(q, def));
  const getChoice = async (flag, q, opts, def) =>
    flags[flag] ?? (yes ? def : await askChoice(q, opts, def));

  const name = await get("name", "Project name", path.basename(root));
  const key = (await get("key", "Ticket key prefix (e.g. PROJ)", "PROJ")).toUpperCase();
  const language = await get("language", "Owner-facing output language (en, vi, …)", "en");
  const profile = await getChoice("profile", "Stack profile", PROFILES, "generic");
  const tracker = await getChoice("tracker", "Issue tracker", TRACKERS, "markdown");
  const design = await getChoice("design", "Design source", DESIGNS, "none");
  const autonomy = await getChoice("autonomy", "Autonomy level (quality gates never relax; this only flips wait-for-human gates)", AUTONOMY, "assisted");
  const toolsRaw = await get("tools", `Agent tools to install (comma-separated: ${TOOLS.join(", ")})`, "claude-code");
  const tools = String(toolsRaw).split(",").map((t) => t.trim()).filter((t) => TOOLS.includes(t));
  if (!tools.length) tools.push("claude-code");
  const today = new Date().toISOString().slice(0, 10);

  const cfg = {
    project: { name, key, language, adopted: today },
    paths: {
      specs: "docs/specs", pm: "docs/pm", qa: "docs/qa", adr: "docs/adr",
      team: "docs/team", design: "docs/design", evidence: "evd", backlog: "docs/backlog",
    },
  };

  // ---- vteam.config.yaml ----------------------------------------------------
  const yaml = `# vteam configuration — the contract between this repo and the framework.
# Schema house of record: the vteam package's docs/DESIGN.md §2.
version: 1

project:
  name: ${name}
  key: ${key}
  language: ${language}
  adopted: ${today}

paths:
  specs: docs/specs
  pm: docs/pm
  qa: docs/qa
  adr: docs/adr
  team: docs/team
  design: docs/design
  evidence: evd
  backlog: docs/backlog

stack:
  profile: ${profile}
  package_manager: npm

git:
  protected_branch: main
  branch_pattern: "^(feat|fix)/{key}-[0-9]+-"
  hooks: managed
  code_paths: [src/, prisma/]

tracker:
  provider: ${tracker}
  done_statuses: [Done, Closed, Resolved]
  review_status: In Review

design:
  provider: ${design}

team:
  size: 1
  capacity_per_day: 0.8

autonomy:
  level: ${autonomy}
  exemptions:
    - real-money
    - legal
    - purchasing
    - credentials
    - data-deletion

review:
  reviewers: 2
  high_stakes_paths: []
  high_stakes_terms: []

models:
  routing: default
`;
  writeFile(cfgFile, yaml);

  // ---- .vteam runtime ---------------------------------------------------------
  copyDir(path.join(pkgRoot, "core", "scripts"), path.join(root, ".vteam", "scripts"));
  copyDir(path.join(pkgRoot, "core", "locales"), path.join(root, ".vteam", "locales"));
  copyDir(path.join(pkgRoot, "profiles", profile), path.join(root, ".vteam", "profiles", profile));
  if (tracker !== "markdown") {
    fs.mkdirSync(path.join(root, ".vteam", "providers"), { recursive: true });
    fs.copyFileSync(path.join(pkgRoot, "providers", "tracker", `${tracker}.py`),
      path.join(root, ".vteam", "providers", `tracker_${tracker}.py`));
  }
  if (design !== "none") {
    fs.mkdirSync(path.join(root, ".vteam", "providers"), { recursive: true });
    fs.copyFileSync(path.join(pkgRoot, "providers", "design", `${design}.py`),
      path.join(root, ".vteam", "providers", `design_${design}.py`));
  }

  // ---- docs skeletons (never clobber existing ledgers) -----------------------
  const T = (f) => fs.readFileSync(path.join(pkgRoot, "core", "templates", "docs", f), "utf8");
  writeIfAbsent(path.join(root, "docs/pm/log.md"), T("log.md"));
  writeIfAbsent(path.join(root, "docs/pm/decisions.md"), T("decisions.md"));
  writeIfAbsent(path.join(root, "docs/pm/plan.yaml"), T("plan.yaml"));
  writeIfAbsent(path.join(root, "docs/pm/sessions/.gitkeep"), "");
  writeIfAbsent(path.join(root, "docs/qa/knowledge-base.md"), T("knowledge-base.md"));
  writeIfAbsent(path.join(root, "docs/qa/known-issues.md"), T("known-issues.md"));
  writeIfAbsent(path.join(root, "docs/specs/INDEX.md"), T("specs-INDEX.md"));
  writeIfAbsent(path.join(root, "docs/specs/changes.md"), T("changes.md"));
  if (tracker === "markdown") writeIfAbsent(path.join(root, "docs/backlog/.gitkeep"), "");

  // ---- doctrine rendered into the repo ---------------------------------------
  const docSrc = path.join(pkgRoot, "core", "doctrine");
  const docDst = path.join(root, "docs", "team");
  for (const rel of walk(docSrc)) {
    const out = path.join(docDst, rel);
    const text = fs.readFileSync(path.join(docSrc, rel), "utf8");
    writeIfAbsent(out, rel.endsWith(".md") ? render(text, cfg) : text);
  }

  // ---- git fence --------------------------------------------------------------
  const hook = path.join(root, ".githooks", "pre-push");
  writeIfAbsent(hook, fs.readFileSync(path.join(pkgRoot, "core", "templates", "hooks", "pre-push"), "utf8"));
  try { fs.chmodSync(hook, 0o755); } catch {}
  try {
    execSync("git config core.hooksPath .githooks", { cwd: root });
    console.log("✓ git config core.hooksPath .githooks");
  } catch { console.log("⚠ could not set core.hooksPath — run it by hand"); }

  // ---- .gitignore: evidence images out, text in --------------------------------
  const gi = path.join(root, ".gitignore");
  const rules = "\n# vteam: evidence text commits, binaries don't\nevd/**\n!evd/**/\n!evd/**/*.md\n!evd/**/*.json\n";
  if (!fs.existsSync(gi) || !fs.readFileSync(gi, "utf8").includes("# vteam:")) {
    fs.appendFileSync(gi, rules);
  }

  // ---- CI workflow --------------------------------------------------------------
  writeIfAbsent(path.join(root, ".github", "workflows", "vteam-gate.yml"),
    `name: vteam gate
on: [push, pull_request]
jobs:
  gate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with: { fetch-depth: 0 }
      - uses: actions/setup-python@v5
        with: { python-version: "3.11" }
      - run: pip install pillow
      - run: bash .vteam/scripts/gate.sh
`);

  // ---- adapters -----------------------------------------------------------------
  for (const tool of tools) {
    const written = await renderTool(tool, root, cfg);
    console.log(`✓ ${tool}: ${written.length} workflow files`);
  }

  console.log(`
vteam installed. Next steps:
  1. Review vteam.config.yaml (high-stakes paths/terms, code_paths, capacity).
  2. ${tracker === "jira" ? "Add JIRA_BASE_URL / JIRA_EMAIL / JIRA_API_TOKEN to .env." :
       "Tickets live in docs/backlog/*.md (markdown tracker — zero services)."}
  ${design === "figma" ? "3. Add FIGMA_ACCESS_TOKEN / FIGMA_FILE_KEY to .env.\n  4." : "3."} Run: npx vteam doctor
  Then start a workday with /team in your agent tool.`);
}

function walk(dir, prefix = "") {
  const out = [];
  for (const e of fs.readdirSync(dir, { withFileTypes: true })) {
    const rel = prefix ? path.join(prefix, e.name) : e.name;
    if (e.isDirectory()) out.push(...walk(path.join(dir, e.name), rel));
    else out.push(rel);
  }
  return out;
}
