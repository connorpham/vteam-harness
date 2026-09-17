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
//   node ui_fidelity.mjs --selftest             # the comparison rules, no browser needed
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
//
// Structure (VT-25): the comparison rules are exported and proven by --selftest;
// playwright is imported lazily inside main(), so the rules can be tested on a
// machine with no browser and the tool still refuses loudly without one.

import { readFileSync, writeFileSync, mkdirSync, existsSync } from "node:fs";
import path from "node:path";
import process from "node:process";
import { execSync } from "node:child_process";
import { pathToFileURL } from "node:url";
import { loadAuth } from "./auth.mjs";

// ── the rules (pure) ─────────────────────────────────────────────────────────
export const toKebab = (k) => k.replace(/[A-Z]/g, (c) => "-" + c.toLowerCase());
const hex = (n) => Number(n).toString(16).padStart(2, "0").toUpperCase();

export function normColor(v) {
  const m = String(v).trim().match(/^rgba?\((\d+),\s*(\d+),\s*(\d+)(?:,\s*([\d.]+))?\)$/);
  if (m) {
    const a = m[4] === undefined ? 1 : Number(m[4]);
    return a === 1 ? `#${hex(m[1])}${hex(m[2])}${hex(m[3])}` : `rgba(${m[1]},${m[2]},${m[3]},${a})`;
  }
  return String(v).trim().toUpperCase();
}

