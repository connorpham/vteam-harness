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

/** Discover the selftest-bearing gates under a scripts dir: any *.py/*.sh/*.mjs
 * whose source contains `--selftest`, with the interpreter its extension names.
 * Sorted for stable output. Exported so tests mirror doctor instead of keeping
 * a second hardcoded list (the drifting-count trap). */
export function discoverSelftests(dir) {
  const INTERP = { ".py": "python3", ".sh": "bash", ".mjs": "node" };
  const found = [];
  const walk = (abs, rel) => {
    let entries = [];
    try { entries = fs.readdirSync(abs, { withFileTypes: true }); } catch { return; }
    for (const e of entries.sort((a, b) => a.name.localeCompare(b.name))) {
      const eAbs = path.join(abs, e.name);
      const eRel = rel ? `${rel}/${e.name}` : e.name;
      if (e.isDirectory()) walk(eAbs, eRel);
      else if (INTERP[path.extname(e.name)] &&
               fs.readFileSync(eAbs, "utf8").includes("--selftest")) {
        found.push({ s: eRel, cmd: INTERP[path.extname(e.name)] });
      }
    }
  };
  walk(dir, "");
  return found;
}

export async function doctor(flags) {
  const root = repoRoot();
  let miss = 0;
  // --json: same checks, machine shape — {ok, checks:[{name,status,detail}]}
  // on stdout and nothing else (exit codes unchanged).
  const json = !!flags.json;
  const checks = [];
  const record = (status, m) =>
    checks.push({ name: String(m).split(/ — |: /)[0].slice(0, 80), status, detail: String(m) });
  const ok = (m) => { record("ok", m); if (!json) console.log(`✅ ${m}`); };
  const bad = (m) => { record("fail", m); miss++; if (!json) console.log(`❌ ${m}`); };
  const warn = (m) => { record("warn", m); if (!json) console.log(`⚠️  ${m}`); };
  const finish = (code) => {
    if (json) console.log(JSON.stringify({ ok: code === 0, checks }, null, 2));
    process.exit(code);
  };

  // 0. prerequisites — diagnose a missing python3 instead of crashing on it
  const py = spawnSync("python3", ["--version"], { encoding: "utf8" });
  if (py.error || py.status !== 0) {
    bad("python3 not found on PATH — the gates are Python; install Python 3 (macOS: xcode-select --install / brew install python3, Debian: apt install python3) and re-run");
    finish(1);
  }
  ok(`python3 available (${String(py.stdout || py.stderr || "").trim()})`);

  // 1. config parses (through the same parser the gates use)
  if (!fs.existsSync(path.join(root, "vteam.config.yaml"))) {
    bad("vteam.config.yaml missing — run `npx vteam-harness init`");
    finish(1);
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
    const gone = [], edited = [];
    for (const [rel, hash] of Object.entries(manifest.files)) {
      const abs = path.join(root, ...rel.split("/"));
      if (!fs.existsSync(abs)) gone.push(rel);
      else if (sha256(fs.readFileSync(abs)) !== hash) edited.push(rel);
    }
    // name the files — "1 file modified" with no name is the silent-ish
    // reporting this framework exists to kill
    const list = (a) => a.slice(0, 5).join(", ") + (a.length > 5 ? ` (+${a.length - 5} more)` : "");
    if (gone.length) bad(`${gone.length} manifest-owned file(s) missing — re-run vteam update: ${list(gone)}`);
    if (edited.length) warn(`${edited.length} framework file(s) locally modified — update will keep yours and park new versions as *.new: ${list(edited)}`);
    if (!gone.length && !edited.length) ok(`manifest verified (${Object.keys(manifest.files).length} framework-owned files intact)`);
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

  // 3b. code_paths must match something real — a fence watching nothing is the
  // silent-skip class this framework exists to kill (field-trial finding #17).
  // [] is an honest unknown (init could not derive → WARN, fence fails closed);
  // a CONFIGURED list matching nothing is a lie in the config → RED.
  if (cfg) {
    const cps = cfgGet(cfg, "git.code_paths", []);
    const list = Array.isArray(cps) ? cps.map(String) : [];
    if (!list.length) {
      warn("git.code_paths is empty — could not derive code_paths — the review fence and stale-verdict gate are OFF until you set git.code_paths in vteam.config.yaml (the pre-push fence fails CLOSED, treating every path as product code, until then)");
    } else {
      const alive = list.filter((cp) => fs.existsSync(path.join(root, cp.replace(/\/$/, ""))));
      if (!alive.length) {
        bad(`git.code_paths ${JSON.stringify(list)} matches NOTHING in this repo — the review fence and stale-verdict gate are watching air; point it at where the code actually lives`);
      } else if (alive.length < list.length) {
        warn(`git.code_paths: ${list.filter((c) => !alive.includes(c)).join(", ")} do(es) not exist — dead entries watch nothing`);
      } else ok(`code_paths alive (${alive.join(", ")})`);
    }
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

  // 5. selftests — every gate must still prove it can go red (python + shell + node).
  // DISCOVERED, not hardcoded: every .vteam/scripts file whose source carries
  // `--selftest` runs with the interpreter its extension names — new gates join
  // the list by existing, and the printed count cannot drift from reality.
  const selftests = discoverSelftests(path.join(root, ".vteam", "scripts"));
  if (!selftests.length) {
    bad("no --selftest gates found under .vteam/scripts — broken install, re-run vteam update");
  }
  let stFail = 0, stRun = 0;
  for (const { s, cmd } of selftests) {
    const red = runSelftest(cmd, [path.join(root, ".vteam/scripts", s)], root);
    stRun++;
    if (red) { bad(`selftest RED: ${s}\n${red}`); stFail++; }
  }
  if (selftests.length && !stFail) ok(`gate selftests green (${stRun} discovered checks prove they can red)`);

  // 6. provider preflight
  if (!json) console.log("── preflight ──");
  const pf = spawnSync("bash", [path.join(root, ".vteam/scripts/preflight.sh"),
    ...(flags.backend ? ["--backend"] : [])],
    json ? { cwd: root, encoding: "utf8" } : { cwd: root, stdio: "inherit" });
  if (pf.status !== 0) miss++;
  if (json) checks.push({ name: "preflight", status: pf.status === 0 ? "ok" : "fail",
    detail: (String(pf.stdout || "") + String(pf.stderr || "")).trim() });

  if (flags.migrate) {
    const { migrate } = await import("./migrate.mjs");
    migrate(flags);
  }

  finish(miss ? 1 : 0);
}
