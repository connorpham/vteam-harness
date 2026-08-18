#!/usr/bin/env node
// e2e.mjs — the end-to-end proof behind "Working and end-to-end tested":
// a fresh repo → init → doctor GREEN, plus the promises around it (nothing
// written on invalid input, re-init never clobbers, update preserves user
// files via the manifest, clean failures outside git / without a TTY).
//
// Zero dependencies. Run: node tests/e2e.mjs   (also `npm test`).
// Each case runs in its own temp dir; the suite exits non-zero on the first
// hard failure and prints a one-line verdict per case.
import { spawnSync } from "node:child_process";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { fileURLToPath } from "node:url";

const PKG = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const CLI = path.join(PKG, "bin", "vteam.mjs");
const TMP = fs.mkdtempSync(path.join(os.tmpdir(), "vteam-e2e-"));
process.on("exit", () => fs.rmSync(TMP, { recursive: true, force: true }));

// a stub `gh` so the preflight hosting-CLI leg is deterministic on machines/CI
// where gh is missing or unauthenticated (we test vteam, not GitHub's CLI)
const BIN = path.join(TMP, "bin");
fs.mkdirSync(BIN);
fs.writeFileSync(path.join(BIN, "gh"), "#!/bin/sh\nexit 0\n");
fs.chmodSync(path.join(BIN, "gh"), 0o755);
const ENV = { ...process.env, PATH: `${BIN}:${process.env.PATH}` };

let n = 0, failed = 0;
function check(name, cond, detail = "") {
  n++;
  if (cond) { console.log(`  ✅ ${name}`); return true; }
  failed++;
  console.log(`  ❌ ${name}${detail ? `\n     ${String(detail).split("\n").join("\n     ")}` : ""}`);
  return false;
}
function run(cmd, args, opts = {}) {
  return spawnSync(cmd, args, { encoding: "utf8", env: ENV, timeout: 120_000, ...opts });
}
function vteam(cwd, ...args) { return run("node", [CLI, ...args], { cwd }); }
function freshRepo(name) {
  const dir = path.join(TMP, name);
  fs.mkdirSync(dir, { recursive: true });
  run("git", ["init", "-q", "-b", "main", dir]);
  run("git", ["-C", dir, "config", "user.email", "e2e@test"]);
  run("git", ["-C", dir, "config", "user.name", "e2e"]);
  fs.writeFileSync(path.join(dir, "README.md"), "# fixture\n");
  run("git", ["-C", dir, "add", "-A"]);
  run("git", ["-C", dir, "commit", "-qm", "init"]);
  // a local bare origin so the preflight git leg has something real to ping
  const bare = path.join(TMP, `${name}-origin.git`);
  run("git", ["init", "-q", "--bare", bare]);
  run("git", ["-C", dir, "remote", "add", "origin", bare]);
  return dir;
}
const INIT_FLAGS = ["init", "--yes", "--name", "Demo", "--key", "DEMO",
  "--language", "en", "--profile", "generic", "--tracker", "markdown",
  "--design", "none", "--autonomy", "assisted", "--tools", "claude-code"];

