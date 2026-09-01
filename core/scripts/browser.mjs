// browser.mjs — the ONE headed-Chrome launcher for watchable browser runs.
//
// Why: qa.md demanded a "HEADED" run four times while naming no mechanism, so
// every session improvised (or quietly went headless). This is the mechanism:
// a REAL Chrome window (`channel: "chrome", headless: false`) the owner can
// watch, slowed just enough to follow. QA journey scripts import it; the same
// helper serves /dev when a change needs to be SEEN before it is captured.
//
// As a library (from evd/<TICKET>/TC_<n>/journey.mjs):
//   import { launch, shot } from "../../../.vteam/scripts/browser.mjs";
//   const { browser, page, headed } = await launch();
//   await page.goto(url);
//   await shot(page, new URL(".", import.meta.url).pathname, 1, "orders_list");
//   await browser.close();
//
// As a CLI:
//   node .vteam/scripts/browser.mjs check      # is Playwright + a Chrome usable here?
//   node .vteam/scripts/browser.mjs --selftest
//
// Headed unless: config `app.headed: never` (unattended 24/7 shifts — the
// visibility drops, NEVER the screenshots) or env EVD_HEADED=0 (EVD_HEADED=1
// forces headed over config). Playwright is the TARGET repo's dependency —
// missing = a loud error naming the install command, never a silent fallback.
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import process from "node:process";
import { pathToFileURL } from "node:url";

const INSTALL_HINT =
  "playwright is not installed in this repo — install it as a dev dependency:\n" +
  "  npm i -D playwright   (then: npx playwright install chrome  — or use the OS Chrome)";

async function playwright() {
  try {
    return await import("playwright");
  } catch {
    throw new Error(INSTALL_HINT);
  }
}

/** Headed unless config/env says otherwise. Config is optional here: outside an
 * installed repo (or with no `app:` section) the default is simply headed. */
export async function wantHeaded() {
  if (process.env.EVD_HEADED === "0") return false;
  if (process.env.EVD_HEADED === "1") return true;
  try {
    // sibling context layer: lib/ctx.mjs sits next to this file in .vteam/scripts
    const { Ctx } = await import(new URL("./lib/ctx.mjs", import.meta.url).href);
    return new Ctx().cfg("app.headed", "auto") !== "never";
  } catch {
    return true; // no repo / no config → a human is running this by hand: headed
  }
}

/** Launch a real Chrome, visibly by default. Returns { browser, context, page,
 * headed }. Prefers the machine's installed Chrome (channel: "chrome"), falls
 * back to Playwright's bundled Chromium with a notice — a missing OS Chrome
 * must not block a verification run. */
export async function launch({ headed, viewport = { width: 1280, height: 800 }, slowMo } = {}) {
  headed ??= await wantHeaded();
  slowMo ??= Number(process.env.EVD_SLOWMO ?? (headed ? 150 : 0));
  const { chromium } = await playwright();
  let browser;
  try {
    browser = await chromium.launch({ channel: "chrome", headless: !headed, slowMo });
  } catch {
    console.error("browser.mjs: OS Chrome unavailable — using Playwright's bundled Chromium " +
      "(npx playwright install chrome to use the real one)");
    browser = await chromium.launch({ headless: !headed, slowMo });
  }
  const context = await browser.newContext({ viewport });
  const page = await context.newPage();
  return { browser, context, page, headed };
}

/** Full-page screenshot named to the evidence standard: NN_<what>.png (the
 * same grammar evd_ui_check enforces on the dev layer — enforced here by
 * construction so QA files never drift from it). Returns the written path. */
export async function shot(page, dir, nn, name) {
  const n = Number(nn);
  if (!Number.isInteger(n) || n < 1 || n > 99) {
    throw new Error(`shot: nn must be an integer 1..99 (got ${JSON.stringify(nn)})`);
  }
  const clean = String(name ?? "").trim().toLowerCase()
    .replace(/\.png$/, "").replace(/[^\w-]+/g, "_").replace(/^_+|_+$/g, "");
  if (!clean) throw new Error("shot: name the file after what it SHOWS (e.g. 'orders_list'), not empty");
  fs.mkdirSync(dir, { recursive: true });
  const file = path.join(dir, `${String(n).padStart(2, "0")}_${clean}.png`);
  await page.screenshot({ path: file, fullPage: true });
  return file;
}

// ---- CLI ----------------------------------------------------------------------
async function check() {
  let pw;
  try {
    pw = await import("playwright");
  } catch {
    console.error(`❌ browser: ${INSTALL_HINT}`);
    process.exit(1);
  }
  try {
    const b = await pw.chromium.launch({ channel: "chrome", headless: true });
    await b.close();
    console.log("✅ browser: Playwright + OS Chrome ready (headed runs use the real Chrome window)");
  } catch {
    try {
      const b = await pw.chromium.launch({ headless: true });
      await b.close();
      console.log("✅ browser: Playwright ready (bundled Chromium — `npx playwright install chrome` for the real one)");
    } catch (e) {
      console.error(`❌ browser: Playwright installed but no launchable browser (${e.message.split("\n")[0]})\n` +
        "  npx playwright install chrome");
      process.exit(1);
    }
  }
}

async function selftest() {
  const fail = (m) => { console.error(`browser selftest: FAIL — ${m}`); process.exit(1); };
  // shot()'s naming contract needs no browser — prove it first, always
  const fakePage = { screenshot: async ({ path: p }) => fs.writeFileSync(p, "png") };
  const td = fs.mkdtempSync(path.join(os.tmpdir(), "vteam-browser-"));
  try {
    const p = await shot(fakePage, td, 3, "Orders List: after save!");
    if (path.basename(p) !== "03_orders_list_after_save.png") fail(`shot naming: ${path.basename(p)}`);
    if (!fs.existsSync(p)) fail("shot did not write the file");
    let reds = 0; // mutations: bad inputs must throw, never write a lawless name
    for (const [nn, name] of [[0, "x"], ["七", "x"], [1, "!!!"], [1, ""]]) {
      try { await shot(fakePage, td, nn, name); } catch { reds++; }
    }
    if (reds !== 4) fail(`shot accepted ${4 - reds} lawless input(s)`);
  } finally {
    fs.rmSync(td, { recursive: true, force: true });
  }
  try {
    await import("playwright");
  } catch {
    console.log("browser selftest: OK (shot naming green + 4 mutations red; launch SKIPPED — " +
      "playwright not installed here; QA runs need it: npm i -D playwright)");
    return;
  }
  // playwright present → a real (headless — selftests never pop windows) launch + shot
  const td2 = fs.mkdtempSync(path.join(os.tmpdir(), "vteam-browser-"));
  try {
    const { browser, page, headed } = await launch({ headed: false });
    if (headed !== false) fail("explicit headed:false ignored");
    await page.goto("about:blank");
    const p = await shot(page, td2, 1, "blank");
    await browser.close();
    const size = fs.statSync(p).size;
    if (size === 0) fail("real screenshot is 0 bytes");
    console.log("browser selftest: OK (shot naming green + 4 mutations red + real launch/screenshot green)");
  } finally {
    fs.rmSync(td2, { recursive: true, force: true });
  }
}

const isMain = process.argv[1] &&
  import.meta.url === pathToFileURL(path.resolve(process.argv[1])).href;
if (isMain) {
  const arg = process.argv[2];
  try {
    if (arg === "--selftest") await selftest();
    else if (arg === "check") await check();
    else { console.log("usage: node browser.mjs check | --selftest"); process.exit(arg ? 1 : 0); }
  } catch (e) {
    console.error(`❌ browser: ${e.message}`);
    process.exit(1);
  }
}
