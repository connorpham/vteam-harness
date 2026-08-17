// Measure design fidelity in NUMBERS, not by eye (/dev T4a self-review).
//
// Why: "this screen matches the design" used to be uncheckable testimony —
// the side-by-side image proves layout, but slightly-off colors/type/spacing
// escape the eye and force reviewers to re-measure. This reads REAL computed
// styles from the browser (after a real sign-in) and compares them against the
// design values the dev extracted from the design source's node data. Results
// land in <evidence>/<TICKET>/dev/fidelity.md — every "match" is a machine
// number.
//
// Usage:
//   node ui_fidelity.mjs <TICKET> [spec.json]   # default spec: <evd>/<T>/dev/fidelity.json
//
// fidelity.json — written BEFORE measuring; expected values come from the
// design node data, NEVER from your own code (measuring code with code is
// self-grading):
// { "user": "admin" | "anon": true, "path": "/admin/products",
//   "viewport": {"width":1280,"height":800},
//   "checks": [ { "selector": "h1", "note": "title — node 12:34",
//                 "expect": { "color": "#111827", "font-size": "24px" },
//                 "intent": "a11y: darker than frame — frame fails 4.5:1 contrast" } ] }
//
// A mismatch WITH a valid intent = INTENDED (not a failure, reason printed).
// Intents are a CLOSED list: must start with "a11y:" | "spec:" | "SRS:" |
// "responsive:" + a reason ≥10 chars — "felt nicer" counts as WRONG.
// Tolerances: colors/font-size/weight = 0 absolute; sizing/spacing px = ±0.75
// (subpixel rounding on correctly declared tokens).

import { chromium } from "playwright";
import { readFileSync, writeFileSync, mkdirSync, existsSync } from "node:fs";
import { execSync } from "node:child_process";
import { loadAuth } from "./auth.mjs";

