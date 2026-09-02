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
//   4. the tarball would ship build artifacts (__pycache__/*.pyc — npm packs
//      gitignored files under "files" directories; 0.15.1 shipped 3 this way)
//   5. the test suite is not green
// Offline: the two network checks warn loudly and step aside; the local ones stand.
import { spawnSync } from "node:child_process";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const run = (cmd, args, opts = {}) =>
  spawnSync(cmd, args, { cwd: ROOT, encoding: "utf8", ...opts });

let failed = 0;
const bad = (what, fix) => {
  console.error(`\n❌ prepublish: ${what}\n   → ${fix}`);
  failed++;
};
const ok = (m) => console.log(`✅ ${m}`);
const warn = (m) => console.log(`⚠️  ${m}`);

const { name, version } = JSON.parse(
  fs.readFileSync(path.join(ROOT, "package.json"), "utf8"));
console.log(`prepublish check — ${name}@${version}`);

// 1. clean tree: whatever is uncommitted would ship or be missing, silently
const dirty = run("git", ["status", "--porcelain"]).stdout.trim();
if (dirty) {
  bad(`working tree is dirty (${dirty.split("\n").length} file(s))`,
    "commit or stash first — a publish must be reproducible from a commit");
} else {
  ok("working tree clean");
}

// 2. publishing exactly what main says
const fetched = run("git", ["fetch", "-q", "origin", "main"]);
if (fetched.status !== 0) {
  warn("could not fetch origin/main (offline?) — skipping the merged-state check");
} else {
  const head = run("git", ["rev-parse", "HEAD"]).stdout.trim();
  const main = run("git", ["rev-parse", "origin/main"]).stdout.trim();
  if (head !== main) {
    const behind = run("git", ["rev-list", "--count", "HEAD..origin/main"]).stdout.trim();
    const ahead = run("git", ["rev-list", "--count", "origin/main..HEAD"]).stdout.trim();
    bad(`HEAD is not origin/main (${behind} behind, ${ahead} ahead)`,
      Number(behind) > 0
        ? "git pull — something is merged on main that this publish would omit (this is the stale-README trap)"
        : "open a PR and merge first — publish only what main carries");
  } else {
    ok(`HEAD == origin/main (${head.slice(0, 8)})`);
  }
}

// 3. version still free — fail here, not after the 2FA prompt
const view = run("npm", ["view", `${name}@${version}`, "version"]);
if (view.status === 0 && view.stdout.trim()) {
  bad(`${name}@${version} is already published`,
    "bump the version — npm never allows republishing, and the page keeps the old tarball's README");
} else if (/ENOTFOUND|ECONN|EAI_AGAIN|network/i.test(view.stderr || "")) {
  warn("registry unreachable — skipping the already-published check");
} else {
  ok(`${version} is free on the registry`);
}

// 4. no build artifacts in the tarball — npm packs everything under a
// directory named in "files", INCLUDING gitignored content (0.15.1 shipped
// core/scripts/lib/__pycache__/*.pyc this way). The gates regenerate
// bytecode locally, so the fix is deletion, never committing an ignore file.
const pack = run("npm", ["pack", "--dry-run", "--json"]);
const packed = pack.status === 0
  ? JSON.parse(pack.stdout)[0].files.map((f) => f.path)
  : [];
const artifacts = packed.filter((p) => /__pycache__|\.pyc$/.test(p));
if (pack.status !== 0) {
  warn("npm pack --dry-run failed — skipping the tarball-artifact check");
} else if (artifacts.length) {
  bad(`tarball would ship ${artifacts.length} build artifact(s): ${artifacts.slice(0, 3).join(", ")}${artifacts.length > 3 ? ", …" : ""}`,
    'delete them and re-run: find . -name __pycache__ -type d -prune -exec rm -rf {} +');
} else {
  ok(`tarball carries no __pycache__/*.pyc (${packed.length} files checked)`);
}

// 5. the suite behind every README claim
const test = run("npm", ["test"], { stdio: "pipe" });
if (test.status !== 0) {
  const tail = (String(test.stdout || "") + String(test.stderr || ""))
    .trim().split("\n").slice(-6).join("\n");
  bad("npm test is not green", `fix it before publishing:\n${tail}`);
} else {
  ok("npm test green");
}

if (failed) {
  console.error(`\nprepublish: ${failed} refusal(s) — nothing was published.`);
  process.exit(1);
}
console.log("\nprepublish: OK — publishing what main carries.");
