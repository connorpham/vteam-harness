#!/usr/bin/env node
// prepublish-check.mjs — refuse to publish something other than what is merged.
//
// Why this exists: npm renders the package page from the published tarball and
// will not let a version be republished. Three times in a row a docs change
// merged to main just AFTER a publish, so the npm page served a stale README
// until the next patch release. The failure mode is always the same — publishing
// at a moment when the tree is not what main says — so it gets a machine check
// instead of a reminder.
//
// Runs from package.json's `prepublishOnly`, so `npm publish` cannot skip it.
// Five refusals, each with the fix in the message:
//   1. dirty working tree
//   2. HEAD ≠ origin/main (behind = something is not merged yet; ahead = your
//      commits are not on main)
//   3. this version already exists on the registry (bump first — a clear failure
//      BEFORE the 2FA dance, not after it)
//   4. the test suite is not green (run with PYTHONDONTWRITEBYTECODE so the
//      Python gates cannot regenerate __pycache__ mid-publish)
//   5. the tarball would ship build artifacts (__pycache__/*.pyc — npm packs
//      gitignored files under "files" directories; 0.15.1 shipped 3 this way).
//      Stale bytecode dirs are auto-cleaned first; this runs LAST so nothing
//      can dirty the tree between the check and the real pack.
// Offline: the two network checks warn loudly and step aside; the local ones stand.
//
// Structure (VT-25): `check({root, run, log, err})` is the whole rule set with an
// injectable command runner, so `--selftest` can prove every refusal fires on a
// fixture repo with a stubbed npm — this file guards every publish and had never
// been shown to refuse one.
import { spawnSync } from "node:child_process";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import process from "node:process";
import { fileURLToPath, pathToFileURL } from "node:url";

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");

/** Run the five refusals against `root`. Returns the number of refusals; every
 * message goes through `log`/`err`. `run(cmd, args, opts)` defaults to spawnSync. */
export function check({ root = ROOT, run = spawnSync, log = console.log, err = console.error } = {}) {
  const sh = (cmd, args, opts = {}) => run(cmd, args, { cwd: root, encoding: "utf8", ...opts });
  let failed = 0;
  const bad = (what, fix) => { err(`\n❌ prepublish: ${what}\n   → ${fix}`); failed++; };
  const ok = (m) => log(`✅ ${m}`);
  const warn = (m) => log(`⚠️  ${m}`);

  const { name, version } = JSON.parse(fs.readFileSync(path.join(root, "package.json"), "utf8"));
  log(`prepublish check — ${name}@${version}`);

  // 1. clean tree: whatever is uncommitted would ship or be missing, silently
  const dirty = String(sh("git", ["status", "--porcelain"]).stdout || "").trim();
  if (dirty) {
    bad(`working tree is dirty (${dirty.split("\n").length} file(s))`,
      "commit or stash first — a publish must be reproducible from a commit");
  } else {
    ok("working tree clean");
  }

  // 2. publishing exactly what main says
  const fetched = sh("git", ["fetch", "-q", "origin", "main"]);
  if (fetched.status !== 0) {
    warn("could not fetch origin/main (offline?) — skipping the merged-state check");
  } else {
    const head = String(sh("git", ["rev-parse", "HEAD"]).stdout || "").trim();
    const main = String(sh("git", ["rev-parse", "origin/main"]).stdout || "").trim();
    if (head !== main) {
      const behind = String(sh("git", ["rev-list", "--count", "HEAD..origin/main"]).stdout || "").trim();
      const ahead = String(sh("git", ["rev-list", "--count", "origin/main..HEAD"]).stdout || "").trim();
      bad(`HEAD is not origin/main (${behind} behind, ${ahead} ahead)`,
        Number(behind) > 0
          ? "git pull — something is merged on main that this publish would omit (this is the stale-README trap)"
          : "open a PR and merge first — publish only what main carries");
    } else {
      ok(`HEAD == origin/main (${head.slice(0, 8)})`);
    }
  }

  // 3. version still free — fail here, not after the 2FA prompt
  const view = sh("npm", ["view", `${name}@${version}`, "version"]);
  if (view.status === 0 && String(view.stdout || "").trim()) {
    bad(`${name}@${version} is already published`,
      "bump the version — npm never allows republishing, and the page keeps the old tarball's README");
  } else if (/ENOTFOUND|ECONN|EAI_AGAIN|network/i.test(String(view.stderr || ""))) {
    warn("registry unreachable — skipping the already-published check");
  } else {
    ok(`${version} is free on the registry`);
  }

  // 4. the suite behind every README claim. PYTHONDONTWRITEBYTECODE: the Python
  // gates the suite runs must not regenerate __pycache__ mid-publish — npm packs
  // the REAL tarball only after this whole script passes, so bytecode written
  // here would ship even though check 5 saw a clean tree (exactly how 0.15.1
  // leaked 3 .pyc files).
  const test = sh("npm", ["test"],
    { stdio: "pipe", env: { ...process.env, PYTHONDONTWRITEBYTECODE: "1" } });
  if (test.status !== 0) {
    const tail = (String(test.stdout || "") + String(test.stderr || ""))
      .trim().split("\n").slice(-6).join("\n");
    bad("npm test is not green", `fix it before publishing:\n${tail}`);
  } else {
    ok("npm test green");
  }

  // 5. no build artifacts in the tarball — npm packs everything under a
  // directory named in "files", INCLUDING gitignored content. Bytecode is
  // regenerated freely by earlier local runs, so stale dirs are DELETED here
  // (never committed, never ignored-away), then the pack list must come back
  // clean. Runs LAST so nothing after it can dirty the tree before the real pack.
  for (const dir of ["core", "profiles", "providers", "src", "bin", "adapters"]) {
    for (const hit of String(sh("find", [dir, "-name", "__pycache__", "-type", "d"]).stdout || "")
      .trim().split("\n").filter(Boolean)) {
      fs.rmSync(path.join(root, hit), { recursive: true, force: true });
      log(`   cleaned ${hit} (regenerated bytecode — never ships)`);
    }
  }
  const pack = sh("npm", ["pack", "--dry-run", "--json"]);
  let packed = [];
  if (pack.status === 0) {
    try { packed = JSON.parse(pack.stdout)[0].files.map((f) => f.path); } catch { packed = null; }
  }
  const artifacts = (packed || []).filter((p) => /__pycache__|\.pyc$/.test(p));
  if (pack.status !== 0 || packed === null) {
    warn("npm pack --dry-run failed — skipping the tarball-artifact check");
  } else if (artifacts.length) {
    bad(`tarball would ship ${artifacts.length} build artifact(s): ${artifacts.slice(0, 3).join(", ")}${artifacts.length > 3 ? ", …" : ""}`,
      "these survived the auto-clean — find where they come from before publishing");
  } else {
    ok(`tarball carries no __pycache__/*.pyc (${packed.length} files checked)`);
  }
  return failed;
}

