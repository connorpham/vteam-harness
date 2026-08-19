// vteam context (Node) — the ONE place .mjs gates resolve repo root, config
// and env. Same contract as ctx.py next to it: constrained YAML subset
// (scalars, nested mappings, inline [a, b] and dash lists, flow mappings
// `{a: b, c: [x, y]}`, quoted values, comments; tab indentation dies loudly,
// tabs inside values are fine), inert .env parsing (key=value text — NEVER
// executed as shell). Parity with ctx.py is fenced by tests/conformance.mjs.
//
// Usage:
//   import { Ctx, parseConfig, repoRoot, loadEnv } from "./ctx.mjs";
//   const c = new Ctx();          // resolves root via `git rev-parse`
//   c.root                        // absolute repo root
//   c.cfg("project.key")          // "PROJ" (throws if missing)
//   c.cfg("project.go_live", null)// default when absent
//   c.path("pm")                  // absolute path to the configured docs/pm
//   c.env("JIRA_API_TOKEN")       // os-env-then-.env lookup
//
// Selftest:  node ctx.mjs --selftest   (includes mutations: bad syntax must red)
import fs from "node:fs";
import path from "node:path";
import process from "node:process";
import { spawnSync } from "node:child_process";
import { fileURLToPath, pathToFileURL } from "node:url";

export const CONFIG_NAME = "vteam.config.yaml";
const MISSING = Symbol("missing");

export function repoRoot(start) {
  const r = spawnSync("git", ["rev-parse", "--show-toplevel"],
    { cwd: start ?? process.cwd(), encoding: "utf8", stdio: ["ignore", "pipe", "ignore"] });
  if (r.status !== 0 || !r.stdout) {
    throw new Error("ctx: not inside a git repository (git rev-parse failed)");
  }
  return r.stdout.trim();
}

function die(ln, msg) {
  throw new Error(`ctx: ${CONFIG_NAME}:${ln}: ${msg}`);
}

/** Split a flow body on commas at nesting depth 0 — a comma inside [], {}
 * or quotes is data, not a separator. Mirrors ctx.py _split_top exactly. */
function splitTop(s, ln) {
  const parts = [];
  let buf = "", depth = 0, quote = "";
  for (const ch of s) {
    if (quote) {
      buf += ch;
      if (ch === quote) quote = "";
    } else if (ch === "'" || ch === '"') {
      quote = ch;
      buf += ch;
    } else if (ch === "[" || ch === "{") {
      depth++;
      buf += ch;
    } else if (ch === "]" || ch === "}") {
      depth--;
      if (depth < 0) die(ln, `unbalanced brackets in flow value: ${JSON.stringify(s)}`);
      buf += ch;
    } else if (ch === "," && depth === 0) {
      parts.push(buf);
      buf = "";
    } else {
      buf += ch;
    }
  }
  if (depth !== 0 || quote) die(ln, `unbalanced brackets in flow value: ${JSON.stringify(s)}`);
  parts.push(buf);
  return parts;
}

function parseScalar(s, ln) {
  s = s.trim();
  if ("&*".includes(s[0] ?? "") || s === "|" || s === ">" ||
      s.startsWith("| ") || s.startsWith("> ")) {
    die(ln, `outside the vteam YAML subset (anchors/multiline): ${JSON.stringify(s)}`);
  }
  if (s.startsWith("[")) {
    if (!s.endsWith("]")) die(ln, `unterminated inline list: ${JSON.stringify(s)}`);
    const inner = s.slice(1, -1).trim();
    return inner ? splitTop(inner, ln).map((x) => parseScalar(x, ln)) : [];
  }
  if (s.startsWith("{")) { // flow mapping {a: b, c: [x, y]} — same as ctx.py
    if (!s.endsWith("}")) die(ln, `unterminated flow mapping: ${JSON.stringify(s)}`);
    const inner = s.slice(1, -1).trim();
    const obj = {};
    if (!inner) return obj;
    for (const part of splitTop(inner, ln)) {
      const m = part.match(/^\s*([A-Za-z_][A-Za-z0-9_-]*)\s*:\s*(.+?)\s*$/);
      if (!m) die(ln, `bad flow mapping entry: ${JSON.stringify(part.trim())}`);
      obj[m[1]] = parseScalar(m[2], ln);
    }
    return obj;
  }
  if ((s.startsWith('"') && s.endsWith('"') && s.length >= 2) ||
      (s.startsWith("'") && s.endsWith("'") && s.length >= 2)) {
    return s.slice(1, -1);
  }
  if (s === "true" || s === "True") return true;
  if (s === "false" || s === "False") return false;
  if (/^-?\d+$/.test(s)) return parseInt(s, 10);
  if (/^-?\d+(\.\d+)?$/.test(s)) return parseFloat(s);
  return s;
}

