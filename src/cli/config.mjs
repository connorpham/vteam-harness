// The CLI's config reader — the SAME section-aware parser the .mjs gates use
// (core/scripts/lib/ctx.mjs, mirroring lib/ctx.py), not a first-match regex.
// Handles nesting, flow mappings `{a: b}`, comments, quoted values, lists.
import fs from "node:fs";
import path from "node:path";
import { parseConfig, CONFIG_NAME } from "../../core/scripts/lib/ctx.mjs";

export { parseConfig, CONFIG_NAME };

/** Parse <root>/vteam.config.yaml. Returns null when absent; throws (loudly,
 * with line numbers) when present but outside the vteam YAML subset. */
export function loadConfig(root) {
  const f = path.join(root, CONFIG_NAME);
  if (!fs.existsSync(f)) return null;
  return parseConfig(fs.readFileSync(f, "utf8"));
}

/** Dotted lookup with a default: cfgGet(cfg, "stack.profile", "generic"). */
export function cfgGet(cfg, dotted, def) {
  let node = cfg;
  for (const part of dotted.split(".")) {
    if (node === null || typeof node !== "object" || Array.isArray(node) || !(part in node)) return def;
    node = node[part];
  }
  return node;
}
