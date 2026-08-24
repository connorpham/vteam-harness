// usage.mjs — measured AI usage history: who ran which model, when, at what
// token cost. MEASURED, not self-reported.
//
// Why this exists: the ledger's `tok ≈` and `(tier)` are written by the agent
// that did the work — self-reporting. perf_report can only audit what the row
// claims. But the agent CLIs already keep ground truth on every machine:
//   Claude Code  ~/.claude/projects/<munged-cwd>/*.jsonl   — every assistant
//                message carries `model` + full `usage` (input/cache/output)
//   Codex        ~/.codex/sessions/YYYY/MM/DD/rollout-*.jsonl — session_meta
//                names the cwd, turn_context names the model, token_count
//                events carry per-turn usage
// This command reads those logs FOR THIS PROJECT ONLY and aggregates them:
// per day × model, per session, per person. `--sync` publishes the numbers
// into {paths.pm}/usage/<actor>.md — one file per person, so a team of humans
// never merge-conflicts, and the owner sees everyone's measured usage in the
// repo even though the raw logs never leave each member's machine.
//
// Honesty boundary, same as perf_report: counts only — tokens, models,
// session times. It NEVER reads or publishes anyone's chat content.
//
// Read-only against the logs; always exits 0 (it is a report, not a gate).
// The flags it prints (ledger says done but no session ran; heavy AI day with
// no ledger row) are for the desk report to surface.
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { execSync } from "node:child_process";
import { repoRoot } from "./util.mjs";
import { loadConfig, cfgGet } from "./config.mjs";
import { parseLedger } from "./board.mjs";

const DAY_MS = 24 * 60 * 60 * 1000;
const DEFAULT_WINDOW_DAYS = 90;
const SESSIONS_SHOWN = 20;
const SESSIONS_SYNCED = 50;
// a day where the AI produced more output than this with no ledger row is
// unlogged work, not idle noodling
const UNLOGGED_OUTPUT_K = 10;

// ---- sources ---------------------------------------------------------------

/** Claude Code names its per-project dir by the cwd with every non-alphanumeric
 * collapsed to '-' (/Users/a/b → -Users-a-b). */
export function mungeCwd(p) {
  return p.replace(/[^A-Za-z0-9]/g, "-");
}

const day = (iso) => (iso || "").slice(0, 10);

function newSession(source, id) {
  return { source, id, start: null, end: null, branch: null, models: {},
    days: {}, msgs: 0, input: 0, cache_read: 0, cache_write: 0, output: 0 };
}

function bump(s, model, u, ts) {
  s.msgs++;
  s.models[model] = (s.models[model] || 0) + 1;
  s.input += u.input || 0;
  s.cache_read += u.cache_read || 0;
  s.cache_write += u.cache_write || 0;
  s.output += u.output || 0;
  if (ts) {
    if (!s.start || ts < s.start) s.start = ts;
    if (!s.end || ts > s.end) s.end = ts;
  }
  // daily accounting bins by the MESSAGE's day, not the session's start day —
  // a session left open across midnight otherwise makes every later day look
  // idle, and the ledger cross-check false-flags real work (found live when
  // vteam's own dogfood day sat inside a week-old session)
  const dk = `${day(ts) || day(s.start) || "unknown"}|${model}`;
  const d = s.days[dk] || (s.days[dk] = { msgs: 0, input: 0, cache_read: 0, cache_write: 0, output: 0 });
  d.msgs++;
  d.input += u.input || 0;
  d.cache_read += u.cache_read || 0;
  d.cache_write += u.cache_write || 0;
  d.output += u.output || 0;
}

/** One session file → one session object, or null (other project / no usage).
 * Claude Code writes one JSONL line per content block, so the SAME assistant
 * message (same message.id + requestId) appears several times with the same
 * usage object — count it once or everything inflates 2-4×. */
