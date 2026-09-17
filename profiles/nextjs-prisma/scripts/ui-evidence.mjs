// Browser evidence capture for UI tickets (/dev T4).
//
// Why: every UI ticket submits one screenshot per acceptance criterion, taken
// after a REAL sign-in through the app's auth flow — never forged cookies.
// Rewriting that flow per ticket is wasteful and error-prone; this is the
// shared tool.
//
// Usage:
//   node .vteam/profiles/nextjs-prisma/scripts/ui-evidence.mjs <TICKET> shots.json [--headless]
//   node .vteam/profiles/nextjs-prisma/scripts/ui-evidence.mjs --selftest
// shots.json is an array of { user, path, file, label, anon?, click?, fill?, viewport? }
//   user  = login name for the role · anon = capture WITHOUT signing in
//   click = selector(s) to click before capturing (post-interaction states are
//           evidence too, not just the load state)
//   fill  = [[selector, value], …] fill-then-blur — form ERROR states only appear
//           after input + blur
//   viewport (optional {width,height}) — match the design frame box; default 1280×800
// Password comes from EVD_PASSWORD (no default ships — a framework must not
// carry seed passwords). Base URL: EVD_BASE_URL → config app.url →
// http://localhost:3000. Auth strategy: ./auth.mjs (swap via EVD_AUTH_MODULE).
//
// Uses the machine's installed Chrome (channel: "chrome").
//
// HEADED by default: the browser visibly opens and walks each shot with a
// human-followable pace (slowMo) — the owner watches the app being used like a
// real user, the same standard the QA lane already holds ("a run the user
// could watch"). Headless is the EXCEPTION, not the default: pass --headless
// or set CI, for machines with no display.
//
// Structure (VT-25): argument parsing, the headed policy and the shots.json
// contract are exported and proven by --selftest; playwright is imported lazily
// inside main(), so the contract is testable on a machine with no browser.

import { readFileSync, mkdirSync } from "node:fs";
import path from "node:path";
import process from "node:process";
import { execSync } from "node:child_process";
import { pathToFileURL } from "node:url";
import { loadAuth } from "./auth.mjs";

// ── the contract (pure) ──────────────────────────────────────────────────────
export function parseArgs(argv) {
  const headlessFlag = argv.includes("--headless");
  const [ticket, shotsFile] = argv.filter((a) => a !== "--headless");
  return { ticket, shotsFile, headlessFlag };
}

/** headed unless: --headless, CI set, or config app.headed: never (an
 * unattended shift — the visibility drops, never the screenshots). */
export function wantHeadless({ headlessFlag = false, ci = "", appHeaded = "" } = {}) {
  return !!headlessFlag || !!ci || appHeaded === "never";
}

/** A shot the tool can actually take, or the reason it cannot. Before VT-25 a
 * shot with no `file` wrote to `<dir>/undefined` and one with no `user` failed
 * inside the sign-in with "sign-in failed for undefined". */
export function shotsProblem(shots) {
  if (!Array.isArray(shots) || shots.length === 0) return "shots.json must be a non-empty array";
  for (const [i, s] of shots.entries()) {
    const tag = `shot #${i + 1}`;
    if (!s || typeof s !== "object" || Array.isArray(s)) return `${tag} is not an object`;
    if (typeof s.path !== "string" || !s.path.startsWith("/")) return `${tag}: path must be a route starting with /`;
    if (typeof s.file !== "string" || !s.file.trim()) return `${tag}: file is required (the png name)`;
    if (!s.anon && (typeof s.user !== "string" || !s.user)) return `${tag}: user is required unless anon: true`;
    if (s.fill !== undefined && !(Array.isArray(s.fill) && s.fill.every((p) => Array.isArray(p) && p.length === 2)))
      return `${tag}: fill must be [[selector, value], …]`;
    if (s.click !== undefined && !(typeof s.click === "string" || (Array.isArray(s.click) && s.click.every((c) => typeof c === "string"))))
      return `${tag}: click must be a selector or a list of selectors`;
  }
  return null;
}

