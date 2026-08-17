// Browser evidence capture for UI tickets (/dev T4).
//
// Why: every UI ticket submits one screenshot per acceptance criterion, taken
// after a REAL sign-in through the app's auth flow — never forged cookies.
// Rewriting that flow per ticket is wasteful and error-prone; this is the
// shared tool.
//
// Usage:
//   node .vteam/profiles/nextjs-prisma/scripts/ui-evidence.mjs <TICKET> shots.json
// shots.json is an array of { user, path, file, label, anon?, click?, fill?, viewport? }
//   user  = login name for the role · anon = capture WITHOUT signing in
//   click = selector(s) to click before capturing (post-interaction states are
//           evidence too, not just the load state)
//   fill  = [[selector, value], …] fill-then-blur — form ERROR states only appear
//           after input + blur
//   viewport (optional {width,height}) — match the design frame box; default 1280×800
// Password comes from EVD_PASSWORD (no default ships — a framework must not
// carry seed passwords). Base URL: EVD_BASE_URL (default http://localhost:3000).
// Auth strategy: ./auth.mjs (swap via EVD_AUTH_MODULE).
//
// Uses the machine's installed Chrome (channel: "chrome").

import { chromium } from "playwright";
import { readFileSync, mkdirSync } from "node:fs";
import { execSync } from "node:child_process";
import { loadAuth } from "./auth.mjs";

const [ticket, shotsFile] = process.argv.slice(2);
if (!ticket || !shotsFile) {
  console.error("usage: node ui-evidence.mjs <TICKET> <shots.json>");
  process.exit(1);
}

const ROOT = execSync("git rev-parse --show-toplevel", { encoding: "utf8" }).trim();
const BASE = process.env.EVD_BASE_URL ?? "http://localhost:3000";
const PASSWORD = process.env.EVD_PASSWORD;
const EVD = (() => {
  try {
    return execSync("python3 .vteam/scripts/lib/ctx.py paths.evidence", { cwd: ROOT, encoding: "utf8" }).trim();
  } catch { return "evd"; }
})();
const OUT = `${ROOT}/${EVD}/${ticket}/dev`; // DEV lane writes under dev/ — the root layer belongs to QA
const shots = JSON.parse(readFileSync(shotsFile, "utf8"));
mkdirSync(OUT, { recursive: true });

const signIn = await loadAuth();
const browser = await chromium.launch({ channel: "chrome" });
let failed = 0;
for (const { user: u, path, file, label, viewport, anon, click, fill } of shots) {
  const context = await browser.newContext({ viewport: viewport ?? { width: 1280, height: 800 } });
  try {
    if (!anon && !PASSWORD) throw new Error("EVD_PASSWORD not set — no default password ships");
    // `anon: true` = capture signed OUT (the login screen itself, 401 pages) —
    // without it, the screens ABOUT being signed out are the only unprovable ones.
    const user = anon ? { role: "ANONYMOUS" } : await signIn(context, BASE, u, PASSWORD);
    const page = await context.newPage();
    const res = await page.goto(BASE + path, { waitUntil: "networkidle" });
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
    console.log(`${file.padEnd(36)} ${String(user.role).padEnd(10)} ${path.padEnd(20)} HTTP ${res.status()}  ${label ?? ""}`);
  } catch (err) {
    failed++;
    console.error(`${file.padEnd(36)} ERROR: ${err.message}`);
  } finally {
    await context.close();
  }
}
await browser.close();
process.exit(failed === 0 ? 0 : 1);