// ── selftest: every refusal on a fixture repo, npm stubbed, git real ─────────
function selftest() {
  const fails = [];
  const expect = (cond, msg) => { if (!cond) fails.push(msg); };
  const tmp = fs.mkdtempSync(path.join(os.tmpdir(), "vteam-prepublish-"));
  try {
    const root = path.join(tmp, "pkg");
    const bare = path.join(tmp, "origin.git");
    fs.mkdirSync(path.join(root, "bin"), { recursive: true });
    fs.writeFileSync(path.join(root, "package.json"),
      JSON.stringify({ name: "vteam-selftest-pkg", version: "0.0.1", files: ["bin"] }, null, 2));
    fs.writeFileSync(path.join(root, "bin", "x.mjs"), "export const x = 1;\n");
    fs.writeFileSync(path.join(root, ".gitignore"), "__pycache__/\n"); // as the real repo does
    const g = (...a) => spawnSync("git", a, { cwd: root, encoding: "utf8" });

    g("init", "-q", "-b", "main"); g("config", "user.email", "t@t"); g("config", "user.name", "t");
    g("add", "-A"); g("commit", "-qm", "init");
    spawnSync("git", ["init", "-q", "--bare", bare]);
    g("remote", "add", "origin", bare); g("push", "-q", "origin", "main");

    // git and find are REAL against the fixture; npm is stubbed per case
    const runner = (over = {}) => (cmd, args, opts) => {
      if (cmd === "git" || cmd === "find") return spawnSync(cmd, args, { encoding: "utf8", ...opts });
      if (cmd === "npm" && args[0] === "view") return over.view ?? { status: 1, stdout: "", stderr: "npm ERR! code E404" };
      if (cmd === "npm" && args[0] === "test") return over.test ?? { status: 0, stdout: "ok", stderr: "" };
      if (cmd === "npm" && args[0] === "pack") return over.pack ?? { status: 0, stdout: JSON.stringify([{ files: [{ path: "bin/x.mjs" }, { path: "package.json" }] }]), stderr: "" };
      throw new Error(`selftest runner: unexpected ${cmd} ${args.join(" ")}`);
    };
    const go = (over) => {
      const logs = [], errs = [];
      const failed = check({ root, run: runner(over), log: (m) => logs.push(m), err: (m) => errs.push(m) });
      return { failed, out: logs.join("\n"), err: errs.join("\n") };
    };

    // green: clean tree, HEAD == origin/main, version free, tests green, clean tarball
    let r = go();
    expect(r.failed === 0, `clean fixture must pass, got ${r.failed}: ${r.err}`);
    expect(/working tree clean/.test(r.out) && /HEAD == origin\/main/.test(r.out) && /is free on the registry/.test(r.out)
      && /npm test green/.test(r.out) && /carries no __pycache__/.test(r.out), `green path must print all five ✅: ${r.out}`);

    // refusal 1: dirty tree
    fs.writeFileSync(path.join(root, "scratch.txt"), "uncommitted\n");
    r = go();
    expect(r.failed === 1 && /working tree is dirty \(1 file/.test(r.err), `dirty tree must refuse: ${r.err}`);
    fs.rmSync(path.join(root, "scratch.txt"));

    // refusal 2: HEAD ahead of origin/main (not merged)
    fs.writeFileSync(path.join(root, "bin", "x.mjs"), "export const x = 2;\n");
    g("commit", "-aqm", "local only");
    r = go();
    expect(r.failed === 1 && /0 behind, 1 ahead/.test(r.err) && /open a PR and merge first/.test(r.err), `unmerged HEAD must refuse: ${r.err}`);
    // …and BEHIND names the stale-README trap
    g("push", "-q", "origin", "main");
    g("reset", "-q", "--hard", "HEAD~1");
    r = go();
    expect(r.failed === 1 && /1 behind, 0 ahead/.test(r.err) && /stale-README trap/.test(r.err), `HEAD behind main must refuse: ${r.err}`);
    g("pull", "-q", "origin", "main");

    // refusal 3: version already on the registry
    r = go({ view: { status: 0, stdout: "0.0.1\n", stderr: "" } });
    expect(r.failed === 1 && /is already published/.test(r.err), `published version must refuse: ${r.err}`);
    // offline registry is a WARN, not a refusal
    r = go({ view: { status: 1, stdout: "", stderr: "npm ERR! ENOTFOUND registry.npmjs.org" } });
    expect(r.failed === 0 && /registry unreachable/.test(r.out), `offline registry must warn and pass: ${r.out}${r.err}`);

    // refusal 4: red suite, with its tail in the message
    r = go({ test: { status: 1, stdout: "…\n  ❌ README claims 190 but the suite ran 192\nE2E: RED", stderr: "" } });
    expect(r.failed === 1 && /npm test is not green/.test(r.err) && /E2E: RED/.test(r.err), `red suite must refuse with the tail: ${r.err}`);

    // refusal 5: bytecode in the tarball; and the auto-clean removes a stale __pycache__ first
    fs.mkdirSync(path.join(root, "bin", "__pycache__"), { recursive: true });
    fs.writeFileSync(path.join(root, "bin", "__pycache__", "x.cpython-311.pyc"), "\x00");
    r = go({ pack: { status: 0, stdout: JSON.stringify([{ files: [{ path: "bin/x.mjs" }, { path: "core/__pycache__/gate.cpython-311.pyc" }] }]), stderr: "" } });
    expect(!fs.existsSync(path.join(root, "bin", "__pycache__")), "a stale __pycache__ dir must be auto-cleaned before the pack check");
    expect(/cleaned bin\/__pycache__/.test(r.out), `the clean must be reported: ${r.out}`);
    expect(r.failed === 1 && /tarball would ship 1 build artifact/.test(r.err), `bytecode in the pack list must refuse: ${r.err}`);
    // a pack that cannot run is a WARN (local checks still stand)
    r = go({ pack: { status: 1, stdout: "", stderr: "boom" } });
    expect(r.failed === 0 && /npm pack --dry-run failed/.test(r.out), `pack failure must warn, not refuse: ${r.out}${r.err}`);
  } finally {
    fs.rmSync(tmp, { recursive: true, force: true });
  }
  if (fails.length) {
    console.error("prepublish-check selftest: FAILED");
    for (const f of fails) console.error(`  x ${f}`);
    process.exit(1);
  }
  console.log("prepublish-check selftest: OK (clean path green; refusals: dirty tree, HEAD ahead, HEAD behind, "
    + "published version, red suite with tail, bytecode in tarball + auto-clean; offline registry and failed pack warn only)");
}

const isMain = process.argv[1] && import.meta.url === pathToFileURL(path.resolve(process.argv[1])).href;
if (isMain) {
  if (process.argv.includes("--selftest")) {
    selftest();
  } else {
    const failed = check();
    if (failed) {
      console.error(`\nprepublish: ${failed} refusal(s) — nothing was published.`);
      process.exit(1);
    }
    console.log("\nprepublish: OK — publishing what main carries.");
  }
}
