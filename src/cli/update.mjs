import fs from "node:fs";
import path from "node:path";
import { pkgRoot, repoRoot, copyDir, render } from "./util.mjs";
import { TOOLS, renderTool, adapterMarker } from "./adapters.mjs";

/** Refresh framework-owned files from the package. NEVER touches user ledgers
 * (docs/pm, docs/qa, docs/specs, docs/backlog, evd/) or vteam.config.yaml. */
export async function update(_flags) {
  const root = repoRoot();
  const cfgFile = path.join(root, "vteam.config.yaml");
  if (!fs.existsSync(cfgFile)) {
    console.log("vteam.config.yaml missing — run `npx vteam init` first.");
    process.exit(1);
  }
  const raw = fs.readFileSync(cfgFile, "utf8");
  const grab = (k) => (raw.match(new RegExp(`^\\s*${k}:\\s*(.+)$`, "m")) || [])[1]?.trim();
  const profile = grab("profile") || "generic";
  const tracker = grab("provider") || "markdown";
  const cfg = {
    project: { name: grab("name"), key: grab("key"), language: grab("language") },
    paths: Object.fromEntries(["specs", "pm", "qa", "adr", "team", "design", "evidence", "backlog"]
      .map((k) => [k, (raw.match(new RegExp(`^  ${k}:\\s*(.+)$`, "m")) || [])[1]?.trim() || `docs/${k}`])),
  };

  copyDir(path.join(pkgRoot, "core", "scripts"), path.join(root, ".vteam", "scripts"));
  copyDir(path.join(pkgRoot, "core", "locales"), path.join(root, ".vteam", "locales"));
  if (fs.existsSync(path.join(pkgRoot, "profiles", profile)))
    copyDir(path.join(pkgRoot, "profiles", profile), path.join(root, ".vteam", "profiles", profile));
  for (const kind of ["tracker", "design"]) {
    const dir = path.join(root, ".vteam", "providers");
    if (!fs.existsSync(dir)) continue;
    for (const f of fs.readdirSync(dir)) {
      const m = f.match(new RegExp(`^${kind}_(\\w+)\\.py$`));
      if (m && fs.existsSync(path.join(pkgRoot, "providers", kind, `${m[1]}.py`)))
        fs.copyFileSync(path.join(pkgRoot, "providers", kind, `${m[1]}.py`), path.join(dir, f));
    }
  }
  console.log("✓ .vteam runtime refreshed");

  // doctrine: overwrite framework files, but respect local edits? Doctrine is
  // framework-owned — refresh it; project-specific rules belong in the config
  // and ledgers, not edits to doctrine (supersession law: one rule, one home).
  const docSrc = path.join(pkgRoot, "core", "doctrine");
  const docDst = path.join(root, cfg.paths.team);
  for (const rel of walk(docSrc)) {
    const text = fs.readFileSync(path.join(docSrc, rel), "utf8");
    const out = path.join(docDst, rel);
    fs.mkdirSync(path.dirname(out), { recursive: true });
    fs.writeFileSync(out, rel.endsWith(".md") ? render(text, cfg) : text);
  }
  console.log(`✓ doctrine refreshed in ${cfg.paths.team}`);

  // re-render adapters for every tool already present (marker from the adapter module)
  for (const tool of TOOLS) {
    if (fs.existsSync(path.join(root, await adapterMarker(tool)))) {
      await renderTool(tool, root, cfg);
      console.log(`✓ ${tool} workflows re-rendered`);
    }
  }
  console.log("update done — ledgers and config untouched.");
}

function walk(dir, prefix = "") {
  const out = [];
  for (const e of fs.readdirSync(dir, { withFileTypes: true })) {
    const rel = prefix ? path.join(prefix, e.name) : e.name;
    if (e.isDirectory()) out.push(...walk(path.join(dir, e.name), rel));
    else out.push(rel);
  }
  return out;
}
