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
import { derivePort } from "../src/cli/init.mjs";

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
  // the fence blocks the very install commit — init must warn BEFORE the first
  // refused push, not let the error message be the tutorial (2026-08-24 review)
  check("init warns that the fence is live from the install commit on",
    /ALLOW_PUSH_MAIN=1/.test(r.stdout) && /PR/.test(r.stdout), r.stdout.slice(-500));
  for (const f of ["vteam.config.yaml", ".vteam/scripts/gate.py", ".vteam/manifest.json",
    ".vteam/scripts/lib/ctx.py", ".vteam/scripts/lib/ctx.mjs", ".vteam/scripts/lib/ctx.sh",
    ".claude/skills/team/SKILL.md", ".claude/agents/backend-specialist.md",
    ".githooks/pre-push",
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
  // The README states this count in prose, in the doctor transcript and in the
  // commands.svg alt text. Found stale (said 22, doctor ran 25) in the
  // 2026-09-03 review — same drift the "N checks" guard at the bottom exists
  // for. Every place that prints the number must agree with discovery.
  {
    // Three different phrasings state it, and before this guard existed the README
    // said 25 in two of them and 22 in the other four — at the same time.
    const readme = fs.readFileSync(path.join(PKG, "README.md"), "utf8");
    const claims = [
      ...readme.matchAll(/(\d+) (?:discovered )?(?:selftests|discovered checks)/g),
      ...readme.matchAll(/\((\d+) today\)/g),
    ].map((m) => Number(m[1]));
    check(`README's selftest count matches discovery (${gates.length})`,
      claims.length > 0 && claims.every((c) => c === gates.length),
      `README claims ${JSON.stringify(claims)}, discovery found ${gates.length}`);
  }
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

    // `owned`: a path this repo declares is never clobbered AND never parked — the
    // recurring `.new` chore was the whole reason for the field. Reviewed finding:
    // the first version only honoured the declaration once a file had diverged.
    const mfPath = path.join(repo, ".vteam", "manifest.json");
    const mf = JSON.parse(fs.readFileSync(mfPath, "utf8"));
    mf.owned = ["docs/team/ops.md"];
    fs.writeFileSync(mfPath, JSON.stringify(mf, null, 2) + "\n");
    fs.rmSync(`${opsFile}.new`, { force: true });
    const r2 = vteam(repo, "update");
    check("owned: update still exits 0", r2.status === 0, r2.stdout + r2.stderr);
    check("owned: the local file is kept", fs.readFileSync(opsFile, "utf8") === opsBefore);
    check("owned: nothing is parked", !fs.existsSync(`${opsFile}.new`), r2.stdout);
    check("owned: update says upstream moved", /OWNS/.test(r2.stdout), r2.stdout);

    // the IN-SYNC case: a declared-owned path that has not forked yet must not be
    // told it "matched no framework file". A reviewer found that warning firing in
    // the most ordinary steady state there is — and right after the hand merge the
    // whole feature exists for.
    const synced = path.join(repo, ".vteam", "profiles");
    const anyOwned = fs.existsSync(synced) ? "docs/team/raci.md" : "docs/team/raci.md";
    const mfS = JSON.parse(fs.readFileSync(mfPath, "utf8"));
    mfS.owned = [anyOwned];
    fs.writeFileSync(mfPath, JSON.stringify(mfS, null, 2) + "\n");
    const r4 = vteam(repo, "update");
    check("owned: an in-sync owned path is not called unmatched",
          !/matched no framework file/.test(r4.stdout), r4.stdout);

    // a malformed declaration is reported and IGNORED — never rewritten over the user
    const mf2 = JSON.parse(fs.readFileSync(mfPath, "utf8"));
    mf2.owned = "docs/team/ops.md";            // a string, not a list
    fs.writeFileSync(mfPath, JSON.stringify(mf2, null, 2) + "\n");
    const r3 = vteam(repo, "update");
    check("owned: a malformed declaration is reported", /must be a list/.test(r3.stdout), r3.stdout);
    check("owned: the malformed declaration is left alone",
          JSON.parse(fs.readFileSync(mfPath, "utf8")).owned === "docs/team/ops.md");
}

// ── 5b. update follows the CURRENT config + prunes orphans + guards agents ──
// VT-24 (2026-09-17 code review): three installer holes. A provider switched
// after init was unreachable (update only refreshed files already present, init
// refused because the config existed); files the package stopped shipping stayed
// on disk forever and dropped out of the manifest; packaged agents and the
// SessionStart hook were written OUTSIDE the manifest, so an upstream change
// never reached a consumer who was told "kept YOURS" about a file never touched.
console.log("5b. update: providers follow config, orphans pruned, agents manifest-guarded");
{
  const dir = freshRepo("t5b");
  const r0 = vteam(dir, ...INIT_FLAGS);
  check("init exits 0", r0.status === 0, r0.stdout + r0.stderr);

  // the gate on a fresh install is GREEN and now RUNS the stale-verdict step
  const g0 = run("bash", [path.join(dir, ".vteam", "scripts", "gate.sh")], { cwd: dir });
  check("gate.sh on a fresh install is GREEN", g0.status === 0 && /GATE: GREEN/.test(g0.stdout),
    g0.stdout.slice(-800) + g0.stderr);
  check("the context-budget step RAN as an advisory measurement and printed a lane total",
    /▶ context-budget:/.test(g0.stdout) && /= mandatory total/.test(g0.stdout) && /context_budget:|over budget/.test(g0.stdout),
    g0.stdout.slice(-1200));
  check("the stale-verdict step RAN (it was named by 5 workflows and wired into 0 profiles)",
    /▶ stale-verdict:/.test(g0.stdout) && /no stale verdicts|no evidence dirs with key/.test(g0.stdout), g0.stdout.slice(-800));
  // VT-39: the cost audit runs everywhere, and on a repo that never synced usage it says
  // so in ONE line and stays out of the way — a check that shouts at a new repo gets removed
  check("the cost step RAN and is quiet on a repo with no measured record",
    /▶ cost:/.test(g0.stdout) && /no measured record to audit against/.test(g0.stdout)
    && !/advisory cost: FAILED/.test(g0.stdout), g0.stdout.slice(-1200));

  // and preflight's driver probe no longer executes the whole gate
  const help = run("python3", [path.join(dir, ".vteam", "scripts", "gate.py"), "--help"], { cwd: dir });
  check("gate.py --help prints usage and runs NO step (preflight probed with it and ran the whole gate)",
    help.status === 0 && !/▶ /.test(help.stdout) && /Usage: gate\.py/.test(help.stdout), help.stdout.slice(0, 300));

  // E10: the gate's transcript also lands in a file, so a backgrounded run can never
  // block on an undrained pipe and a RED can be re-read after the terminal scrolled
  const tr = g0.stdout.match(/📝 transcript: (\S+)/);
  check("gate.sh names its transcript file and the file carries the GATE line",
    !!tr && fs.existsSync(tr[1]) && /GATE: GREEN/.test(fs.readFileSync(tr[1], "utf8")), g0.stdout.slice(-300));

  // VT-37: the graph computes the execution plan the PM lane used to derive in prose
  {
    const bl = path.join(dir, "docs", "backlog");
    fs.mkdirSync(bl, { recursive: true });
    fs.writeFileSync(path.join(bl, "DEMO-10.md"), "# DEMO-10: base\n- status: To Do\n");
    fs.writeFileSync(path.join(bl, "DEMO-11.md"), "# DEMO-11: next\n- status: To Do\n- blocked-by: DEMO-10\n");
    fs.writeFileSync(path.join(bl, "DEMO-12.md"), "# DEMO-12: other\n- status: To Do\n");
    for (const [k, scope] of [["DEMO-10", "src/a/"], ["DEMO-11", "src/b/"], ["DEMO-12", "src/c/"]]) {
      fs.mkdirSync(path.join(dir, "evd", k, "dev"), { recursive: true });
      fs.writeFileSync(path.join(dir, "evd", k, "dev", "tasksheet.md"), `# ${k}\nCODE-SCOPE: ${scope}\n`);
    }
    const pl = vteam(dir, "graph", "--plan", "--json");
    check("graph --plan exits 0 and parses", pl.status === 0 && !!JSON.parse(pl.stdout || "{}").waves,
      pl.stdout.slice(0, 300) + pl.stderr);
    const plan = JSON.parse(pl.stdout);
    const wave = (n) => (plan.waves.find((w) => w.level === n) || { batches: [] }).batches.flat().map((x) => x.key);
    check("a blocked-by edge becomes a LATER wave, not a blocker",
      wave(0).includes("DEMO-10") && wave(0).includes("DEMO-12") && wave(1).includes("DEMO-11"),
      JSON.stringify(plan.waves.map((w) => [w.level, w.batches.flat().map((x) => x.key)])));
    check("the plan names what it does NOT decide (the lane keeps the judgement calls)",
      Array.isArray(plan.decided_by_the_lane_not_here) && plan.decided_by_the_lane_not_here.length >= 2,
      JSON.stringify(plan.decided_by_the_lane_not_here));
    check("every wave-0 item carries the lane it is owed",
      plan.waves[0].batches.flat().every((x) => x.next_lane === "dev" || x.next_lane === "qa"),
      JSON.stringify(plan.waves[0].batches.flat().map((x) => [x.key, x.next_lane])));
    const human = vteam(dir, "graph", "--plan");
    check("graph --plan prints a human plan with the critical path",
      human.status === 0 && /EXECUTION PLAN/.test(human.stdout) && /CRITICAL PATH/.test(human.stdout),
      human.stdout.slice(0, 300));
    for (const k of ["DEMO-10", "DEMO-11", "DEMO-12"]) {
      fs.rmSync(path.join(bl, `${k}.md`), { force: true });
      fs.rmSync(path.join(dir, "evd", k), { recursive: true, force: true });
    }
  }

  // VT-36: the risk class is measured from the diff, and a docs-only change needs no
  // reviewer card — the fence stops charging a README typo what it charges a rewrite
  {
    const rc = (...a) => run("python3", [path.join(dir, ".vteam", "scripts", "review_check.py"), ...a], { cwd: dir });
    const cc = (...a) => run("python3", [path.join(dir, ".vteam", "scripts", "change_class.py"), ...a], { cwd: dir });
    // the install itself commits on main first — otherwise switching back would take
    // .vteam/ with it and every later check in this section would lose its runtime
    run("git", ["-C", dir, "add", "-A"]);
    run("git", ["-C", dir, "commit", "-qm", "chore: vteam init"]);
    run("git", ["-C", dir, "checkout", "-qb", "feat/DEMO-7-copy"]);
    fs.appendFileSync(path.join(dir, "README.md"), "\na documentation line\n");
    run("git", ["-C", dir, "add", "-A"]);
    run("git", ["-C", dir, "commit", "-qm", "docs(DEMO-7): a line"]);
    const cls = cc("--base", "main", "--sha", "HEAD");
    check("change_class calls a docs-only diff `docs`", /change-class: docs/.test(cls.stdout), cls.stdout + cls.stderr);
    const r = rc("DEMO-7", "--base", "main", "--sha", "HEAD");
    check("review_check needs NO dossier for a docs-only diff, and says why",
      r.status === 0 && /No reviewer card required/.test(r.stdout) && /change class `docs`/.test(r.stdout),
      r.stdout + r.stderr);

    // the knob is the whole reversal: one config line puts the uniform fence back
    const cfgPath = path.join(dir, "vteam.config.yaml");
    const cfg0 = fs.readFileSync(cfgPath, "utf8");
    fs.writeFileSync(cfgPath, cfg0.replace("proportional: true", "proportional: false"));
    const rOff = rc("DEMO-7", "--base", "main", "--sha", "HEAD");
    check("review.proportional: false restores the uniform fence on the same docs-only diff",
      rOff.status === 1 && /review\.md NOT in commit/.test(rOff.stdout), rOff.stdout + rOff.stderr);
    fs.writeFileSync(cfgPath, cfg0);

    // …and a code file's skeleton moving is `logic` again: two cards, three bullets
    fs.mkdirSync(path.join(dir, "src"), { recursive: true });
    fs.writeFileSync(path.join(dir, "src", "app.ts"), "export const MAX = 5;\n");
    run("git", ["-C", dir, "add", "-A"]);
    run("git", ["-C", dir, "commit", "-qm", "feat(DEMO-7): a constant"]);
    const cls2 = cc("--base", "main", "--sha", "HEAD");
    check("change_class calls a new code file `logic` (nothing to compare a skeleton against)",
      /change-class: logic/.test(cls2.stdout), cls2.stdout);
    const r2 = rc("DEMO-7", "--base", "main", "--sha", "HEAD");
    check("review_check demands the dossier again once code moves",
      r2.status === 1 && /review\.md NOT in commit/.test(r2.stdout), r2.stdout + r2.stderr);
    run("git", ["-C", dir, "checkout", "-q", "main"]);
  }

  // E1: a repo with NO origin remote is a legitimate local-only shape — preflight
  // says how push/PR change (local --no-ff merge, review_check by hand), it does not RED
  run("git", ["-C", dir, "remote", "remove", "origin"]);
  const pf = run("bash", [path.join(dir, ".vteam", "scripts", "preflight.sh")], { cwd: dir });
  check("preflight on a local-only repo (no origin) is GREEN and names the local-merge rule",
    pf.status === 0 && /⚠️\s+Git\s+no origin remote — local-only repo/.test(pf.stdout) && /PREFLIGHT: GREEN/.test(pf.stdout),
    pf.stdout.slice(-900) + pf.stderr.slice(-300));
  run("git", ["-C", dir, "remote", "add", "origin", path.join(TMP, "t5b-origin.git")]);

  // (a) provider follows the config: markdown → github after init
  const cfgF = path.join(dir, "vteam.config.yaml");
  fs.writeFileSync(cfgF, fs.readFileSync(cfgF, "utf8").replace("provider: markdown", "provider: github"));
  const r1 = vteam(dir, "update");
  const ghProv = path.join(dir, ".vteam", "providers", "tracker_github.py");
  check("update installs the provider the config names NOW", r1.status === 0 && fs.existsSync(ghProv),
    r1.stdout + r1.stderr);
  // switch back: the github provider is an orphan the framework no longer needs here
  fs.writeFileSync(cfgF, fs.readFileSync(cfgF, "utf8").replace("provider: github", "provider: markdown"));

  // (b) orphans: plant two files the "previous package" owned
  const mfPath = path.join(dir, ".vteam", "manifest.json");
  const mf = JSON.parse(fs.readFileSync(mfPath, "utf8"));
  const { createHash } = await import("node:crypto");
  const sha = (s) => createHash("sha256").update(s).digest("hex");
  fs.writeFileSync(path.join(dir, ".vteam", "scripts", "old_gate.py"), "# retired\n");
  mf.files[".vteam/scripts/old_gate.py"] = sha("# retired\n");            // unmodified orphan
  fs.writeFileSync(path.join(dir, ".vteam", "scripts", "old_edited.py"), "# user changed me\n");
  mf.files[".vteam/scripts/old_edited.py"] = sha("# what the package wrote\n"); // modified orphan
  fs.writeFileSync(path.join(dir, ".vteam", "scripts", "old_owned.py"), "# forked on purpose\n");
  mf.files[".vteam/scripts/old_owned.py"] = sha("# forked on purpose\n");
  mf.owned = [".vteam/scripts/old_owned.py"];                            // owned orphan
  fs.writeFileSync(mfPath, JSON.stringify(mf, null, 2) + "\n");
  const r2 = vteam(dir, "update");
  check("update exits 0 with orphans present", r2.status === 0, r2.stdout + r2.stderr);
  check("unmodified orphan REMOVED and reported",
    !fs.existsSync(path.join(dir, ".vteam", "scripts", "old_gate.py")) && /old_gate\.py/.test(r2.stdout), r2.stdout);
  check("modified orphan KEPT and reported (never deletes user work)",
    fs.existsSync(path.join(dir, ".vteam", "scripts", "old_edited.py")) && /KEPT[\s\S]*old_edited\.py/.test(r2.stdout), r2.stdout);
  check("owned orphan untouched", fs.existsSync(path.join(dir, ".vteam", "scripts", "old_owned.py")));
  check("switched-away provider pruned as an unmodified orphan", !fs.existsSync(ghProv), r2.stdout);
  const mf2 = JSON.parse(fs.readFileSync(mfPath, "utf8"));
  check("manifest no longer tracks the pruned/kept orphans, still tracks the owned one",
    !(".vteam/scripts/old_gate.py" in mf2.files) && !(".vteam/scripts/old_edited.py" in mf2.files) &&
    (".vteam/scripts/old_owned.py" in mf2.files), JSON.stringify(Object.keys(mf2.files).filter((k) => /old_/.test(k))));

  // (c) packaged agents + hook live in the manifest and obey it
  check("manifest records the packaged agents and both hooks (SessionStart + SessionEnd)",
    ".claude/agents/backend-specialist.md" in mf2.files && ".claude/hooks/vteam-session-start.sh" in mf2.files &&
    ".claude/hooks/vteam-session-end.sh" in mf2.files, Object.keys(mf2.files).filter((f) => f.includes("hooks")).join(","));
  const agent = path.join(dir, ".claude", "agents", "backend-specialist.md");
  const pkgAgent = fs.readFileSync(path.join(PKG, "core", "agents", "backend-specialist.md"), "utf8");
  // simulate "the package changed": pretend the framework last wrote a different body
  fs.writeFileSync(agent, pkgAgent + "\n<!-- older packaged text -->\n");
  const mf3 = JSON.parse(fs.readFileSync(mfPath, "utf8"));
  mf3.files[".claude/agents/backend-specialist.md"] = sha(pkgAgent + "\n<!-- older packaged text -->\n");
  fs.writeFileSync(mfPath, JSON.stringify(mf3, null, 2) + "\n");
  const r3 = vteam(dir, "update");
  check("an UNMODIFIED agent is refreshed to the new packaged text (was: kept forever)",
    r3.status === 0 && fs.readFileSync(agent, "utf8") === pkgAgent, r3.stdout);
  // and a user-edited agent is parked, not clobbered
  fs.writeFileSync(agent, pkgAgent + "\nMY LOCAL AGENT RULE\n");
  const r4 = vteam(dir, "update");
  check("a user-EDITED agent is kept and the new version parked as .new",
    r4.status === 0 && /MY LOCAL AGENT RULE/.test(fs.readFileSync(agent, "utf8")) &&
    fs.existsSync(`${agent}.new`), r4.stdout);
}

// ── 5c. profile detection asks the manifest, adapters emit valid YAML ──────
console.log("5c. detectProfile needs `next`; copilot/windsurf frontmatter is quoted");
{
  const prismaRepo = (name, deps) => {
    const d = freshRepo(name);
    fs.mkdirSync(path.join(d, "prisma"));
    fs.writeFileSync(path.join(d, "prisma", "schema.prisma"), "// schema\n");
    fs.writeFileSync(path.join(d, "package.json"), JSON.stringify({ name, dependencies: deps }));
    run("git", ["-C", d, "add", "-A"]); run("git", ["-C", d, "commit", "-qm", "prisma"]);
    return d;
  };
  const noNext = prismaRepo("t5c-express", { express: "4", "@prisma/client": "6" });
  const rA = vteam(noNext, "init", "--yes", "--tools", "claude-code");
  check("prisma WITHOUT next detects `node` (nextjs-prisma ran `next typegen` and reddened it)",
    rA.status === 0 && /profile: node$/m.test(fs.readFileSync(path.join(noNext, "vteam.config.yaml"), "utf8")),
    rA.stdout + rA.stderr + fs.readFileSync(path.join(noNext, "vteam.config.yaml"), "utf8").match(/profile:.*/)?.[0]);
  const withNext = prismaRepo("t5c-next", { next: "15", "@prisma/client": "6" });
  const rB = vteam(withNext, "init", "--yes", "--tools", "claude-code");
  check("prisma WITH next detects `nextjs-prisma`",
    rB.status === 0 && /profile: nextjs-prisma$/m.test(fs.readFileSync(path.join(withNext, "vteam.config.yaml"), "utf8")));
  // VT-31 (benchmark E2/E7/E15): a Next app gets a RUNNABLE app: block, on a port no other
  // checkout on the machine shares — the arm that started with an empty block wired it by
  // hand an hour in, and two arms on :3000 had the gate measure each other's server.
  const cfgNext = fs.readFileSync(path.join(withNext, "vteam.config.yaml"), "utf8");
  const port = derivePort(withNext);
  check("Next repo: init prefills app.url with the port derived from the checkout path",
    port >= 3100 && port < 3900 && new RegExp(`^  url: "http://127\\.0\\.0\\.1:${port}"$`, "m").test(cfgNext),
    cfgNext.match(/^app:[\s\S]*?headed:.*$/m)?.[0]);
  check("Next repo: app.start runs next on that same port and app.health probes /",
    new RegExp(`^  start: "npx next dev -p ${port}"$`, "m").test(cfgNext) && /^  health: "\/"$/m.test(cfgNext),
    cfgNext.match(/^app:[\s\S]*?headed:.*$/m)?.[0]);
  check("init tells the owner which port was pinned and why",
    new RegExp(`pinned to port ${port}`).test(rB.stdout) && /never share a port/.test(rB.stdout), rB.stdout);
  check("the port is a function of the path — three checkouts, three ports (deterministic fixture)",
    new Set(["/tmp/arm-a", "/tmp/arm-b", "/tmp/arm-c"].map(derivePort)).size === 3);
  check("a repo WITHOUT next keeps the empty app: block exactly as before",
    /^  start: ""$/m.test(fs.readFileSync(path.join(noNext, "vteam.config.yaml"), "utf8")) &&
    /^  url: ""$/m.test(fs.readFileSync(path.join(noNext, "vteam.config.yaml"), "utf8")) &&
    !/pinned to port/.test(rA.stdout));
  // the typegen step declares its skip on a repo where next is absent
  const gy = fs.readFileSync(path.join(PKG, "profiles", "nextjs-prisma", "gates.yaml"), "utf8");
  check("nextjs-prisma typegen probes for `next` (declared skip, not a red)",
    /typegen:[\s\S]*?requires_cmd:[^\n]*next[\s\S]*?skip_reason:/.test(gy));

  const dir = freshRepo("t5c-tools");
  const r = vteam(dir, "init", "--yes", "--tools", "copilot,windsurf", "--profile", "generic",
    "--tracker", "markdown", "--design", "none");
  check("init --tools copilot,windsurf exits 0", r.status === 0, r.stdout + r.stderr);
  for (const f of [".github/prompts/plan.prompt.md", ".windsurf/workflows/plan.md"]) {
    const line2 = fs.readFileSync(path.join(dir, f), "utf8").split("\n")[1];
    check(`${f}: description is a quoted YAML scalar (plan.md's "kernel: Why" broke the plain form)`,
      /^description: "[^"]*"$/.test(line2), line2.slice(0, 120));
  }
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

  // ── SessionEnd stop-state record (VT-34): the benchmark arm ended with 11 uncommitted
  // files and no note; a session that ends mid-ticket now leaves STOP-STATE.md behind.
  check("t1 got the session-end hook script",
    fs.existsSync(path.join(repo, ".claude", "hooks", "vteam-session-end.sh")));
  check("t1 settings.json carries the SessionEnd entry",
    Array.isArray(s.hooks?.SessionEnd) && s.hooks.SessionEnd.some((e) =>
      e.hooks?.some((h) => String(h.command).includes("vteam-session-end"))),
    JSON.stringify(s.hooks?.SessionEnd));
  check("SessionEnd entry merged alongside the user's hooks too",
    Array.isArray(merged.hooks?.SessionEnd) && merged.hooks.SessionEnd.length === 1 &&
    Array.isArray(merged.hooks?.PreToolUse), JSON.stringify(merged.hooks));
  check("stop_state.sh installed with the runtime",
    fs.existsSync(path.join(repo, ".vteam", "scripts", "stop_state.sh")));
  // the hook, run the way Claude Code runs it, on a ticket branch with work in flight
  const g = (...a) => run("git", a, { cwd: dir }); // freshRepo already init'd main + identity
  g("add", "-A"); g("commit", "-qm", "init");
  g("checkout", "-q", "-b", "feat/DEMO-1-half-done");
  fs.writeFileSync(path.join(dir, "half.txt"), "half done\n");
  const end = run("bash", [path.join(dir, ".claude", "hooks", "vteam-session-end.sh")],
    { cwd: dir, env: { ...ENV, CLAUDE_PROJECT_DIR: dir } });
  const stopFile = path.join(dir, "evd", "DEMO-1", "dev", "STOP-STATE.md");
  check("SessionEnd hook exits 0 and records the stop state of the ticket in flight",
    end.status === 0 && fs.existsSync(stopFile), end.stdout + end.stderr);
  const stopText = fs.existsSync(stopFile) ? fs.readFileSync(stopFile, "utf8") : "";
  check("STOP-STATE.md names the branch, the uncommitted file and a recorded: timestamp",
    /^- branch: feat\/DEMO-1-half-done$/m.test(stopText) && /^- uncommitted: 1 files$/m.test(stopText) &&
    /^- recorded: \d{4}-\d{2}-\d{2}T/m.test(stopText) && /half\.txt/.test(stopText), stopText.slice(0, 400));
  // and on the protected branch with a clean tree it records nothing (no noise on every exit)
  g("checkout", "-q", "--", "."); fs.rmSync(path.join(dir, "half.txt"), { force: true }); g("checkout", "-q", "main");
  fs.rmSync(path.join(dir, "evd", "DEMO-1"), { recursive: true, force: true });
  const quiet = run("bash", [path.join(dir, ".claude", "hooks", "vteam-session-end.sh")],
    { cwd: dir, env: { ...ENV, CLAUDE_PROJECT_DIR: dir } });
  check("SessionEnd hook on a clean protected branch writes nothing and still exits 0",
    quiet.status === 0 && !fs.existsSync(stopFile), quiet.stdout + quiet.stderr);

  // ── lane environment (VT-35, field finding E13): worktrees share vteam.config.yaml,
  // so a lane derives port/database/scratch from the worktree it runs in.
  check("lane_env.sh installed with the runtime",
    fs.existsSync(path.join(repo, ".vteam", "scripts", "lane_env.sh")));
  const lanesRoot = path.join(TMP, "lanes");
  const le = run("bash", [path.join(dir, ".vteam", "scripts", "lane_env.sh"), "--print"],
    { cwd: dir, env: { ...ENV, VTEAM_LANES_ROOT: lanesRoot } });
  const lePort = Number((le.stdout.match(/^export PORT=(\d+)$/m) || [])[1]);
  const { derivePort } = await import(path.join(PKG, "src", "cli", "init.mjs"));
  check("lane_env derives the SAME port init wrote for this checkout (one scheme, two writers)",
    le.status === 0 && lePort === derivePort(dir) && /^export APP_URL="http:\/\/127\.0\.0\.1:\d+"$/m.test(le.stdout),
    `lane_env: ${le.stdout.slice(0, 200)}${le.stderr} · derivePort=${derivePort(dir)}`);
  const leR1 = run("bash", [path.join(dir, ".vteam", "scripts", "lane_env.sh"), "--lane", "R1"],
    { cwd: dir, env: { ...ENV, VTEAM_LANES_ROOT: lanesRoot } });
  const r1Port = Number((leR1.stdout.match(/^export PORT=(\d+)$/m) || [])[1]);
  check("a reviewer lane (--lane R1) in the same worktree gets its own port and scratch dir",
    leR1.status === 0 && r1Port > 0 && r1Port !== lePort && /^export VTEAM_SCRATCH=".*-R1"$/m.test(leR1.stdout),
    leR1.stdout.slice(0, 300) + leR1.stderr);
  check("lane_env leaves the marker parallel_check reads (PORT recorded under VTEAM_LANES_ROOT)",
    fs.existsSync(lanesRoot) && fs.readdirSync(lanesRoot).some((d) =>
      fs.existsSync(path.join(lanesRoot, d, "lane.env")) &&
      new RegExp(`^PORT=${lePort}$`, "m").test(fs.readFileSync(path.join(lanesRoot, d, "lane.env"), "utf8"))),
    fs.existsSync(lanesRoot) ? fs.readdirSync(lanesRoot).join(",") : "no lanes root");
}

// ── 14c. app: env — scripts installed, Environment block rendered per config ─
console.log("14c. app: env — scripts installed, Environment block rendered");
{
  // the env toolchain ships with core/scripts on every install
  for (const f of ["app_check.sh", "browser.mjs", "open_files.sh"]) {
    check(`installed .vteam/scripts/${f}`, fs.existsSync(path.join(repo, ".vteam", "scripts", f)));
  }
  // t1 has an EMPTY app: section → the lanes render the "not configured" branch
  const qa1 = fs.readFileSync(path.join(repo, ".claude", "skills", "qa", "SKILL.md"), "utf8");
  check("empty app: renders the 'not configured' Environment branch",
    /\*\*Environment:\*\*/.test(qa1) && /not configured/.test(qa1), qa1.slice(0, 600));
  // a configured app: → update re-renders with resolved values + the mechanism
  const dir = freshRepo("t14c");
  vteam(dir, "init", "--yes", "--name", "Demo", "--key", "DEMO", "--language", "en",
    "--profile", "generic", "--tracker", "markdown", "--design", "none",
    "--autonomy", "assisted", "--tools", "claude-code,cursor");
  const cfgF = path.join(dir, "vteam.config.yaml");
  fs.writeFileSync(cfgF, fs.readFileSync(cfgF, "utf8")
    .replace('  start: ""', "  start: npm run dev")
    .replace('  url: ""', "  url: http://localhost:3456"));
  const up = vteam(dir, "update");
  check("update after configuring app: exits 0", up.status === 0, up.stdout + up.stderr);
  const qa2 = fs.readFileSync(path.join(dir, ".claude", "skills", "qa", "SKILL.md"), "utf8");
  check("qa skill carries the resolved app values + the headed mechanism",
    /start: `npm run dev`/.test(qa2) && /http:\/\/localhost:3456/.test(qa2) &&
    /app_check\.sh --wait 60/.test(qa2) && /browser\.mjs/.test(qa2), qa2.slice(0, 900));
  const dev2 = fs.readFileSync(path.join(dir, ".claude", "skills", "dev", "SKILL.md"), "utf8");
  check("dev skill tells the lane to open edited files in the owner's editor",
    /open_files\.sh/.test(dev2) && /\*\*Environment\*\*/.test(dev2), dev2.slice(0, 900));
  const gl = fs.readFileSync(path.join(dir, ".claude", "skills", "guidelines", "SKILL.md"), "utf8");
  check("guidelines (method-only) gets NO Environment block", !/\*\*Environment/.test(gl));
  const qaCursor = fs.readFileSync(path.join(dir, ".cursor", "commands", "qa.md"), "utf8");
  check("the mechanism is tool-neutral: cursor's qa render names browser.mjs too",
    /browser\.mjs/.test(qaCursor) && /app_check\.sh/.test(qaCursor), qaCursor.slice(0, 600));
  // and the dead flag stays dead: /verify no longer advertises --headed
  const vf = fs.readFileSync(path.join(dir, ".claude", "skills", "verify", "SKILL.md"), "utf8");
  check("verify's dead --headed flag is gone (headedness lives in app.headed)",
    !/--headed/.test(vf), vf.split("\n").slice(0, 6).join("\n"));
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
  // E14: a done ticket must have been dispatched — the ledger row is part of the record
  fs.appendFileSync(path.join(repo, "docs", "pm", "log.md"),
    "| 2026-01-02 | dev | e2e | DEMO-1 — auth | done · tok ≈ 1k | PR #1 |\n");
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

// ── 19. resume — crash recovery DERIVED from committed artifacts ───────────
// ops.md §1: all state is external; ops-247.md §1: a stored "resume" file
// would be a second source of truth. So `vteam resume` READS the books —
// claim, branch, tasksheet, review dossier, QA verdict, ledger — and derives
// the furthest PROVEN stage. This section proves the derivation ladder end to
// end on a real installed repo: each artifact added promotes the stage.
console.log("19. resume — derived crash recovery (artifact ladder)");
{
  const repo19 = freshRepo("t19");
  vteam(repo19, ...INIT_FLAGS);

  const st = vteam(repo19, "resume", "--selftest");
  check("resume --selftest is green", st.status === 0 && /selftest: OK/.test(st.stdout),
    st.stdout + st.stderr);

  const bad = vteam(repo19, "resume");
  check("resume without a key exits 1 and says the grammar", bad.status === 1 &&
    /<PROJ>-<n>|DEMO-1/.test(bad.stderr), bad.stderr);

  // rung 0: never started
  let r = vteam(repo19, "resume", "DEMO-9");
  check("untouched ticket derives 'no trace' and exits 0 (a mirror never fails the build)",
    r.status === 0 && /no trace/.test(r.stdout) && /never started/.test(r.stdout), r.stdout);

  // rung 1: expired claim, no work → orphaned, and the answer cites pm.md P0.1c
  fs.writeFileSync(path.join(repo19, "docs", "backlog", "DEMO-9.md"),
    "# DEMO-9 demo ticket\n\nclaimed 2026-01-01T00:00:00Z · branch feat/DEMO-9-x\n");
  r = vteam(repo19, "resume", "DEMO-9");
  check("expired claim derives orphaned + the recovery-lane move",
    /PAST TTL/.test(r.stdout) && /orphaned/.test(r.stdout) && /P0\.1c/.test(r.stdout), r.stdout);

  // rung 2: tasksheet exists → resume /dev, don't restart
  fs.mkdirSync(path.join(repo19, "evd", "DEMO-9", "dev"), { recursive: true });
  fs.writeFileSync(path.join(repo19, "evd", "DEMO-9", "dev", "tasksheet.md"), "# tasksheet\n");
  r = vteam(repo19, "resume", "DEMO-9");
  check("tasksheet promotes the stage: re-dispatch /dev resuming committed work",
    /tasksheet written/.test(r.stdout) && /resumes/.test(r.stdout), r.stdout);

  // rung 3: review dossier → hand to QA
  fs.writeFileSync(path.join(repo19, "evd", "DEMO-9", "dev", "review.md"), "# cards\n");
  r = vteam(repo19, "resume", "DEMO-9");
  check("review dossier promotes to: dispatch /qa",
    /review dossier committed/.test(r.stdout) && /\/qa DEMO-9/.test(r.stdout), r.stdout);

  // rung 4: QA verdict outranks everything — and the H1 word-boundary law holds
  fs.writeFileSync(path.join(repo19, "evd", "DEMO-9", "REPORT.md"),
    "# DEMO-9 — PASS\n\nCOMMIT: abc1234\n");
  r = vteam(repo19, "resume", "DEMO-9");
  check("PASS verdict → nothing to resume", /qa-verdict PASS/.test(r.stdout) &&
    /nothing to resume/.test(r.stdout), r.stdout);

  // --json is machine-readable and derivation matches the human view
  const j = JSON.parse(vteam(repo19, "resume", "DEMO-9", "--json").stdout);
  check("--json carries the same derivation", j.stage === "qa-verdict PASS" &&
    j.tasksheet === true && j.review_dossier === true, JSON.stringify(j));

  // determinism: a reader run twice answers the same
  check("resume is a pure reader (two runs, identical output)",
    vteam(repo19, "resume", "DEMO-9").stdout === r.stdout);
}

// ── 20. VT-25: the tools that had no test behind them prove themselves ──────
// The 2026-09-17 review found five scripts with neither a selftest nor an e2e
// case. orca_team.sh joined doctor's discovery (section 3); the three profile
// scripts and the publish guard are not under .vteam/scripts, so they run here.
console.log("20. profile tools + publish guard — selftests (no browser, no network)");
{
  for (const rel of ["profiles/nextjs-prisma/scripts/auth.mjs",
    "profiles/nextjs-prisma/scripts/ui_fidelity.mjs",
    "profiles/nextjs-prisma/scripts/ui-evidence.mjs",
    "tools/prepublish-check.mjs"]) {
    const r = run("node", [path.join(PKG, rel), "--selftest"], { cwd: PKG });
    check(`${rel} --selftest green`, r.status === 0 && /selftest: OK/.test(r.stdout), r.stdout + r.stderr);
  }
  // the profile tools import playwright LAZILY: the contract is provable from a
  // directory with no node_modules at all
  const bare = path.join(TMP, "t20-bare");
  fs.mkdirSync(bare, { recursive: true });
  const r = run("node", [path.join(PKG, "profiles", "nextjs-prisma", "scripts", "ui_fidelity.mjs"), "--selftest"], { cwd: bare });
  check("ui_fidelity --selftest needs no playwright (lazy import inside main)", r.status === 0, r.stdout + r.stderr);
  // …and without playwright a REAL run refuses loudly, naming the install, instead of a stack trace
  const spec = path.join(bare, "fidelity.json");
  fs.writeFileSync(spec, JSON.stringify({ anon: true, path: "/", checks: [{ selector: "h1", expect: { color: "#000000" } }] }));
  run("git", ["init", "-q", bare]);
  const r2 = run("node", [path.join(PKG, "profiles", "nextjs-prisma", "scripts", "ui_fidelity.mjs"), "T-1", spec], { cwd: bare });
  check("ui_fidelity without playwright: loud refusal naming `npm i -D playwright`, no stack trace",
    r2.status === 1 && /playwright is not installed/.test(r2.stderr) && !/at .*\.mjs:\d+/.test(r2.stderr), r2.stdout + r2.stderr);
}

// ── every shipped version has a CHANGELOG entry ────────────────────────────

// 22 versions were published before this file existed and none of them said
// what changed. A changelog nobody is forced to write is a changelog that stops
// at the version someone last remembered.
{
  const pkgVersion = JSON.parse(fs.readFileSync(path.join(PKG, "package.json"), "utf8")).version;
  const changelog = fs.readFileSync(path.join(PKG, "CHANGELOG.md"), "utf8");
  const newest = changelog.match(/^## (\d+\.\d+\.\d+)/m);
  check(`CHANGELOG's newest entry is the shipping version (${pkgVersion})`,
    newest && newest[1] === pkgVersion,
    `package.json is ${pkgVersion}, CHANGELOG's newest entry is ${newest ? newest[1] : "(none found)"}`);
}

// ── the README's "N checks" claim is machine-verified ──────────────────────
// Found stale (said 119, suite ran 139) in the 2026-08-24 review: a count
// nobody re-runs is a count that drifts. This is deliberately the LAST check —
// the README must state the suite's full total, this line included.
{
  const readme = fs.readFileSync(path.join(PKG, "README.md"), "utf8");
  const m = readme.match(/\*\*(\d+) checks\*\*/);
  n++;
  if (m && Number(m[1]) === n) {
    console.log(`  ✅ README's "${m[1]} checks" claim matches the suite (${n})`);
  } else {
    failed++;
    console.log(`  ❌ README claims "${m ? m[1] : "(no **N checks** found)"}" but the suite ran ${n} — fix README.md's number`);
  }
}

console.log(`\n${failed === 0 ? "E2E: GREEN" : "E2E: RED"} — ${n - failed}/${n} checks passed`);
process.exit(failed === 0 ? 0 : 1);
