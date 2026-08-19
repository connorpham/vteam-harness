// board.mjs — `vteam board`: a READ-ONLY local dashboard over the proof trail.
//
// The framework's paper trail already lives in files (backlog tickets, the
// dispatch ledger, the decision queue, evd/<KEY>/REPORT.md verdicts). This
// serves those files back as one page so a human can see the state of the team
// without grepping — and NOTHING else:
//
//   * loopback ONLY (127.0.0.1). This reads private project data; binding
//     0.0.0.0 would publish a repo's backlog to the LAN. Not configurable.
//   * GET only. There is no mutating endpoint anywhere in this file — no POST
//     handler exists to be reached; every non-GET method answers 405. A board
//     that could transition a ticket would be a second, ungated write path
//     around the gates.
//   * exactly two routes (/ and /api/state) plus 404. No static file serving,
//     so there is no path-traversal surface to get wrong.
//   * never reads .env and never surfaces env values — only the handful of
//     config keys named in readConfigPanel().
//   * doctor is REPORTED, never RUN: the server shells out to nothing. It shows
//     a cached `.vteam/doctor.json` (write it with `vteam doctor --json >
//     .vteam/doctor.json`) or says plainly that no cache exists.
//
// State is assembled fresh per request (no cache) — the page is a window onto
// the working tree, so a stale panel would be a lie about the repo.
//
// v1 reads the markdown backlog only. With tracker.provider = jira|github the
// tickets panel returns null plus a note; inventing a ticket list from a remote
// tracker without calling it would be exactly the fabrication the gates exist
// to stop.
//
// Selftest:  node src/cli/board.mjs --selftest
//   Boots on port 0 against a temp fixture repo (2 tickets in different
//   statuses, a 3-row ledger, evd/ with one REPORT), asserts the parses, then
//   the mutations that must NOT crash or pass silently: POST → 405,
//   /../etc/passwd → 404, a malformed ticket file → a `warnings` entry.
import { spawnSync } from "node:child_process";
import fs from "node:fs";
import http from "node:http";
import os from "node:os";
import path from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";
import { repoRoot } from "./util.mjs";
import { loadConfig, cfgGet, CONFIG_NAME } from "./config.mjs";

const DEFAULT_PORT = 4177;
const HOST = "127.0.0.1";          // loopback only — see the header
const LEDGER_ROWS = 50;            // panel depth: last N rows
const RAW_DECISION_LINES = 20;     // fallback when decisions.md has no statuses
const KEY_RE = /^[A-Za-z][A-Za-z0-9]*-[0-9]+$/;   // same grammar as tracker.py
const VERDICTS = ["PASS", "FAIL", "PARTIAL", "NEW-BUG", "BLOCKED", "UNCLEAR"];
const READ_CAP = 2_000_000;        // bytes — never slurp a stray binary
const EVD_FILE_CAP = 200;          // files listed per ticket

// ---- small fs helpers (all failure-tolerant: a board must never crash) -------
function readSmall(abs) {
  try {
    if (fs.statSync(abs).size > READ_CAP) return null;
    return fs.readFileSync(abs, "utf8");
  } catch { return null; }
}
function listDir(abs) {
  try { return fs.readdirSync(abs, { withFileTypes: true }); } catch { return []; }
}
function rel(root, abs) { return path.relative(root, abs).split(path.sep).join("/"); }

// ---- tickets ----------------------------------------------------------------
/** status → category, mirroring tracker.py Tracker.status_category exactly. */
export function statusCategory(status, cfg) {
  const s = String(status).trim().toLowerCase();
  const doneRaw = cfgGet(cfg, "tracker.done_statuses", ["Done", "Closed", "Resolved"]);
  const done = (Array.isArray(doneRaw) ? doneRaw : [doneRaw]).map((x) => String(x).toLowerCase());
  const review = String(cfgGet(cfg, "tracker.review_status", "In Review")).toLowerCase();
  if (done.includes(s)) return "done";
  if (s === review) return "in_review";
  if (s === "in progress" || s === "doing") return "in_progress";
  return "todo";
}

