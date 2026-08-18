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

// ── 11. audit: the zero-commitment grader (works with AND without vteam) ─────
console.log("11. audit — grade with and without vteam installed");
{
  // installed repo (t1) scores high through the same rubric as everyone else
  const r1 = vteam(repo, "audit", "--json");
  check("audit --json exits 0", r1.status === 0, r1.stdout + r1.stderr);
  let a1 = null;
  try { a1 = JSON.parse(r1.stdout); } catch { /* checked below */ }
  check("audit --json is valid JSON on stdout", a1 !== null, r1.stdout.slice(0, 400));
  check("installed repo scores ≥ 70", a1 !== null && a1.score >= 70,
    JSON.stringify(a1?.dimensions ?? a1));
  check("dimensions carry the rubric shape", a1 !== null && Array.isArray(a1.dimensions) &&
    a1.dimensions.length === 6 && a1.dimensions.reduce((s, d) => s + d.max, 0) === 100 &&
    a1.dimensions.every((d) => d.name && "points" in d && "max" in d && d.fix &&
      Array.isArray(d.found) && Array.isArray(d.missing)), r1.stdout.slice(0, 400));
  // bare repo: the accountability gap in numbers
  const bare = path.join(TMP, "t11-bare");
  fs.mkdirSync(bare);
  run("git", ["init", "-q", "-b", "main", bare]);
  const r2 = vteam(bare, "audit", "--json");
  let a2 = null;
  try { a2 = JSON.parse(r2.stdout); } catch { /* checked below */ }
  check("bare repo scores < 30", r2.status === 0 && a2 !== null && a2.score < 30, r2.stdout);
  // human report prints the grade banner and the funnel
  const r3 = vteam(bare, "audit");
  check("terminal report prints the grade banner", r3.status === 0 &&
    /\/100 · grade/.test(r3.stdout), r3.stdout + r3.stderr);
  check("low score funnels to init", /vteam-harness init/.test(r3.stdout), r3.stdout);
  // the grader proves ITSELF: fixture ordering + manifest mutation red
  const st = run("node", [path.join(PKG, "src", "cli", "audit.mjs"), "--selftest"]);
  check("audit --selftest green", st.status === 0, st.stdout + st.stderr);
}

// ── 12. doctor --json: machine shape, same checks, same exit codes ───────────
console.log("12. doctor --json");
{
  const r = vteam(repo, "doctor", "--json");
  let d = null;
  try { d = JSON.parse(r.stdout); } catch { /* checked below */ }
  check("doctor --json is valid JSON on stdout (nothing else)", d !== null, r.stdout.slice(0, 400));
  check("doctor --json ok mirrors the exit code", d !== null && d.ok === (r.status === 0),
    `status=${r.status} ok=${d?.ok}`);
  check("checks carry name/status/detail", d !== null && Array.isArray(d.checks) &&
    d.checks.length > 0 && d.checks.every((c) => c.name && c.status && "detail" in c),
    r.stdout.slice(0, 400));
}

// ── 13. github tracker: installs, hints, and proves itself offline ───────────
console.log("13. init --tracker github");
{
  const dir = freshRepo("t13");
  const r = vteam(dir, "init", "--yes", "--tracker", "github", "--design", "none",
    "--profile", "generic", "--tools", "claude-code");
  check("init --tracker github exits 0", r.status === 0, r.stdout + r.stderr);
  check("github provider installed", fs.existsSync(
    path.join(dir, ".vteam", "providers", "tracker_github.py")));
  check("next steps mention GITHUB_TOKEN", /GITHUB_TOKEN/.test(r.stdout), r.stdout);
  const st = run("python3", [path.join(dir, ".vteam", "providers", "tracker_github.py"),
    "--selftest"], { cwd: dir });
  check("github provider --selftest green from the installed repo", st.status === 0,
    st.stdout + st.stderr);
}