export function readClaudeSessions(claudeDir, root, sinceIso) {
  const dir = path.join(claudeDir, "projects", mungeCwd(root));
  let files = [];
  try { files = fs.readdirSync(dir).filter((f) => f.endsWith(".jsonl")); } catch { return []; }
  const sessions = [];
  for (const f of files) {
    let text;
    try { text = fs.readFileSync(path.join(dir, f), "utf8"); } catch { continue; }
    const s = newSession("claude", path.basename(f, ".jsonl"));
    const seen = new Set();
    for (const line of text.split("\n")) {
      if (!line.includes('"assistant"')) continue;      // cheap pre-filter
      let o;
      try { o = JSON.parse(line); } catch { continue; } // torn writes happen; skip, never crash
      if (o.type !== "assistant" || !o.message?.usage) continue;
      const key = `${o.message.id || o.uuid}:${o.requestId || ""}`;
      if (seen.has(key)) continue;
      seen.add(key);
      const u = o.message.usage;
      bump(s, o.message.model || "(unknown)", {
        input: u.input_tokens, cache_read: u.cache_read_input_tokens,
        cache_write: u.cache_creation_input_tokens, output: u.output_tokens,
      }, o.timestamp);
      if (o.gitBranch && !s.branch) s.branch = o.gitBranch;
    }
    if (s.msgs && day(s.start) >= sinceIso) sessions.push(s);
  }
  return sessions;
}

/** Codex keeps ALL projects in one date-sharded tree — the first line
 * (session_meta) names the cwd, so foreign projects cost one line's read.
 * token_count events carry cumulative + per-turn usage; sum the per-turn
 * (`last_token_usage`) so retried/compacted turns are not double-counted. */
export function readCodexSessions(codexDir, root, sinceIso) {
  const base = path.join(codexDir, "sessions");
  const sessions = [];
  let years = [];
  try { years = fs.readdirSync(base); } catch { return []; }
  for (const y of years) for (const m of safeList(path.join(base, y)))
    for (const d of safeList(path.join(base, y, m))) {
      if (`${y}-${m}-${d}` < sinceIso) continue;
      for (const f of safeList(path.join(base, y, m, d))) {
        if (!f.endsWith(".jsonl")) continue;
        const s = readCodexFile(path.join(base, y, m, d, f), root);
        if (s) sessions.push(s);
      }
    }
  return sessions;
}

function safeList(p) {
  try { return fs.readdirSync(p); } catch { return []; }
}

function readCodexFile(file, root) {
  let text;
  try { text = fs.readFileSync(file, "utf8"); } catch { return null; }
  const lines = text.split("\n");
  const s = newSession("codex", path.basename(file, ".jsonl"));
  let model = "(unknown)";
  for (const line of lines) {
    if (!line) continue;
    let o;
    try { o = JSON.parse(line); } catch { continue; }
    const p = o.payload || {};
    if (o.type === "session_meta") {
      const cwd = p.cwd || "";
      if (cwd !== root && !cwd.startsWith(root + path.sep)) return null; // other project — done after one line
      s.start = p.timestamp || o.timestamp;
    } else if (o.type === "turn_context" && p.model) {
      model = p.model;
    } else if (o.type === "event_msg" && p.type === "token_count" && p.info?.last_token_usage) {
      const u = p.info.last_token_usage;
      bump(s, model, {
        input: (u.input_tokens || 0) - (u.cached_input_tokens || 0),
        cache_read: u.cached_input_tokens, cache_write: 0, output: u.output_tokens,
      }, o.timestamp);
    }
  }
  return s.msgs ? s : null;
}

// ---- aggregation -----------------------------------------------------------

const dominantModel = (s) =>
  Object.entries(s.models).sort((a, b) => b[1] - a[1] || (a[0] < b[0] ? -1 : 1))[0]?.[0] || "(unknown)";

/** sessions → sorted daily rows (date × source × model) + per-model totals.
 * Daily rows come from each session's per-message-day bins (a multi-day
 * session contributes to EVERY day it touched); the sessions column counts
 * sessions ACTIVE on that day. Model totals stay per dominant model. */
