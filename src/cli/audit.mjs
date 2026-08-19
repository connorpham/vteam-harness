// audit.mjs — `vteam audit`: grade ANY repo's AI-agent accountability, 0-100.
// The zero-commitment mirror: it works in repos WITHOUT vteam installed (that
// is the point), reads only the local filesystem + git (no network, zero
// deps), never writes, and always exits 0 — audit is a mirror, not a gate.
//
// RUBRIC — every point is a concrete offline observation; no fake precision.
// Each dimension asks: what would a MACHINE need to see to believe "done"?
//   GATES        20  CI pipeline exists (8) · a pipeline step actually runs
//                    tests/gates (6) · a test entrypoint in the repo (6)
//   HOOKS        15  git hooks ACTIVE — core.hooksPath / .git/hooks / .husky
//                    (8; .pre-commit-config.yaml alone = 4, activation is not
//                    verifiable offline) · secret scan wired into hook/CI (7)
//   EVIDENCE     20  QA/evidence tree exists as files (8) · durable decision/
//                    QA ledger (6) · that evidence is tracked by git (6)
//   REVIEW TRAIL 15  machine fence for PR-only main (8; CODEOWNERS alone = 4,
//                    server-side rules are invisible offline) · per-change
//                    review dossiers committed (7; convention docs alone = 4)
//   VERDICTS     15  approvals tied to commits: vteam manifest (8) + stale-
//                    verdict gate (7); hand-pinned commit SHAs in review
//                    files = 6
//   SELF-PROOF   15  the repo's checks prove they can FAIL: ≥3 files carry a
//                    --selftest (10; 1-2 = 6) · mutation proof — selftests
//                    that force reds, or a mutation-testing tool (5)
// Grades: A ≥85 · B ≥70 · C ≥55 · D ≥35 · F <35. Calibration: a bare repo
// lands near 0; a well-tested OSS repo without agent machinery lands mid; a
// vteam install scores high ONLY where its wiring is actually live (silent
// hooks or uncommitted evidence = points off — vteam grades itself through
// the same rubric as everyone else).
//
// The scan is bounded (dependency/build dirs skipped, file-count and file-size
// caps) — a grader must stay instant on monorepos.
//
// Selftest:  node src/cli/audit.mjs --selftest
//   Builds 3 fixture repos (bare / CI+tests / vteam-shaped) and asserts the
//   ordering low < mid < high, ≥1 fully-red dimension in the low fixture,
//   high ≥ 70, and the mutation: deleting the manifest from the high fixture
//   MUST drop its score — a grader that has never been red does not exist.
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { spawnSync } from "node:child_process";
import { pathToFileURL } from "node:url";
import { repoRoot } from "./util.mjs";

const SKIP_DIRS = new Set([".git", "node_modules", "dist", "build", "out", "vendor",
  ".venv", "venv", "__pycache__", ".next", "target", "coverage", ".cache"]);
const READ_CAP = 1_000_000; // bytes — never slurp a bundle to grep one word

function sh(root, cmd, args) {
  const r = spawnSync(cmd, args,
    { cwd: root, encoding: "utf8", stdio: ["ignore", "pipe", "ignore"] });
  return r.status === 0 ? String(r.stdout).trim() : "";
}

function readSmall(abs) {
  try {
    if (fs.statSync(abs).size > READ_CAP) return "";
    return fs.readFileSync(abs, "utf8");
  } catch { return ""; }
}
function readAt(root, rel) { return readSmall(path.join(root, ...rel.split("/"))); }
function exists(root, rel) { return fs.existsSync(path.join(root, ...rel.split("/"))); }
function listDir(root, rel) {
  try { return fs.readdirSync(path.join(root, ...rel.split("/"))); } catch { return []; }
}