// ── 14. SessionStart hook: wired on fresh install, merges without clobbering ─
console.log("14. SessionStart doctrine re-injection");
{
  check("t1 got the hook script",
    fs.existsSync(path.join(repo, ".claude", "hooks", "vteam-session-start.sh")));
  const s = JSON.parse(fs.readFileSync(path.join(repo, ".claude", "settings.json"), "utf8"));
  check("t1 settings.json carries the SessionStart entry",
    Array.isArray(s.hooks?.SessionStart) && s.hooks.SessionStart.some((e) =>
      e.hooks?.some((h) => String(h.command).includes("vteam-session-start"))),
    JSON.stringify(s).slice(0, 300));
  // pre-existing settings must survive the merge byte-meaningfully
  const dir = freshRepo("t14");
  const settings = path.join(dir, ".claude", "settings.json");
  fs.mkdirSync(path.dirname(settings), { recursive: true });
  fs.writeFileSync(settings, JSON.stringify({ env: { MY_VAR: "keep-me" },
    hooks: { PreToolUse: [{ matcher: "Bash", hooks: [] }] } }, null, 2));
  const r = vteam(dir, "init", "--yes", "--tracker", "markdown", "--design", "none",
    "--profile", "generic", "--tools", "claude-code");
  check("init over existing settings.json exits 0", r.status === 0, r.stdout + r.stderr);
  const merged = JSON.parse(fs.readFileSync(settings, "utf8"));
  check("user env survived the merge", merged.env?.MY_VAR === "keep-me",
    JSON.stringify(merged).slice(0, 300));
  check("user PreToolUse hook survived", Array.isArray(merged.hooks?.PreToolUse));
  check("SessionStart entry added alongside", Array.isArray(merged.hooks?.SessionStart) &&
    merged.hooks.SessionStart.length === 1);
  // hook script actually runs and echoes doctrine
  const hk = run("bash", [path.join(dir, ".claude", "hooks", "vteam-session-start.sh")],
    { cwd: dir, env: { ...ENV, CLAUDE_PROJECT_DIR: dir } });
  check("hook script runs and injects the non-negotiables", hk.status === 0 &&
    /gate|evidence|done/i.test(hk.stdout), hk.stdout + hk.stderr);
}

// ── 15. board: read-only dashboard over the proof trail ─────────────────────
console.log("15. board — read-only dashboard");
{
  const st = run("node", [path.join(PKG, "src", "cli", "board.mjs"), "--selftest"]);
  check("board --selftest green (parses + 405/404/warning mutations red)", st.status === 0,
    st.stdout + st.stderr);

  // boot the real board against the installed t1 repo on an ephemeral port and
  // probe it out-of-process: the routing table and the read-only fence, live.
  fs.writeFileSync(path.join(repo, "docs", "backlog", "DEMO-1.md"),
    "# DEMO-1: e2e ticket\n- status: In Progress\n- labels: e2e\n");
  const probe = `
    import http from "node:http";
    import { createServer } from ${JSON.stringify(path.join(PKG, "src", "cli", "board.mjs"))};
    const get = (port, p, method = "GET") => new Promise((res, rej) => {
      const r = http.request({ host: "127.0.0.1", port, path: p, method }, (x) => {
        let b = ""; x.setEncoding("utf8"); x.on("data", (d) => b += d);
        x.on("end", () => res({ status: x.statusCode, body: b }));
      }); r.on("error", rej); r.end();
    });
    const srv = createServer(process.cwd());
    await new Promise((d) => srv.listen(0, "127.0.0.1", d));
    const port = srv.address().port;
    const out = {
      bind: srv.address().address,
      page: (await get(port, "/")).status,
      state: await get(port, "/api/state"),
      post: (await get(port, "/api/state", "POST")).status,
      traversal: (await get(port, "/../etc/passwd")).status,
      dotenv: (await get(port, "/.env")).status,
    };
    out.state = { status: out.state.status, json: JSON.parse(out.state.body) };
    await new Promise((d) => srv.close(d));
    console.log(JSON.stringify(out));
  `;
  const p = run("node", ["--input-type=module", "-e", probe], { cwd: repo });
  let o = null;
  try { o = JSON.parse(String(p.stdout).trim().split("\n").pop()); } catch { /* reported below */ }
  if (check("board serves / and /api/state from an installed repo",
    !!o && o.page === 200 && o.state.status === 200, p.stdout + p.stderr)) {
    check("binds loopback only (private project data never hits the LAN)",
      o.bind === "127.0.0.1", o.bind);
    check("state reports the installed config (no env values)",
      o.state.json.config.key === "DEMO" && o.state.json.config.autonomy === "assisted" &&
      !JSON.stringify(o.state.json).includes("PATH="), JSON.stringify(o.state.json.config));
    check("state reads the markdown backlog", o.state.json.tickets.tickets.some((t) =>
      t.key === "DEMO-1" && t.status_category === "in_progress"),
      JSON.stringify(o.state.json.tickets));
    check("state names the ledger it read", o.state.json.ledger.source === "docs/pm/log.md" &&
      o.state.json.ledger.exists, JSON.stringify(o.state.json.ledger).slice(0, 200));
    check("no mutating endpoint: POST → 405", o.post === 405, String(o.post));
    check("no static serving: /../etc/passwd and /.env → 404",
      o.traversal === 404 && o.dotenv === 404, `${o.traversal} / ${o.dotenv}`);
    check("doctor panel is cache-only (the server runs nothing)",
      o.state.json.doctor.exists === false, JSON.stringify(o.state.json.doctor));
  }
}

console.log(`\n${failed === 0 ? "E2E: GREEN" : "E2E: RED"} — ${n - failed}/${n} checks passed`);
process.exit(failed === 0 ? 0 : 1);