export function aggregate(sessions) {
  const daily = new Map();
  const models = new Map();
  for (const s of sessions) {
    const model = dominantModel(s);
    const mrow = models.get(model) ||
      { model, sessions: 0, msgs: 0, input: 0, cache_read: 0, cache_write: 0, output: 0 };
    mrow.sessions++; mrow.msgs += s.msgs; mrow.input += s.input;
    mrow.cache_read += s.cache_read; mrow.cache_write += s.cache_write; mrow.output += s.output;
    models.set(model, mrow);
    for (const [dk, d] of Object.entries(s.days)) {
      const [date, m] = dk.split("|");
      const k = `${date}|${s.source}|${m}`;
      const row = daily.get(k) ||
        { date, source: s.source, model: m, sessions: 0, msgs: 0,
          input: 0, cache_read: 0, cache_write: 0, output: 0 };
      row.sessions++; row.msgs += d.msgs; row.input += d.input;
      row.cache_read += d.cache_read; row.cache_write += d.cache_write; row.output += d.output;
      daily.set(k, row);
    }
  }
  const byKey = (a, b) => (a.date + a.source + a.model < b.date + b.source + b.model ? -1 : 1);
  return {
    daily: [...daily.values()].sort(byKey),
    models: [...models.values()].sort((a, b) => b.output - a.output),
  };
}

// ---- ledger cross-check ----------------------------------------------------

/** Self-report vs measurement, per day. Two structural lies are flagged; the
 * claimed-vs-measured ratio is only REPORTED (tok ≈ is a rough mix by design). */
export function crossCheck(dailyRows, ledgerRows, actor, sinceIso) {
  const measured = new Map(); // day → output tokens
  for (const r of dailyRows)
    measured.set(r.date, (measured.get(r.date) || 0) + r.output);
  const mine = ledgerRows.filter((r) => !r.malformed && (r.actor === actor || r.actor === null)
    && r.date >= sinceIso);
  const flags = [];
  const claimedDays = new Map(); // day → {done, tok_k}
  for (const r of mine) {
    const c = claimedDays.get(r.date) || { done: 0, tok_k: 0 };
    if (r.result_kind === "done") c.done++;
    if (r.tok) c.tok_k += /[kK]$/.test(r.tok) ? parseFloat(r.tok) : parseFloat(r.tok) / 1000;
    claimedDays.set(r.date, c);
  }
  for (const [d, c] of [...claimedDays].sort()) {
    if (c.done && !measured.has(d))
      flags.push(`🚩 ${d}: ledger says ${c.done} done item(s) but NO AI session is recorded ` +
        `on this machine that day — other machine, or work that never ran?`);
  }
  for (const [d, out] of [...measured].sort()) {
    if (out / 1000 >= UNLOGGED_OUTPUT_K && !claimedDays.has(d))
      flags.push(`🚩 ${d}: ${fmtK(out)} output tokens measured but the ledger has no row ` +
        `from ${actor} that day — unlogged work is invisible to every report`);
  }
  const claimed = [...claimedDays.values()].reduce((a, c) => a + c.tok_k, 0);
  const spent = dailyRows.reduce((a, r) => a + r.input + r.output, 0) / 1000;
  return { flags, claimed_k: Math.round(claimed), measured_k: Math.round(spent) };
}

// ---- rendering -------------------------------------------------------------

export function fmtK(n) {
  if (n >= 1e6) return (n / 1e6).toFixed(1) + "M";
  if (n >= 1000) return Math.round(n / 1000) + "k";
  return String(n);
}

const dur = (s) => {
  if (!s.start || !s.end) return "—";
  const min = Math.round((new Date(s.end) - new Date(s.start)) / 60000);
  return min >= 60 ? `${Math.floor(min / 60)}h${String(min % 60).padStart(2, "0")}` : `${min}m`;
};

