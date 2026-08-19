import fs from "node:fs";
import path from "node:path";
import { execSync } from "node:child_process";
import { pkgRoot, gitRoot, ask, askChoice, writeIfAbsent, writeFile, render } from "./util.mjs";
import { parseConfig } from "./config.mjs";
import { ManifestGuard, walkFiles } from "./manifest.mjs";
import { TOOLS, renderTool } from "./adapters.mjs";

const PROFILES = ["generic", "node", "python", "nextjs-prisma", "go", "rust"];
const TRACKERS = ["markdown", "jira", "github"];
const DESIGNS = ["none", "figma"];
const AUTONOMY = ["off", "assisted", "full"];
const VALUE_FLAGS = ["name", "key", "language", "profile", "tracker", "design", "autonomy", "tools"];

/** The CI workflow init installs (update refreshes it under the manifest rule). */
export const CI_WORKFLOW = `name: vteam gate
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
`;

/** The .gitignore rules init appends (tokens live in .env — .env stays out of git). */
export const GITIGNORE_RULES = [
  "# vteam: evidence text commits, binaries don't",
  "evd/**",
  "!evd/**/",
  "!evd/**/*.md",
  "!evd/**/*.json",
  "# vteam: tokens live in .env — .env never commits",
  ".env",
  "# vteam: machine-local doctor snapshot for `vteam board`",
  ".vteam/doctor.json",
];

function fail(msg) {
  console.error(`vteam init: ${msg}`);
  process.exit(1);
}

/** A user string as a YAML scalar that round-trips through lib/ctx.py's
 * constrained parser (quotes stripped, NO escape sequences, ' #' always a
 * comment — even inside quotes). Anything that can't round-trip is rejected
 * BEFORE any file is written. */