// ── 1. fresh install: the headline path ─────────────────────────────────────
console.log("1. fresh repo → init --yes");
const repo = freshRepo("t1");
{
  const r = vteam(repo, ...INIT_FLAGS);
  check("init exits 0", r.status === 0, r.stdout + r.stderr);
  for (const f of ["vteam.config.yaml", ".vteam/scripts/gate.py", ".vteam/manifest.json",
    ".vteam/scripts/lib/ctx.py", ".vteam/scripts/lib/ctx.mjs", ".vteam/scripts/lib/ctx.sh",
    ".claude/skills/team/SKILL.md", ".githooks/pre-push",
    ".github/workflows/vteam-gate.yml", "docs/pm/log.md", "docs/backlog/.gitkeep"]) {
    check(`created ${f}`, fs.existsSync(path.join(repo, f)));
  }
  const gi = fs.readFileSync(path.join(repo, ".gitignore"), "utf8");
  check(".gitignore covers .env (tokens never commit)", /^\.env$/m.test(gi), gi);
  // rendered skills carry no unresolved template vars
  let unresolved = [];
  const skills = path.join(repo, ".claude", "skills");
  for (const d of fs.readdirSync(skills)) {
    const t = fs.readFileSync(path.join(skills, d, "SKILL.md"), "utf8");
    const m = t.match(/\{(paths|project|team|review|git|stack)\.[a-z_]+\}/g);
    if (m) unresolved.push(`${d}: ${m.join(", ")}`);
  }
  check("no unresolved {vars} in rendered skills", unresolved.length === 0, unresolved.join("\n"));
  const cfgText = fs.readFileSync(path.join(repo, "vteam.config.yaml"), "utf8");
  check("config carries the chosen key", /key: DEMO/.test(cfgText));
}

// ── 2. doctor GREEN on that fresh install ───────────────────────────────────
console.log("2. doctor on the fresh install");
{
  const r = vteam(repo, "doctor");
  check("doctor exits 0 (init → doctor green, the README claim)", r.status === 0,
    r.stdout + r.stderr);
  check("doctor verified the manifest", /manifest verified/.test(r.stdout), r.stdout);
  check("doctor ran the selftests", /gate selftests green/.test(r.stdout), r.stdout);
}

// ── 3. every installed gate selftest passes from the target repo ────────────
console.log("3. installed gate selftests");
{
  const dir = path.join(repo, ".vteam", "scripts");
  const py = fs.readdirSync(dir).filter((f) => f.endsWith(".py"));
  for (const f of py) {
    const src = fs.readFileSync(path.join(dir, f), "utf8");
    if (!src.includes("--selftest")) continue;
    const r = run("python3", [path.join(dir, f), "--selftest"], { cwd: repo });
    check(`selftest ${f}`, r.status === 0, r.stdout + r.stderr);
  }
  for (const [cmd, f] of [["bash", "docs_shrink_check.sh"], ["bash", "lib/ctx.sh"], ["node", "lib/ctx.mjs"]]) {
    const r = run(cmd, [path.join(dir, f), "--selftest"], { cwd: repo });
    check(`selftest ${f}`, r.status === 0, r.stdout + r.stderr);
  }
}

// ── 4. re-init refuses to clobber an edited install ─────────────────────────
console.log("4. re-init keeps user edits");
{
  const cfgFile = path.join(repo, "vteam.config.yaml");
  const edited = fs.readFileSync(cfgFile, "utf8").replace("name: 'Demo'", "name: 'Demo Edited'");
  fs.writeFileSync(cfgFile, edited);
  const r = vteam(repo, ...INIT_FLAGS);
  check("second init refuses (config exists)", r.status === 1, r.stdout + r.stderr);
  check("user's config edit survives", fs.readFileSync(cfgFile, "utf8").includes("Demo Edited"));
}

// ── 5. update: ledgers untouched, user-modified doctrine → .new ─────────────
console.log("5. update honors the manifest");
{
  const ledger = path.join(repo, "docs", "pm", "log.md");
  fs.appendFileSync(ledger, "\n2026-01-01 · T1 · RESULT: done · tok≈1k\n");
  const ledgerBefore = fs.readFileSync(ledger, "utf8");
  const opsFile = path.join(repo, "docs", "team", "ops.md");
  fs.appendFileSync(opsFile, "\nMY LOCAL RULE — do not lose this.\n");
  const opsBefore = fs.readFileSync(opsFile, "utf8");
  const r = vteam(repo, "update");
  check("update exits 0", r.status === 0, r.stdout + r.stderr);
  check("ledger untouched by update", fs.readFileSync(ledger, "utf8") === ledgerBefore);
  check("user-modified doctrine kept", fs.readFileSync(opsFile, "utf8") === opsBefore);
  check("new version parked as ops.md.new", fs.existsSync(`${opsFile}.new`), r.stdout);
  check("update reported the conflict", /ops\.md/.test(r.stdout), r.stdout);
}

