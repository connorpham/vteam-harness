import fs from "node:fs";
import path from "node:path";
import { execSync, spawnSync } from "node:child_process";
import { pkgRoot, repoRoot } from "./util.mjs";

export async function doctor(flags) {
  const root = repoRoot();
  let miss = 0;
  const ok = (m) => console.log(`✅ ${m}`);
  const bad = (m) => { console.log(`❌ ${m}`); miss++; };
  const warn = (m) => console.log(`⚠️  ${m}`);

  // 1. config parses (through the same parser the gates use)
  if (!fs.existsSync(path.join(root, "vteam.config.yaml"))) {
    bad("vteam.config.yaml missing — run `npx vteam init`");
    process.exit(1);
  }
  const p = spawnSync("python3", [path.join(root, ".vteam/scripts/lib/ctx.py"), "version"],
    { cwd: root, encoding: "utf8" });
  if (p.status === 0) ok(`config parses (version ${p.stdout.trim()})`);
  else bad(`config does not parse: ${p.stderr || p.stdout}`.trim());

  // 2. install integrity
  for (const f of ["scripts/gate.py", "scripts/log_check.py", "scripts/review_check.py",
    "scripts/evd_check.py", "scripts/preflight.sh", "scripts/lib/ctx.py"]) {
    if (!fs.existsSync(path.join(root, ".vteam", f))) bad(`.vteam/${f} missing — re-run vteam update`);
  }
  if (miss === 0) ok(".vteam runtime complete");

  // 3. hooks fence
  try {
    const hooks = execSync("git config core.hooksPath", { cwd: root, encoding: "utf8" }).trim();
    if (hooks === ".githooks") ok("core.hooksPath = .githooks");
    else bad(`core.hooksPath is ${hooks || "(unset)"} — the pre-push fence is silent; run: git config core.hooksPath .githooks`);
  } catch {
    bad("core.hooksPath unset — run: git config core.hooksPath .githooks");
  }

  // 4. model-routing staleness
  const mr = [path.join(root, "docs/team/model-routing.data.yaml"),
              path.join(pkgRoot, "core/doctrine/model-routing.data.yaml")].find(fs.existsSync);
  if (mr) {
    const m = fs.readFileSync(mr, "utf8").match(/snapshot_date:\s*(\d{4}-\d{2}-\d{2})/);
    if (m) {
      const age = (Date.now() - new Date(m[1]).getTime()) / 86400000;
      if (age > 90) warn(`model-routing price snapshot is ${Math.round(age)} days old — update the data file before trusting the routing economics`);
      else ok(`model-routing snapshot fresh (${m[1]})`);
    }
  }

  // 5. selftests — every gate must still prove it can go red
  const selftests = ["log_check.py", "verbatim_gate.py", "review_check.py", "evd_check.py",
    "evd_ui_check.py", "dor_check.py", "comment_check.py", "schedule_check.py", "lib/ctx.py"];
  let stFail = 0;
  for (const s of selftests) {
    const r = spawnSync("python3", [path.join(root, ".vteam/scripts", s), "--selftest"],
      { cwd: root, encoding: "utf8" });
    if (r.status !== 0) { bad(`selftest RED: ${s}\n${(r.stdout + r.stderr).trim()}`); stFail++; }
  }
  if (!stFail) ok(`gate selftests green (${selftests.length} gates prove they can red)`);

  // 6. provider preflight
  console.log("── preflight ──");
  const pf = spawnSync("bash", [path.join(root, ".vteam/scripts/preflight.sh"),
    ...(flags.backend ? ["--backend"] : [])], { cwd: root, stdio: "inherit" });
  if (pf.status !== 0) miss++;

  if (flags.migrate) {
    warn("--migrate (legacy sentinel rewriter) ships with the dogfood milestone — not yet implemented");
  }

  process.exit(miss ? 1 : 0);
}