const [ticket, specArg] = process.argv.slice(2);
if (!ticket) {
  console.error("usage: node ui_fidelity.mjs <TICKET> [spec.json]");
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
const DIR = `${ROOT}/${EVD}/${ticket}/dev`;
const SPEC = specArg ?? `${DIR}/fidelity.json`;
if (!existsSync(SPEC)) {
  console.error(`❌ ${SPEC} missing — write the spec (selectors + expects from design node data) BEFORE measuring`);
  process.exit(1);
}
const spec = JSON.parse(readFileSync(SPEC, "utf8"));
if (!Array.isArray(spec.checks) || spec.checks.length === 0) {
  console.error("❌ fidelity.json has no checks — an empty spec is not measuring");
  process.exit(1);
}
mkdirSync(DIR, { recursive: true });

const toKebab = (k) => k.replace(/[A-Z]/g, (c) => "-" + c.toLowerCase());
const hex = (n) => Number(n).toString(16).padStart(2, "0").toUpperCase();
function normColor(v) {
  const m = String(v).trim().match(/^rgba?\((\d+),\s*(\d+),\s*(\d+)(?:,\s*([\d.]+))?\)$/);
  if (m) {
    const a = m[4] === undefined ? 1 : Number(m[4]);
    return a === 1 ? `#${hex(m[1])}${hex(m[2])}${hex(m[3])}` : `rgba(${m[1]},${m[2]},${m[3]},${a})`;
  }
  return String(v).trim().toUpperCase();
}
function compare(prop, expected, measured) {
  const p = toKebab(prop);
  if (/color/.test(p)) return normColor(expected) === normColor(measured);
  const pe = parseFloat(expected), pm = parseFloat(measured);
  // font-size: zero tolerance — 13.5px is 13.5px; type scales have no "close enough"
  if (p === "font-size" && !Number.isNaN(pe) && !Number.isNaN(pm)) return pe === pm;
  if (String(expected).endsWith("px") && !Number.isNaN(pe) && !Number.isNaN(pm))
    return Math.abs(pe - pm) <= 0.75;
  if (p === "font-family")
    return String(measured).toLowerCase().includes(
      String(expected).split(",")[0].trim().toLowerCase().replace(/['"]/g, ""));
  return String(expected).trim().toLowerCase() === String(measured).trim().toLowerCase();
}

const INTENT_OK = /^(a11y|spec|SRS|responsive)\s*[:：]\s*.{10,}/;

const signIn = await loadAuth();
const browser = await chromium.launch({ channel: "chrome" });
const context = await browser.newContext({ viewport: spec.viewport ?? { width: 1280, height: 800 } });
const rows = [];
let wrong = 0, intended = 0;
try {
  if (!spec.anon && !PASSWORD) throw new Error("EVD_PASSWORD not set — no default password ships");
  // `"anon": true` = measure a signed-out screen (the login screen itself) —
  // otherwise the first screen every user meets is the only unmeasurable one.
  const user = spec.anon ? { role: "ANONYMOUS" } : await signIn(context, BASE, spec.user, PASSWORD);
  const page = await context.newPage();
  const res = await page.goto(BASE + spec.path, { waitUntil: "networkidle" });
  if (!res || res.status() >= 400) throw new Error(`${spec.path} returned HTTP ${res?.status()}`);
  console.log(`▶ measuring ${spec.path} (role ${user.role})`);

  for (const check of spec.checks) {
    const el = page.locator(check.selector).first();
    if ((await el.count()) === 0) {
      wrong++;
      rows.push({ sel: check.selector, prop: "—", exp: "—", act: "ELEMENT NOT FOUND",
                  verdict: "❌ DEVIATION: WRONG", note: check.note ?? "" });
      continue;
    }
    for (const [prop, expected] of Object.entries(check.expect ?? {})) {
      const measured = await el.evaluate(
        (node, p) => getComputedStyle(node).getPropertyValue(p), toKebab(prop));
      const ok = compare(prop, expected, measured);
      let verdict = "✅ match";
      if (!ok) {
        if (typeof check.intent === "string" && INTENT_OK.test(check.intent.trim())) {
          intended++; verdict = `🟡 INTENDED — ${check.intent.trim()}`;
        } else if (typeof check.intent === "string" && check.intent.trim()) {
          wrong++; verdict = `❌ DEVIATION: WRONG (intent "${check.intent.trim().slice(0, 40)}" outside the closed list a11y:/spec:/responsive:)`;
        } else {
          wrong++; verdict = "❌ DEVIATION: WRONG";
        }
      }
      rows.push({ sel: check.selector, prop: toKebab(prop), exp: String(expected),
                  act: /color/.test(toKebab(prop)) ? normColor(measured) : String(measured).trim(),
                  verdict, note: check.note ?? "" });
    }
  }
} catch (err) {
  console.error(`❌ ui_fidelity: ${err.message}`);
  await browser.close();
  process.exit(1);
}
await browser.close();

const tbl = rows.map((r) => `| \`${r.sel}\` | ${r.prop} | ${r.exp} | ${r.act} | ${r.verdict} | ${r.note} |`).join("\n");
writeFileSync(`${DIR}/fidelity.md`, `# Fidelity — ${ticket} · ${spec.path}

Measured by \`ui_fidelity.mjs\` (browser computed styles after a real sign-in;
expecteds extracted from the design source's node data — see \`fidelity.json\`).
Tolerances: colors/font-size/weight = 0; sizing/spacing px ±0.75 (subpixel).
Result: **${rows.length} measurements · ${rows.length - wrong - intended} match · ${intended} intended deviations (with reasons) · ${wrong} wrong**.

| Selector | Property | Design | Measured | Verdict | Note |
|---|---|---|---|---|---|
${tbl}
`);
console.log(`\n${rows.length} measurements · ${rows.length - wrong - intended} match · ${intended} intended · ${wrong} wrong → ${DIR}/fidelity.md`);
if (wrong > 0) {
  console.error(`❌ ${wrong} deviations WITHOUT a sanctioned intent — fix the code or declare a closed-list intent, then re-measure`);
  process.exit(1);
}
console.log("✅ fidelity holds — every remaining deviation is intended, with a reason");