// ── 6. invalid input writes NOTHING ──────────────────────────────────────────
console.log("6. invalid --profile: clean failure, zero writes");
{
  const dir = freshRepo("t6");
  const before = fs.readdirSync(dir).sort().join(",");
  const r = vteam(dir, "init", "--yes", "--profile", "bogus");
  check("exits 1", r.status === 1);
  check("names the valid values", /generic/.test(r.stdout + r.stderr), r.stdout + r.stderr);
  check("wrote nothing", fs.readdirSync(dir).sort().join(",") === before &&
    !fs.existsSync(path.join(dir, "vteam.config.yaml")));
}

// ── 7. outside git: one clean line, no crash ─────────────────────────────────
console.log("7. init outside a git repo");
{
  const dir = path.join(TMP, "t7-not-git");
  fs.mkdirSync(dir);
  const r = vteam(dir, "init", "--yes");
  check("exits non-zero", r.status !== 0);
  check("clean one-line diagnosis (no raw git stderr)",
    /not a git repository — run `git init`/.test(r.stdout + r.stderr) &&
    !/fatal:/.test(r.stdout + r.stderr), r.stdout + r.stderr);
}

// ── 8. non-TTY without --yes: fast clean error, never a hang ─────────────────
console.log("8. non-TTY init without --yes");
{
  const dir = freshRepo("t8");
  const r = run("node", [CLI, "init"], { cwd: dir, input: "" });
  check("exits non-zero fast", r.status !== 0 && r.signal === null, `status=${r.status} signal=${r.signal}`);
  check("says what to do", /non-interactive session: pass --yes/.test(r.stdout + r.stderr),
    r.stdout + r.stderr);
}

// ── 9. a second tool renders its native surface ──────────────────────────────
console.log("9. --tools cursor");
{
  const dir = freshRepo("t9");
  const r = vteam(dir, "init", "--yes", "--tools", "cursor", "--tracker", "markdown",
    "--design", "none", "--profile", "generic");
  check("init exits 0", r.status === 0, r.stdout + r.stderr);
  const cursorDir = path.join(dir, ".cursor");
  check(".cursor/ output exists", fs.existsSync(cursorDir),
    fs.readdirSync(dir).join(","));
}

// ── 10. the pre-push fence goes RED for real (live-environment gate) ─────────
console.log("10. pre-push fence + secret scan");
{
  // direct push to the protected branch is refused…
  const r1 = run("git", ["-C", repo, "push", "origin", "main"]);
  check("push to protected main refused", r1.status !== 0 &&
    /No direct pushes/.test(r1.stdout + r1.stderr), r1.stdout + r1.stderr);
  // …and a branch carrying a token is refused BEFORE any hatch (fail closed)
  run("git", ["-C", repo, "checkout", "-qb", "feat/DEMO-1-leak"]);
  fs.writeFileSync(path.join(repo, "src.txt"),
    "token = ghp_" + "Abcdefghijklmnopqrstuvwxyz0123456789\n");
  run("git", ["-C", repo, "add", "-A"]);
  run("git", ["-C", repo, "commit", "-qm", "DEMO-1 leak fixture"]);
  const r2 = run("git", ["-C", repo, "push", "origin", "feat/DEMO-1-leak"]);
  check("secret in the outgoing diff refused", r2.status !== 0 &&
    /SECRET in the outgoing diff/.test(r2.stdout + r2.stderr), r2.stdout + r2.stderr);
}

console.log(`\n${failed === 0 ? "E2E: GREEN" : "E2E: RED"} — ${n - failed}/${n} checks passed`);
process.exit(failed === 0 ? 0 : 1);
