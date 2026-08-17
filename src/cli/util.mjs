import fs from "node:fs";
import path from "node:path";
import readline from "node:readline";
import { fileURLToPath } from "node:url";
import { execSync } from "node:child_process";

export const pkgRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..", "..");

export function repoRoot() {
  try {
    return execSync("git rev-parse --show-toplevel", { encoding: "utf8" }).trim();
  } catch {
    return process.cwd();
  }
}

// ---- prompts ---------------------------------------------------------------
const rl = () => readline.createInterface({ input: process.stdin, output: process.stdout });

export async function ask(question, def) {
  const r = rl();
  const answer = await new Promise((res) => r.question(`${question}${def ? ` [${def}]` : ""}: `, res));
  r.close();
  return (answer || "").trim() || def || "";
}

export async function askChoice(question, options, def) {
  const r = rl();
  const menu = options.map((o, i) => `  ${i + 1}) ${o}`).join("\n");
  const answer = await new Promise((res) =>
    r.question(`${question}\n${menu}\nchoice [${def}]: `, res));
  r.close();
  const a = (answer || "").trim();
  if (!a) return def;
  const n = parseInt(a, 10);
  if (!Number.isNaN(n) && options[n - 1]) return options[n - 1];
  return options.includes(a) ? a : def;
}

// ---- rendering -------------------------------------------------------------
/** Substitute {paths.x} and {project.x} template vars from the config object. */
export function render(text, cfg) {
  return text.replace(/\{(paths|project)\.([a-z_]+)\}/g, (m, group, key) => {
    const v = cfg[group]?.[key];
    return v === undefined ? m : String(v);
  });
}

export function parseFrontmatter(text) {
  const m = text.match(/^---\n([\s\S]*?)\n---\n/);
  if (!m) return { meta: {}, body: text };
  const meta = {};
  for (const line of m[1].split("\n")) {
    const km = line.match(/^([a-z_-]+):\s*(.*)$/);
    if (km) meta[km[1]] = km[2].replace(/^"(.*)"$/, "$1");
  }
  return { meta, body: text.slice(m[0].length) };
}

// ---- fs helpers ------------------------------------------------------------
export function copyDir(src, dst) {
  fs.mkdirSync(dst, { recursive: true });
  for (const e of fs.readdirSync(src, { withFileTypes: true })) {
    const s = path.join(src, e.name);
    const d = path.join(dst, e.name);
    if (e.isDirectory()) copyDir(s, d);
    else {
      fs.copyFileSync(s, d);
      fs.chmodSync(d, fs.statSync(s).mode);
    }
  }
}

/** Write only when absent — user ledgers are never clobbered. */
export function writeIfAbsent(file, content) {
  if (fs.existsSync(file)) return false;
  fs.mkdirSync(path.dirname(file), { recursive: true });
  fs.writeFileSync(file, content);
  return true;
}

export function writeFile(file, content) {
  fs.mkdirSync(path.dirname(file), { recursive: true });
  fs.writeFileSync(file, content);
}

// ---- arg parsing -----------------------------------------------------------
export function parseArgs(argv) {
  const flags = {};
  const positional = [];
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i];
    if (a.startsWith("--")) {
      const key = a.slice(2);
      if (i + 1 < argv.length && !argv[i + 1].startsWith("--")) flags[key] = argv[++i];
      else flags[key] = true;
    } else positional.push(a);
  }
  return { flags, positional };
}