function renderReport(actor, sinceIso, agg, sessions, check) {
  const L = [`Measured AI usage — ${actor} · this project · since ${sinceIso}`,
    `(from local session logs: counts only — models, tokens, times. Never chat content.)`, ""];
  if (!sessions.length) {
    L.push("No sessions found for this project in the window.",
      "Sources scanned: Claude Code (~/.claude/projects) and Codex (~/.codex/sessions).");
    return L.join("\n");
  }
  L.push("By model:");
  for (const m of agg.models)
    L.push(`  ${m.model.padEnd(26)} ${String(m.sessions).padStart(3)} sessions · ` +
      `in ${fmtK(m.input).padStart(7)} · cache ${fmtK(m.cache_read).padStart(7)} · out ${fmtK(m.output).padStart(7)}`);
  L.push("", "Daily (date × source × model):");
  for (const r of agg.daily)
    L.push(`  ${r.date}  ${r.source.padEnd(6)} ${r.model.padEnd(26)} ` +
      `${String(r.sessions).padStart(2)}s ${String(r.msgs).padStart(4)}msg · ` +
      `in ${fmtK(r.input).padStart(7)} · out ${fmtK(r.output).padStart(7)}`);
  const recent = [...sessions].sort((a, b) => (a.start < b.start ? 1 : -1)).slice(0, SESSIONS_SHOWN);
  L.push("", `Sessions (last ${recent.length} of ${sessions.length}):`);
  for (const s of recent)
    L.push(`  ${(s.start || "").slice(0, 16).replace("T", " ")}  ${s.source.padEnd(6)} ` +
      `${dominantModel(s).padEnd(26)} ${dur(s).padStart(5)} · ${String(s.msgs).padStart(4)}msg · ` +
      `out ${fmtK(s.output).padStart(6)} · ${s.branch || "—"}`);
  L.push("", `Ledger cross-check: claimed tok ≈ ${check.claimed_k}k · measured in+out ${check.measured_k}k`);
  L.push(...(check.flags.length ? check.flags.map((f) => "  " + f)
    : ["  ✅ every done day has a session, every heavy day has a ledger row"]));
  return L.join("\n");
}

export function actorSlug(name) {
  return name.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-+|-+$/g, "") || "unknown";
}

/** The published file: one per person, machine-written, machine-read (by
 * perf_report). Raw integers, no locale separators — parseability wins. */
export function renderSyncFile(actor, sinceIso, todayIso, agg, sessions, check) {
  const L = [`# Measured AI usage — ${actor}`, "",
    "<!-- written by `vteam usage --sync` — measured from local session logs.",
    "     Counts only: models, tokens, session times. NEVER chat content.",
    "     Machine-read by perf_report; do not hand-edit — re-run the sync. -->", "",
    `ACTOR: ${actor}`, `UPDATED: ${todayIso}`, `WINDOW: ${sinceIso} → ${todayIso}`, "",
    "## Daily by model", "",
    "| Date | Source | Model | Sessions | Msgs | Input | CacheRead | CacheWrite | Output |",
    "|---|---|---|---|---|---|---|---|---|"];
  for (const r of agg.daily)
    L.push(`| ${r.date} | ${r.source} | ${r.model} | ${r.sessions} | ${r.msgs} ` +
      `| ${r.input} | ${r.cache_read} | ${r.cache_write} | ${r.output} |`);
  const recent = [...sessions].sort((a, b) => (a.start < b.start ? 1 : -1)).slice(0, SESSIONS_SYNCED);
  L.push("", "## Recent sessions", "",
    "| Started (UTC) | Source | Model | Branch | Duration | Msgs | Input | Output |",
    "|---|---|---|---|---|---|---|---|");
  for (const s of recent)
    L.push(`| ${(s.start || "").slice(0, 16).replace("T", " ")} | ${s.source} | ${dominantModel(s)} ` +
      `| ${s.branch || "—"} | ${dur(s)} | ${s.msgs} | ${s.input} | ${s.output} |`);
  L.push("", "## Ledger cross-check", "",
    `- claimed \`tok ≈\` ${check.claimed_k}k · measured in+out ${check.measured_k}k`);
  L.push(...(check.flags.length ? check.flags.map((f) => `- ${f}`)
    : ["- ✅ every done day has a session, every heavy day has a ledger row"]));
  L.push("");
  return L.join("\n");
}

// ---- entry -----------------------------------------------------------------

export function resolveActor(root) {
  let a = (process.env.VTEAM_ACTOR || "").trim();
  if (!a) {
    try {
      a = execSync("git config user.name",
        { cwd: root, encoding: "utf8", stdio: ["ignore", "pipe", "ignore"] }).trim();
    } catch { a = ""; }
  }
  a = a.split(/\s+/).join(" ");
  return a && !a.includes("|") ? a : null;
}