export function compare(prop, expected, measured) {
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

export const INTENT_OK = /^(a11y|spec|SRS|responsive)\s*[:：]\s*.{10,}/;

/** The verdict for one measurement — the string fidelity.md carries and
 * evd_ui_check greps (`DEVIATION: WRONG` reds the DEV evidence). */
export function verdictFor(ok, intent) {
  if (ok) return { verdict: "✅ match", kind: "match" };
  if (typeof intent === "string" && INTENT_OK.test(intent.trim())) {
    return { verdict: `🟡 INTENDED — ${intent.trim()}`, kind: "intended" };
  }
  if (typeof intent === "string" && intent.trim()) {
    return { verdict: `❌ DEVIATION: WRONG (intent "${intent.trim().slice(0, 40)}" outside the closed list a11y:/spec:/responsive:)`, kind: "wrong" };
  }
  return { verdict: "❌ DEVIATION: WRONG", kind: "wrong" };
}

/** fidelity.json must carry a non-empty checks array — an empty spec is not measuring. */
export function specProblem(spec) {
  if (!spec || typeof spec !== "object" || Array.isArray(spec)) return "fidelity.json is not an object";
  if (!Array.isArray(spec.checks) || spec.checks.length === 0) return "fidelity.json has no checks — an empty spec is not measuring";
  return null;
}

export function renderFidelityMd(ticket, specPath, rows, wrong, intended) {
  const tbl = rows.map((r) => `| \`${r.sel}\` | ${r.prop} | ${r.exp} | ${r.act} | ${r.verdict} | ${r.note} |`).join("\n");
  return `# Fidelity — ${ticket} · ${specPath}

Measured by \`ui_fidelity.mjs\` (browser computed styles after a real sign-in;
expecteds extracted from the design source's node data — see \`fidelity.json\`).
Tolerances: colors/font-size/weight = 0; sizing/spacing px ±0.75 (subpixel).
Result: **${rows.length} measurements · ${rows.length - wrong - intended} match · ${intended} intended deviations (with reasons) · ${wrong} wrong**.

| Selector | Property | Design | Measured | Verdict | Note |
|---|---|---|---|---|---|
${tbl}
`;
}

// ── the run ──────────────────────────────────────────────────────────────────
async function main(argv) {
  const [ticket, specArg] = argv;
  if (!ticket) {
    console.error("usage: node ui_fidelity.mjs <TICKET> [spec.json] | --selftest");
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
  const DIR = `${ROOT}/${EVD}/${ticket}/dev`;
  const SPEC = specArg ?? `${DIR}/fidelity.json`;
  if (!existsSync(SPEC)) {
    console.error(`❌ ${SPEC} missing — write the spec (selectors + expects from design node data) BEFORE measuring`);
    process.exit(1);
  }
  const spec = JSON.parse(readFileSync(SPEC, "utf8"));
  const problem = specProblem(spec);
  if (problem) {
    console.error(`❌ ${problem}`);
    process.exit(1);
  }
  mkdirSync(DIR, { recursive: true });

  let chromium;
  try { ({ chromium } = await import("playwright")); }
  catch {
    console.error("❌ ui_fidelity: playwright is not installed in this repo — npm i -D playwright (then npx playwright install chrome)");
    process.exit(1);
  }
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
        const { verdict, kind } = verdictFor(compare(prop, expected, measured), check.intent);
        if (kind === "intended") intended++;
        if (kind === "wrong") wrong++;
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

  writeFileSync(`${DIR}/fidelity.md`, renderFidelityMd(ticket, spec.path, rows, wrong, intended));
  console.log(`\n${rows.length} measurements · ${rows.length - wrong - intended} match · ${intended} intended · ${wrong} wrong → ${DIR}/fidelity.md`);
  if (wrong > 0) {
    console.error(`❌ ${wrong} deviations WITHOUT a sanctioned intent — fix the code or declare a closed-list intent, then re-measure`);
    process.exit(1);
  }
  console.log("✅ fidelity holds — every remaining deviation is intended, with a reason");
}

// ── selftest: the rules, without a browser ───────────────────────────────────
function selftest() {
  const fails = [];
  const ok = (cond, msg) => { if (!cond) fails.push(msg); };
  // colours: browser rgb() and design hex are the same colour; alpha survives; case does not matter
  ok(normColor("rgb(17, 24, 39)") === "#111827", "rgb → hex");
  ok(normColor("rgba(17, 24, 39, 0.5)") === "rgba(17,24,39,0.5)", "rgba keeps alpha");
  ok(compare("color", "#111827", "rgb(17, 24, 39)"), "design hex == measured rgb");
  ok(!compare("color", "#111828", "rgb(17, 24, 39)"), "one unit off is a different colour (0 tolerance)");
  ok(compare("backgroundColor", "#FFFFFF", "rgb(255, 255, 255)"), "camelCase prop still reads as a colour");
  // font-size: zero tolerance; other px: ±0.75
  ok(compare("font-size", "13.5px", "13.5px") && !compare("font-size", "13.5px", "13.4px"), "font-size has no 'close enough'");
  ok(compare("padding-left", "16px", "16.5px") && !compare("padding-left", "16px", "17px"), "px tolerance is ±0.75");
  ok(compare("fontWeight", "600", "600") && !compare("fontWeight", "600", "700"), "weight: exact");
  ok(compare("font-family", '"Inter", sans-serif', "Inter, ui-sans-serif, system-ui"), "font-family matches on the first family");
  ok(!compare("font-family", "Roboto, sans-serif", "Inter, system-ui"), "wrong family is wrong");
  // the intent grammar is a CLOSED list with a real reason
  ok(INTENT_OK.test("a11y: darker than the frame — the frame fails 4.5:1"), "a11y intent with a reason");
  ok(INTENT_OK.test("spec: SRS 3.2 says 24px on mobile"), "spec intent");
  ok(!INTENT_OK.test("felt nicer"), "a vibe is not an intent");
  ok(!INTENT_OK.test("a11y: short"), "an intent needs ≥10 chars of reason");
  ok(!INTENT_OK.test("brand: the designer prefers it this way"), "an off-list prefix is not sanctioned");
  // the verdict rule — the strings fidelity.md carries
  ok(verdictFor(true, "felt nicer").kind === "match", "a match is a match whatever the intent says");
  ok(verdictFor(false, "a11y: darker than the frame — contrast 4.5:1").verdict.startsWith("🟡 INTENDED — a11y:"), "sanctioned intent → INTENDED");
  const off = verdictFor(false, "felt nicer");
  ok(off.kind === "wrong" && /DEVIATION: WRONG \(intent "felt nicer" outside the closed list/.test(off.verdict), "off-list intent → WRONG, naming the intent");
  ok(verdictFor(false, undefined).verdict === "❌ DEVIATION: WRONG", "no intent → WRONG");
  // the spec must measure something
  ok(specProblem({ checks: [] }) !== null && specProblem({ path: "/x" }) !== null && specProblem(null) !== null, "empty/absent checks refused");
  ok(specProblem({ checks: [{ selector: "h1", expect: {} }] }) === null, "a spec with a check is accepted");
  // the report the DEV gate reads: counts line + one row per measurement + the WRONG marker
  const md = renderFidelityMd("T-1", "/admin", [
    { sel: "h1", prop: "color", exp: "#111827", act: "#111827", verdict: "✅ match", note: "" },
    { sel: "h1", prop: "font-size", exp: "24px", act: "20px", verdict: "❌ DEVIATION: WRONG", note: "n" },
  ], 1, 0);
  ok(/2 measurements · 1 match · 0 intended deviations \(with reasons\) · 1 wrong/.test(md), "counts line");
  ok((md.match(/^\| `h1` \|/gm) || []).length === 2, "one table row per measurement");
  ok(/DEVIATION: WRONG/.test(md), "the marker evd_ui_check greps is in the file");
  if (fails.length) {
    console.error("ui_fidelity selftest: FAILED");
    for (const f of fails) console.error(`  x ${f}`);
    process.exit(1);
  }
  console.log("ui_fidelity selftest: OK (colour/px/font-size/weight/family rules, closed-list intents, verdict strings, spec guard, fidelity.md shape)");
}

const isMain = process.argv[1] && import.meta.url === pathToFileURL(path.resolve(process.argv[1])).href;
if (isMain) {
  if (process.argv.includes("--selftest")) selftest();
  else await main(process.argv.slice(2));
}
