import fs from "node:fs";
import path from "node:path";
import { execSync, spawnSync } from "node:child_process";
import { repoRoot } from "./util.mjs";
import { loadConfig, cfgGet } from "./config.mjs";
import { loadManifest, sha256, MANIFEST_REL } from "./manifest.mjs";

/** Run a selftest-bearing gate. Returns "" on green, the output on red. */
function runSelftest(cmd, args, cwd) {
  const r = spawnSync(cmd, [...args, "--selftest"], { cwd, encoding: "utf8" });
  if (r.error) return `spawn failed: ${r.error.message}`;
  if (r.status !== 0) return (String(r.stdout || "") + String(r.stderr || "")).trim();
  return "";
}

export async function doctor(flags) {
  const root = repoRoot();
  let miss = 0;
  const ok = (m) => console.log(`✅ ${m}`);
  const bad = (m) => { console.log(`❌ ${m}`); miss++; };
  const warn = (m) => console.log(`⚠️  ${m}`);

  // 0. prerequisites — diagnose a missing python3 instead of crashing on it
  const py = spawnSync("python3", ["--version"], { encoding: "utf8" });
  if (py.error || py.status !== 0) {
    bad("python3 not found on PATH — the gates are Python; install Python 3 (macOS: xcode-select --install / brew install python3, Debian: apt install python3) and re-run");
    process.exit(1);
  }
  ok(`python3 available (${String(py.stdout || py.stderr || "").trim()})`);

  // 1. config parses (through the same parser the gates use)
  if (!fs.existsSync(path.join(root, "vteam.config.yaml"))) {
    bad("vteam.config.yaml missing — run `npx vteam init`");
    process.exit(1);
  }
  const p = spawnSync("python3", [path.join(root, ".vteam/scripts/lib/ctx.py"), "version"],
    { cwd: root, encoding: "utf8" });
  if (p.status === 0) ok(`config parses (version ${String(p.stdout || "").trim()})`);
  else bad(`config does not parse: ${(String(p.stderr || "") + String(p.stdout || "")).trim()}`);
  let cfg = null;
  try { cfg = loadConfig(root); } catch { /* step 1 already reported the parse failure */ }

  // 2. install integrity — runtime files, counted separately from other misses
  let runtimeMiss = 0;
  for (const f of ["scripts/gate.py", "scripts/log_check.py", "scripts/review_check.py",
    "scripts/evd_check.py", "scripts/preflight.sh", "scripts/lib/ctx.py",
    "scripts/lib/ctx.mjs", "scripts/lib/ctx.sh", "scripts/lib/tracker.py"]) {
    if (!fs.existsSync(path.join(root, ".vteam", f))) {
      bad(`.vteam/${f} missing — re-run vteam update`);
      runtimeMiss++;
    }
  }
  if (runtimeMiss === 0) ok(".vteam runtime complete");

  // 2b. manifest — the mechanism behind "update never touches your files"
  const manifest = loadManifest(root);
  if (!manifest) {
    warn(`${MANIFEST_REL} missing (pre-manifest install) — run vteam update once to write it`);
  } else {
    let gone = 0, edited = 0;
    for (const [rel, hash] of Object.entries(manifest.files)) {
      const abs = path.join(root, ...rel.split("/"));
      if (!fs.existsSync(abs)) gone++;
      else if (sha256(fs.readFileSync(abs)) !== hash) edited++;
    }
    if (gone) bad(`${gone} manifest-owned file(s) missing — re-run vteam update`);
    if (edited) warn(`${edited} framework file(s) locally modified — update will keep yours and park new versions as *.new`);
    if (!gone && !edited) ok(`manifest verified (${Object.keys(manifest.files).length} framework-owned files intact)`);
  }

  // 3. hooks fence — only when this install manages hooks (git.hooks: managed)
  const hooksMode = cfg ? String(cfgGet(cfg, "git.hooks", "managed")) : "managed";
  if (hooksMode === "managed") {
    let hooks = "";
    try {
      hooks = execSync("git config core.hooksPath",
        { cwd: root, encoding: "utf8", stdio: ["ignore", "pipe", "ignore"] }).trim();
    } catch { /* unset */ }
    if (hooks === ".githooks") ok("core.hooksPath = .githooks");
    else bad(`core.hooksPath is ${hooks || "(unset)"} — the pre-push fence is silent; run: git config core.hooksPath .githooks`);
  } else {
    warn("git.hooks: external — hook wiring is yours; make sure your manager runs .githooks/pre-push");
  }

  // 4. model-routing staleness — at the CONFIGURED doctrine path, not a literal
  const teamDir = cfg ? String(cfgGet(cfg, "paths.team", "docs/team")) : "docs/team";
  const routing = cfg ? String(cfgGet(cfg, "models.routing", "default")) : "default";
  const dataName = routing === "default" ? "model-routing.data.yaml" : routing;
  const mr = [path.join(root, teamDir, dataName), path.join(root, dataName)].find(fs.existsSync);
  if (!mr) {
    bad(`${dataName} not found under ${teamDir} — model routing is unresolvable; re-run vteam update`);
  } else {
    const m = fs.readFileSync(mr, "utf8").match(/snapshot_date:\s*(\d{4}-\d{2}-\d{2})/);
    if (m) {
      const age = (Date.now() - new Date(m[1]).getTime()) / 86400000;
      if (age > 90) warn(`model-routing price snapshot is ${Math.round(age)} days old — update the data file before trusting the routing economics`);
      else ok(`model-routing snapshot fresh (${m[1]})`);
    }
  }

  // 5. selftests — every gate must still prove it can go red (python + shell + node)
  const selftests = [
    ...["gate.py", "log_check.py", "verbatim_gate.py", "review_check.py", "evd_check.py",
      "evd_ui_check.py", "dor_check.py", "comment_check.py", "schedule_check.py",
      "stale_verdict_check.py", "perf_report.py", "model_route.py",
      "lib/ctx.py", "lib/tracker.py"].map((s) => ({ s, cmd: "python3" })),
    ...["docs_shrink_check.sh", "lib/ctx.sh"].map((s) => ({ s, cmd: "bash" })),
    { s: "lib/ctx.mjs", cmd: "node" },
  ];
  let stFail = 0, stRun = 0;
  for (const { s, cmd } of selftests) {
    const file = path.join(root, ".vteam/scripts", s);
    if (!fs.existsSync(file)) { warn(`selftest SKIP: .vteam/scripts/${s} not installed`); continue; }
    const red = runSelftest(cmd, [file], root);
    stRun++;
    if (red) { bad(`selftest RED: ${s}\n${red}`); stFail++; }
  }
  if (!stFail) ok(`gate selftests green (${stRun} checks prove they can red)`);

  // 6. provider preflight
  console.log("── preflight ──");
  const pf = spawnSync("bash", [path.join(root, ".vteam/scripts/preflight.sh"),
    ...(flags.backend ? ["--backend"] : [])], { cwd: root, stdio: "inherit" });
  if (pf.status !== 0) miss++;

  if (flags.migrate) {
    const { migrate } = await import("./migrate.mjs");
    migrate(flags);
  }

  process.exit(miss ? 1 : 0);
}