export async function usage(flags) {
  if (flags.selftest) return selftest();
  const root = repoRoot();
  const cfg = loadConfig(root) || {};
  const todayIso = new Date().toISOString().slice(0, 10);
  const sinceIso = typeof flags.since === "string" && /^\d{4}-\d{2}-\d{2}$/.test(flags.since)
    ? flags.since
    : new Date(Date.now() - DEFAULT_WINDOW_DAYS * DAY_MS).toISOString().slice(0, 10);
  const actor = resolveActor(root) || "(unknown)";
  const claudeDir = process.env.CLAUDE_CONFIG_DIR || path.join(os.homedir(), ".claude");
  const codexDir = process.env.CODEX_HOME || path.join(os.homedir(), ".codex");
  const sessions = [
    ...readClaudeSessions(claudeDir, root, sinceIso),
    ...readCodexSessions(codexDir, root, sinceIso),
  ];
  const agg = aggregate(sessions);
  const pmRel = String(cfgGet(cfg, "paths.pm", "docs/pm"));
  let ledgerRows = [];
  try {
    ledgerRows = parseLedger(fs.readFileSync(path.join(root, pmRel, "log.md"), "utf8"));
  } catch { /* no ledger yet — the cross-check just has nothing to check */ }
  const check = crossCheck(agg.daily, ledgerRows, actor, sinceIso);

  if (flags.json) {
    console.log(JSON.stringify({ actor, since: sinceIso, models: agg.models,
      daily: agg.daily, sessions: sessions.length, cross_check: check }, null, 2));
    return;
  }
  if (flags.sync) {
    const dir = path.join(root, pmRel, "usage");
    fs.mkdirSync(dir, { recursive: true });
    const file = path.join(dir, `${actorSlug(actor)}.md`);
    fs.writeFileSync(file, renderSyncFile(actor, sinceIso, todayIso, agg, sessions, check));
    console.log(`wrote ${path.relative(root, file)} — ${sessions.length} session(s), ` +
      `${agg.models.length} model(s), ${check.flags.length} flag(s). Commit it so the team sees it.`);
    if (check.flags.length) for (const f of check.flags) console.log("  " + f);
    return;
  }
  console.log(renderReport(actor, sinceIso, agg, sessions, check));
}