// ── the run ──────────────────────────────────────────────────────────────────
async function main(argv) {
  const { ticket, shotsFile, headlessFlag } = parseArgs(argv);
  if (!ticket || !shotsFile) {
    console.error("usage: node ui-evidence.mjs <TICKET> <shots.json> [--headless] | --selftest");
    process.exit(1);
  }
  const ROOT = execSync("git rev-parse --show-toplevel", { encoding: "utf8" }).trim();
  const cfg = (key) => { // one optional config value; absent key → ""
    try {
      return execSync(`python3 .vteam/scripts/lib/ctx.py ${key}`,
        { cwd: ROOT, encoding: "utf8", stdio: ["ignore", "pipe", "ignore"] }).trim();
    } catch { return ""; }
  };
  // base URL: env override → the repo's own app.url (vteam.config.yaml) → default
  const BASE = process.env.EVD_BASE_URL ?? (cfg("app.url") || "http://localhost:3000");
  const PASSWORD = process.env.EVD_PASSWORD;
  const EVD = cfg("paths.evidence") || "evd";
  const OUT = `${ROOT}/${EVD}/${ticket}/dev`; // DEV lane writes under dev/ — the root layer belongs to QA
  const shots = JSON.parse(readFileSync(shotsFile, "utf8"));
  const problem = shotsProblem(shots);
  if (problem) {
    console.error(`❌ ${shotsFile}: ${problem}`);
    process.exit(1);
  }
  mkdirSync(OUT, { recursive: true });
  const HEADLESS = wantHeadless({ headlessFlag, ci: process.env.CI, appHeaded: cfg("app.headed") });

  let chromium;
  try { ({ chromium } = await import("playwright")); }
  catch {
    console.error("❌ ui-evidence: playwright is not installed in this repo — npm i -D playwright (then npx playwright install chrome)");
    process.exit(1);
  }
  const signIn = await loadAuth();
  // headed runs pace every action so a human can follow what the "user" does
  const browser = await chromium.launch({
    channel: "chrome",
    headless: HEADLESS,
    slowMo: HEADLESS ? 0 : 300,
  });
  if (!HEADLESS) console.log("HEADED run — watch the browser: it signs in and walks each screen like a real user (use --headless on machines with no display)");
  let failed = 0;
  for (const { user: u, path: route, file, label, viewport, anon, click, fill } of shots) {
    const context = await browser.newContext({ viewport: viewport ?? { width: 1280, height: 800 } });
    try {
      if (!anon && !PASSWORD) throw new Error("EVD_PASSWORD not set — no default password ships");
      // `anon: true` = capture signed OUT (the login screen itself, 401 pages) —
      // without it, the screens ABOUT being signed out are the only unprovable ones.
      const user = anon ? { role: "ANONYMOUS" } : await signIn(context, BASE, u, PASSWORD);
      const page = await context.newPage();
      const res = await page.goto(BASE + route, { waitUntil: "networkidle" });
      if (fill) {
        for (const [sel, val] of fill) {
          await page.fill(sel, String(val));
          await page.locator(sel).blur();
        }
        await page.waitForTimeout(200);
      }
      if (click) {
        for (const sel of [].concat(click)) await page.click(sel);
        await page.waitForTimeout(150);
      }
      await page.screenshot({ path: `${OUT}/${file}`, fullPage: true });
      console.log(`${file.padEnd(36)} ${String(user.role).padEnd(10)} ${route.padEnd(20)} HTTP ${res.status()}  ${label ?? ""}`);
    } catch (err) {
      failed++;
      console.error(`${file.padEnd(36)} ERROR: ${err.message}`);
    } finally {
      await context.close();
    }
  }
  await browser.close();
  process.exit(failed === 0 ? 0 : 1);
}

// ── selftest: the contract, without a browser ────────────────────────────────
function selftest() {
  const fails = [];
  const ok = (cond, msg) => { if (!cond) fails.push(msg); };
  // args: --headless is a flag anywhere, never a positional
  let a = parseArgs(["T-1", "shots.json"]);
  ok(a.ticket === "T-1" && a.shotsFile === "shots.json" && !a.headlessFlag, "plain args");
  a = parseArgs(["--headless", "T-1", "shots.json"]);
  ok(a.ticket === "T-1" && a.shotsFile === "shots.json" && a.headlessFlag, "--headless first is still a flag");
  ok(parseArgs(["T-1"]).shotsFile === undefined, "a missing shots file is undefined, not the flag");
  // the headed policy: headed unless flag / CI / app.headed never
  ok(!wantHeadless({}), "default is HEADED");
  ok(wantHeadless({ headlessFlag: true }), "--headless → headless");
  ok(wantHeadless({ ci: "true" }), "CI → headless");
  ok(wantHeadless({ appHeaded: "never" }), "app.headed: never → headless");
  ok(!wantHeadless({ appHeaded: "auto" }), "app.headed: auto stays headed");
  // the shots contract
  const good = [{ user: "admin", path: "/admin", file: "01_admin_home.png", label: "home" },
                { anon: true, path: "/login", file: "02_login.png", click: "#more", fill: [["#q", "x"]] }];
  ok(shotsProblem(good) === null, "a valid shots.json is accepted");
  ok(/non-empty array/.test(shotsProblem([]) || ""), "empty list refused");
  ok(/user is required/.test(shotsProblem([{ path: "/x", file: "a.png" }]) || ""), "no user and not anon refused");
  ok(/file is required/.test(shotsProblem([{ user: "u", path: "/x" }]) || ""), "no file refused");
  ok(/path must be a route/.test(shotsProblem([{ user: "u", path: "x", file: "a.png" }]) || ""), "path without / refused");
  ok(/fill must be/.test(shotsProblem([{ user: "u", path: "/x", file: "a.png", fill: ["#q", "x"] }]) || ""), "flat fill refused");
  ok(/click must be/.test(shotsProblem([{ user: "u", path: "/x", file: "a.png", click: 3 }]) || ""), "non-selector click refused");
  if (fails.length) {
    console.error("ui-evidence selftest: FAILED");
    for (const f of fails) console.error(`  x ${f}`);
    process.exit(1);
  }
  console.log("ui-evidence selftest: OK (args + --headless flag, headed policy: default/flag/CI/app.headed, shots.json contract green + 6 refusals)");
}

const isMain = process.argv[1] && import.meta.url === pathToFileURL(path.resolve(process.argv[1])).href;
if (isMain) {
  if (process.argv.includes("--selftest")) selftest();
  else await main(process.argv.slice(2));
}
