// Claude Code — native skills with subagent spawning (the reference adapter).
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

export const id = "claude-code";
export const marker = ".claude/skills/team/SKILL.md";

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
 * Subagents (core/agents/*.md → .claude/agents/) follow the same
 * non-destructive rule as the hook: written when absent, a user-edited copy
 * is kept — loudly, never silently.
 * Then the SessionStart hook. Two writes, both non-destructive:
 * the hook script (a user-edited copy is kept — loudly, never silently), and a
 * SessionStart entry merged into .claude/settings.json — parsed and added only
 * when absent; when the entry is already there the file is not rewritten, so
 * user content stays byte-for-byte. A file this adapter cannot faithfully
 * preserve (unparseable JSON, unexpected shapes) is warned about and SKIPPED,
 * never overwritten. */
export function pointers(root) {
  const changed = [];
  const settingsRel = ".claude/settings.json";
  const skip = (msg) => { console.log(`⚠ claude-code: ${msg}`); return changed; };

  // 0) the specialist subagents, from the packaged core/agents/
  const agentsSrc = path.join(pkgRoot, "core", "agents");
  if (fs.existsSync(agentsSrc)) {
    for (const f of fs.readdirSync(agentsSrc).filter((n) => n.endsWith(".md")).sort()) {
      const rel = `.claude/agents/${f}`;
      const wantAgent = fs.readFileSync(path.join(agentsSrc, f), "utf8");
      const abs = path.join(root, ".claude", "agents", f);
      const haveAgent = fs.existsSync(abs) ? fs.readFileSync(abs, "utf8") : null;
      if (haveAgent === null) {
        fs.mkdirSync(path.dirname(abs), { recursive: true });
        fs.writeFileSync(abs, wantAgent);
        changed.push(rel);
      } else if (haveAgent !== wantAgent) {
        console.log(`⚠ claude-code: ${rel} differs from the packaged version — kept YOURS ` +
          "(delete it and re-run vteam update for a fresh copy)");
      }
    }
  }

  // 1) the hook script, from the packaged template
  const want = fs.readFileSync(
    path.join(pkgRoot, "core", "templates", "hooks", "session-start"), "utf8");
  const hookAbs = path.join(root, ...HOOK_REL.split("/"));
  const have = fs.existsSync(hookAbs) ? fs.readFileSync(hookAbs, "utf8") : null;
  if (have === null) {
    fs.mkdirSync(path.dirname(hookAbs), { recursive: true });
    fs.writeFileSync(hookAbs, want);
    changed.push(HOOK_REL);
  } else if (have !== want) {
    console.log(`⚠ claude-code: ${HOOK_REL} differs from the packaged template — kept YOURS ` +
      "(delete it and re-run vteam update for a fresh copy)");
  }
  try { fs.chmodSync(hookAbs, 0o755); } catch { /* mode is cosmetic: the settings entry runs it via bash */ }

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