/** Bounded repo walk — rel paths, forward slashes, dep/build dirs skipped. */
function walk(root, cap = 6000) {
  const out = [];
  const stack = [""];
  while (stack.length && out.length < cap) {
    const relDir = stack.pop();
    let entries = [];
    try { entries = fs.readdirSync(path.join(root, relDir), { withFileTypes: true }); }
    catch { continue; }
    for (const e of entries) {
      if (out.length >= cap) break;
      const rel = relDir ? `${relDir}/${e.name}` : e.name;
      if (e.isDirectory()) { if (!SKIP_DIRS.has(e.name)) stack.push(rel); }
      else if (e.isFile()) out.push(rel);
    }
  }
  return out;
}

function trackedSet(root) {
  const out = sh(root, "git", ["ls-files"]);
  return new Set(out ? out.split("\n") : []);
}

// ---- rubric machinery --------------------------------------------------------
function dim(name, max, fix) { return { name, max, points: 0, found: [], missing: [], fix }; }
function hit(d, pts, note) { d.points = Math.min(d.max, d.points + pts); d.found.push(note); }
function miss(d, note) { d.missing.push(note); }

export function grade(score) {
  return score >= 85 ? "A" : score >= 70 ? "B" : score >= 55 ? "C" : score >= 35 ? "D" : "F";
}

