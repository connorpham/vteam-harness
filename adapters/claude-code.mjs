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
// SessionEnd stop-state record: a session that ends with a ticket in flight leaves
// {paths.evidence}/<KEY>/dev/STOP-STATE.md behind (core/scripts/stop_state.sh) instead of
// a dirty tree nobody explained — the 2026-09-03 benchmark arm ended exactly like that.
const END_HOOK_REL = ".claude/hooks/vteam-session-end.sh";
const END_HOOK_ENTRY = {
  hooks: [{ type: "command", command: `bash "$CLAUDE_PROJECT_DIR"/${END_HOOK_REL}` }],
};
// hook name → [settings.json event, entry, substring that proves the entry is already there]
const HOOK_EVENTS = [
  ["SessionStart", HOOK_ENTRY, "vteam-session-start"],
  ["SessionEnd", END_HOOK_ENTRY, "vteam-session-end"],
];

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

  // 1) the hook scripts, from the packaged templates (exec bit travels with them)
  for (const [rel, tpl] of [[HOOK_REL, "session-start"], [END_HOOK_REL, "session-end"]]) {
    const want = fs.readFileSync(path.join(pkgRoot, "core", "templates", "hooks", tpl), "utf8");
    if (write(rel, want, 0o755) !== "current") changed.push(rel);
  }

  // 2) merge the SessionStart + SessionEnd entries into settings.json
  const settingsAbs = path.join(root, ...settingsRel.split("/"));
  let settings = {};
  if (fs.existsSync(settingsAbs)) {
    try {
      settings = JSON.parse(fs.readFileSync(settingsAbs, "utf8"));
    } catch (e) {
      return skip(`${settingsRel} is NOT valid JSON (${e.message}) — SessionStart/SessionEnd hooks NOT wired.\n` +
        `  Fix the file and re-run vteam update, or add these entries yourself:\n` +
        `  hooks.SessionStart: ${JSON.stringify(HOOK_ENTRY)}\n` +
        `  hooks.SessionEnd: ${JSON.stringify(END_HOOK_ENTRY)}`);
    }
    if (typeof settings !== "object" || settings === null || Array.isArray(settings)) {
      return skip(`${settingsRel} is not a JSON object — SessionStart/SessionEnd hooks NOT wired (fix it, re-run vteam update)`);
    }
  }
  settings.hooks ??= {};
  if (typeof settings.hooks !== "object" || settings.hooks === null || Array.isArray(settings.hooks)) {
    return skip(`${settingsRel} has a non-object "hooks" key — SessionStart/SessionEnd hooks NOT wired (fix it, re-run vteam update)`);
  }
  const added = [];
  for (const [event, entry, needle] of HOOK_EVENTS) {
    settings.hooks[event] ??= [];
    if (!Array.isArray(settings.hooks[event])) {
      return skip(`${settingsRel} has a non-array hooks.${event} — ${event} hook NOT wired (fix it, re-run vteam update)`);
    }
    const present = settings.hooks[event].some((e) =>
      Array.isArray(e?.hooks) &&
      e.hooks.some((h) => typeof h?.command === "string" && h.command.includes(needle)));
    if (present) continue; // already wired — nothing to add for this event
    settings.hooks[event].push(entry);
    added.push(event);
  }
  if (added.length === 0) return changed; // both wired — the file stays untouched, byte for byte

  fs.mkdirSync(path.dirname(settingsAbs), { recursive: true });
  fs.writeFileSync(settingsAbs, JSON.stringify(settings, null, 2) + "\n");
  changed.push(`${settingsRel} (${added.join(" + ")} hook merged)`);
  return changed;
}