/** Parse the vteam YAML subset. Throws loudly on anything outside it. */
export function parseConfig(text) {
  const lines = []; // [lineno, indent, stripped]
  let ln = 0;
  for (const raw of text.split("\n")) {
    ln++;
    if (raw.trimStart().startsWith("#") || !raw.trim()) continue;
    if (raw.slice(0, raw.length - raw.trimStart().length).includes("\t")) {
      die(ln, "tab indentation is not supported — use spaces"); // tabs INSIDE values stay legal
    }
    const s = raw.replace(/\s#.*$/, "").trimEnd(); // subset: '#' never appears in values
    if (s.trim()) lines.push([ln, s.length - s.trimStart().length, s.trim()]);
  }

  let pos = 0;
  function block(indent) {
    const d = {};
    while (pos < lines.length) {
      const [n, ind, s] = lines[pos];
      if (ind < indent) break;
      if (ind > indent) die(n, "bad indentation");
      if (s.startsWith("- ")) die(n, "dash-list item without a parent key");
      const m = s.match(/^([A-Za-z_][A-Za-z0-9_-]*):(?:\s*(.*))?$/);
      if (!m) die(n, `outside the vteam YAML subset: ${JSON.stringify(s)}`);
      const key = m[1];
      const val = (m[2] ?? "").trim();
      pos++;
      if (val) {
        d[key] = parseScalar(val, n);
      } else if (pos < lines.length && lines[pos][1] > ind) {
        const childInd = lines[pos][1];
        if (lines[pos][2].startsWith("- ")) {
          const items = [];
          while (pos < lines.length && lines[pos][1] === childInd &&
                 lines[pos][2].startsWith("- ")) {
            items.push(parseScalar(lines[pos][2].slice(2), lines[pos][0]));
            pos++;
          }
          d[key] = items;
        } else {
          d[key] = block(childInd);
        }
      } else {
        d[key] = {};
      }
    }
    return d;
  }

  return lines.length ? block(lines[0][1]) : {};
}

/** Inert .env loader: os env wins, .env fills the gaps. Never executed. */
export function loadEnv(root) {
  const env = { ...process.env };
  const file = path.join(root, ".env");
  if (fs.existsSync(file)) {
    for (let raw of fs.readFileSync(file, "utf8").split("\n")) {
      raw = raw.trim();
      if (!raw || raw.startsWith("#") || !raw.includes("=")) continue;
      const i = raw.indexOf("=");
      const k = raw.slice(0, i).trim();
      const v = raw.slice(i + 1).trim().replace(/^"(.*)"$/, "$1").replace(/^'(.*)'$/, "$1");
      if (!(k in env)) env[k] = v;
    }
  }
  return env;
}

export class Ctx {
  constructor(start) {
    this.root = repoRoot(start);
    const cfgFile = path.join(this.root, CONFIG_NAME);
    if (!fs.existsSync(cfgFile)) {
      throw new Error(`ctx: ${CONFIG_NAME} not found at repo root — run \`npx vteam-harness init\``);
    }
    this._cfg = parseConfig(fs.readFileSync(cfgFile, "utf8"));
    this._env = loadEnv(this.root);
  }

  cfg(dotted, def = MISSING) {
    let node = this._cfg;
    for (const part of dotted.split(".")) {
      if (node === null || typeof node !== "object" || Array.isArray(node) || !(part in node)) {
        if (def === MISSING) throw new Error(`ctx: missing config key '${dotted}' in ${CONFIG_NAME}`);
        return def;
      }
      node = node[part];
    }
    return node;
  }

  path(name) {
    return path.join(this.root, String(this.cfg(`paths.${name}`)));
  }

  env(key, def = undefined) {
    return this._env[key] ?? def;
  }
}

// ---- selftest / CLI ----------------------------------------------------------
function selftest() {
  const here = path.dirname(fileURLToPath(import.meta.url));
  let sample = null;
  for (let p = here; ; ) {
    const cand = path.join(p, "core", "templates", "vteam.config.example.yaml");
    if (fs.existsSync(cand)) { sample = fs.readFileSync(cand, "utf8"); break; }
    const up = path.dirname(p);
    if (up === p) break;
    p = up;
  }
  if (sample === null) { // installed repos don't carry the package templates
    sample = 'version: 1\nproject:\n  key: PROJ\npaths:\n  pm: docs/pm\n' +
      'git:\n  branch_pattern: "^(feat|fix)/{key}-[0-9]+-"\n' +
      'tracker:\n  done_statuses: [Done, Closed, Resolved]\n' +
      'autonomy:\n  exemptions:\n    - real-money\n' +
      'team:\n  capacity_per_day: 0.8\nreview:\n  high_stakes_paths: []\n';
  }
  const assert = (cond, msg) => { if (!cond) { console.error(`ctx.mjs selftest FAILED: ${msg}`); process.exit(1); } };
  const cfg = parseConfig(sample);
  assert(cfg.version === 1, "version");
  assert(cfg.project.key === "PROJ", "project.key");
  assert(cfg.paths.pm === "docs/pm", "paths.pm");
  assert(cfg.git.branch_pattern === "^(feat|fix)/{key}-[0-9]+-", "git.branch_pattern");
  assert(JSON.stringify(cfg.tracker.done_statuses) === '["Done","Closed","Resolved"]', "done_statuses");
  assert(cfg.autonomy.exemptions[0] === "real-money", "exemptions");
  assert(cfg.team.capacity_per_day === 0.8, "capacity_per_day");
  assert(JSON.stringify(cfg.review.high_stakes_paths) === "[]", "high_stakes_paths");
  // flow mappings (README config style), incl. a 2-element list inside a
  // flow map — the exact shape README's by_label ships (H3 regression):
  const flow = parseConfig("stack: { profile: nextjs-prisma, package_manager: npm }\n");
  assert(flow.stack.profile === "nextjs-prisma", "flow mapping profile");
  assert(flow.stack.package_manager === "npm", "flow mapping package_manager");
  const flow2 = parseConfig("docs:\n  task_context:\n    by_label: { payment: [a.md, b.md], auth: [c.md] }\n");
  assert(JSON.stringify(flow2.docs.task_context.by_label.payment) === '["a.md","b.md"]',
    "flow map with 2-element list (H3)");
  assert(JSON.stringify(flow2.docs.task_context.by_label.auth) === '["c.md"]',
    "flow map with 1-element list");
  // quoted values with the characters init escapes
  const q = parseConfig("project:\n  name: 'My App: The \"Sequel\"'\n");
  assert(q.project.name === 'My App: The "Sequel"', "quoted name with colon+quotes");
  // .env is INERT: metacharacters come back as text, nothing executes
  const marker = path.join(here, `.ctx-selftest-${process.pid}`);
  const tmp = fs.mkdtempSync(path.join(here, ".ctx-selftest-env-"));
  try {
    fs.writeFileSync(path.join(tmp, ".env"), `EVIL=$(touch ${marker})\nPLAIN=ok\n`);
    const env = loadEnv(tmp);
    assert(env.EVIL === `$(touch ${marker})`, ".env value kept as text");
    assert(!fs.existsSync(marker), ".env must never execute");
    assert(env.PLAIN === "ok", ".env plain value");
  } finally {
    fs.rmSync(tmp, { recursive: true, force: true });
    fs.rmSync(marker, { force: true });
  }
  // mutation half — a parser that has never been red does not exist:
  let reds = 0;
  for (const bad of ["b: &anchor x\n", "a:\n  - 1\n - 2\n", "weird ! line\n",
                     "a:\n\tb: 1\n",   // tab indentation must die loudly (H10)
                     "x: { a }\n",     // flow entry without a value
                     "x: { a: b\n"]) { // unterminated flow mapping
    try {
      parseConfig(bad);
      console.error(`ctx.mjs selftest FAILED: should have rejected ${JSON.stringify(bad)}`);
      process.exit(1);
    } catch { reds++; }
  }
  console.log(`ctx.mjs selftest: OK (parse green + flow mapping + inert .env + ${reds} mutations red)`);
}

const isMain = process.argv[1] &&
  import.meta.url === pathToFileURL(path.resolve(process.argv[1])).href;
if (isMain) {
  try {
    if (process.argv.includes("--selftest")) selftest();
    else if (process.argv[2]) console.log(new Ctx().cfg(process.argv[2]));
    else console.log("usage: node ctx.mjs <dotted.key> | --selftest");
  } catch (e) {
    console.error(e.message);
    process.exit(1);
  }
}