// ---- selftest ---------------------------------------------------------------
// The law applies to readers too: a parser that has never seen a hostile
// fixture is a parser you merely hope works.
function selftest() {
  let failed = 0;
  const check = (cond, ...why) => { if (!cond) { failed++; console.error("❌", ...why); } };
  const tmp = fs.mkdtempSync(path.join(os.tmpdir(), "vteam-usage-"));
  const root = path.join(tmp, "proj");
  const claudeDir = path.join(tmp, "claude");
  const codexDir = path.join(tmp, "codex");
  const projDir = path.join(claudeDir, "projects", mungeCwd(root));
  fs.mkdirSync(projDir, { recursive: true });

  const asst = (id, req, model, out, ts, branch) => JSON.stringify({
    type: "assistant", requestId: req, timestamp: ts, gitBranch: branch,
    message: { id, model, usage: { input_tokens: 10, cache_read_input_tokens: 500,
      cache_creation_input_tokens: 100, output_tokens: out } } });
  fs.writeFileSync(path.join(projDir, "s1.jsonl"), [
    asst("m1", "r1", "claude-fable-5", 1000, "2026-08-10T09:00:00Z", "feat/x"),
    asst("m1", "r1", "claude-fable-5", 1000, "2026-08-10T09:00:01Z", "feat/x"), // dup content block
    asst("m2", "r2", "claude-fable-5", 2000, "2026-08-10T10:30:00Z", "feat/x"),
    "{torn json", "",
  ].join("\n"));
  const cs = readClaudeSessions(claudeDir, root, "2026-08-01");
  check(cs.length === 1 && cs[0].msgs === 2, "dup message.id must count ONCE", cs);
  check(cs[0].output === 3000 && cs[0].branch === "feat/x", "sum + branch", cs);
  check(readClaudeSessions(claudeDir, root, "2026-08-11").length === 0, "since filter");

  const cxDir = path.join(codexDir, "sessions", "2026", "08", "12");
  fs.mkdirSync(cxDir, { recursive: true });
  const cx = (cwd) => [
    JSON.stringify({ type: "session_meta", timestamp: "2026-08-12T03:00:00Z",
      payload: { cwd, timestamp: "2026-08-12T03:00:00Z" } }),
    JSON.stringify({ type: "turn_context", payload: { model: "gpt-5.5" } }),
    JSON.stringify({ type: "event_msg", timestamp: "2026-08-12T03:05:00Z",
      payload: { type: "token_count", info: { last_token_usage:
        { input_tokens: 800, cached_input_tokens: 600, output_tokens: 300 } } } }),
  ].join("\n");
  fs.writeFileSync(path.join(cxDir, "rollout-a.jsonl"), cx(root));
  fs.writeFileSync(path.join(cxDir, "rollout-b.jsonl"), cx("/somewhere/else"));
  const xs = readCodexSessions(codexDir, root, "2026-08-01");
  check(xs.length === 1, "foreign-cwd codex session must be skipped", xs);
  check(xs[0].input === 200 && xs[0].cache_read === 600 && xs[0].output === 300,
    "codex cached split", xs);

  const agg = aggregate([...cs, ...xs]);
  check(agg.daily.length === 2 && agg.models.length === 2, "day×model rows", agg);

  // a session spanning midnight must contribute to EVERY day it touched —
  // binning it on the start day false-flags every later day as idle
  fs.writeFileSync(path.join(projDir, "s2.jsonl"), [
    asst("m3", "r3", "claude-fable-5", 500, "2026-08-13T23:50:00Z", "main"),
    asst("m4", "r4", "claude-fable-5", 700, "2026-08-14T00:10:00Z", "main"),
  ].join("\n"));
  const spans = readClaudeSessions(claudeDir, root, "2026-08-01");
  const spanAgg = aggregate(spans.filter((x) => x.id === "s2"));
  check(spanAgg.daily.length === 2 &&
    spanAgg.daily[0].date === "2026-08-13" && spanAgg.daily[0].output === 500 &&
    spanAgg.daily[1].date === "2026-08-14" && spanAgg.daily[1].output === 700,
    "midnight-spanning session bins per MESSAGE day", spanAgg.daily);
  fs.rmSync(path.join(projDir, "s2.jsonl"));

  const rows = parseLedger([
    "| Date | Lane | Actor | Item | Result | Link |", "|---|---|---|---|---|---|",
    "| 2026-08-10 | DEV | An | T-1 | done · tok ≈ 40k | PR #1 |",
    "| 2026-08-15 | DEV | An | T-2 | done · tok ≈ 40k | PR #2 |", // done, no session that day
  ].join("\n"));
  const chk = crossCheck(agg.daily, rows, "An", "2026-08-01");
  check(chk.flags.some((f) => f.includes("2026-08-15") && f.includes("NO AI session")),
    "done-day-without-session must flag", chk.flags);
  check(chk.flags.some((f) => f.includes("2026-08-12") && f.includes("no row")) === false,
    "codex day under 10k output must NOT flag", chk.flags);
  const clean = crossCheck(agg.daily, rows.slice(0, -1).concat(parseLedger(
    "| Date | Lane | Actor | Item | Result | Link |\n|---|---|---|---|---|---|\n| 2026-08-10 | DEV | An | T-1 | done · tok ≈ 40k | PR #1 |")),
    "An", "2026-08-01");
  check(clean.flags.length === 0, "clean history must not flag", clean.flags);

  check(actorSlug("Connor Phạm  Jr.") === "connor-ph-m-jr", actorSlug("Connor Phạm  Jr."));
  const f1 = renderSyncFile("An", "2026-08-01", "2026-08-21", agg, [...cs, ...xs], chk);
  const f2 = renderSyncFile("An", "2026-08-01", "2026-08-21", agg, [...cs, ...xs], chk);
  check(f1 === f2, "sync must be deterministic");
  check(/^ACTOR: An$/m.test(f1) && /^\| 2026-08-10 \| claude \| claude-fable-5 \| 1 \| 2 \| \d+ \| \d+ \| \d+ \| \d+ \|$/m.test(f1),
    "sync file must keep the shape perf_report parses", f1);
  fs.rmSync(tmp, { recursive: true, force: true });
  if (failed) { console.error(`usage selftest: ${failed} FAILED`); process.exit(1); }
  console.log("usage selftest: OK (dedup + torn line + codex cwd filter + since filter "
    + "+ 2 cross-check flags + clean path + deterministic sync)");
}
