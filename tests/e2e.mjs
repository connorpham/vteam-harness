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
import { discoverSelftests } from "../src/cli/doctor.mjs";

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
function freshRepo(name, { srcFile = true } = {}) {
  const dir = path.join(TMP, name);
  fs.mkdirSync(dir, { recursive: true });
  run("git", ["init", "-q", "-b", "main", dir]);
  run("git", ["-C", dir, "config", "user.email", "e2e@test"]);
  run("git", ["-C", dir, "config", "user.name", "e2e"]);
  fs.writeFileSync(path.join(dir, "README.md"), "# fixture\n");
  if (srcFile) { // real source so init's code_paths derivation has something to find
    fs.mkdirSync(path.join(dir, "src"));
    fs.writeFileSync(path.join(dir, "src", "index.js"), "export const fixture = true;\n");
  }
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
  // rendered skills carry no unresolved template vars — all 7 groups render() substitutes
  let unresolved = [];
  const skills = path.join(repo, ".claude", "skills");
  for (const d of fs.readdirSync(skills)) {
    const t = fs.readFileSync(path.join(skills, d, "SKILL.md"), "utf8");
    const m = t.match(/\{(paths|project|team|review|git|stack|autonomy)\.[a-z_]+\}/g);
    if (m) unresolved.push(`${d}: ${m.join(", ")}`);
  }
  check("no unresolved {vars} in rendered skills", unresolved.length === 0, unresolved.join("\n"));
  const cfgText = fs.readFileSync(path.join(repo, "vteam.config.yaml"), "utf8");
  check("config carries the chosen key", /key: DEMO/.test(cfgText));
  check("code_paths derived from the repo's real src/", /code_paths: \[src\/\]/.test(cfgText),
    cfgText.match(/code_paths.*$/m)?.[0]);
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

// ── 2b. src-less repo: honest [] — init warns, doctor warns, fence fails closed ─
console.log("2b. src-less repo: code_paths [] is a WARN, and the fence fails CLOSED");
{
  const dir = freshRepo("t2b", { srcFile: false });
  const r = vteam(dir, ...INIT_FLAGS);
  check("init exits 0 on a src-less repo", r.status === 0, r.stdout + r.stderr);
  check("init warns LOUDLY that derivation found nothing",
    /could not derive code_paths/.test(r.stdout + r.stderr), r.stdout + r.stderr);
  check("config carries an honest code_paths: [] (never invented paths)",
    /code_paths: \[\]/.test(fs.readFileSync(path.join(dir, "vteam.config.yaml"), "utf8")),
    fs.readFileSync(path.join(dir, "vteam.config.yaml"), "utf8").match(/code_paths.*$/m)?.[0]);
  const d = vteam(dir, "doctor");
  check("doctor exits 0 — an honest unknown WARNS, it does not red", d.status === 0,
    d.stdout + d.stderr);
  check("doctor's warn names the fix (set git.code_paths)",
    /code_paths is empty[\s\S]*set git\.code_paths/.test(d.stdout), d.stdout);
  // fail closed: with [] EVERY path is product code — code on a non-ticket
  // branch is refused, never silently waved through an open fence
  run("git", ["-C", dir, "add", "-A"]);
  run("git", ["-C", dir, "commit", "-qm", "install vteam"]);
  run("git", ["-C", dir, "checkout", "-qb", "just-a-branch"]);
  fs.writeFileSync(path.join(dir, "tool.py"), "print('product code')\n");
  run("git", ["-C", dir, "add", "-A"]);
  run("git", ["-C", dir, "commit", "-qm", "code without a ticket"]);
  const p = run("git", ["-C", dir, "push", "origin", "just-a-branch"]);
  check("push of product code on a non-ticket branch REFUSED (fail closed)",
    p.status !== 0 && /does not match/.test(p.stdout + p.stderr), p.stdout + p.stderr);
  check("fence says WHY it failed closed",
    /FAILING CLOSED: treating EVERY path as product code/.test(p.stdout + p.stderr),
    p.stdout + p.stderr);
}

// ── 3. every installed gate selftest passes from the target repo ────────────
// The list is DISCOVERED with doctor's own helper (any .vteam/scripts *.py/*.sh/*.mjs
// carrying --selftest, interpreter by extension) — one home, counts cannot drift.
console.log("3. installed gate selftests (discovered — mirrors doctor)");
{
  const dir = path.join(repo, ".vteam", "scripts");
  const gates = discoverSelftests(dir);
  check("discovery finds the full battery (≥ 15, spanning py+sh+mjs)",
    gates.length >= 15 && ["python3", "bash", "node"].every((c) => gates.some((g) => g.cmd === c)),
    JSON.stringify(gates));
  for (const { s, cmd } of gates) {
    const r = run(cmd, [path.join(dir, s), "--selftest"], { cwd: repo });
    check(`selftest ${s}`, r.status === 0, r.stdout + r.stderr);
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

// ── 16. team.size > 1: the Actor column is machinery, not prose ──────────────
console.log("16. team accountability — actor column, migrate, per-person report");
{
  // fresh installs ship the v2 header (actor costs a solo owner nothing)
  const tpl = fs.readFileSync(path.join(repo, "docs", "pm", "log.md"), "utf8");
  check("fresh ledger header carries Actor", /\| Date \| Lane \| Actor \|/.test(tpl), tpl.slice(0, 200));
  {
    const gat = fs.existsSync(path.join(repo, ".gitattributes"))
      ? fs.readFileSync(path.join(repo, ".gitattributes"), "utf8") : "";
    check("init wrote union-merge attributes for ALL append-only shared files (ledger, hatch-log, KB, known-issues)",
      /docs\/pm\/log\.md merge=union/.test(gat) &&
      /hatch-log\.md merge=union/.test(gat) &&
      /knowledge-base\.md merge=union/.test(gat) &&
      /known-issues\.md merge=union/.test(gat), gat);
    check("decisions.md is deliberately NOT union-merged (in-place status edits need real conflict resolution)",
      !/decisions\.md merge=union/.test(gat), gat);
  }

  // union merge PROVEN, not promised: two humans append to the same knowledge
  // file on parallel branches; the merge must land clean with BOTH lines.
  {
    // both "humans" branch from the SAME baseline commit (t1's main never had
    // the install committed — going through it would sweep docs/qa off disk)
    const dir = repo;
    run("git", ["-C", dir, "add", "-A"]);
    run("git", ["-C", dir, "commit", "-qm", "baseline for union proof"]);
    const base = run("git", ["-C", dir, "rev-parse", "HEAD"]).stdout.trim();
    const kb = path.join(dir, "docs", "qa", "knowledge-base.md");
    run("git", ["-C", dir, "checkout", "-qb", "human-a", base]);
    fs.appendFileSync(kb, "\n- lesson from A: retry the flaky webhook test\n");
    run("git", ["-C", dir, "commit", "-aqm", "A lesson"]);
    run("git", ["-C", dir, "checkout", "-qb", "human-b", base]);
    fs.appendFileSync(kb, "\n- lesson from B: seed the db before e2e\n");
    run("git", ["-C", dir, "commit", "-aqm", "B lesson"]);
    const mg = run("git", ["-C", dir, "merge", "--no-edit", "human-a"]);
    const merged = fs.readFileSync(kb, "utf8");
    check("two humans appending the same KB file merge WITHOUT conflict (union)",
      mg.status === 0 && merged.includes("lesson from A") && merged.includes("lesson from B"),
      mg.stdout + mg.stderr);
  }

  // a real 2-human repo with a legacy ledger: red → migrate → green → per-person
  const dir = freshRepo("t16");
  const r0 = vteam(dir, "init", "--yes", "--key", "TT", "--tracker", "markdown",
    "--design", "none", "--profile", "generic", "--tools", "claude-code");
  check("init exits 0", r0.status === 0, r0.stdout + r0.stderr);
  fs.writeFileSync(path.join(dir, "vteam.config.yaml"),
    fs.readFileSync(path.join(dir, "vteam.config.yaml"), "utf8").replace("size: 1", "size: 2"));
  fs.writeFileSync(path.join(dir, "docs", "pm", "log.md"),
    "# Dispatch ledger\n\n| Date | Lane | Item | Result | Link |\n|---|---|---|---|---|\n" +
    "| 2026-12-01 | DEV | TT-1 | done (workhorse) · tok ≈ 90k | PR #1 |\n");
  const red = run("python3", [path.join(dir, ".vteam", "scripts", "log_check.py")], { cwd: dir });
  check("legacy ledger + team.size 2 → log_check RED naming the Actor column",
    red.status === 1 && /Actor column/.test(red.stdout), red.stdout + red.stderr);
  const mig = vteam(dir, "doctor", "--migrate", "--apply");
  check("doctor --migrate --apply rewrites the ledger", mig.status === 0 || /APPLIED/.test(mig.stdout),
    mig.stdout + mig.stderr);
  const green = run("python3", [path.join(dir, ".vteam", "scripts", "log_check.py")], { cwd: dir });
  check("migrated ledger is green (legacy rows carry — )", green.status === 0,
    green.stdout + green.stderr);
  fs.appendFileSync(path.join(dir, "docs", "pm", "log.md"),
    "| 2026-12-02 | DEV | An | TT-2 | done (frontier) · tok ≈ 200k | PR #2 |\n");
  const pr = run("python3", [path.join(dir, ".vteam", "scripts", "perf_report.py")], { cwd: dir });
  check("perf_report groups by person and attributes the frontier flag",
    /Who did what \(by person\)/.test(pr.stdout) && /\| An \|/.test(pr.stdout) &&
    /An.*frontier/.test(pr.stdout), pr.stdout.slice(0, 600));
  check("the per-person table ships the never-reads-chat honesty note",
    /never reads anyone's chat/.test(pr.stdout));
  // board rollup
  const probe16 = `
    import { createServer } from ${JSON.stringify(path.join(PKG, "src", "cli", "board.mjs"))};
    import http from "node:http";
    const srv = createServer(process.cwd());
    await new Promise((d) => srv.listen(0, "127.0.0.1", d));
    const port = srv.address().port;
    const body = await new Promise((res, rej) => {
      http.get({ host: "127.0.0.1", port, path: "/api/state" }, (x) => {
        let b = ""; x.on("data", (d) => b += d); x.on("end", () => res(b));
      }).on("error", rej);
    });
    await new Promise((d) => srv.close(d));
    console.log(JSON.stringify(JSON.parse(body).ledger.by_actor));
  `;
  const bp = run("node", ["--input-type=module", "-e", probe16], { cwd: dir });
  let ba = null;
  try { ba = JSON.parse(String(bp.stdout).trim().split("\n").pop()); } catch { /* below */ }
  check("board rolls the ledger up by actor", !!ba && ba["An"] && ba["An"].items === 1 &&
    ba["—"] && ba["—"].items === 1, bp.stdout + bp.stderr);
}

// ── 17. graph: the implicit work graph, made visible (reports, never gates) ──
console.log("17. graph — the work graph made visible");
{
  const st = run("node", [path.join(PKG, "src", "cli", "graph.mjs"), "--selftest"]);
  check("graph --selftest green (ready/dangling/cycle/verdict + 9 mutations red)", st.status === 0,
    st.stdout + st.stderr);

  // a real chain in the installed t1 repo: DEMO-1 Done → DEMO-2 ready → DEMO-3 blocked + dangling
  const bl = path.join(repo, "docs", "backlog");
  fs.writeFileSync(path.join(bl, "DEMO-1.md"), "# DEMO-1: schema\n- status: Done\n");
  // a Done ticket needs its QA verdict or graph_check (correctly) reds MAST 1.2
  fs.mkdirSync(path.join(repo, "evd", "DEMO-1"), { recursive: true });
  fs.writeFileSync(path.join(repo, "evd", "DEMO-1", "REPORT.md"),
    "# Verification report DEMO-1 — PASS\nCOMMIT: deadbeef\nVERIFIED-AT: 2026-01-02T10:00:00+00:00\n");
  fs.writeFileSync(path.join(bl, "DEMO-2.md"), "# DEMO-2: api\n- status: To Do\n- blocked-by: DEMO-1\n");
  fs.writeFileSync(path.join(bl, "DEMO-3.md"), "# DEMO-3: ui\n- status: To Do\n- blocked-by: DEMO-2, GHOST-9\n");

  const g = vteam(repo, "graph", "--json");
  check("graph --json exits 0 (a mirror never fails the build)", g.status === 0, g.stdout + g.stderr);
  let m = null;
  try { m = JSON.parse(g.stdout); } catch { /* reported below */ }
  check("graph --json is valid JSON on stdout", m !== null, g.stdout.slice(0, 400));
  check("ready is machine-computed, not guessed",
    !!m && m.nodes.filter((x) => x.ready === true).map((x) => x.key).join() === "DEMO-2",
    JSON.stringify(m && m.nodes.map((x) => [x.key, x.ready])));
  check("dangling blocked-by is a loud finding",
    !!m && m.findings.dangling.length === 1 && m.findings.dangling[0].to === "GHOST-9",
    JSON.stringify(m && m.findings));
  check("--json is byte-stable on one commit (no timestamp)",
    vteam(repo, "graph", "--json").stdout === g.stdout);

  const d = vteam(repo, "graph", "--dot");
  check("graph --dot emits a digraph", d.status === 0 && /^digraph vteam_graph \{/.test(d.stdout) &&
    d.stdout.trimEnd().endsWith("}"), d.stdout.slice(0, 300));

  const h = vteam(repo, "graph");
  check("graph human report names its sources and exits 0",
    h.status === 0 && /── READY/.test(h.stdout) && /docs\/backlog\/<KEY>\.md/.test(h.stdout),
    h.stdout.slice(0, 600));

  // and the GATE sees the same dangling edge as a failure (mirror vs gate)
  const gc = run("python3", [path.join(repo, ".vteam", "scripts", "graph_check.py")], { cwd: repo });
  check("graph_check (the gate) reds the same dangling edge the mirror reported",
    gc.status === 1 && /GHOST-9/.test(gc.stdout), gc.stdout + gc.stderr);
  fs.unlinkSync(path.join(bl, "DEMO-3.md"));
  const gc2 = run("python3", [path.join(repo, ".vteam", "scripts", "graph_check.py")], { cwd: repo });
  check("dropping the bad edge turns the gate green", gc2.status === 0, gc2.stdout + gc2.stderr);
}

// ── 18. measured usage: session logs → vteam usage → perf_report merge ──────
// The chain the team-accountability promise stands on: the agent CLI's own
// logs (ground truth) → `usage --json/--sync` (per person, counts only) →
// perf_report putting claimed `tok ≈` next to measured. Both cross-check
// flags are proven to fire AND to stay quiet on an honest history.
console.log("18. measured usage history (vteam usage + perf_report merge)");
{
  const repo18 = freshRepo("t18");
  vteam(repo18, ...INIT_FLAGS);
  // usage resolves the root via git, which returns the REAL path (/private/var
  // on macOS, not the /var symlink) — the fixture logs must be keyed the same way
  const realRepo18 = fs.realpathSync(repo18);
  const claudeDir = path.join(TMP, "t18-claude");
  const codexDir = path.join(TMP, "t18-codex");
  const proj = path.join(claudeDir, "projects", realRepo18.replace(/[^A-Za-z0-9]/g, "-"));
  fs.mkdirSync(proj, { recursive: true });
  const asst = (id, out, ts) => JSON.stringify({
    type: "assistant", requestId: `r-${id}`, timestamp: ts, gitBranch: "main",
    message: { id, model: "claude-fable-5", usage: { input_tokens: 100,
      cache_read_input_tokens: 5000, cache_creation_input_tokens: 50, output_tokens: out } } });
  fs.writeFileSync(path.join(proj, "sess1.jsonl"), [
    asst("a1", 40000, "2026-08-10T02:00:00Z"),
    asst("a1", 40000, "2026-08-10T02:00:01Z"), // same message, second content block
    asst("a2", 30000, "2026-08-10T03:00:00Z"),
  ].join("\n"));
  const cxd = path.join(codexDir, "sessions", "2026", "08", "11");
  fs.mkdirSync(cxd, { recursive: true });
  fs.writeFileSync(path.join(cxd, "rollout-x.jsonl"), [
    JSON.stringify({ type: "session_meta", payload: { cwd: realRepo18, timestamp: "2026-08-11T05:00:00Z" } }),
    JSON.stringify({ type: "turn_context", payload: { model: "gpt-5.5" } }),
    JSON.stringify({ type: "event_msg", timestamp: "2026-08-11T05:02:00Z",
      payload: { type: "token_count", info: { last_token_usage:
        { input_tokens: 2000, cached_input_tokens: 1500, output_tokens: 500 } } } }),
  ].join("\n"));
  const env18 = { ...ENV, CLAUDE_CONFIG_DIR: claudeDir, CODEX_HOME: codexDir, VTEAM_ACTOR: "An Nguyen" };
  const u18 = (...a) => run("node", [CLI, "usage", ...a], { cwd: repo18, env: env18 });

  const st = u18("--selftest");
  check("usage --selftest is green", st.status === 0 && /selftest: OK/.test(st.stdout), st.stdout + st.stderr);

  let j = JSON.parse(u18("--json", "--since", "2026-08-01").stdout);
  check("both sources are read: fable-5 (claude) and gpt-5.5 (codex)",
    j.models.map((m) => m.model).sort().join() === "claude-fable-5,gpt-5.5", JSON.stringify(j.models));
  check("duplicate content-block lines count ONCE (2 msgs, 70k out, not 3/110k)",
    j.models.find((m) => m.model === "claude-fable-5").msgs === 2 &&
    j.models.find((m) => m.model === "claude-fable-5").output === 70000, JSON.stringify(j.models));
  check("70k-output day with an empty ledger is flagged as unlogged work",
    j.cross_check.flags.some((f) => f.includes("2026-08-10") && f.includes("no row")),
    JSON.stringify(j.cross_check));

  // an honest ledger clears the flag; a done row on a sessionless day raises the other one
  fs.writeFileSync(path.join(repo18, "docs", "pm", "log.md"), [
    "| Date | Lane | Actor | Item | Result | Link |", "|---|---|---|---|---|---|",
    "| 2026-08-10 | DEV | An Nguyen | DEMO-1 | done · tok ≈ 60k | PR #1 |",
    "| 2026-08-15 | DEV | An Nguyen | DEMO-2 | done · tok ≈ 40k | PR #2 |",
    "| 2026-08-11 | QA | Binh | DEMO-1 | done · tok ≈ 9k | DEMO-1 |", ""].join("\n"));
  j = JSON.parse(u18("--json", "--since", "2026-08-01").stdout);
  check("logged day no longer flagged; done-day-without-session now is",
    !j.cross_check.flags.some((f) => f.includes("2026-08-10")) &&
    j.cross_check.flags.some((f) => f.includes("2026-08-15") && f.includes("NO AI session")),
    JSON.stringify(j.cross_check.flags));

  const sy = u18("--sync", "--since", "2026-08-01");
  const syncFile = path.join(repo18, "docs", "pm", "usage", "an-nguyen.md");
  check("--sync writes one file per person under docs/pm/usage/",
    sy.status === 0 && fs.existsSync(syncFile), sy.stdout + sy.stderr);
  const body1 = fs.readFileSync(syncFile, "utf8");
  u18("--sync", "--since", "2026-08-01");
  check("sync is idempotent (re-run writes byte-identical content)",
    fs.readFileSync(syncFile, "utf8") === body1);
  check("sync file carries ACTOR, the daily table and the honesty boundary",
    /^ACTOR: An Nguyen$/m.test(body1) &&
    /\| 2026-08-10 \| claude \| claude-fable-5 \| 1 \| 2 \| 200 \| 10000 \| 100 \| 70000 \|/.test(body1) &&
    /NEVER chat content/.test(body1), body1.slice(0, 700));

  const pr = run("python3", [path.join(repo18, ".vteam", "scripts", "perf_report.py")], { cwd: repo18 });
  check("perf_report merges the synced file: person × model measured row",
    pr.status === 0 && /\| An Nguyen \| claude \| claude-fable-5 \| 1 \| 2 \| 0k \| 10k \| 70k \|/.test(pr.stdout),
    pr.stdout.slice(-1500));
  check("claimed tok ≈ sits NEXT TO measured, per person",
    /An Nguyen\*\*: claimed `tok ≈` 100k · measured in\+out 71k/.test(pr.stdout), pr.stdout.slice(-1500));
  check("a person with ledger rows but no synced file is named",
    /\*\*Binh\*\* has ledger rows but NO synced usage file/.test(pr.stdout), pr.stdout.slice(-1500));
}

// ── 19. checkpoint and resume — ticket crash recovery ─────────────────────
// When /dev crashes mid-work, the ticket is partially done. Checkpoint saves
// progress ({completed_lanes, next_lane, code_sha}). Resume reads it and tells
// PM what lanes to skip, recovering without re-doing earlier work.
console.log("19. checkpoint-resume — ticket recovery (fixture crash → resume)");
{
  const repo19 = freshRepo("t19");
  vteam(repo19, ...INIT_FLAGS);
  const evdRel = "evd";  // matches vteam.config.yaml default: paths.evidence: evd
  fs.mkdirSync(path.join(repo19, evdRel, "DEMO-1"), { recursive: true });

  // Simulate lane progress: DEMO-1 completed [plan, dor, dev], ready for qa
  const checkpoint = {
    ticket: "DEMO-1",
    completed_lanes: ["plan", "dor", "dev"],
    next_lane: "qa",
    code_sha: "abc12345",
    saved_at: "2026-08-24T12:00:00Z",
  };
  fs.writeFileSync(path.join(repo19, evdRel, "DEMO-1", ".checkpoint"),
    JSON.stringify(checkpoint, null, 2));

  // vteam resume reads checkpoint and prints next lane
  const res = vteam(repo19, "resume", "DEMO-1");
  check("resume exits 0", res.status === 0, res.stderr);
  check("resume names completed lanes", /plan.*dor.*dev/.test(res.stdout), res.stdout);
  check("resume names next lane (qa)", /qa/.test(res.stdout), res.stdout);
  check("resume shows code sha", /abc1234/.test(res.stdout), res.stdout);

  // vteam checkpoint query reads the same
  const q = vteam(repo19, "checkpoint", "query", "DEMO-1");
  check("checkpoint query exits 0", q.status === 0, q.stderr);
  check("checkpoint query repeats the message", /DEMO-1.*qa/.test(q.stdout), q.stdout);

  // vteam checkpoint save overwrites deterministically (idempotent)
  const save1 = vteam(repo19, "checkpoint", "save", "DEMO-1", "dev");
  const cp1 = fs.readFileSync(path.join(repo19, evdRel, "DEMO-1", ".checkpoint"), "utf8");
  const save2 = vteam(repo19, "checkpoint", "save", "DEMO-1", "dev");
  const cp2 = fs.readFileSync(path.join(repo19, evdRel, "DEMO-1", ".checkpoint"), "utf8");
  check("checkpoint save is idempotent", cp1 === cp2, `save1:\n${cp1}\nsave2:\n${cp2}`);

  // resume fails loudly when checkpoint missing
  const nocp = vteam(repo19, "resume", "DEMO-2");
  check("resume exits 1 when checkpoint missing", nocp.status === 1, nocp.stderr);
  check("resume error message is specific", /no checkpoint/.test(nocp.stderr), nocp.stderr);

  // vteam checkpoint save writes a file; query reads it back
  vteam(repo19, "checkpoint", "save", "DEMO-1", "qa");
  const qfinal = vteam(repo19, "checkpoint", "query", "DEMO-1");
  check("after save, query reflects new lane", /qa/.test(qfinal.stdout), qfinal.stdout);
}

console.log(`\n${failed === 0 ? "E2E: GREEN" : "E2E: RED"} — ${n - failed}/${n} checks passed`);
process.exit(failed === 0 ? 0 : 1);
