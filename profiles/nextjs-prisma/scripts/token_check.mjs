// Every Tailwind class used in the code MUST really emit a CSS rule.
//
// Why: during a 128-value hardcoded-color → token migration, a rewrite mapped a
// color to a token name that was NEVER DECLARED. Tailwind v4 skips unknown
// classes IN SILENCE: no warning, no build error — the CSS rule simply doesn't
// exist. Header text lost its color and silently reversed a recorded decision,
// while lint, tsc, tests and build all stayed green.
//
// HOW IT MEASURES — this is the second design, and the change matters:
// the first version compared token names against the declared `--color-*` list
// plus an "ignore" list for structural utilities. That list was wrong in BOTH
// directions (swallowed real tokens sharing a prefix; flagged valid utilities
// off-list) — and the cheapest escape for anyone hitting a false positive was
// ADDING TO THE LIST, i.e. reopening the exact hole. The real criterion isn't
// "does this look like a utility" but **"did Tailwind emit a rule for this
// class"** — the actual symptom of the actual disease. No list to maintain.
// The price: this step must run AFTER the build, since it reads emitted CSS.
import { readFileSync, readdirSync, statSync, existsSync } from "node:fs";
import { join } from "node:path";
import { execSync } from "node:child_process";

const ROOT = execSync("git rev-parse --show-toplevel", { encoding: "utf8" }).trim();

/**
 * Extract class names from a code snippet.
 * Leading boundary includes quotes/braces/commas: the FIRST class of every
 * quoted string used to sit in a blind spot. The variant chain is ARBITRARY
 * (`xl:`, `peer-checked:`, `data-[open]:`, `!`) — Tailwind allows custom
 * variants, so a hardcoded list never keeps up.
 */
const CLASS_RE =
  /(?:^|[\s"'`{(,[])((?:[a-z0-9@._[\]-]+:)*!?(?:bg|text|border|outline|ring|fill|stroke|decoration|shadow|from|via|to)-[a-z][a-z0-9./[\]#%_-]*)/g;

export function classesIn(txt) {
  return [...txt.matchAll(CLASS_RE)].map((m) => m[1]);
}

function files(dir, pat) {
  return readdirSync(dir).flatMap((n) => {
    const p = join(dir, n);
    if (statSync(p).isDirectory()) return n === "generated" ? [] : files(p, pat);
    return pat.test(n) ? [p] : [];
  });
}

/** SELF-CHECK the extractor before checking anyone else (fixtures file). */
function selfCheck() {
  const F = join(import.meta.dirname, "token_check.fixtures.txt");
  const bad = [];
  for (const line of readFileSync(F, "utf8").split("\n")) {
    if (!line.trim() || line.startsWith("#")) continue;
    const [expect, code] = line.split("\t");
    if (!code) continue;
    const found = classesIn(code).length > 0;
    if ((expect === "FOUND") !== found) {
      bad.push(`  ${expect === "FOUND" ? "MISSED " : "FALSE+ "}: ${code.trim()}`);
    }
  }
  if (bad.length) {
    console.log(`❌ GATE SELF-CHECK FAILED — ${bad.length} cases:\n${bad.join("\n")}`);
    console.log("\nFix CLASS_RE here, or the expectation in token_check.fixtures.txt.");
    process.exit(1);
  }
}

selfCheck();
if (process.argv.includes("--selftest")) {
  console.log("token_check selftest: OK (extractor matrix green)");
  process.exit(0);
}

// --- compare against emitted CSS ---------------------------------------------
const DIST = join(ROOT, ".next/static/chunks");
if (!existsSync(DIST)) {
  console.log("❌ no built CSS yet — this step must run AFTER `next build`");
  process.exit(1);
}
const cssFiles = readdirSync(DIST).filter((n) => n.endsWith(".css"));
const CSS = cssFiles.map((n) => readFileSync(join(DIST, n), "utf8")).join("\n");

// The CSS must be FRESH, not merely present: deleting a token and running the
// gate without rebuilding once produced a false green on the exact original bug.
const newest = (dir, pat) => Math.max(...files(dir, pat).map((f) => statSync(f).mtimeMs), 0);
const cssMs = Math.max(...cssFiles.map((n) => statSync(join(DIST, n)).mtimeMs), 0);
const srcMs = newest(join(ROOT, "src"), /\.(?:[jt]sx?|mjs|css)$/);
if (cssMs < srcMs) {
  console.log("❌ built CSS is older than the source — run `next build`, then measure.");
  console.log(`   CSS: ${new Date(cssMs).toISOString()}  ·  src: ${new Date(srcMs).toISOString()}`);
  process.exit(1);
}
if (!CSS) {
  console.log("❌ no CSS files found in .next/static/chunks");
  process.exit(1);
}

/**
 * Did Tailwind emit a rule for this class? Search by the FULL escaped name
 * including variants (`hover:bg-x` emits `.hover\:bg-x:hover{…}`). There is
 * deliberately NO fallback that strips variants and searches the base name:
 * that branch existed once, and it reopened the exact bug class this gate
 * exists to catch (`hoverr:text-ink` — typo'd variant, valid base — passed).
 */
function hasRule(cls) {
  const esc = cls.replace(/[.:/[\]#%()!]/g, (c) => "\\" + c);
  return CSS.includes(`.${esc}`);
}

const missing = new Set();
for (const f of files(join(ROOT, "src"), /\.(?:[jt]sx?|mjs)$/)) {
  for (const cls of classesIn(readFileSync(f, "utf8"))) {
    if (!hasRule(cls)) missing.add(`${f.replace(ROOT + "/", "")}: ${cls}`);
  }
}

if (missing.size) {
  console.log(`❌ ${missing.size} classes emit NO CSS rule — Tailwind is skipping them silently:\n`);
  for (const k of missing) console.log(`  ${k}`);
  console.log("\nUsually an undeclared @theme token, or a typo'd class name.");
  console.log("Known limit: dynamically composed classes (`text-${x}`) can't be scanned.");
  process.exit(1);
}
console.log("✅ every Tailwind class in src/ emits a real CSS rule");
