// Claude Code — native skills with subagent spawning (the reference adapter).
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

export const id = "claude-code";
export const marker = ".claude/skills/team/SKILL.md";
// everything this adapter writes lives here — update prunes orphans under these only
export const outputDirs = [".claude/skills/", ".claude/agents/", ".claude/hooks/"];


const pkgRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");

// SessionStart doctrine re-injection: /clear and compaction erase the rules,
// and a SessionStart hook's stdout is added back into the agent's context
// (code.claude.com/docs/en/hooks) — so the non-negotiables outlive the window.
const HOOK_REL = ".claude/hooks/vteam-session-start.sh";
const HOOK_ENTRY = {
  matcher: "startup|clear|compact",
  hooks: [{ type: "command", command: `bash "$CLAUDE_PROJECT_DIR"/${HOOK_REL}` }],
};

export function render(wf, ctx) {
  const hint = wf.args ? `argument-hint: "${wf.args.replace(/"/g, "'")}"\n` : "";
  return {
    path: path.join(".claude", "skills", wf.name, "SKILL.md"),
    text: `---\nname: ${wf.name}\ndescription: "${wf.description.replace(/"/g, "'")}"\n${hint}---\n\n${wf.body}`,
  };
}

/** Post-step: install the specialist subagents and the SessionStart hook.
 * Subagents (core/agents/*.md → .claude/agents/) and the hook script go through
 * `write` — the caller's manifest-guarded path (init: force; update: sync), so an
 * unmodified copy is refreshed when the package changes and a user-edited copy
 * is parked as `.new`, exactly like a workflow file. The first version wrote
 * them directly and kept ANY differing copy, so an upstream agent change never
 * reached a consumer, who was told "kept YOURS" about a file it never touched.
 * The SessionStart entry is MERGED into .claude/settings.json — parsed and added
 * only when absent; when the entry is already there the file is not rewritten,
 * so user content stays byte-for-byte. A file this adapter cannot faithfully
 * preserve (unparseable JSON, unexpected shapes) is warned about and SKIPPED,
 * never overwritten. */
export function pointers(root, write = (rel, text, mode) => {
  const abs = path.join(root, ...rel.split("/"));
  fs.mkdirSync(path.dirname(abs), { recursive: true });
  fs.writeFileSync(abs, text);
  if (mode !== undefined) fs.chmodSync(abs, mode);
}) {
  const changed = [];
  const settingsRel = ".claude/settings.json";
  const skip = (msg) => { console.log(`⚠ claude-code: ${msg}`); return changed; };

  // 0) the specialist subagents, from the packaged core/agents/
  const agentsSrc = path.join(pkgRoot, "core", "agents");
  if (fs.existsSync(agentsSrc)) {
    for (const f of fs.readdirSync(agentsSrc).filter((n) => n.endsWith(".md")).sort()) {
      const rel = `.claude/agents/${f}`;
      const status = write(rel, fs.readFileSync(path.join(agentsSrc, f), "utf8"));
      if (status !== "current") changed.push(rel);
    }
  }

  // 1) the hook script, from the packaged template (exec bit travels with it)
  const want = fs.readFileSync(
    path.join(pkgRoot, "core", "templates", "hooks", "session-start"), "utf8");
  if (write(HOOK_REL, want, 0o755) !== "current") changed.push(HOOK_REL);
  const hookAbs = path.join(root, ...HOOK_REL.split("/"));


  // 2) merge the SessionStart entry into settings.json
  const settingsAbs = path.join(root, ...settingsRel.split("/"));
  let settings = {};
  if (fs.existsSync(settingsAbs)) {
    try {
      settings = JSON.parse(fs.readFileSync(settingsAbs, "utf8"));
    } catch (e) {
      return skip(`${settingsRel} is NOT valid JSON (${e.message}) — SessionStart hook NOT wired.\n` +
        `  Fix the file and re-run vteam update, or add this entry to hooks.SessionStart yourself:\n` +
        `  ${JSON.stringify(HOOK_ENTRY)}`);
    }
    if (typeof settings !== "object" || settings === null || Array.isArray(settings)) {
      return skip(`${settingsRel} is not a JSON object — SessionStart hook NOT wired (fix it, re-run vteam update)`);
    }
  }
  settings.hooks ??= {};
  if (typeof settings.hooks !== "object" || settings.hooks === null || Array.isArray(settings.hooks)) {
    return skip(`${settingsRel} has a non-object "hooks" key — SessionStart hook NOT wired (fix it, re-run vteam update)`);
  }
  settings.hooks.SessionStart ??= [];
  if (!Array.isArray(settings.hooks.SessionStart)) {
    return skip(`${settingsRel} has a non-array hooks.SessionStart — SessionStart hook NOT wired (fix it, re-run vteam update)`);
  }
  const present = settings.hooks.SessionStart.some((e) =>
    Array.isArray(e?.hooks) &&
    e.hooks.some((h) => typeof h?.command === "string" && h.command.includes("vteam-session-start")));
  if (present) return changed; // already wired — the file stays untouched

  settings.hooks.SessionStart.push(HOOK_ENTRY);
  fs.mkdirSync(path.dirname(settingsAbs), { recursive: true });
  fs.writeFileSync(settingsAbs, JSON.stringify(settings, null, 2) + "\n");
  changed.push(`${settingsRel} (SessionStart hook merged)`);
  return changed;
}