/** Score one repo through the rubric. Pure read — never writes, never networks. */
export function scoreRepo(root) {
  const files = walk(root);
  const tracked = trackedSet(root);
  const dims = [];

  // ---- GATES: can anything fail red once the work leaves this machine? -------
  const g = dim("GATES", 20,
    "a CI pipeline that runs the tests on every push — a red X nobody can talk past");
  dims.push(g);
  const ciFiles = listDir(root, ".github/workflows")
    .filter((f) => /\.ya?ml$/.test(f)).map((f) => `.github/workflows/${f}`)
    .concat([".gitlab-ci.yml", ".circleci/config.yml", "azure-pipelines.yml",
      "Jenkinsfile", ".travis.yml"].filter((f) => exists(root, f)));
  if (ciFiles.length) hit(g, 8, `CI pipeline: ${ciFiles.slice(0, 3).join(", ")}`);
  else miss(g, "no CI pipeline (.github/workflows/, .gitlab-ci.yml, …) — nothing can go red off this machine");
  const ciRaw = ciFiles.map((f) => readAt(root, f)).join("\n");
  const ciRun = ciRaw.split("\n").filter((l) => !/uses:/.test(l)).join("\n");
  if (/\b(tests?|pytest|gate|lint|tox|vitest|jest|verify|check)\b/i.test(ciRun))
    hit(g, 6, "CI runs real checks (test/gate step in the pipeline)");
  else miss(g, ciFiles.length ? "CI exists but no step in it runs tests or gates"
    : "no CI step runs tests or gates");
  const testSignals = [];
  try {
    const t = JSON.parse(readAt(root, "package.json") || "null")?.scripts?.test;
    if (t && !/no test specified/.test(t)) testSignals.push(`package.json test: ${JSON.stringify(t)}`);
  } catch { /* unparseable package.json — no signal */ }
  if (exists(root, "pytest.ini") || exists(root, "tox.ini") ||
      /\[tool:pytest\]/.test(readAt(root, "setup.cfg")) ||
      /pytest/.test(readAt(root, "pyproject.toml"))) testSignals.push("pytest/tox configured");
  if (/^(test|check):/m.test(readAt(root, "Makefile"))) testSignals.push("Makefile test target");
  const testFiles = files.filter((f) =>
    /(^|\/)(tests?|__tests__|spec)\//.test(f) || /\.(test|spec)\.[cm]?[jt]sx?$/.test(f) ||
    /(^|\/)test_[^/]+\.py$/.test(f) || /_test\.(go|py|rb)$/.test(f));
  if (testFiles.length) testSignals.push(`${testFiles.length} test file(s)`);
  if (testSignals.length)
    hit(g, 6, `test entrypoint: ${testSignals[0]}${testSignals.length > 1 ? ` (+${testSignals.length - 1} more)` : ""}`);
  else miss(g, "no test entrypoint (package.json test / pytest / Makefile / tests/)");

  // ---- HOOKS: does a push get checked at all? ---------------------------------
  const h = dim("HOOKS", 15,
    "an ACTIVE pre-push/pre-commit hook with a fail-closed secret scan — checked machinery, not policy prose");
  dims.push(h);
  const hookFiles = []; // { rel, text }
  const hp = sh(root, "git", ["config", "--get", "core.hooksPath"]);
  if (hp) {
    const dirAbs = path.isAbsolute(hp) ? hp : path.join(root, hp);
    for (const nm of listDir(dirAbs, "")) {
      const abs = path.join(dirAbs, nm);
      try { if (fs.statSync(abs).isFile()) hookFiles.push({ rel: `${hp}/${nm}`, text: readSmall(abs) }); } catch { /* unreadable — skip */ }
    }
  }
  for (const nm of listDir(root, ".git/hooks")) {
    if (nm.endsWith(".sample")) continue;
    const abs = path.join(root, ".git", "hooks", nm);
    try { if (fs.statSync(abs).isFile()) hookFiles.push({ rel: `.git/hooks/${nm}`, text: readSmall(abs) }); } catch { /* unreadable — skip */ }
  }
  for (const nm of listDir(root, ".husky")) {
    if (nm.startsWith("_") || nm.startsWith(".")) continue;
    const abs = path.join(root, ".husky", nm);
    try { if (fs.statSync(abs).isFile()) hookFiles.push({ rel: `.husky/${nm}`, text: readSmall(abs) }); } catch { /* unreadable — skip */ }
  }
  const preCommitCfg = readAt(root, ".pre-commit-config.yaml");
  if (hookFiles.length)
    hit(h, 8, `active hooks: ${hookFiles.slice(0, 3).map((x) => x.rel).join(", ")}${hp ? ` (core.hooksPath=${hp})` : ""}`);
  else if (preCommitCfg) {
    hit(h, 4, ".pre-commit-config.yaml present");
    miss(h, "pre-commit activation not verifiable offline — `pre-commit install` writes .git/hooks");
  } else miss(h, "no active git hooks — a push leaves this machine completely unchecked");
  const hookText = hookFiles.map((x) => x.text).join("\n") + "\n" + preCommitCfg;
  if (/gitleaks|trufflehog|detect-secrets|secretlint|git-secrets|SECRET SCAN|SECRET in|ghp_|AKIA/.test(hookText + "\n" + ciRaw))
    hit(h, 7, "secret scan wired (hook or CI)");
  else miss(h, "no secret scan in hooks or CI — a leaked token sails through");

  // ---- EVIDENCE: do QA artifacts outlive the chat session? --------------------
  const e = dim("EVIDENCE", 20,
    "QA/review artifacts committed as files (evd/, docs/qa) — proof that outlives the session");
  dims.push(e);
  const evRoots = ["evd", "docs/qa", "docs/evidence", "evidence", "qa", "docs/reviews", "test-results"];
  const evFiles = files.filter((f) => evRoots.some((d) => f.startsWith(d + "/")));
  if (evFiles.length) {
    const roots = [...new Set(evFiles.map((f) =>
      f.startsWith("docs/") ? f.split("/").slice(0, 2).join("/") : f.split("/")[0]))];
    hit(e, 8, `evidence tree: ${roots.join(", ")} (${evFiles.length} file(s))`);
  } else miss(e, "no evidence tree (evd/, docs/qa, …) — QA results die with the session");
  const ledgers = ["docs/pm/log.md", "docs/pm/decisions.md", "docs/decisions.md",
    "docs/qa/known-issues.md"].filter((f) => exists(root, f))
    .concat(listDir(root, "docs/adr").filter((f) => f.endsWith(".md")).map((f) => `docs/adr/${f}`));
  if (ledgers.length) hit(e, 6, `durable ledger: ${ledgers.slice(0, 2).join(", ")}`);
  else miss(e, "no durable ledger (docs/pm/log.md, decisions.md, ADRs)");
  const durable = [...new Set([...evFiles, ...ledgers])].filter((f) => tracked.has(f));
  if (durable.length) hit(e, 6, `${durable.length} evidence/ledger file(s) tracked by git`);
  else miss(e, evFiles.length + ledgers.length
    ? "evidence exists but is NOT tracked by git — commit it or it dies with the checkout"
    : "nothing to track — no evidence to commit");

  // ---- REVIEW TRAIL: PR-only main + verdicts as committed files ---------------
  const r = dim("REVIEW TRAIL", 15,
    "a machine fence forcing branch+PR onto main, and per-change review verdicts committed as files");
  dims.push(r);
  if (/no direct push|protected[ _-]?branch|branch protection|ALLOW_PUSH_MAIN/i.test(hookText))
    hit(r, 8, "pre-push fence covers the protected branch");
  else if (exists(root, ".github/CODEOWNERS") || exists(root, "CODEOWNERS") || exists(root, "docs/CODEOWNERS"))
    hit(r, 4, "CODEOWNERS present (server-side branch protection is not verifiable offline)");
  else miss(r, "nothing on this machine stops a direct push to main");
  const reviewDocs = files.filter((f) =>
    /review/i.test(f) && /\.(md|json|txt)$/i.test(f) && !f.startsWith(".github/"));
  const dossiers = reviewDocs.filter((f) => /^evd\//.test(f) || /(^|\/)reviews\//i.test(f));
  if (dossiers.length)
    hit(r, 7, `review dossiers committed: ${dossiers.slice(0, 2).join(", ")}${dossiers.length > 2 ? " …" : ""}`);
  else if (reviewDocs.length || files.some((f) => /PULL_REQUEST_TEMPLATE/i.test(f))) {
    hit(r, 4, `review convention documented: ${reviewDocs[0] ?? "PR template"}`);
    miss(r, "no per-change review dossiers — approvals live in chat/PR UI, not in the repo");
  } else miss(r, "no committed review records of any kind");

  // ---- VERDICTS: is any approval tied to the commit it approved? --------------
  const v = dim("VERDICTS", 15,
    "approvals pinned to the commits they approved, plus a staleness check — a verdict for old code must expire");
  dims.push(v);
  let man = null;
  try { man = JSON.parse(readAt(root, ".vteam/manifest.json") || "null"); } catch { man = null; }
  const manOk = !!(man && typeof man.files === "object");
  if (manOk) hit(v, 8, `vteam manifest: ${Object.keys(man.files).length} framework file(s) pinned by sha256`);
  if (exists(root, ".vteam/scripts/stale_verdict_check.py"))
    hit(v, 7, "stale-verdict gate installed (.vteam/scripts/stale_verdict_check.py)");
  if (v.points === 0) {
    const pinned = [...new Set([...evFiles, ...reviewDocs])].slice(0, 25).filter((f) =>
      /\bcommit\b[^\n]{0,16}\b[0-9a-f]{7,40}\b|\b[0-9a-f]{40}\b/i.test(readAt(root, f)));
    if (pinned.length) hit(v, 6, `review/evidence files reference commits by hand (e.g. ${pinned[0]})`);
    else miss(v, "no mechanism ties an approval to a commit — every verdict is \"trust me, it was this version\"");
  } else if (v.points < v.max) {
    miss(v, manOk ? "stale-verdict gate missing — approvals never expire"
      : "no update-guarded manifest — framework bytes are unpinned");
  }

  // ---- SELF-PROOF: have the checks ever been shown to catch a break? ----------
  const s = dim("SELF-PROOF", 15,
    "checks that prove they can FAIL: --selftest modes with red mutations, or a mutation-testing tool");
  dims.push(s);
  const selftesters = [];
  let mutationWord = false;
  for (const f of files.filter((x) => /\.(py|sh|bash|mjs|cjs|js|ts)$/.test(x)).slice(0, 400)) {
    const t = readAt(root, f);
    if (t.includes("--selftest")) {
      selftesters.push(f);
      if (/mutation/i.test(t)) mutationWord = true;
    }
  }
  if (selftesters.length >= 3)
    hit(s, 10, `${selftesters.length} checks carry --selftest (e.g. ${selftesters[0]})`);
  else if (selftesters.length) {
    hit(s, 6, `${selftesters.length} check(s) carry --selftest`);
    miss(s, "most checks cannot demonstrate a red");
  } else miss(s, "no check can demonstrate it fails — green that cannot go red is decoration");
  const mutTool = files.some((f) => /(^|\/)(stryker\.conf|\.stryker)/.test(f)) ||
    /mutmut|cosmic-ray/.test(readAt(root, "pyproject.toml") + readAt(root, "setup.cfg"));
  if (mutationWord || mutTool)
    hit(s, 5, mutationWord ? "selftests force red mutations" : "mutation-testing tool configured");
  else miss(s, "no mutation proof — the checks have never been shown to catch a break");

  const score = dims.reduce((a, d) => a + d.points, 0);
  return { score, grade: grade(score), dimensions: dims };
}

// ---- CLI -----------------------------------------------------------------------
export async function audit(flags) {
  const root = repoRoot();
  const report = scoreRepo(root);
  if (flags.json) {          // machine mode: the report and NOTHING else on stdout
    console.log(JSON.stringify(report, null, 2));
    return;
  }
  console.log(`vteam audit — AI-agent accountability · ${root}\n`);
  console.log(`  ${report.score}/100 · grade ${report.grade}    (A ≥85 · B ≥70 · C ≥55 · D ≥35 · F <35)\n`);
  for (const d of report.dimensions) {
    console.log(`${d.name.padEnd(13)}${String(d.points).padStart(3)}/${d.max}`);
    for (const f of d.found) console.log(`   ✅ ${f}`);
    for (const m of d.missing) console.log(`   ❌ ${m}`);
    if (d.points < d.max) console.log(`   → a machine would need to see: ${d.fix}`);
  }
  console.log("");
  if (fs.existsSync(path.join(root, ".vteam", "manifest.json"))) {
    console.log(report.score < 100
      ? "vteam is installed — every ❌ above is un-wired accountability. Verify the install: npx vteam-harness doctor"
      : "Fully machine-checked. Keep the reds honest: npx vteam-harness doctor");
  } else if (report.score < 70) {
    console.log(`Every ❌ above is a claim an AI agent can make without proof.
Close the gap in one command:  npx vteam-harness init
(15 machine gates · evidence pinned to commits · every gate ships a --selftest that proves it can fail)`);
  } else {
    console.log(`Solid base — the ❌ lines are where an agent can still self-report "done".
The missing machinery is one command away:  npx vteam-harness init`);
  }
}

// ---- selftest -------------------------------------------------------------------
function put(root, rel, text) {
  const abs = path.join(root, ...rel.split("/"));
  fs.mkdirSync(path.dirname(abs), { recursive: true });
  fs.writeFileSync(abs, text);
}
function git(cwd, ...args) {
  spawnSync("git", args, { cwd, encoding: "utf8", stdio: ["ignore", "pipe", "ignore"] });
}
function fixtureRepo(tmp, name) {
  const dir = path.join(tmp, name);
  fs.mkdirSync(dir, { recursive: true });
  git(dir, "init", "-q", "-b", "main");
  git(dir, "config", "user.email", "selftest@vteam");
  git(dir, "config", "user.name", "selftest");
  return dir;
}

function selftest() {
  const assert = (cond, msg) => {
    if (!cond) { console.error(`audit selftest FAILED: ${msg}`); process.exit(1); }
  };
  const tmp = fs.mkdtempSync(path.join(os.tmpdir(), "vteam-audit-selftest-"));
  try {
    // LOW — a bare repo: nothing can fail red anywhere.
    const lowDir = fixtureRepo(tmp, "low");
    put(lowDir, "README.md", "# bare\n");
    git(lowDir, "add", "-A"); git(lowDir, "commit", "-qm", "init");

    // MID — honest OSS shape: CI + tests, zero agent-accountability machinery.
    const midDir = fixtureRepo(tmp, "mid");
    put(midDir, "package.json", JSON.stringify({ scripts: { test: "node --test" } }));
    put(midDir, "tests/app.test.js", "// real tests live here\n");
    put(midDir, ".github/workflows/ci.yml", "name: ci\non: [push]\njobs:\n  t:\n    runs-on: ubuntu-latest\n    steps:\n      - run: npm test\n");
    git(midDir, "add", "-A"); git(midDir, "commit", "-qm", "init");

    // HIGH — vteam-shaped: manifest + live hooks + selftests + committed evidence.
    const highDir = fixtureRepo(tmp, "high");
    put(highDir, "package.json", JSON.stringify({ scripts: { test: "node tests/e2e.mjs" } }));
    put(highDir, "tests/e2e.mjs", "// suite\n");
    put(highDir, ".github/workflows/vteam-gate.yml",
      "name: vteam gate\non: [push]\njobs:\n  gate:\n    runs-on: ubuntu-latest\n    steps:\n      - run: bash .vteam/scripts/gate.sh\n");
    put(highDir, ".githooks/pre-push",
      "#!/usr/bin/env bash\n# No direct pushes to main — branch + PR.\n# SECRET SCAN (fail closed): ghp_/AKIA token patterns.\nexit 1\n");
    git(highDir, "config", "core.hooksPath", ".githooks");
    put(highDir, ".vteam/manifest.json",
      JSON.stringify({ version: "0.0.0-selftest", files: { "docs/team/ops.md": "0".repeat(64) } }));
    for (const gate of ["gate.py", "evd_check.py", "stale_verdict_check.py"])
      put(highDir, `.vteam/scripts/${gate}`, "# --selftest: green fixture + red mutations (mutation proof)\n");
    put(highDir, "evd/DEMO-1/review-1.md",
      "APPROVE — reviewed at commit 0123456789abcdef0123456789abcdef01234567\n");
    put(highDir, "docs/pm/log.md", "2026-01-01 · DEMO-1 · RESULT: done\n");
    put(highDir, "docs/pm/decisions.md", "D1 — decided.\n");
    put(highDir, "docs/qa/known-issues.md", "none\n");
    git(highDir, "add", "-A"); git(highDir, "commit", "-qm", "fixture");

    const low = scoreRepo(lowDir), mid = scoreRepo(midDir), high = scoreRepo(highDir);
    for (const rep of [low, mid, high]) {   // shape sanity — the --json contract
      assert(rep.dimensions.reduce((a, d) => a + d.max, 0) === 100, "dimension maxima must sum to 100");
      assert(rep.dimensions.every((d) => d.points >= 0 && d.points <= d.max &&
        d.name && d.fix && Array.isArray(d.found) && Array.isArray(d.missing)), "dimension shape");
      assert(rep.grade === grade(rep.score), "grade matches score");
    }
    assert(low.score < 30, `bare repo must score <30, got ${low.score}`);
    assert(low.dimensions.some((d) => d.points === 0),
      "low fixture must have at least one fully-red dimension");
    assert(low.score < mid.score && mid.score < high.score,
      `ordering low<mid<high violated: ${low.score} / ${mid.score} / ${high.score}`);
    assert(high.score >= 70, `vteam-shaped repo must score ≥70, got ${high.score}`);
    // mutation half — pull the manifest out of the high fixture: the score MUST drop
    fs.rmSync(path.join(highDir, ".vteam", "manifest.json"));
    const mutated = scoreRepo(highDir);
    assert(mutated.score < high.score,
      `manifest-removal mutation must lower the score: ${mutated.score} !< ${high.score}`);
    console.log(`audit selftest: OK (low=${low.score} < mid=${mid.score} < high=${high.score}; manifest mutation red → ${mutated.score})`);
  } finally {
    fs.rmSync(tmp, { recursive: true, force: true });
  }
}

// ---- entrypoint -------------------------------------------------------------------
const isMain = process.argv[1] &&
  import.meta.url === pathToFileURL(path.resolve(process.argv[1])).href;
if (isMain) {
  try {
    const argv = process.argv.slice(2);
    if (argv.includes("--selftest") || argv.includes("selftest")) selftest();
    else await audit({ json: argv.includes("--json") });
  } catch (e) {
    console.error(`audit: ${e.message}`);
    process.exit(1);
  }
}