function yamlStr(s, what) {
  if (/[\r\n]/.test(s)) fail(`${what} must be a single line`);
  if (/\s#/.test(s)) fail(`${what} cannot contain ' #' — the config parser treats it as a comment`);
  if (s.includes("'") && s.includes('"')) fail(`${what} cannot mix single and double quotes`);
  if (/^\s|\s$/.test(s)) fail(`${what} cannot start or end with whitespace`);
  return s.includes("'") ? `"${s}"` : `'${s}'`;
}

export async function init(flags) {
  // ---- preconditions ---------------------------------------------------------
  const root = gitRoot();
  if (!root) fail("not a git repository — run `git init` first, then re-run `vteam init`.");
  const cfgFile = path.join(root, "vteam.config.yaml");
  if (fs.existsSync(cfgFile)) {
    console.log("vteam.config.yaml already exists — use `vteam update` to refresh the install.");
    process.exit(1);
  }
  for (const f of VALUE_FLAGS) {
    if (flags[f] === true) fail(`--${f} requires a value (e.g. --${f} <value>)`);
  }

  // ---- gather (prompt only on a real TTY) --------------------------------------
  const yes = !!flags.yes;
  const needTTY = (flag) => {
    if (!process.stdin.isTTY) {
      fail(`non-interactive session: pass --yes or all flags (missing --${flag})`);
    }
  };
  const get = async (flag, q, def) => {
    if (flags[flag] !== undefined) return String(flags[flag]);
    if (yes) return def;
    needTTY(flag);
    return ask(q, def);
  };
  const getChoice = async (flag, q, opts, def) => {
    if (flags[flag] !== undefined) return String(flags[flag]);
    if (yes) return def;
    needTTY(flag);
    return askChoice(q, opts, def);
  };

  const name = await get("name", "Project name", path.basename(root));
  const keyRaw = await get("key", "Ticket key prefix (e.g. PROJ)", "PROJ");
  const language = await get("language", "Owner-facing output language (en, vi, …)", "en");
  const profile = await getChoice("profile", "Stack profile", PROFILES, detectProfile(root));
  const tracker = await getChoice("tracker", "Issue tracker", TRACKERS, "markdown");
  const design = await getChoice("design", "Design source", DESIGNS, "none");
  const autonomy = await getChoice("autonomy", "Autonomy level (quality gates never relax; this only flips wait-for-human gates)", AUTONOMY, "assisted");
  const toolsRaw = await get("tools", `Agent tools to install (comma-separated: ${TOOLS.join(", ")})`, "claude-code");

  // ---- validate EVERYTHING before the first write -------------------------------
  if (!/^[A-Za-z][A-Za-z0-9]*$/.test(keyRaw)) {
    fail(`--key must match ^[A-Za-z][A-Za-z0-9]*$ (got ${JSON.stringify(keyRaw)})`);
  }
  const key = keyRaw.toUpperCase();
  if (!/^[A-Za-z]{2,8}$/.test(language)) {
    fail(`--language must be a 2-8 letter code like en, vi (got ${JSON.stringify(language)})`);
  }
  if (!PROFILES.includes(profile)) fail(`unknown --profile ${JSON.stringify(profile)} — valid: ${PROFILES.join(", ")}`);
  if (!TRACKERS.includes(tracker)) fail(`unknown --tracker ${JSON.stringify(tracker)} — valid: ${TRACKERS.join(", ")}`);
  if (!DESIGNS.includes(design)) fail(`unknown --design ${JSON.stringify(design)} — valid: ${DESIGNS.join(", ")}`);
  if (!AUTONOMY.includes(autonomy)) fail(`unknown --autonomy ${JSON.stringify(autonomy)} — valid: ${AUTONOMY.join(", ")}`);
  const tools = String(toolsRaw).split(",").map((t) => t.trim()).filter(Boolean);
  if (!tools.length) tools.push("claude-code");
  for (const t of tools) {
    if (!TOOLS.includes(t)) fail(`unknown --tools value ${JSON.stringify(t)} — valid: ${TOOLS.join(", ")}`);
  }
  const nameYaml = yamlStr(name, "--name");
  const today = new Date().toISOString().slice(0, 10);
  const codePaths = deriveCodePaths(root);
  const pkgManager = detectPackageManager(root);
  if (codePaths.length) {
    console.log(`✓ code_paths derived from this repo: [${codePaths.join(", ")}] — review in vteam.config.yaml (the review fence watches ONLY these)`);
  } else {
    console.log(`⚠ could not derive code_paths — the review fence and stale-verdict gate are OFF until you set git.code_paths in vteam.config.yaml
  (until then the pre-push fence FAILS CLOSED: it treats EVERY path as product code — never invented paths, never a silent open fence)`);
  }

  // hooks safety: NEVER silently disable an existing hook manager (husky, lefthook,
  // populated .git/hooks). If one is present, ship the fence but leave wiring manual.
  let currentHooksPath = "";
  try {
    currentHooksPath = execSync("git config core.hooksPath",
      { cwd: root, encoding: "utf8", stdio: ["ignore", "pipe", "ignore"] }).trim();
  } catch { /* unset */ }
  let existingHooks = [];
  try {
    const hooksDir = path.join(root, ".git", "hooks");
    existingHooks = fs.readdirSync(hooksDir).filter((f) => !f.endsWith(".sample"));
  } catch { /* .git may be a worktree file — treat as no local hooks */ }
  const foreignHooksPath = currentHooksPath && currentHooksPath !== ".githooks";
  const hooksMode = (foreignHooksPath || existingHooks.length) ? "external" : "managed";

  // ---- vteam.config.yaml ----------------------------------------------------
  const yaml = `# vteam configuration — the contract between this repo and the framework.
# Schema house of record: the vteam package's docs/DESIGN.md §2.
version: 1

project:
  name: ${nameYaml}
  key: ${key}
  language: ${language.toLowerCase()}
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

specs:
  # the ORIGINAL spec documents BA shards from (verbatim_gate compares shards
  # in paths.specs against these — leave empty until you have source docs;
  # never point it at paths.specs itself: self-comparison is self-grading)
  sources: []

docs:
  task_context:            # extra background /dev reads at T1, keyed by ticket label/type
    always: []             # read for EVERY ticket, e.g. [docs/architecture.md]
    by_label: {}           # label/type (lowercase) -> file list; a mapped-but-missing
                           # file is reported LOUDLY in the task sheet, never guessed

stack:
  profile: ${profile}
  package_manager: ${pkgManager}

git:
  protected_branch: main
  branch_pattern: "^(feat|fix)/{key}-[0-9]+-"
  merge_strategy: merge
  # merge | squash | rebase — how PRs land on the protected branch. squash and
  # rebase DISCARD branch shas, so QA verdicts anchor by VERIFIED-AT (qa workflow)
  # and stale_verdict_check falls back to it; set this to match your repo.
  hooks: ${hooksMode}
  # Derived from THIS repo's layout at init time (field-trial finding #17: a
  # hardcoded [src/, prisma/] default silently lost the review fence on repos
  # whose code lives in lib/, app/ or root files). Review it — the review fence
  # and stale-verdict gate only watch what is listed here. An empty list means
  # derivation found nothing: doctor warns, and the pre-push fence FAILS CLOSED
  # (every path is treated as product code) until you fill it in.
  code_paths: [${codePaths.join(", ")}]

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
  # agent may merge its own green PR — only honored at level: full; flip to
  # false to keep every merge in human hands even at full autonomy
  self_merge: ${autonomy === "full"}
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

  // round-trip proof BEFORE writing: the generated YAML must come back
  // identical through the same constrained parser the gates use.
  let cfg;
  try {
    cfg = parseConfig(yaml);
  } catch (e) {
    fail(`generated config does not parse (${e.message}) — check --name/--key values`);
  }
  if (cfg.project.name !== name) fail(`project.name would not round-trip through the config parser (got ${JSON.stringify(cfg.project.name)}) — simplify --name`);
  if (cfg.project.key !== key) fail("project.key would not round-trip through the config parser");

  writeFile(cfgFile, yaml);

  // ---- .vteam runtime (recorded in the manifest) --------------------------------
  const guard = new ManifestGuard(root);
  guard.forceDir(path.join(pkgRoot, "core", "scripts"), ".vteam/scripts");
  guard.forceDir(path.join(pkgRoot, "core", "locales"), ".vteam/locales");
  guard.forceDir(path.join(pkgRoot, "profiles", profile), `.vteam/profiles/${profile}`);
  if (tracker !== "markdown") {
    guard.force(`.vteam/providers/tracker_${tracker}.py`,
      fs.readFileSync(path.join(pkgRoot, "providers", "tracker", `${tracker}.py`)));
  }
  if (design !== "none") {
    guard.force(`.vteam/providers/design_${design}.py`,
      fs.readFileSync(path.join(pkgRoot, "providers", "design", `${design}.py`)));
  }

  // ---- docs skeletons (user ledgers from day one — never clobbered, never manifest-owned)
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

  // ---- doctrine rendered into the repo (recorded only when actually written) ----
  const docSrc = path.join(pkgRoot, "core", "doctrine");
  for (const rel of walkFiles(docSrc)) {
    const text = fs.readFileSync(path.join(docSrc, ...rel.split("/")), "utf8");
    const rendered = rel.endsWith(".md") ? render(text, cfg) : text;
    const outRel = `docs/team/${rel}`;
    if (writeIfAbsent(path.join(root, ...outRel.split("/")), rendered)) guard.record(outRel, rendered);
    else console.log(`⚠ ${outRel} already exists — kept yours (vteam update will offer ${outRel}.new)`);
  }

  // ---- git fence --------------------------------------------------------------
  const hookText = fs.readFileSync(path.join(pkgRoot, "core", "templates", "hooks", "pre-push"), "utf8");
  const hookAbs = path.join(root, ".githooks", "pre-push");
  if (writeIfAbsent(hookAbs, hookText)) guard.record(".githooks/pre-push", hookText);
  try { fs.chmodSync(hookAbs, 0o755); } catch { /* pre-existing user hook: leave its mode */ }
  if (hooksMode === "managed") {
    try {
      execSync("git config core.hooksPath .githooks", { cwd: root });
      console.log("✓ git config core.hooksPath .githooks");
    } catch { console.log("⚠ could not set core.hooksPath — run it by hand"); }
  } else {
    const reason = foreignHooksPath
      ? `core.hooksPath is already ${JSON.stringify(currentHooksPath)}`
      : `.git/hooks already contains: ${existingHooks.join(", ")}`;
    console.log(`⚠ existing git hooks detected (${reason}) — NOT overwriting your hook setup.
  vteam's pre-push fence sits at .githooks/pre-push but is NOT active. To wire it:
    - have your hook manager's pre-push run:  .githooks/pre-push "$@"
      (husky: add that line to .husky/pre-push), or
    - switch entirely:  git config core.hooksPath .githooks  (disables your current hooks).
  The config records git.hooks: external — vteam will not touch hook wiring.`);
  }

  // ---- .gitignore: evidence images out, text in, .env out -----------------------
  const gi = path.join(root, ".gitignore");
  if (!fs.existsSync(gi) || !fs.readFileSync(gi, "utf8").includes("# vteam:")) {
    fs.appendFileSync(gi, "\n" + GITIGNORE_RULES.join("\n") + "\n");
  }

  // ---- CI workflow --------------------------------------------------------------
  const ciRel = ".github/workflows/vteam-gate.yml";
  if (writeIfAbsent(path.join(root, ...ciRel.split("/")), CI_WORKFLOW)) guard.record(ciRel, CI_WORKFLOW);

  // ---- adapters (outputs are framework-owned → recorded) --------------------------
  for (const tool of tools) {
    const written = await renderTool(tool, root, cfg, (rel, text) => guard.force(rel, text));
    console.log(`✓ ${tool}: ${written.length} workflow files`);
  }

  guard.save(pkgVersion());
  console.log(`
vteam installed. Next steps:
  1. Review vteam.config.yaml (high-stakes paths/terms, code_paths, capacity).
  2. ${tracker === "jira" ? "Add JIRA_BASE_URL / JIRA_EMAIL / JIRA_API_TOKEN to .env (gitignored)." :
       tracker === "github" ? "Add GITHUB_TOKEN to .env (gitignored); repo auto-detected from origin or set GITHUB_REPO=owner/repo." :
       "Tickets live in docs/backlog/*.md (markdown tracker — zero services)."}
  ${design === "figma" ? "3. Add FIGMA_ACCESS_TOKEN / FIGMA_FILE_KEY to .env (gitignored).\n  4." : "3."} Run: npx vteam-harness doctor
  Then start a workday with /team in your agent tool.`);
}

export function pkgVersion() {
  try {
    return JSON.parse(fs.readFileSync(path.join(pkgRoot, "package.json"), "utf8")).version ?? "0";
  } catch { return "0"; }
}

/** Where does product code actually live HERE? (field-trial finding #17 — a
 * hardcoded default silently lost the review fence on non-src/ layouts).
 * Heuristic: conventional source dirs that exist and contain source files,
 * plus root-level source files, plus prisma/ when present. Finds nothing →
 * returns [] and init warns LOUDLY: an honest unknown beats invented paths
 * (doctor warns on []; the pre-push fence fails CLOSED until it is set). */
function deriveCodePaths(root) {
  const SRC_EXT = /\.(ts|tsx|js|jsx|mjs|cjs|py|go|rs|rb|php|java|kt|swift|c|cc|cpp|h|cs|vue|svelte)$/;
  const CANDIDATE_DIRS = ["src", "lib", "app", "apps", "packages", "cmd", "pkg", "internal", "server", "api", "core"];
  const out = [];
  const hasSource = (dir, depth = 0) => {
    if (depth > 2) return false;
    let entries;
    try { entries = fs.readdirSync(dir, { withFileTypes: true }); } catch { return false; }
    return entries.some((e) => e.isFile() ? SRC_EXT.test(e.name)
      : (e.isDirectory() && !e.name.startsWith(".") && e.name !== "node_modules" &&
         hasSource(path.join(dir, e.name), depth + 1)));
  };
  for (const d of CANDIDATE_DIRS) {
    if (fs.existsSync(path.join(root, d)) && hasSource(path.join(root, d))) out.push(`${d}/`);
  }
  if (fs.existsSync(path.join(root, "prisma"))) out.push("prisma/");
  for (const e of fs.readdirSync(root, { withFileTypes: true })) {
    if (e.isFile() && SRC_EXT.test(e.name) && !/\.(config|test|spec)\./.test(e.name)) out.push(e.name);
  }
  return [...new Set(out)];
}

/** Detect the stack profile from the repo instead of defaulting blind
 * (field-trial finding #19: a Go repo on `generic` went green running nothing). */
function detectProfile(root) {
  const has = (f) => fs.existsSync(path.join(root, f));
  if (has("go.mod")) return "go";
  if (has("Cargo.toml")) return "rust";
  if (has("prisma/schema.prisma") && has("package.json")) return "nextjs-prisma";
  if (has("package.json")) return "node";
  if (has("pyproject.toml") || has("setup.py") || has("requirements.txt")) return "python";
  return "generic";
}

/** Detect the package manager from the lockfile actually present — a pnpm repo
 * initialized as npm makes lockfile_check flag the repo's OWN lockfile. */
function detectPackageManager(root) {
  const has = (f) => fs.existsSync(path.join(root, f));
  if (has("pnpm-lock.yaml")) return "pnpm";
  if (has("yarn.lock")) return "yarn";
  if (has("bun.lockb") || has("bun.lock")) return "bun";
  return "npm";
}
