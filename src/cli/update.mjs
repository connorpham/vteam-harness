import fs from "node:fs";
import path from "node:path";
import { pkgRoot, repoRoot, render } from "./util.mjs";
import { loadConfig, cfgGet } from "./config.mjs";
import { ManifestGuard, walkFiles } from "./manifest.mjs";
import { TOOLS, renderTool, adapterMarker } from "./adapters.mjs";
import { CI_WORKFLOW, GITIGNORE_RULES, GITATTR_RULES, pkgVersion } from "./init.mjs";

/** Refresh framework-owned files from the package. NEVER touches user ledgers
 * (docs/pm, docs/qa, docs/specs, docs/backlog, evd/) or vteam.config.yaml —
 * and that promise is now a mechanism, not a comment: every write goes through
 * the manifest guard, which only overwrites files whose on-disk hash matches
 * what the framework last wrote. Anything else gets a `<file>.new` neighbor. */
export async function update(_flags) {
  const root = repoRoot();
  const cfgFile = path.join(root, "vteam.config.yaml");
  if (!fs.existsSync(cfgFile)) {
    console.log("vteam.config.yaml missing — run `npx vteam-harness init` first.");
    process.exit(1);
  }
  let userCfg;
  try {
    userCfg = loadConfig(root); // the gates' own parser — sections, flow maps, comments, quotes
  } catch (e) {
    console.error(`vteam update: ${e.message}`);
    process.exit(1);
  }
  const profile = String(cfgGet(userCfg, "stack.profile", "generic"));
  const cfg = {
    ...userCfg,
    paths: { // defaults must match init's — evidence lives at evd, not docs/evidence
      specs: "docs/specs", pm: "docs/pm", qa: "docs/qa", adr: "docs/adr",
      team: "docs/team", design: "docs/design", evidence: "evd", backlog: "docs/backlog",
      ...(userCfg.paths ?? {}),
    },
  };
  const guard = new ManifestGuard(root);
  if (!guard.old) {
    console.log("⚠ no .vteam/manifest.json (pre-manifest install) — files that differ from " +
      "this package version are kept and offered as *.new; this run writes the manifest.");
  }

  // ---- .vteam runtime -----------------------------------------------------------
  guard.syncDir(path.join(pkgRoot, "core", "scripts"), ".vteam/scripts");
  guard.syncDir(path.join(pkgRoot, "core", "locales"), ".vteam/locales");
  if (fs.existsSync(path.join(pkgRoot, "profiles", profile))) {
    guard.syncDir(path.join(pkgRoot, "profiles", profile), `.vteam/profiles/${profile}`);
  }
  for (const kind of ["tracker", "design"]) {
    const dir = path.join(root, ".vteam", "providers");
    if (!fs.existsSync(dir)) continue;
    for (const f of fs.readdirSync(dir)) {
      const m = f.match(new RegExp(`^${kind}_(\\w+)\\.py$`));
      if (m && fs.existsSync(path.join(pkgRoot, "providers", kind, `${m[1]}.py`))) {
        guard.sync(`.vteam/providers/${f}`,
          fs.readFileSync(path.join(pkgRoot, "providers", kind, `${m[1]}.py`)));
      }
    }
  }
  console.log("✓ .vteam runtime refreshed");

  // ---- doctrine (framework-owned, but user edits are preserved as conflicts) -----
  const docSrc = path.join(pkgRoot, "core", "doctrine");
  const teamDir = String(cfg.paths.team).replace(/\/+$/, "");
  for (const rel of walkFiles(docSrc)) {
    const text = fs.readFileSync(path.join(docSrc, ...rel.split("/")), "utf8");
    guard.sync(`${teamDir}/${rel}`, rel.endsWith(".md") ? render(text, cfg) : text);
  }
  console.log(`✓ doctrine refreshed in ${teamDir}`);

  // ---- git fence + CI workflow (same rule: refresh, never clobber edits) ---------
  guard.sync(".githooks/pre-push",
    fs.readFileSync(path.join(pkgRoot, "core", "templates", "hooks", "pre-push"), "utf8"), 0o755);
  guard.sync(".github/workflows/vteam-gate.yml", CI_WORKFLOW);

  // ---- .gitattributes rules: additive only (union merge for append-only files) ---
  const ga = path.join(root, ".gitattributes");
  const gaText = fs.existsSync(ga) ? fs.readFileSync(ga, "utf8") : "";
  const gaHave = new Set(gaText.split("\n").map((l) => l.trim()));
  const gaMissing = GITATTR_RULES.filter((r) => !gaHave.has(r));
  if (gaMissing.length) {
    fs.appendFileSync(ga, (gaText && !gaText.endsWith("\n") ? "\n" : "") + gaMissing.join("\n") + "\n");
    console.log(`✓ .gitattributes union-merge rules refreshed (${gaMissing.length} added)`);
  }

  // ---- .gitignore rules: additive only — user lines are never touched ------------
  const gi = path.join(root, ".gitignore");
  const giText = fs.existsSync(gi) ? fs.readFileSync(gi, "utf8") : "";
  const giLines = new Set(giText.split("\n").map((l) => l.trim()));
  const missing = GITIGNORE_RULES.filter((r) => !giLines.has(r));
  if (missing.length) {
    fs.appendFileSync(gi, "\n" + missing.join("\n") + "\n");
    console.log(`✓ .gitignore rules refreshed (${missing.length} added)`);
  }

  // ---- adapters: re-render every tool already present ------------------------------
  for (const tool of TOOLS) {
    if (fs.existsSync(path.join(root, await adapterMarker(tool)))) {
      await renderTool(tool, root, cfg, (rel, text) => guard.sync(rel, text));
      console.log(`✓ ${tool} workflows re-rendered`);
    }
  }

  guard.save(pkgVersion());
  if (guard.conflicts.length) {
    console.log(`\n⚠ ${guard.conflicts.length} file(s) differ from what the framework last wrote — kept YOURS, new version parked beside it:`);
    for (const c of guard.conflicts) console.log(`  ${c}  →  ${c}.new`);
    console.log("  Review each pair, merge what you want, then delete the .new file.");
  }
  console.log("update done — ledgers and config untouched.");
}