/** Parse one markdown ticket. Returns {ticket} or {warning} — never throws. */
export function parseTicket(key, text, cfg, relFile) {
  const field = (name) => {
    const m = text.match(new RegExp(`^- ${name}:\\s*(.*)$`, "m"));
    return m ? m[1].trim() : "";
  };
  const h1 = text.match(/^# \S+?:\s*(.*)$/m);
  const statusLine = text.match(/^- status:\s*(.*)$/m);
  const problems = [];
  if (!h1) problems.push("no `# KEY: summary` title line");
  if (!statusLine) problems.push("no `- status:` line");
  if (problems.length) {
    return { warning: `${relFile}: ${problems.join(" and ")} — ticket skipped (fix the file; see tracker.py MarkdownTracker)` };
  }
  const status = statusLine[1].trim() || "To Do";
  const commentsPart = text.includes("## Comments") ? text.split("## Comments").slice(1).join("## Comments") : "";
  const comments = commentsPart ? (commentsPart.match(/^### /gm) || []).length : 0;
  return {
    ticket: {
      key: key.toUpperCase(),
      summary: h1[1].trim(),
      status,
      status_category: statusCategory(status, cfg),
      labels: field("labels").split(",").map((x) => x.trim()).filter(Boolean),
      assignee: field("assignee"),
      estimate: field("estimate"),
      comments,
      file: relFile,
    },
  };
}

function readTicketsPanel(root, cfg, warnings) {
  const provider = String(cfgGet(cfg, "tracker.provider", "markdown"));
  const dirRel = String(cfgGet(cfg, "paths.backlog", "docs/backlog"));
  const dirAbs = path.join(root, dirRel);
  if (provider !== "markdown") {
    return {
      provider, source: dirRel, exists: fs.existsSync(dirAbs), tickets: null,
      note: `the board reads the markdown backlog only in v1 — tracker.provider is '${provider}', so this panel shows nothing rather than guessing at ${provider} state`,
    };
  }
  if (!fs.existsSync(dirAbs)) {
    return { provider, source: dirRel, exists: false, tickets: [],
      note: `no backlog directory — create ${dirRel}/ and add one <KEY>.md per ticket` };
  }
  const tickets = [];
  for (const e of listDir(dirAbs)) {
    if (!e.isFile() || !e.name.endsWith(".md")) continue;
    const key = e.name.slice(0, -3);
    const relFile = `${dirRel}/${e.name}`;
    if (!KEY_RE.test(key)) {
      warnings.push(`${relFile}: filename is not <PREFIX>-<number> — not a ticket, skipped`);
      continue;
    }
    const text = readSmall(path.join(dirAbs, e.name));
    if (text === null) { warnings.push(`${relFile}: unreadable (too large or permissions) — skipped`); continue; }
    const r = parseTicket(key, text, cfg, relFile);
    if (r.warning) warnings.push(r.warning);
    else tickets.push(r.ticket);
  }
  tickets.sort((a, b) => a.key.localeCompare(b.key, "en", { numeric: true }));
  return { provider, source: dirRel, exists: true, tickets,
    note: tickets.length ? null : `no tickets yet — add ${dirRel}/<KEY>.md (see the markdown tracker format)` };
}

// ---- ledger ----------------------------------------------------------------
// MUST match core/scripts/lib/ledger.py — conformance fixtures in
// ledger.py --selftest cover both (the selftest below asserts this mirror
// against `ledger.py --fixtures`, so the two grammars cannot drift silently).
export function resultKind(result) {
  const r = String(result).trim();
  if (/^done\b/.test(r)) return "done";
  if (/^blocked:\s*\S/.test(r)) return "blocked";   // a bare 'blocked:' has no reason
  if (/^failed:\s*\S/.test(r)) return "failed";
  return "other";          // log_check reds these; the board shows them as-is
}

/** Parse the {paths.pm}/log.md dispatch table. Two shapes, same as ledger.py:
 * v2     | Date | Lane | Actor | Item | Result | Link |
 * legacy | Date | Lane | Item | Result | Link |        (actor -> null) */
export function parseLedger(text) {
  const rows = [];
  let inTable = false;
  for (const line of text.split("\n")) {
    if (/^\|\s*Date\s*\|/i.test(line)) { inTable = true; continue; }
    if (!inTable || !line.startsWith("|") || line.startsWith("|---")) continue;
    const cells = line.trim().replace(/^\|/, "").replace(/\|$/, "").split("|").map((c) => c.trim());
    let date, lane, actor, item, result, link;
    if (cells.length === 6) [date, lane, actor, item, result, link] = cells;
    else if (cells.length === 5) { [date, lane, item, result, link] = cells; actor = null; }
    else { rows.push({ malformed: true, raw: line.trim(), columns: cells.length }); continue; }
    // token accounting — ledger.py's space rule: exactly one space each side
    // of ≈, optional case-insensitive k suffix ('tok≈90k' is malformed → null)
    const tokM = result.match(/tok ≈ (\d+(?:\.\d+)?)([kK])?\b/);
    const tok = tokM ? tokM[1] + (tokM[2] || "") : null;
    rows.push({ date, lane, actor, item, result, result_kind: resultKind(result), tok, link });
  }
  return rows;
}

function readLedgerPanel(root, cfg) {
  const pmRel = String(cfgGet(cfg, "paths.pm", "docs/pm"));
  const source = `${pmRel}/log.md`;
  const text = readSmall(path.join(root, pmRel, "log.md"));
  if (text === null) {
    return { source, exists: false, rows: [], rows_total: 0, totals: {},
      note: `no dispatch ledger — create ${source} with the header row \`| Date | Lane | Item | Result | Link |\`` };
  }
  const all = parseLedger(text);
  const totals = { done: 0, blocked: 0, failed: 0, other: 0, malformed: 0 };
  for (const r of all) totals[r.malformed ? "malformed" : r.result_kind]++;
  // per-person rollup — only when the Actor column exists (team.size > 1 installs)
  let by_actor = null;
  if (all.some((r) => !r.malformed && r.actor)) {
    by_actor = {};
    for (const r of all) {
      if (r.malformed) continue;
      const who = r.actor || "(legacy)";
      by_actor[who] ??= { items: 0, done: 0, tok_k: 0 };
      by_actor[who].items++;
      if (r.result_kind === "done") by_actor[who].done++;
      if (r.tok) by_actor[who].tok_k += /[kK]$/.test(r.tok) ? parseFloat(r.tok) : parseFloat(r.tok) / 1000;
    }
  }
  return { source, exists: true, rows: all.slice(-LEDGER_ROWS), rows_total: all.length, totals, by_actor,
    note: all.length ? null : `${source} exists but has no data rows yet` };
}

// ---- decisions --------------------------------------------------------------
/** Conservative parse: table rows whose Status cell carries a known sentinel.
 * Unknown format (no sentinel anywhere) → mode "raw" and the last lines. */
export function parseDecisions(text) {
  const sentinel = /(🔴\s*OPEN|\bOPEN\b|PROVISIONAL|✅\s*DECIDED|\bDECIDED\b)/;
  const items = [];
  let section = "";
  let sawAnySentinel = false;
  for (const line of text.split("\n")) {
    const h = line.match(/^##+\s*(.+)$/);
    if (h) { section = h[1].trim(); continue; }
    if (!line.startsWith("|") || line.startsWith("|---") || /^\|\s*#\s*\|/.test(line)) continue;
    const cells = line.trim().replace(/^\|/, "").replace(/\|$/, "").split("|").map((c) => c.trim());
    const statusIdx = cells.findIndex((c) => sentinel.test(c));
    if (statusIdx === -1) continue;
    sawAnySentinel = true;
    const status = cells[statusIdx];
    if (!/\bOPEN\b/.test(status)) continue;   // PROVISIONAL/DECIDED are not the queue
    items.push({
      section,
      id: cells[0] || "",
      text: cells.slice(1, statusIdx).filter(Boolean).join(" · "),
      status,
      due: cells[statusIdx + 1] || "",
    });
  }
  return { mode: sawAnySentinel ? "parsed" : "raw", open: items };
}

function readDecisionsPanel(root, cfg) {
  const pmRel = String(cfgGet(cfg, "paths.pm", "docs/pm"));
  const source = `${pmRel}/decisions.md`;
  const text = readSmall(path.join(root, pmRel, "decisions.md"));
  if (text === null) {
    return { source, exists: false, mode: "missing", open: [], raw: [],
      note: `no decision queue — create ${source} (statuses: 🔴 OPEN · 🟡 PROVISIONAL · ✅ DECIDED)` };
  }
  const { mode, open } = parseDecisions(text);
  if (mode === "raw") {
    const lines = text.split("\n").filter((l) => l.trim());
    return { source, exists: true, mode: "raw", open: [], raw: lines.slice(-RAW_DECISION_LINES),
      note: `${source} carries no recognizable status marker (🔴 OPEN / PROVISIONAL / ✅ DECIDED) — showing the last ${RAW_DECISION_LINES} non-empty lines verbatim instead of guessing` };
  }
  return { source, exists: true, mode: "parsed", open, raw: [],
    note: open.length ? null : `no 🔴 OPEN rows in ${source} — nothing is waiting on the owner` };
}

// ---- evidence --------------------------------------------------------------
function walkFiles(absDir, baseAbs, out) {
  for (const e of listDir(absDir)) {
    if (out.length >= EVD_FILE_CAP) return;
    const abs = path.join(absDir, e.name);
    if (e.isDirectory()) walkFiles(abs, baseAbs, out);
    else if (e.isFile()) {
      let size = null;
      try { size = fs.statSync(abs).size; } catch { /* vanished mid-walk */ }
      out.push({ path: path.relative(baseAbs, abs).split(path.sep).join("/"), size });
    }
  }
}

/** VERDICT + pinned COMMIT out of an evd REPORT.md — from the H1 line ONLY,
 * word-boundary matched, mirroring evd_check.py: a `VERDICT:` line elsewhere in
 * the file (which evd_check reds) must not display as a verdict here, and
 * '# PASSPORT verification' is not PASS. */
export function parseReport(text) {
  const h1 = (text.split("\n").find((l) => l.startsWith("# ")) || "");
  const m = h1.toUpperCase().match(new RegExp("\\b(" + VERDICTS.join("|") + ")\\b"));
  const verdict = m ? m[1] : null;
  const commit = (text.match(/COMMIT\s*[:：]\s*([0-9a-f]{7,40})\b/i) || [])[1] || null;
  return { verdict, commit, h1: h1.replace(/^#\s*/, "").trim() };
}

function readEvidencePanel(root, cfg) {
  const evdRel = String(cfgGet(cfg, "paths.evidence", "evd"));
  const evdAbs = path.join(root, evdRel);
  if (!fs.existsSync(evdAbs)) {
    return { source: evdRel, exists: false, tickets: [],
      note: `no evidence tree — gates write it as ${evdRel}/<KEY>/ (REPORT.md · manifest.md · debate.md)` };
  }
  const tickets = [];
  for (const e of listDir(evdAbs)) {
    if (!e.isDirectory() || !KEY_RE.test(e.name)) continue;
    const dirAbs = path.join(evdAbs, e.name);
    const files = [];
    walkFiles(dirAbs, dirAbs, files);
    files.sort((a, b) => a.path.localeCompare(b.path));
    const reportText = readSmall(path.join(dirAbs, "REPORT.md"));
    tickets.push({
      key: e.name.toUpperCase(),
      dir: `${evdRel}/${e.name}`,
      files,
      truncated: files.length >= EVD_FILE_CAP,
      report: reportText === null
        ? { exists: false, verdict: null, commit: null, h1: null }
        : { exists: true, ...parseReport(reportText) },
    });
  }
  tickets.sort((a, b) => a.key.localeCompare(b.key, "en", { numeric: true }));
  return { source: evdRel, exists: true, tickets,
    note: tickets.length ? null : `${evdRel}/ has no <KEY>/ directories yet` };
}

// ---- doctor (cached only — the server runs nothing) -------------------------
const DOCTOR_CACHE_REL = ".vteam/doctor.json";
function readDoctorPanel(root) {
  const abs = path.join(root, DOCTOR_CACHE_REL);
  const text = readSmall(abs);
  if (text === null) {
    return { source: DOCTOR_CACHE_REL, exists: false, summary: null,
      note: `no cached doctor run — the board never runs doctor itself; refresh with \`vteam doctor --json > ${DOCTOR_CACHE_REL}\`` };
  }
  let parsed = null;
  try { parsed = JSON.parse(text); } catch {
    return { source: DOCTOR_CACHE_REL, exists: true, summary: null,
      note: `${DOCTOR_CACHE_REL} is not valid JSON — re-run \`vteam doctor --json > ${DOCTOR_CACHE_REL}\`` };
  }
  let cachedAt = null;
  try { cachedAt = fs.statSync(abs).mtime.toISOString(); } catch { /* ignore */ }
  const checks = Array.isArray(parsed?.checks) ? parsed.checks : [];
  const counts = { ok: 0, warn: 0, fail: 0 };
  for (const c of checks) if (c && c.status in counts) counts[c.status]++;
  return {
    source: DOCTOR_CACHE_REL, exists: true, cached_at: cachedAt,
    summary: { ok: parsed?.ok === true, counts, total: checks.length,
      failing: checks.filter((c) => c && c.status !== "ok").map((c) => ({ name: c.name, status: c.status })).slice(0, 20) },
    note: "last-known result, as of the cache timestamp — not a live check",
  };
}

// ---- config panel (explicit allowlist — never env, never .env) --------------
function readConfigPanel(cfg) {
  return {
    source: CONFIG_NAME,
    name: cfg ? String(cfgGet(cfg, "project.name", "(unnamed)")) : null,
    key: cfg ? String(cfgGet(cfg, "project.key", "?")) : null,
    autonomy: cfg ? String(cfgGet(cfg, "autonomy.level", "assisted")) : null,
    stack_profile: cfg ? String(cfgGet(cfg, "stack.profile", "generic")) : null,
    tracker_provider: cfg ? String(cfgGet(cfg, "tracker.provider", "markdown")) : null,
  };
}

// ---- state assembly --------------------------------------------------------
/** Everything /api/state returns. Fresh read of the working tree, no cache. */
export function collectState(root) {
  if (typeof root !== "string" || !root) {
    throw new Error("collectState: root must be an absolute repo path (got " + typeof root + ")");
  }
  const warnings = [];
  let cfg = null;
  try { cfg = loadConfig(root); } catch (e) { warnings.push(`${CONFIG_NAME}: ${e.message}`); }
  if (cfg === null && !warnings.length) {
    warnings.push(`${CONFIG_NAME} not found at ${root} — run \`npx vteam init\`; every panel below is empty because nothing tells the board where to look`);
  }
  const c = cfg ?? {};
  return {
    generated_at: new Date().toISOString(),
    root,
    config: readConfigPanel(cfg),
    tickets: readTicketsPanel(root, c, warnings),
    ledger: readLedgerPanel(root, c),
    decisions: readDecisionsPanel(root, c),
    evidence: readEvidencePanel(root, c),
    doctor: readDoctorPanel(root),
    warnings,
  };
}

// ---- the page --------------------------------------------------------------
// Self-contained: inline CSS + inline JS, zero network beyond /api/state.
// Client JS avoids backticks so this stays one readable template literal.
const PAGE = `<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>vteam board</title>
<style>
:root{color-scheme:light dark;--bg:#f7f7f8;--panel:#fff;--ink:#16181d;--dim:#5d6470;
--line:#e2e4e9;--accent:#2b5fd9;--ok:#1a7f45;--warn:#8a5a00;--bad:#b3261e;--chip:#eef0f4}
@media (prefers-color-scheme:dark){:root{--bg:#0e1013;--panel:#171a20;--ink:#e7e9ee;
--dim:#98a0ad;--line:#272c35;--accent:#7aa2ff;--ok:#4ec27f;--warn:#e0aa4a;--bad:#ff7b6e;--chip:#212632}}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);font:14px/1.5 ui-sans-serif,-apple-system,Segoe UI,Roboto,sans-serif}
header{padding:18px 22px;border-bottom:1px solid var(--line);display:flex;flex-wrap:wrap;gap:14px;align-items:baseline}
h1{font-size:17px;margin:0}
main{padding:18px 22px 60px;max-width:1400px}
section{background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:14px 16px;margin-bottom:18px}
h2{font-size:13px;text-transform:uppercase;letter-spacing:.06em;margin:0 0 2px}
.src{font:11px/1.4 ui-monospace,SFMono-Regular,Menlo,monospace;color:var(--dim);margin-bottom:10px}
.empty{color:var(--dim);font-style:italic}
.cols{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:12px}
.col h3{font-size:12px;margin:0 0 8px;color:var(--dim);text-transform:uppercase;letter-spacing:.05em}
.card{border:1px solid var(--line);border-radius:8px;padding:8px 10px;margin-bottom:8px}
.card .k{font:12px ui-monospace,Menlo,monospace;color:var(--accent)}
.meta{font-size:11px;color:var(--dim);margin-top:4px}
table{width:100%;border-collapse:collapse;font-size:13px}
th,td{text-align:left;padding:5px 8px;border-bottom:1px solid var(--line);vertical-align:top}
th{font-size:11px;text-transform:uppercase;letter-spacing:.05em;color:var(--dim)}
td.mono,.mono{font-family:ui-monospace,Menlo,monospace;font-size:12px}
.badge{display:inline-block;padding:1px 7px;border-radius:99px;font-size:11px;font-weight:600;background:var(--chip);color:var(--dim)}
.b-done{background:color-mix(in srgb,var(--ok) 18%,transparent);color:var(--ok)}
.b-blocked{background:color-mix(in srgb,var(--warn) 20%,transparent);color:var(--warn)}
.b-failed,.b-bad{background:color-mix(in srgb,var(--bad) 18%,transparent);color:var(--bad)}
.b-ok{background:color-mix(in srgb,var(--ok) 18%,transparent);color:var(--ok)}
.chips{display:flex;gap:6px;flex-wrap:wrap}
.alert{border-color:var(--bad)}
.alert h2{color:var(--bad)}
ul{margin:6px 0 0;padding-left:20px}
li{margin:2px 0}
pre{margin:0;overflow-x:auto;font-size:12px;background:var(--chip);padding:8px;border-radius:6px}
.wrap{overflow-x:auto}
.ro{font-size:11px;color:var(--dim)}
</style></head><body>
<header><h1>vteam board</h1><span id="hdr" class="ro"></span>
<span class="ro">read-only · loopback · GET only</span></header>
<main id="main"><p class="empty">loading /api/state …</p></main>
<script>
function esc(s){return String(s==null?"":s).replace(/[&<>"']/g,function(c){
return {"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c];});}
function src(p){return '<div class="src">read from: '+esc(p)+'</div>';}
function empty(msg){return '<p class="empty">'+esc(msg)+'</p>';}
var CATS=[["todo","To do"],["in_progress","In progress"],["in_review","In review"],["done","Done"]];

function ticketsPanel(t){
  var h='<section><h2>Tickets</h2>'+src(t.source+(t.provider?'  (tracker.provider: '+t.provider+')':''));
  if(t.tickets===null){return h+empty(t.note)+'</section>';}
  if(!t.tickets.length){return h+empty(t.note||'no tickets')+'</section>';}
  h+='<div class="cols">';
  for(var i=0;i<CATS.length;i++){
    var cat=CATS[i][0],label=CATS[i][1];
    var list=t.tickets.filter(function(x){return x.status_category===cat;});
    h+='<div class="col"><h3>'+esc(label)+' ('+list.length+')</h3>';
    if(!list.length){h+='<p class="empty">none</p>';}
    for(var j=0;j<list.length;j++){var k=list[j];
      h+='<div class="card"><span class="k">'+esc(k.key)+'</span> '+esc(k.summary)+
         '<div class="meta">'+esc(k.status)+
         (k.labels.length?' · '+esc(k.labels.join(', ')):'')+
         (k.assignee?' · '+esc(k.assignee):'')+
         ' · '+k.comments+' comment'+(k.comments===1?'':'s')+
         '<br><span class="mono">'+esc(k.file)+'</span></div></div>';}
    h+='</div>';}
  return h+'</div></section>';
}

function ledgerPanel(l){
  var h='<section><h2>Dispatch ledger</h2>'+src(l.source);
  if(!l.exists||!l.rows.length){return h+empty(l.note||'no rows')+'</section>';}
  var tot=l.totals,chips='<div class="chips" style="margin-bottom:8px">';
  var keys=["done","blocked","failed","other","malformed"];
  for(var i=0;i<keys.length;i++){if(tot[keys[i]]){
    chips+='<span class="badge b-'+(keys[i]==="done"?"done":keys[i]==="blocked"?"blocked":keys[i]==="other"?"":"failed")+'">'+
      esc(keys[i])+' '+tot[keys[i]]+'</span>';}}
  chips+='<span class="badge">'+l.rows_total+' rows total · showing last '+l.rows.length+'</span></div>';
  h+=chips+'<div class="wrap"><table><tr><th>Date</th><th>Lane</th><th>Item</th><th>Result</th><th>tok</th><th>Link</th></tr>';
  for(var r=0;r<l.rows.length;r++){var row=l.rows[r];
    if(row.malformed){h+='<tr><td colspan="6"><span class="badge b-bad">malformed ('+row.columns+' cols)</span> <span class="mono">'+esc(row.raw)+'</span></td></tr>';continue;}
    h+='<tr><td class="mono">'+esc(row.date)+'</td><td>'+esc(row.lane)+'</td><td>'+esc(row.item)+
       '</td><td><span class="badge b-'+esc(row.result_kind)+'">'+esc(row.result_kind)+'</span> '+esc(row.result)+
       '</td><td class="mono">'+esc(row.tok||'—')+'</td><td class="mono">'+esc(row.link)+'</td></tr>';}
  return h+'</table></div></section>';
}

function decisionsPanel(d){
  var open=d.open||[];
  var h='<section'+(open.length?' class="alert"':'')+'><h2>Decision queue'+(open.length?' — '+open.length+' OPEN':'')+'</h2>'+src(d.source);
  if(d.mode==='raw'){h+=empty(d.note)+'<pre>'+esc(d.raw.join('\\n'))+'</pre>';return h+'</section>';}
  if(!open.length){return h+empty(d.note||'nothing open')+'</section>';}
  h+='<div class="wrap"><table><tr><th>#</th><th>Section</th><th>Waiting on the owner</th><th>Status</th><th>Due</th></tr>';
  for(var i=0;i<open.length;i++){var o=open[i];
    h+='<tr><td class="mono">'+esc(o.id)+'</td><td>'+esc(o.section)+'</td><td>'+esc(o.text)+
       '</td><td><span class="badge b-failed">'+esc(o.status)+'</span></td><td class="mono">'+esc(o.due||'—')+'</td></tr>';}
  return h+'</table></div></section>';
}

function evidencePanel(e){
  var h='<section><h2>Evidence</h2>'+src(e.source+'/&lt;KEY&gt;/');
  if(!e.tickets.length){return h+empty(e.note||'no evidence')+'</section>';}
  h+='<div class="cols">';
  for(var i=0;i<e.tickets.length;i++){var t=e.tickets[i],r=t.report;
    var badge=!r.exists?'<span class="badge b-bad">no REPORT.md</span>'
      :'<span class="badge '+(r.verdict==='PASS'?'b-ok':r.verdict?'b-failed':'')+'">'+esc(r.verdict||'no verdict line')+'</span>';
    h+='<div class="card"><span class="k">'+esc(t.key)+'</span> '+badge+
       '<div class="meta">'+esc(r.commit?'COMMIT '+r.commit:r.exists?'no pinned COMMIT line':'')+
       '<br><span class="mono">'+esc(t.dir)+'/</span> — '+t.files.length+' file'+(t.files.length===1?'':'s')+
       (t.truncated?' (truncated)':'')+'</div><ul class="mono">';
    for(var j=0;j<t.files.length&&j<12;j++){h+='<li>'+esc(t.files[j].path)+'</li>';}
    if(t.files.length>12){h+='<li>… +'+(t.files.length-12)+' more</li>';}
    h+='</ul></div>';}
  return h+'</div></section>';
}

function doctorPanel(d){
  var h='<section><h2>Doctor (cached)</h2>'+src(d.source);
  if(!d.summary){return h+empty(d.note)+'</section>';}
  var s=d.summary;
  h+='<div class="chips"><span class="badge '+(s.ok?'b-ok':'b-failed')+'">'+(s.ok?'green':'red')+'</span>'+
     '<span class="badge b-ok">ok '+s.counts.ok+'</span><span class="badge b-blocked">warn '+s.counts.warn+
     '</span><span class="badge b-failed">fail '+s.counts.fail+'</span>'+
     '<span class="badge">cached '+esc(d.cached_at||'unknown')+'</span></div>';
  if(s.failing.length){h+='<ul>';for(var i=0;i<s.failing.length;i++){
    h+='<li><span class="badge b-'+(s.failing[i].status==='fail'?'failed':'blocked')+'">'+esc(s.failing[i].status)+'</span> '+esc(s.failing[i].name)+'</li>';}h+='</ul>';}
  h+='<p class="ro">'+esc(d.note)+'</p>';
  return h+'</section>';
}

function warnPanel(w){
  if(!w.length)return '';
  return '<section class="alert"><h2>Warnings — files the board could not read as expected</h2>'+
    '<ul>'+w.map(function(x){return '<li class="mono">'+esc(x)+'</li>';}).join('')+'</ul></section>';
}

function render(s){
  var c=s.config;
  document.getElementById('hdr').innerHTML=esc((c.name||'no project')+' ('+(c.key||'?')+')')+
    ' · autonomy <b>'+esc(c.autonomy||'?')+'</b> · stack <b>'+esc(c.stack_profile||'?')+
    '</b> · tracker <b>'+esc(c.tracker_provider||'?')+'</b> · '+esc(c.source)+
    ' · read '+esc(s.generated_at);
  document.getElementById('main').innerHTML=
    warnPanel(s.warnings)+decisionsPanel(s.decisions)+ticketsPanel(s.tickets)+
    ledgerPanel(s.ledger)+evidencePanel(s.evidence)+doctorPanel(s.doctor)+
    '<p class="ro">Every panel above names the file it was read from. State is re-read from disk on each load — reload to refresh. This server has no write endpoint.</p>';
}

fetch('/api/state').then(function(r){return r.json();}).then(render).catch(function(e){
  document.getElementById('main').innerHTML='<section class="alert"><h2>Could not load /api/state</h2><pre>'+
    esc(e&&e.message||e)+'</pre></section>';});
</script></body></html>
`;

// ---- server ----------------------------------------------------------------
/** The whole routing table: GET / and GET /api/state. Nothing else exists. */
export function createServer(root) {
  return http.createServer((req, res) => {
    const send = (code, type, body) => {
      res.writeHead(code, {
        "content-type": type,
        "cache-control": "no-store",
        "x-content-type-options": "nosniff",
        // the page loads nothing off-origin; say so to the browser too
        "content-security-policy": "default-src 'none'; style-src 'unsafe-inline'; script-src 'unsafe-inline'; connect-src 'self'",
      });
      res.end(body);
    };
    if (req.method !== "GET") {
      res.writeHead(405, { "content-type": "application/json", allow: "GET", "cache-control": "no-store" });
      res.end(JSON.stringify({ error: "method not allowed", detail: "vteam board is read-only: it has no mutating endpoint at all — GET / or GET /api/state" }));
      return;
    }
    let route = "";
    try { route = new URL(req.url, `http://${HOST}`).pathname; } catch { route = ""; }
    if (route === "/api/state") {
      let state;
      try { state = collectState(root); } catch (e) {
        send(500, "application/json; charset=utf-8",
          JSON.stringify({ error: "state assembly failed", detail: String(e && e.message || e) }, null, 2));
        return;
      }
      send(200, "application/json; charset=utf-8", JSON.stringify(state, null, 2));
      return;
    }
    if (route === "/") { send(200, "text/html; charset=utf-8", PAGE); return; }
    send(404, "application/json; charset=utf-8", JSON.stringify({
      error: "not found",
      detail: "vteam board serves exactly two routes and no files: GET / and GET /api/state",
    }));
  });
}

export async function board(flags = {}) {
  const root = repoRoot();
  const port = flags.port === undefined || flags.port === true ? DEFAULT_PORT : Number(flags.port);
  if (!Number.isInteger(port) || port < 0 || port > 65535) {
    console.error(`board: --port ${flags.port} is not a valid port (0-65535)`);
    process.exit(1);
  }
  const server = createServer(root);
  server.on("error", (e) => {
    if (e.code === "EADDRINUSE") {
      console.error(`board: 127.0.0.1:${port} is already in use — pick another with --port <n>`);
    } else console.error(`board: ${e.message}`);
    process.exit(1);
  });
  await new Promise((done) => server.listen(port, HOST, done));
  const live = server.address().port;
  console.log(`vteam board — read-only dashboard for ${root}`);
  console.log(`  http://${HOST}:${live}/`);
  console.log(`  GET / and GET /api/state only · loopback only · no write endpoint · nothing opened for you`);
  console.log("  Ctrl-C to stop.");
  for (const sig of ["SIGINT", "SIGTERM"]) {
    process.on(sig, () => { server.close(() => process.exit(0)); });
  }
}

// ---- selftest --------------------------------------------------------------
function httpReq(port, reqPath, method = "GET") {
  return new Promise((resolve, reject) => {
    const r = http.request({ host: HOST, port, path: reqPath, method }, (res) => {
      let body = "";
      res.setEncoding("utf8");
      res.on("data", (d) => { body += d; });
      res.on("end", () => resolve({ status: res.statusCode, headers: res.headers, body }));
    });
    r.on("error", reject);
    r.end();
  });
}

function put(root, relPath, text) {
  const abs = path.join(root, ...relPath.split("/"));
  fs.mkdirSync(path.dirname(abs), { recursive: true });
  fs.writeFileSync(abs, text);
}

function fixture(dir) {
  put(dir, "vteam.config.yaml",
    "version: 1\nproject:\n  name: Board Fixture\n  key: DEMO\n  adopted: 2026-01-01\n" +
    "paths:\n  backlog: docs/backlog\n  pm: docs/pm\n  evidence: evd\n" +
    "stack:\n  profile: generic\n" +
    "tracker:\n  provider: markdown\n  done_statuses: [Done, Closed]\n  review_status: In Review\n" +
    "autonomy:\n  level: assisted\n");
  put(dir, "docs/backlog/DEMO-1.md",
    "# DEMO-1: first ticket\n- status: To Do\n- labels: api, urgent\n\nbody\n" +
    "\n## Comments\n### 2026-01-02 09:00 UTC\nfirst\n\n### 2026-01-02 10:00 UTC\nsecond\n");
  put(dir, "docs/backlog/DEMO-2.md",
    "# DEMO-2: second ticket\n- status: In Progress\n- assignee: dev\n- labels: ui\n\nbody\n");
  put(dir, "docs/pm/log.md",
    "# Dispatch ledger\n\n| Date | Lane | Item | Result | Link |\n|---|---|---|---|---|\n" +
    "| 2026-01-02 | DEV | DEMO-1 | done (workhorse) · tok ≈ 90k | PR #1 |\n" +
    "| 2026-01-03 | QA | DEMO-1 | blocked: Q2 open | DEMO-1 |\n" +
    "| 2026-01-04 | DEV | DEMO-2 | failed: evd_check | PR #2 |\n");
  put(dir, "docs/pm/decisions.md",
    "# Decision queue\n\n## 1. Open questions\n\n| # | Question | Blocks | Status | Due |\n|---|---|---|---|---|\n" +
    "| Q1 | pick the payment provider | DEMO-2 | 🔴 OPEN | 2026-02-01 |\n" +
    "| Q2 | naming | — | ✅ DECIDED 2026-01-05 | — |\n");
  put(dir, "evd/DEMO-1/REPORT.md",
    "# Verification report DEMO-1 — PASS\nCOMMIT: abc1234\n\n## 1. What was checked\nthings\n");
  put(dir, "evd/DEMO-1/manifest.md", "TC list\n");
  put(dir, "evd/DEMO-1/tc-01/shot.png", "not-a-real-png");
}

async function selftest() {
  const assert = (cond, msg) => {
    if (!cond) { console.error(`board selftest FAILED: ${msg}`); process.exit(1); }
  };

  // ---- H4 conformance: this file MIRRORS core/scripts/lib/ledger.py ---------
  // The canonical grammar emits its fixture table (the 6 rows the audit caught
  // three parsers disagreeing on); the mirror must reproduce it exactly.
  // python3 is a hard dependency of the framework (every gate is python), so a
  // failed spawn here is a real red, not an environment quirk to paper over.
  const ledgerPy = fileURLToPath(new URL("../../core/scripts/lib/ledger.py", import.meta.url));
  assert(fs.existsSync(ledgerPy), `canonical grammar file missing: ${ledgerPy}`);
  const px = spawnSync("python3", [ledgerPy, "--fixtures"], { encoding: "utf8" });
  assert(px.status === 0, `python3 ledger.py --fixtures failed: ${px.stderr || px.error}`);
  const fixtures = JSON.parse(px.stdout);
  assert(fixtures.length === 6, `expected 6 conformance rows, got ${fixtures.length}`);
  const hdr = "| Date | Lane | Item | Result | Link |\n|---|---|---|---|---|\n";
  for (const f of fixtures) {
    const row = parseLedger(hdr + `| 2026-01-02 | DEV | X-1 | ${f.result} | PR #1 |\n`)[0];
    assert(row.result_kind === f.kind,
      `H4 drift on ${JSON.stringify(f.result)}: board kind ${row.result_kind} vs canonical ${f.kind}`);
    assert(row.tok === f.tok,
      `H4 drift on ${JSON.stringify(f.result)}: board tok ${JSON.stringify(row.tok)} vs canonical ${JSON.stringify(f.tok)}`);
  }

  const tmp = fs.mkdtempSync(path.join(os.tmpdir(), "vteam-board-selftest-"));
  let server = null;
  try {
    fixture(tmp);
    server = createServer(tmp);
    await new Promise((done) => server.listen(0, HOST, done));
    const port = server.address().port;
    assert(server.address().address === HOST, `must bind loopback only, got ${server.address().address}`);

    // ---- green: /api/state parses the fixture -------------------------------
    const r1 = await httpReq(port, "/api/state");
    assert(r1.status === 200, `/api/state status ${r1.status}`);
    assert(/no-store/.test(String(r1.headers["cache-control"])), "state must be uncacheable");
    const s = JSON.parse(r1.body);

    assert(s.config.name === "Board Fixture" && s.config.key === "DEMO", "config project name/key");
    assert(s.config.autonomy === "assisted" && s.config.stack_profile === "generic", "config autonomy/stack");
    assert(!JSON.stringify(s).includes("PATH="), "state must never carry env values");

    assert(s.tickets.tickets.length === 2, `expected 2 tickets, got ${s.tickets.tickets.length}`);
    const t1 = s.tickets.tickets.find((t) => t.key === "DEMO-1");
    const t2 = s.tickets.tickets.find((t) => t.key === "DEMO-2");
    assert(t1.status_category === "todo" && t2.status_category === "in_progress",
      `status_category: ${t1.status_category} / ${t2.status_category}`);
    assert(t1.summary === "first ticket" && t1.comments === 2 && t1.labels.length === 2,
      `DEMO-1 parse: ${JSON.stringify(t1)}`);
    assert(t1.file === "docs/backlog/DEMO-1.md", "ticket carries its source path");

    assert(s.ledger.rows.length === 3 && s.ledger.rows_total === 3, `ledger rows: ${s.ledger.rows.length}`);
    assert(s.ledger.rows[0].result_kind === "done" && s.ledger.rows[0].tok === "90k",
      `ledger row 0: ${JSON.stringify(s.ledger.rows[0])}`);
    assert(s.ledger.totals.done === 1 && s.ledger.totals.blocked === 1 && s.ledger.totals.failed === 1,
      `ledger totals: ${JSON.stringify(s.ledger.totals)}`);
    assert(s.ledger.source === "docs/pm/log.md", "ledger names its file");

    assert(s.decisions.mode === "parsed" && s.decisions.open.length === 1,
      `decisions: ${JSON.stringify(s.decisions)}`);
    assert(/payment provider/.test(s.decisions.open[0].text) && s.decisions.open[0].due === "2026-02-01",
      "OPEN row content + due date");

    assert(s.evidence.tickets.length === 1, `evidence tickets: ${s.evidence.tickets.length}`);
    const ev = s.evidence.tickets[0];
    assert(ev.report.exists && ev.report.verdict === "PASS" && ev.report.commit === "abc1234",
      `evidence report: ${JSON.stringify(ev.report)}`);
    assert(ev.files.length === 3 && ev.files.some((f) => f.path === "tc-01/shot.png"),
      `evidence files: ${JSON.stringify(ev.files)}`);

    assert(s.doctor.exists === false && /never runs doctor/.test(s.doctor.note),
      "doctor panel must be cache-only and say so");
    assert(s.warnings.length === 0, `clean fixture must warn about nothing: ${JSON.stringify(s.warnings)}`);

    // ---- the page is self-contained ----------------------------------------
    const r2 = await httpReq(port, "/");
    assert(r2.status === 200 && /vteam board/.test(r2.body), "/ must serve the page");
    assert(!/https?:\/\/(?!127\.0\.0\.1)/.test(r2.body.replace(/http:\/\/\$\{HOST\}/g, "")),
      "page must reference no off-host URL (no CDN)");
    assert(/docs\/pm\/log\.md|read from/.test(r2.body), "page must show source paths");

    // ---- mutations: the reds this board must be able to produce -------------
    let reds = 0;
    for (const method of ["POST", "PUT", "PATCH", "DELETE"]) {
      const m = await httpReq(port, "/api/state", method);
      assert(m.status === 405, `${method} /api/state must be 405, got ${m.status}`);
      assert(String(m.headers.allow) === "GET", `${method} must advertise Allow: GET`);
      reds++;
    }
    for (const bad of ["/../etc/passwd", "/%2e%2e/%2e%2e/etc/passwd", "/index.html",
      "/api/state/../../etc/passwd", "/docs/pm/log.md", "/.env"]) {
      const m = await httpReq(port, bad);
      assert(m.status === 404, `${bad} must be 404 (no static serving), got ${m.status}`);
      assert(!/root:|passwd|vteam.config/.test(m.body), `${bad} leaked file content`);
      reds++;
    }

    // malformed ticket file: a warning, NOT a crash and NOT a silent drop
    put(tmp, "docs/backlog/DEMO-3.md", "this file has no title line and no status line\n");
    put(tmp, "docs/backlog/notes.md", "a stray non-ticket file\n");
    const r3 = await httpReq(port, "/api/state");
    assert(r3.status === 200, `state must survive a malformed ticket, got ${r3.status}`);
    const s3 = JSON.parse(r3.body);
    assert(s3.warnings.some((w) => w.includes("DEMO-3.md")),
      `malformed ticket must land in warnings: ${JSON.stringify(s3.warnings)}`);
    assert(s3.warnings.some((w) => w.includes("notes.md")), "non-ticket filename must warn");
    assert(s3.tickets.tickets.length === 2, "the two good tickets must still parse");
    reds += 2;

    // verdicts come from the H1 ONLY, word-boundary matched (mirrors evd_check):
    // '# PASSPORT…' is not PASS, and a VERDICT: line outside the H1 — which
    // evd_check reds — must not display as a verdict here either
    put(tmp, "evd/DEMO-4/REPORT.md",
      "# PASSPORT verification sweep\nVERDICT: PASS\nCOMMIT: abc1234\n");
    const sV = JSON.parse((await httpReq(port, "/api/state")).body);
    const dV = sV.evidence.tickets.find((t) => t.key === "DEMO-4");
    assert(dV && dV.report.exists && dV.report.verdict === null,
      `PASSPORT/body-verdict must not read as PASS: ${JSON.stringify(dV && dV.report)}`);
    reds++;

    // non-markdown tracker: tickets null + the v1 note, never invented rows
    put(tmp, "vteam.config.yaml",
      fs.readFileSync(path.join(tmp, "vteam.config.yaml"), "utf8").replace("provider: markdown", "provider: jira"));
    const s4 = JSON.parse((await httpReq(port, "/api/state")).body);
    assert(s4.tickets.tickets === null && /markdown backlog only in v1/.test(s4.tickets.note),
      `jira provider must yield tickets:null + note: ${JSON.stringify(s4.tickets)}`);
    reds++;

    // a broken config must degrade to warnings, not a 500
    put(tmp, "vteam.config.yaml", "project: &anchor bad\n");
    const r5 = await httpReq(port, "/api/state");
    assert(r5.status === 200, `unparseable config must not 500, got ${r5.status}`);
    assert(JSON.parse(r5.body).warnings.some((w) => w.includes(CONFIG_NAME)),
      "unparseable config must surface as a warning");
    reds++;

    console.log(`board selftest: OK (ledger grammar conforms to ledger.py's 6 H4 fixtures; state parse green: 2 tickets/3 ledger rows/1 OPEN decision/1 evd verdict; ${reds} mutations red — 4 non-GET methods 405, 6 traversal/static paths 404, malformed ticket + stray file warned, PASSPORT/body verdict null, jira provider null, bad config degraded)`);
  } finally {
    if (server) await new Promise((done) => server.close(done));
    fs.rmSync(tmp, { recursive: true, force: true });
  }
}

// ---- entrypoint ------------------------------------------------------------
const isMain = process.argv[1] &&
  import.meta.url === pathToFileURL(path.resolve(process.argv[1])).href;
if (isMain) {
  try {
    const argv = process.argv.slice(2);
    if (argv.includes("--selftest") || argv.includes("selftest")) await selftest();
    else {
      const pi = argv.indexOf("--port");
      await board({ port: pi === -1 ? undefined : argv[pi + 1] });
    }
  } catch (e) {
    console.error(`board: ${e.message}`);
    process.exit(1);
  }
}
