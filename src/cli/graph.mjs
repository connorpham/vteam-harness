// graph.mjs — `vteam graph`: MAKE THE IMPLICIT WORK GRAPH VISIBLE.
//
// The dependency graph of a project already exists — it is just scattered across
// files no human reads together: `- blocked-by:` lines in backlog tickets, the
// sprint contract in plan.yaml, the dispatch history in log.md, the verdicts in
// evd/<KEY>/REPORT.md. "What can start now?" is therefore answered by memory,
// which is exactly how a blocked ticket gets dispatched and a done ticket ships
// without a verdict. This command computes that answer from the files instead.
//
// What it is NOT: a gate. graph REPORTS and always exits 0 — it is a mirror
// (same contract as `vteam audit`). Dangling edges and cycles are printed
// loudly, but the build is failed by dor_check/schedule_check/gate.py, not here.
// One rule, one home: the gate lives elsewhere; this file only looks.
//
// Read-only, Node built-ins only, no network, nothing spawned but `git
// rev-parse HEAD` (so a --json dump can be pinned to a commit).
//
// SOURCES (every panel names its file — board.mjs's honesty convention):
//   {paths.backlog}/<KEY>.md   nodes: key, status, labels, `- blocked-by:` edges
//   {paths.pm}/plan.yaml       sprint membership + day-costs (annotation only)
//   {paths.pm}/log.md          dispatch count, last lane/actor/result per ticket
//   {paths.evidence}/<KEY>/    REPORT.md H1 verdict + pinned COMMIT
//
// GRAMMAR REUSE: the markdown ticket / ledger / REPORT parsers are imported from
// board.mjs — this file adds no second grammar for them. The ONE exception is
// `- blocked-by:` (board.parseTicket does not surface links yet), mirrored here
// from tracker.py MarkdownTracker._parse, via board.parseTicket's blocked_by.
//
// Selftest:  node src/cli/graph.mjs --selftest
//   Temp fixture repo: 6 tickets covering every finding (a done ticket with a
//   PASS verdict, one genuinely ready, one pointing at a GHOST key, a 2-cycle,
//   a done ticket with no verdict), a 2-item plan, a ledger with actors. Asserts
//   the ready set is exactly the one computable ticket, then the mutations:
//   malformed ticket → warning not crash, jira provider → honest note not
//   invented edges, empty repo → empty report, and exit 0 in every mode.
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { spawnSync } from "node:child_process";
import { fileURLToPath, pathToFileURL } from "node:url";
import { repoRoot } from "./util.mjs";
import { loadConfig, cfgGet, CONFIG_NAME } from "./config.mjs";
import { parseConfig } from "../../core/scripts/lib/ctx.mjs";
// the markdown backlog / ledger / REPORT grammars — imported, never re-written
import { parseTicket, parseLedger, parseReport } from "./board.mjs";

const KEY_RE = /^[A-Za-z][A-Za-z0-9]*-[0-9]+$/;        // tracker.py KEY_RE
const KEY_TOKEN = /\b([A-Za-z][A-Za-z0-9]*-[0-9]+)\b/; // ledger Item cell → key
const READ_CAP = 2_000_000;   // bytes — never slurp a stray binary
const MAX_CYCLES = 50;        // a graph report must stay bounded
const DASH = "—";

// ---- small fs helpers (failure-tolerant: a mirror must never crash) ---------
function readSmall(abs) {
  try {
    if (fs.statSync(abs).size > READ_CAP) return null;
    return fs.readFileSync(abs, "utf8");
  } catch { return null; }
}
function listDir(abs) {
  try { return fs.readdirSync(abs, { withFileTypes: true }); } catch { return []; }
}
function byKey(a, b) { return String(a).localeCompare(String(b), "en", { numeric: true }); }

// ---- the one grammar this file owns ----------------------------------------
/** A plan cost → person-days. Mirrors schedule_check.py parse_cost ("1.5",
 * "1.5d", "12h"), except that a bad cost is REPORTED, never fatal — graph is a
 * mirror, so an unparseable plan must still yield a graph. */
export function parseCost(raw, hoursPerDay = 8) {
  const m = String(raw).trim().match(/^([0-9.]+)([dhDH]?)$/);
  if (!m) return null;
  const n = parseFloat(m[1]);
  if (!Number.isFinite(n)) return null;
  return m[2].toLowerCase() === "h" ? n / (hoursPerDay || 8) : n;
}

// ---- source readers ---------------------------------------------------------
function readTickets(root, cfg, warnings) {
  const provider = String(cfgGet(cfg, "tracker.provider", "markdown"));
  const dirRel = String(cfgGet(cfg, "paths.backlog", "docs/backlog"));
  const dirAbs = path.join(root, dirRel);
  const src = { provider, source: `${dirRel}/<KEY>.md`, dir: dirRel, exists: fs.existsSync(dirAbs) };
  if (provider !== "markdown") {
    // Rule 4: never fake an edge we cannot read offline.
    return { ...src, available: false, tickets: [],
      note: `tracker=${provider}: blocked_by edges live in the tracker — this offline view shows plan/ledger/evidence only` };
  }
  if (!src.exists) {
    return { ...src, available: true, tickets: [],
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
    const r = parseTicket(key, text, cfg ?? {}, relFile);   // board.mjs grammar
    if (r.warning) { warnings.push(r.warning); continue; }
    tickets.push({ ...r.ticket });  // blocked_by comes from board.parseTicket (one home)
  }
  tickets.sort((a, b) => byKey(a.key, b.key));
  return { ...src, available: true, tickets,
    note: tickets.length ? null : `no tickets yet — add ${dirRel}/<KEY>.md (see tracker.py MarkdownTracker)` };
}

function readPlan(root, cfg, warnings) {
  const pmRel = String(cfgGet(cfg, "paths.pm", "docs/pm"));
  const source = `${pmRel}/plan.yaml`;
  const hoursPerDay = Number(cfgGet(cfg, "team.hours_per_day", 8)) || 8;
  const text = readSmall(path.join(root, pmRel, "plan.yaml"));
  if (text === null) {
    return { source, exists: false, sprints: [], byKey: {},
      note: `no sprint plan — create ${source} (sprint-N: start/end/items: ["KEY 1.5d"])` };
  }
  let data = null;
  try { data = parseConfig(text); } catch (e) {
    warnings.push(`${source}: ${e.message} — plan annotations unavailable`);
    return { source, exists: true, sprints: [], byKey: {}, note: `${source} did not parse` };
  }
  const sprints = [];
  for (const [name, s] of Object.entries(data ?? {})) {
    const m = name.match(/^sprint-(\d+)$/);
    if (!m || s === null || typeof s !== "object" || Array.isArray(s)) continue;
    const items = [];
    for (const row of Array.isArray(s.items) ? s.items : []) {
      const im = String(row).trim().match(/^(\S+)\s+(\S+)$/);
      if (!im) {
        warnings.push(`${source}: item ${JSON.stringify(String(row))} in ${name} is not "KEY <days|hours>" — skipped`);
        continue;
      }
      const cost = parseCost(im[2], hoursPerDay);
      if (cost === null) warnings.push(`${source}: cost ${JSON.stringify(im[2])} on ${im[1]} in ${name} is not <n>, <n>d or <n>h`);
      items.push({ key: im[1].toUpperCase(), cost, cost_raw: im[2] });
    }
    sprints.push({ name, n: Number(m[1]), start: s.start ?? null, end: s.end ?? null, items });
  }
  sprints.sort((a, b) => a.n - b.n);
  const map = {};
  for (const sp of sprints) {
    for (const it of sp.items) {
      if (map[it.key]) {
        warnings.push(`${source}: ${it.key} is planned in both ${map[it.key].sprint} and ${sp.name} — first wins in this view`);
        continue;
      }
      map[it.key] = { sprint: sp.name, cost: it.cost, cost_raw: it.cost_raw };
    }
  }
  return { source, exists: true, sprints, byKey: map,
    note: sprints.length ? null : `${source} has no sprint-N blocks yet` };
}

function readLedger(root, cfg) {
  const pmRel = String(cfgGet(cfg, "paths.pm", "docs/pm"));
  const source = `${pmRel}/log.md`;
  const text = readSmall(path.join(root, pmRel, "log.md"));
  if (text === null) {
    return { source, exists: false, byKey: {}, rows: 0, malformed: 0,
      note: `no dispatch ledger — create ${source} with the header row \`| Date | Lane | Actor | Item | Result | Link |\`` };
  }
  const rows = parseLedger(text);            // board.mjs grammar
  const map = {};
  let malformed = 0;
  for (const r of rows) {
    if (r.malformed) { malformed++; continue; }
    const km = String(r.item || "").match(KEY_TOKEN);
    if (!km) continue;                        // a row about no ticket in particular
    const key = km[1].toUpperCase();
    map[key] ??= { dispatches: 0, last_lane: null, last_actor: null, last_result: null, last_date: null };
    const e = map[key];
    e.dispatches++;
    e.last_lane = r.lane || null;             // file order is chronological (appends)
    e.last_actor = r.actor || null;
    e.last_result = r.result || null;
    e.last_date = r.date || null;
  }
  return { source, exists: true, byKey: map, rows: rows.length, malformed,
    note: rows.length ? null : `${source} exists but has no data rows yet` };
}

function readEvidence(root, cfg) {
  const evdRel = String(cfgGet(cfg, "paths.evidence", "evd"));
  const evdAbs = path.join(root, evdRel);
  const src = { source: `${evdRel}/<KEY>/REPORT.md`, dir: evdRel, exists: fs.existsSync(evdAbs) };
  if (!src.exists) {
    return { ...src, byKey: {},
      note: `no evidence tree — gates write it as ${evdRel}/<KEY>/ (REPORT.md · manifest.md · debate.md)` };
  }
  const map = {};
  for (const e of listDir(evdAbs)) {
    if (!e.isDirectory() || !KEY_RE.test(e.name)) continue;
    const key = e.name.toUpperCase();
    const reportRel = `${evdRel}/${e.name}/REPORT.md`;
    const text = readSmall(path.join(evdAbs, e.name, "REPORT.md"));
    if (text === null) {
      map[key] = { verdict: null, commit: null, report: null, dir: `${evdRel}/${e.name}` };
      continue;
    }
    // the H1-line verdict rule, straight from board.parseReport (== evd_check.py)
    const { verdict, commit } = parseReport(text);
    map[key] = { verdict, commit, report: reportRel, dir: `${evdRel}/${e.name}` };
  }
  const n = Object.keys(map).length;
  return { ...src, byKey: map, note: n ? null : `${evdRel}/ has no <KEY>/ directories yet` };
}

function headCommit(root) {
  const r = spawnSync("git", ["rev-parse", "HEAD"],
    { cwd: root, encoding: "utf8", stdio: ["ignore", "pipe", "ignore"] });
  return r.status === 0 && r.stdout ? r.stdout.trim() : null;
}

// ---- cycles ----------------------------------------------------------------
/** Tarjan strongly-connected components over the `blocks` adjacency. Every
 * cycle lives entirely inside one SCC, so this is the cheap filter that keeps
 * the expensive path enumeration below off the acyclic 99% of a real backlog
 * (a dense DAG would otherwise cost exponential time to prove cycle-free). */
function sccs(adj, keys) {
  const index = new Map(), low = new Map(), onStack = new Set();
  const stack = [], out = [];
  let counter = 0;
  for (const root of keys) {
    if (index.has(root)) continue;
    const work = [[root, 0]];             // iterative: a long chain must not blow the stack
    while (work.length) {
      const frame = work[work.length - 1];
      const v = frame[0], i = frame[1];
      if (i === 0) {
        index.set(v, counter); low.set(v, counter); counter++;
        stack.push(v); onStack.add(v);
      }
      const nbrs = adj.get(v) ?? [];
      if (i < nbrs.length) {
        frame[1]++;
        const w = nbrs[i];
        if (!index.has(w)) work.push([w, 0]);
        else if (onStack.has(w)) low.set(v, Math.min(low.get(v), index.get(w)));
        continue;
      }
      work.pop();
      if (work.length) {
        const p = work[work.length - 1][0];
        low.set(p, Math.min(low.get(p), low.get(v)));
      }
      if (low.get(v) === index.get(v)) {
        const comp = [];
        for (;;) {
          const w = stack.pop();
          onStack.delete(w);
          comp.push(w);
          if (w === v) break;
        }
        out.push(comp);
      }
    }
  }
  return out;
}

/** Every simple cycle in the `blocks` adjacency, each canonicalised by rotating
 * to its smallest key so A>B>A and B>A>B report once (a self-blocked ticket
 * comes back as the 1-cycle [A]).
 *
 * Bounded twice over: enumeration runs only INSIDE a strongly connected
 * component, and a step budget stops a pathological tangle. A mirror that hangs
 * on a big repo is a mirror nobody runs — and truncation is reported on the
 * result (`.truncated`), never hidden. */
export function findCycles(adj, keys) {
  const seen = new Set();
  const cycles = [];
  let truncated = false;
  let budget = 200_000;              // DFS steps, across every component
  for (const comp of sccs(adj, keys)) {
    const inComp = new Set(comp);
    const selfLoop = comp.length === 1 && (adj.get(comp[0]) ?? []).includes(comp[0]);
    if (comp.length === 1 && !selfLoop) continue;   // acyclic node: nothing to walk
    const inPath = new Map();   // key -> index in the current path
    const path0 = [];
    const dfs = (node) => {
      if (cycles.length >= MAX_CYCLES || budget-- <= 0) return;
      inPath.set(node, path0.length);
      path0.push(node);
      for (const next of adj.get(node) ?? []) {
        if (inPath.has(next)) {
          const cyc = path0.slice(inPath.get(next));
          let min = 0;
          for (let i = 1; i < cyc.length; i++) if (byKey(cyc[i], cyc[min]) < 0) min = i;
          const rot = cyc.slice(min).concat(cyc.slice(0, min));
          const sig = rot.join("|");
          if (!seen.has(sig)) { seen.add(sig); cycles.push(rot); }
        } else if (inComp.has(next)) {
          dfs(next);
        }
        if (cycles.length >= MAX_CYCLES || budget <= 0) break;
      }
      path0.pop();
      inPath.delete(node);
    };
    for (const k of [...comp].sort(byKey)) {
      if (cycles.length >= MAX_CYCLES || budget <= 0) break;
      dfs(k);
    }
    if (cycles.length >= MAX_CYCLES || budget <= 0) truncated = true;
  }
  cycles.sort((a, b) => byKey(a.join(">"), b.join(">")));
  cycles.truncated = truncated;   // reported, never hidden
  return cycles;
}

// ---- the model -------------------------------------------------------------
/** Read every source and compute the graph. Pure data — no printing, no exit. */
export function buildGraph(root) {
  const warnings = [];
  let cfg = null;
  try { cfg = loadConfig(root); } catch (e) { warnings.push(`${CONFIG_NAME}: ${e.message}`); }
  if (cfg === null && !warnings.length) {
    warnings.push(`${CONFIG_NAME} not found at ${root} — run \`npx vteam-harness init\`; paths fall back to the defaults (docs/backlog, docs/pm, evd)`);
  }
  const c = cfg ?? {};
  const tk = readTickets(root, c, warnings);
  const plan = readPlan(root, c, warnings);
  const ledger = readLedger(root, c);
  const evd = readEvidence(root, c);

  const ticketByKey = new Map(tk.tickets.map((t) => [t.key, t]));
  // node set = tickets, plus every key the plan/ledger/evidence talks about
  // (marked in_backlog:false — an honest "we heard of it, there is no ticket")
  const keys = new Set(ticketByKey.keys());
  for (const k of Object.keys(plan.byKey)) keys.add(k);
  for (const k of Object.keys(ledger.byKey)) keys.add(k);
  for (const k of Object.keys(evd.byKey)) keys.add(k);

  const doneOf = (key) => {
    const t = ticketByKey.get(key);
    return t ? t.status_category === "done" : null;   // null = not knowable offline
  };

  const nodes = [];
  const edges = [];
  const dangling = [];
  const adj = new Map();          // blocker -> [blocked]  ("A blocks B")
  for (const key of [...keys].sort(byKey)) adj.set(key, []);

  for (const key of [...keys].sort(byKey)) {
    const t = ticketByKey.get(key) ?? null;
    const p = plan.byKey[key] ?? null;
    const l = ledger.byKey[key] ?? null;
    const e = evd.byKey[key] ?? null;
    const blockedBy = t ? [...t.blocked_by].sort(byKey) : [];
    const blockedOn = [];
    for (const b of blockedBy) {
      const exists = ticketByKey.has(b);
      if (!exists) {
        dangling.push({ from: key, to: b, file: t.file,
          detail: `no ${tk.dir}/${b}.md — the blocker does not exist` });
      }
      if (!exists || doneOf(b) !== true) blockedOn.push(b);
      edges.push({ from: b, to: key, kind: "blocks", dangling: !exists });
      if (!adj.has(b)) adj.set(b, []);
      adj.get(b).push(key);
    }
    const cat = t ? t.status_category : null;
    nodes.push({
      key,
      in_backlog: !!t,
      summary: t ? t.summary : null,
      status: t ? t.status : null,
      status_category: cat,
      labels: t ? t.labels : [],
      assignee: t ? (t.assignee || null) : null,
      file: t ? t.file : null,
      blocked_by: blockedBy,
      blocked_on: blockedOn,
      // ready is MACHINE-computed: open, and every blocker provably Done.
      // null when the ticket itself is not readable offline (non-markdown
      // tracker, or a key that only the plan/ledger/evd knows) — a guess would
      // be exactly the fabrication the gates exist to stop.
      ready: t ? (cat !== "done" && blockedOn.length === 0) : null,
      dispatches: l ? l.dispatches : 0,
      last_lane: l ? l.last_lane : null,
      last_actor: l ? l.last_actor : null,
      last_result: l ? l.last_result : null,
      evidence: e ? { verdict: e.verdict, commit: e.commit, report: e.report } : null,
      sprint: p ? p.sprint : null,
      cost: p ? p.cost : null,
      cost_raw: p ? p.cost_raw : null,
    });
  }
  for (const [k, v] of adj) { v.sort(byKey); adj.set(k, v); }
  edges.sort((a, b) => byKey(a.from, b.from) || byKey(a.to, b.to));
  dangling.sort((a, b) => byKey(a.from, b.from) || byKey(a.to, b.to));

  const cycles = findCycles(adj, [...ticketByKey.keys()].sort(byKey));
  const cyclePairs = new Set();
  for (const cyc of cycles) {
    for (let i = 0; i < cyc.length; i++) cyclePairs.add(`${cyc[i]}|${cyc[(i + 1) % cyc.length]}`);
  }
  for (const e of edges) e.in_cycle = cyclePairs.has(`${e.from}|${e.to}`);

  // a Done ticket whose evidence carries no PASS verdict: the framework's
  // whole premise is that "done" is a machine observation, not a claim
  const doneWithoutVerdict = [];
  for (const n of nodes) {
    if (n.status_category !== "done") continue;
    const v = n.evidence?.verdict ?? null;
    if (v === "PASS") continue;
    doneWithoutVerdict.push({
      key: n.key, status: n.status, file: n.file,
      verdict: v,
      reason: !n.evidence ? `no ${evd.dir}/${n.key}/ directory`
        : n.evidence.report === null ? `no ${evd.dir}/${n.key}/REPORT.md`
          : v === null ? `${n.evidence.report}: no verdict word in the H1 line`
            : `${n.evidence.report}: H1 verdict is ${v}, not PASS`,
    });
  }
  doneWithoutVerdict.sort((a, b) => byKey(a.key, b.key));

  const outsideBacklog = nodes.filter((n) => !n.in_backlog).map((n) => n.key);
  const stats = {
    tickets: nodes.length,
    edges: edges.length,
    ready: nodes.filter((n) => n.ready === true).length,
    blocked: nodes.filter((n) => n.blocked_on.length > 0).length,
    done: nodes.filter((n) => n.status_category === "done").length,
  };
  return {
    generated_at_commit: headCommit(root),
    root,
    tracker: { provider: tk.provider, backlog_available: tk.available, note: tk.note },
    sources: {
      backlog: tk.source, plan: plan.source, ledger: ledger.source, evidence: evd.source,
      config: CONFIG_NAME,
    },
    notes: {
      backlog: tk.note, plan: plan.note, ledger: ledger.note, evidence: evd.note,
    },
    stats,
    nodes,
    edges,
    findings: {
      dangling,
      cycles: cycles.map((path0) => ({ path: path0, display: [...path0, path0[0]].join(" → ") })),
      cycles_truncated: !!cycles.truncated,
      done_without_verdict: doneWithoutVerdict,
      keys_outside_backlog: outsideBacklog,
    },
    warnings,
  };
}

// ---- rendering: --json -----------------------------------------------------
/** The machine contract. Stable ordering everywhere and NO timestamp — the
 * dump is pinned to generated_at_commit instead, so two runs on one commit are
 * byte-identical and diffable. */
export function toJson(m) {
  return {
    generated_at_commit: m.generated_at_commit,
    tracker: m.tracker,
    sources: m.sources,
    stats: m.stats,
    nodes: m.nodes,
    edges: m.edges,
    findings: m.findings,
    warnings: m.warnings,
  };
}

// ---- rendering: --dot ------------------------------------------------------
const DOT_FILL = {
  done: "#d6efdc", in_review: "#e6dcf7", in_progress: "#d8e6f8", todo: "#ffffff",
};
function dotEsc(s) {
  return String(s ?? "").replace(/\\/g, "\\\\").replace(/"/g, '\\"').replace(/\n/g, "\\n");
}
/** A Graphviz digraph. Every identifier and label is quoted + escaped, so no
 * ticket summary can break out of the string and corrupt the syntax. */
export function toDot(m) {
  const L = [];
  L.push("digraph vteam_graph {");
  L.push("  rankdir=LR;");
  L.push('  labelloc="t";');
  L.push(`  label="vteam graph — ${dotEsc(m.stats.tickets)} tickets · ${dotEsc(m.stats.edges)} edges · ${dotEsc(m.stats.ready)} ready (commit ${dotEsc(m.generated_at_commit ? m.generated_at_commit.slice(0, 7) : "unpinned")})";`);
  L.push('  fontname="Helvetica";');
  L.push('  node [shape=box, style="rounded,filled", fontname="Helvetica", fontsize=10, color="#555555", fillcolor="#ffffff"];');
  L.push('  edge [color="#555555", arrowsize=0.7];');
  const known = new Set(m.nodes.map((n) => n.key));
  for (const n of m.nodes) {
    const bits = [n.key];
    if (n.summary) bits.push(n.summary.length > 34 ? `${n.summary.slice(0, 33)}…` : n.summary);
    bits.push([n.status ?? "no ticket file", n.sprint, n.evidence?.verdict].filter(Boolean).join(" · "));
    const attrs = [`label="${dotEsc(bits.join("\n"))}"`,
      `fillcolor="${DOT_FILL[n.status_category] ?? "#eeeeee"}"`];
    if (n.ready === true) attrs.push("penwidth=2");             // ready = start now
    if (!n.in_backlog) attrs.push('style="rounded,filled,dashed"');
    L.push(`  "${dotEsc(n.key)}" [${attrs.join(", ")}];`);
  }
  // dangling targets get a node of their own so the broken edge is visible
  for (const d of m.findings.dangling) {
    if (known.has(d.to)) continue;
    L.push(`  "${dotEsc(d.to)}" [label="${dotEsc(`${d.to}\nno such ticket`)}", fillcolor="#fbdcdc", style="rounded,filled,dashed", color="#b3261e"];`);
    known.add(d.to);
  }
  for (const e of m.edges) {
    const attrs = [];
    if (e.in_cycle) attrs.push('color="#b3261e"', "penwidth=2", 'label="cycle"', 'fontcolor="#b3261e"', "fontsize=9");
    else if (e.dangling) attrs.push('color="#b3261e"', 'style="dashed"');
    L.push(`  "${dotEsc(e.from)}" -> "${dotEsc(e.to)}"${attrs.length ? ` [${attrs.join(", ")}]` : ""};`);
  }
  L.push("}");
  return `${L.join("\n")}\n`;
}

// ---- rendering: the human report -------------------------------------------
function table(headers, rows) {
  const w = headers.map((h, i) => Math.max(h.length, ...rows.map((r) => String(r[i] ?? "").length)));
  const line = (cells) => cells.map((c, i) => String(c ?? "").padEnd(i === cells.length - 1 ? 0 : w[i])).join("  ").trimEnd();
  return [line(headers), ...rows.map(line)];
}

export function renderHuman(m) {
  const out = [];
  const s = m.stats;
  out.push(`vteam graph — the implicit work graph, made visible · ${m.root}`);
  out.push("");
  out.push(`  ${s.tickets} ticket${s.tickets === 1 ? "" : "s"} · ${s.edges} edge${s.edges === 1 ? "" : "s"} · ${s.ready} ready · ${s.blocked} blocked · ${s.done} done` +
    `    (commit ${m.generated_at_commit ? m.generated_at_commit.slice(0, 7) : "unpinned — not a git repo"})`);
  out.push("");
  if (!m.tracker.backlog_available) {
    out.push(`  ⚠️  ${m.tracker.note}`);
    out.push("");
  }

  // ---- READY ----
  const ready = m.nodes.filter((n) => n.ready === true);
  out.push(`── READY — what a machine says can start now (${ready.length}) ──`);
  out.push(`   read from: ${m.sources.backlog} + ${m.sources.plan} + ${m.sources.ledger} + ${m.sources.evidence}`);
  if (!ready.length) {
    out.push(`   ${m.stats.tickets === 0 ? "no tickets to graph yet" : "nothing is startable: every open ticket is waiting on another (see BLOCKED and FINDINGS)"}`);
  } else {
    const rows = ready.map((n) => [
      n.key,
      n.sprint ?? DASH,
      n.cost === null ? DASH : `${n.cost}d`,
      n.dispatches ? `${n.dispatches}× ${[n.last_lane, n.last_actor].filter(Boolean).join("/") || "?"}` : DASH,
      n.evidence?.verdict ?? DASH,
      n.blocked_by.length ? `${n.blocked_by.join(", ")} ✅` : "none",
    ]);
    for (const l of table(["KEY", "SPRINT", "COST", "DISPATCHED", "EVD", "BLOCKERS CLEARED"], rows)) out.push(`   ${l}`);
  }
  out.push("");

  // ---- BLOCKED ----
  const blocked = m.nodes.filter((n) => n.blocked_on.length > 0);
  out.push(`── BLOCKED — waiting on another ticket (${blocked.length}) ──`);
  out.push(`   read from: ${m.sources.backlog} (\`- blocked-by:\` lines)`);
  if (!blocked.length) out.push("   nothing is blocked");
  else {
    const rows = blocked.map((n) => [
      n.key,
      "←",
      n.blocked_on.map((b) => {
        const t = m.nodes.find((x) => x.key === b);
        return `${b} (${t && t.in_backlog ? t.status : "no such ticket"})`;
      }).join(" · "),
    ]);
    for (const l of table(["KEY", "", "WAITING ON"], rows)) out.push(`   ${l}`);
  }
  out.push("");

  // ---- FINDINGS ----
  const f = m.findings;
  const nFind = f.dangling.length + f.cycles.length + f.done_without_verdict.length;
  out.push(`── FINDINGS (${nFind}) ──`);
  if (!nFind) out.push("   ✅ no dangling blockers, no cycles, every Done ticket carries a PASS verdict");
  for (const d of f.dangling) out.push(`   ❌ dangling blocker: ${d.from} → ${d.to} · ${d.detail} (${d.file})`);
  for (const c of f.cycles) out.push(`   ❌ cycle: ${c.display} — these tickets block each other; nothing in the loop can ever be ready`);
  if (f.cycles_truncated) out.push(`   ⚠️  cycle search stopped at its bound — there may be more cycles than the ${f.cycles.length} listed above`);
  for (const d of f.done_without_verdict) out.push(`   ⚠️  done without a PASS verdict: ${d.key} (status ${d.status}) — ${d.reason}`);
  if (f.keys_outside_backlog.length) {
    out.push(`   ℹ️  ${f.keys_outside_backlog.length} key${f.keys_outside_backlog.length === 1 ? "" : "s"} named by the plan/ledger/evidence with no ticket file: ${f.keys_outside_backlog.join(", ")}`);
  }
  out.push("");

  // ---- sources / warnings ----
  const notes = Object.entries(m.notes).filter(([, v]) => v);
  if (notes.length) {
    out.push("── SOURCES ──");
    for (const [k, v] of notes) out.push(`   ${k}: ${v}`);
    out.push("");
  }
  if (m.warnings.length) {
    out.push(`── WARNINGS — files this report could not read as expected (${m.warnings.length}) ──`);
    for (const w of m.warnings) out.push(`   ${w}`);
    out.push("");
  }
  out.push("graph REPORTS, it never fails the build (always exit 0) — it is a mirror of the files above.");
  out.push("The gates that DO fail are dor_check.py (blocked-by not Done), schedule_check.py (plan) and evd_check.py (verdicts).");
  out.push("  --json  machine shape, pinned to the commit   --dot  Graphviz digraph (pipe to `dot -Tsvg`)");
  return out.join("\n");
}

// ---- command ---------------------------------------------------------------
export async function graph(flags = {}) {
  const root = repoRoot();
  const m = buildGraph(root);
  if (flags.json) console.log(JSON.stringify(toJson(m), null, 2));
  else if (flags.dot) process.stdout.write(toDot(m));
  else console.log(renderHuman(m));
  // never a non-zero exit: findings are reported, not enforced (see the header)
}

// ---- selftest --------------------------------------------------------------
function put(root, relPath, text) {
  const abs = path.join(root, ...relPath.split("/"));
  fs.mkdirSync(path.dirname(abs), { recursive: true });
  fs.writeFileSync(abs, text);
}
function git(root, ...args) {
  spawnSync("git", ["-C", root, ...args], { encoding: "utf8", stdio: ["ignore", "pipe", "pipe"] });
}
function initRepo(dir) {
  fs.mkdirSync(dir, { recursive: true });
  spawnSync("git", ["init", "-q", "-b", "main", dir], { stdio: "ignore" });
  git(dir, "config", "user.email", "selftest@vteam");
  git(dir, "config", "user.name", "selftest");
  put(dir, "README.md", "# graph fixture\n");
  git(dir, "add", "-A");
  git(dir, "commit", "-qm", "fixture");
  return dir;
}
const SELF = fileURLToPath(import.meta.url);
function runCli(cwd, ...args) {
  return spawnSync(process.execPath, [SELF, ...args], { cwd, encoding: "utf8", timeout: 60_000 });
}

/** The fixture the spec asks for:
 *   GRA-1  Done, evd PASS + COMMIT                  → not ready (done)
 *   GRA-2  To Do, blocked-by GRA-1 (Done)            → THE ready one
 *   GRA-3  To Do, blocked-by GRA-2 + GHOST-9         → blocked + dangling finding
 *   GRA-4  To Do, blocked-by GRA-5  ┐
 *   GRA-5  To Do, blocked-by GRA-4  ┘                → cycle finding
 *   GRA-6  Done, no evd                              → done_without_verdict */
function fixture(dir) {
  put(dir, "vteam.config.yaml",
    "version: 1\nproject:\n  name: Graph Fixture\n  key: GRA\n" +
    "paths:\n  backlog: docs/backlog\n  pm: docs/pm\n  evidence: evd\n" +
    "team:\n  hours_per_day: 8\n" +
    "tracker:\n  provider: markdown\n  done_statuses: [Done, Closed]\n  review_status: In Review\n");
  put(dir, "docs/backlog/GRA-1.md", "# GRA-1: schema\n- status: Done\n- labels: db\n");
  put(dir, "docs/backlog/GRA-2.md", "# GRA-2: api on the schema\n- status: To Do\n- blocked-by: GRA-1\n- estimate: 1d\n");
  put(dir, "docs/backlog/GRA-3.md", "# GRA-3: ui on the api\n- status: To Do\n- blocked-by: GRA-2, GHOST-9\n");
  put(dir, "docs/backlog/GRA-4.md", "# GRA-4: left half\n- status: To Do\n- blocked-by: GRA-5\n");
  put(dir, "docs/backlog/GRA-5.md", "# GRA-5: right half\n- status: In Progress\n- blocked-by: GRA-4\n");
  put(dir, "docs/backlog/GRA-6.md", "# GRA-6: shipped without proof\n- status: Done\n");
  put(dir, "docs/pm/plan.yaml",
    "sprint-1:\n  start: 2026-01-05\n  end: 2026-01-16\n  items:\n    - \"GRA-1 1.5\"\n    - \"GRA-2 4h\"\n");
  put(dir, "docs/pm/log.md",
    "# Dispatch ledger\n\n| Date | Lane | Actor | Item | Result | Link |\n|---|---|---|---|---|---|\n" +
    "| 2026-01-05 | DEV | An | GRA-1 | done (workhorse) · tok ≈ 90k | PR #1 |\n" +
    "| 2026-01-06 | QA | Binh | GRA-1 | done · tok ≈ 12k | evd/GRA-1 |\n" +
    "| 2026-01-07 | DEV | Chi | GRA-5 | blocked: waits on GRA-4 | — |\n");
  put(dir, "evd/GRA-1/REPORT.md", "# Verification report GRA-1 — PASS\nCOMMIT: abc1234\n\n## checked\nthings\n");
}

function selftest() {
  const assert = (cond, msg) => {
    if (!cond) { console.error(`graph selftest FAILED: ${msg}`); process.exit(1); }
  };
  const tmp = fs.mkdtempSync(path.join(os.tmpdir(), "vteam-graph-selftest-"));
  try {
    const repo = initRepo(path.join(tmp, "repo"));
    fixture(repo);
    const m = buildGraph(repo);
    const node = (k) => m.nodes.find((n) => n.key === k);

    // ---- green: the graph the files describe --------------------------------
    assert(m.stats.tickets === 6, `expected 6 nodes, got ${m.stats.tickets}: ${m.nodes.map((n) => n.key).join(",")}`);
    assert(m.stats.edges === 5, `expected 5 edges, got ${m.stats.edges}`);
    assert(m.stats.done === 2, `expected 2 done, got ${m.stats.done}`);
    assert(m.generated_at_commit && /^[0-9a-f]{40}$/.test(m.generated_at_commit),
      `report must pin the commit, got ${m.generated_at_commit}`);

    // the headline claim: ready is exactly {GRA-2}
    const readySet = m.nodes.filter((n) => n.ready === true).map((n) => n.key).sort();
    assert(JSON.stringify(readySet) === '["GRA-2"]', `ready set must be exactly [GRA-2], got ${JSON.stringify(readySet)}`);
    assert(node("GRA-1").ready === false, "a Done ticket is never 'ready'");
    assert(JSON.stringify(node("GRA-3").blocked_on) === '["GHOST-9","GRA-2"]',
      `GRA-3 blocked_on: ${JSON.stringify(node("GRA-3").blocked_on)}`);

    // plan + ledger + evidence annotations landed on the right nodes
    assert(node("GRA-1").sprint === "sprint-1" && node("GRA-1").cost === 1.5, `plan on GRA-1: ${JSON.stringify(node("GRA-1"))}`);
    assert(node("GRA-2").cost === 0.5, `"4h" must be 0.5d at hours_per_day 8, got ${node("GRA-2").cost}`);
    assert(node("GRA-1").dispatches === 2 && node("GRA-1").last_actor === "Binh" && node("GRA-1").last_lane === "QA",
      `ledger rollup on GRA-1: ${JSON.stringify(node("GRA-1"))}`);
    assert(node("GRA-5").dispatches === 1 && node("GRA-5").last_actor === "Chi", "ledger actor column must be read");
    assert(node("GRA-1").evidence.verdict === "PASS" && node("GRA-1").evidence.commit === "abc1234",
      `evidence on GRA-1: ${JSON.stringify(node("GRA-1").evidence)}`);
    assert(node("GRA-6").evidence === null, "GRA-6 has no evd dir");

    // ---- findings ----------------------------------------------------------
    assert(m.findings.dangling.length === 1 && m.findings.dangling[0].from === "GRA-3" &&
      m.findings.dangling[0].to === "GHOST-9",
      `dangling must be exactly GRA-3 → GHOST-9: ${JSON.stringify(m.findings.dangling)}`);
    assert(m.findings.cycles.length === 1 &&
      JSON.stringify(m.findings.cycles[0].path) === '["GRA-4","GRA-5"]' &&
      m.findings.cycles[0].display === "GRA-4 → GRA-5 → GRA-4",
      `cycle must be exactly [GRA-4,GRA-5]: ${JSON.stringify(m.findings.cycles)}`);
    const dwv = m.findings.done_without_verdict;
    assert(dwv.length === 1 && dwv[0].key === "GRA-6" && /no evd\/GRA-6\/ directory/.test(dwv[0].reason),
      `done_without_verdict must be exactly GRA-6: ${JSON.stringify(dwv)}`);
    assert(m.warnings.length === 0, `clean fixture must warn about nothing: ${JSON.stringify(m.warnings)}`);

    // ---- conformance: the MIRROR and the GATE must agree -------------------
    // core/scripts/graph_check.py is the gate that FAILS the build on these
    // same three findings (dangling / cycle / done-without-verdict). Same repo,
    // same verdicts — or one of the two is lying about the project. Skipped
    // LOUDLY (named in the OK line) when the gate or python3 is not present.
    let gateVerdict;
    const gatePy = fileURLToPath(new URL("../../core/scripts/graph_check.py", import.meta.url));
    if (!fs.existsSync(gatePy)) gateVerdict = "graph_check.py absent — parity UNCHECKED";
    else {
      const g = spawnSync("python3", [gatePy], { cwd: repo, encoding: "utf8" });
      if (g.error) gateVerdict = "python3 unavailable — parity UNCHECKED";
      else {
        const gout = `${g.stdout || ""}${g.stderr || ""}`;
        assert(g.status === 1, `the gate must RED where the mirror reports findings, got exit ${g.status}: ${gout}`);
        assert(/GRA-3: blocked-by GHOST-9/.test(gout), `gate must name the same dangling edge: ${gout}`);
        assert(/GRA-4 → GRA-5 → GRA-4/.test(gout), `gate must name the same cycle: ${gout}`);
        assert(/GRA-6/.test(gout), `gate must name the same unproven Done ticket: ${gout}`);
        assert(!/GRA-1\b/.test(gout), `the gate must NOT flag GRA-1, which the mirror reports as PASS-proven: ${gout}`);
        assert(!/GRA-2\b/.test(gout), `the gate must NOT flag GRA-2, the ticket the mirror calls ready: ${gout}`);
        gateVerdict = "graph_check.py reds on the same 3 findings, clean on the same 2 tickets";
      }
    }

    // ---- --json: parses, stable, exit 0 ------------------------------------
    const j1 = runCli(repo, "--json");
    assert(j1.status === 0, `--json must exit 0, got ${j1.status}: ${j1.stderr}`);
    const parsed = JSON.parse(j1.stdout);
    assert(Array.isArray(parsed.nodes) && Array.isArray(parsed.edges) &&
      parsed.findings && Array.isArray(parsed.findings.dangling) &&
      Array.isArray(parsed.findings.cycles) && Array.isArray(parsed.findings.done_without_verdict),
      "--json contract: {generated_at_commit, nodes, edges, findings{dangling,cycles,done_without_verdict}}");
    assert(parsed.generated_at_commit === m.generated_at_commit, "--json must carry the commit");
    const j2 = runCli(repo, "--json");
    assert(j1.stdout === j2.stdout, "--json must be byte-stable across runs (sorted, no timestamp)");
    assert(JSON.stringify(parsed.nodes.map((n) => n.key)) ===
      JSON.stringify([...parsed.nodes.map((n) => n.key)].sort(byKey)), "nodes must be key-sorted");

    // ---- --dot: syntactically valid by construction -------------------------
    const d1 = runCli(repo, "--dot");
    assert(d1.status === 0, `--dot must exit 0, got ${d1.status}: ${d1.stderr}`);
    const dot = d1.stdout;
    assert(/^digraph vteam_graph \{/m.test(dot) && dot.trimEnd().endsWith("}"), "dot must open a digraph and close it");
    assert((dot.match(/\{/g) || []).length === (dot.match(/\}/g) || []).length, "dot braces must balance");
    for (const line of dot.split("\n")) {
      if (!line.trim() || /^(digraph|\})/.test(line.trim())) continue;
      assert(/[;{]$/.test(line.trim()), `dot statement must end in ';' — got ${JSON.stringify(line)}`);
      assert(((line.match(/(?<!\\)"/g) || []).length % 2) === 0, `unbalanced quotes in dot line ${JSON.stringify(line)}`);
    }
    assert(/"GRA-1" -> "GRA-2";/.test(dot), "dot must carry the blocks edge GRA-1 -> GRA-2");
    assert(/"GRA-4" -> "GRA-5" \[color="#b3261e"[^\]]*label="cycle"/.test(dot) &&
      /"GRA-5" -> "GRA-4" \[color="#b3261e"[^\]]*label="cycle"/.test(dot),
      "dot must mark BOTH cycle edges red + labelled");
    assert(/"GRA-2" \[label="GRA-2[^\]]*penwidth=2\]/.test(dot), "the ready node must carry penwidth=2");
    assert(/"GHOST-9" \[label="GHOST-9\\nno such ticket"/.test(dot), "the dangling target must appear as a node");
    assert(/"GRA-1" \[label="[^"]*", fillcolor="#d6efdc"/.test(dot), "status must drive the node color");
    // opportunistic: if graphviz is installed, let dot itself judge the syntax
    const which = spawnSync("dot", ["-V"], { encoding: "utf8" });
    let dotVerdict = "graphviz not installed — syntax proven by construction + the assertions above";
    if (!which.error) {
      const r = spawnSync("dot", ["-Tsvg"], { input: dot, encoding: "utf8" });
      assert(r.status === 0, `dot -Tsvg rejected the digraph: ${r.stderr}`);
      assert(/<svg/.test(r.stdout), "dot -Tsvg produced no svg");
      dotVerdict = "dot -Tsvg rendered it";
    }

    // ---- default human report ----------------------------------------------
    const h = runCli(repo);
    assert(h.status === 0, `human report must exit 0, got ${h.status}: ${h.stderr}`);
    assert(/── READY/.test(h.stdout) && /── BLOCKED/.test(h.stdout) && /── FINDINGS/.test(h.stdout),
      "human report must carry the READY / BLOCKED / FINDINGS panels");
    assert(/docs\/backlog\/<KEY>\.md/.test(h.stdout) && /docs\/pm\/plan\.yaml/.test(h.stdout) &&
      /docs\/pm\/log\.md/.test(h.stdout) && /evd\/<KEY>\/REPORT\.md/.test(h.stdout),
      "every panel must name the file it was read from");
    assert(/GHOST-9/.test(h.stdout) && /GRA-4 → GRA-5 → GRA-4/.test(h.stdout) && /GRA-6/.test(h.stdout),
      "the three findings must be printed loudly");

    // ---- mutations: the reds a mirror must still survive --------------------
    let reds = 0;
    // 1. malformed ticket + stray file → warnings, NOT a crash, graph intact
    put(repo, "docs/backlog/GRA-7.md", "this file has no title line and no status line\n");
    put(repo, "docs/backlog/notes.md", "a stray non-ticket file\n");
    const m2 = buildGraph(repo);
    assert(m2.warnings.some((w) => w.includes("GRA-7.md")), `malformed ticket must warn: ${JSON.stringify(m2.warnings)}`);
    assert(m2.warnings.some((w) => w.includes("notes.md")), "non-ticket filename must warn");
    assert(m2.stats.tickets === 6, `the 6 good tickets must still graph, got ${m2.stats.tickets}`);
    assert(runCli(repo).status === 0, "a malformed ticket must not change the exit code");
    reds += 2;
    fs.rmSync(path.join(repo, "docs/backlog/GRA-7.md"));
    fs.rmSync(path.join(repo, "docs/backlog/notes.md"));

    // 2. a bad plan item / bad cost → warning, plan annotations degrade
    put(repo, "docs/pm/plan.yaml",
      "sprint-1:\n  start: 2026-01-05\n  end: 2026-01-16\n  items:\n    - \"GRA-1\"\n    - \"GRA-2 later\"\n");
    const m3 = buildGraph(repo);
    assert(m3.warnings.some((w) => /is not "KEY <days\|hours>"/.test(w)), `bad plan item must warn: ${JSON.stringify(m3.warnings)}`);
    assert(m3.warnings.some((w) => /is not <n>, <n>d or <n>h/.test(w)), "bad cost must warn");
    assert(m3.nodes.find((n) => n.key === "GRA-2").ready === true, "a broken plan must not change readiness");
    reds += 2;

    // 3. a ticket that blocks ITSELF is a 1-cycle, not a hang and not silence
    put(repo, "docs/backlog/GRA-8.md", "# GRA-8: eats its own tail\n- status: To Do\n- blocked-by: GRA-8\n");
    const mSelf = buildGraph(repo);
    assert(mSelf.findings.cycles.some((c) => JSON.stringify(c.path) === '["GRA-8"]' &&
      c.display === "GRA-8 → GRA-8"), `self-block must report as a 1-cycle: ${JSON.stringify(mSelf.findings.cycles)}`);
    assert(mSelf.nodes.find((n) => n.key === "GRA-8").ready === false, "a self-blocked ticket is never ready");
    fs.rmSync(path.join(repo, "docs/backlog/GRA-8.md"));
    reds++;

    // 4. boundedness: a DENSE ACYCLIC graph must be proven cycle-free fast.
    // Naive all-simple-paths enumeration is exponential here (60 nodes, 1770
    // edges) — the SCC filter is what makes `vteam graph` safe on a real repo.
    const dense = new Map();
    const denseKeys = [];
    for (let i = 1; i <= 60; i++) denseKeys.push(`BIG-${i}`);
    for (let i = 0; i < denseKeys.length; i++) {
      dense.set(denseKeys[i], denseKeys.slice(i + 1));   // complete DAG i -> j, i<j
    }
    const t0 = Date.now();
    const noCycles = findCycles(dense, denseKeys);
    const ms = Date.now() - t0;
    assert(noCycles.length === 0 && !noCycles.truncated,
      `a complete DAG has no cycles: ${JSON.stringify(noCycles.slice(0, 3))}`);
    assert(ms < 2000, `cycle search on a 60-node dense DAG took ${ms}ms — the SCC bound is broken`);
    reds++;

    // 5. non-markdown tracker: ONE honest line, zero invented edges
    put(repo, "vteam.config.yaml",
      fs.readFileSync(path.join(repo, "vteam.config.yaml"), "utf8").replace("provider: markdown", "provider: jira"));
    const m4 = buildGraph(repo);
    assert(m4.stats.edges === 0 && m4.nodes.every((n) => n.blocked_by.length === 0),
      "a non-markdown tracker must yield NO backlog edges — never faked");
    assert(m4.nodes.every((n) => n.ready === null), "readiness is unknowable without the tracker → null, not a guess");
    assert(/^tracker=jira: blocked_by edges live in the tracker/.test(m4.tracker.note),
      `jira note: ${JSON.stringify(m4.tracker.note)}`);
    assert(m4.nodes.some((n) => n.key === "GRA-1" && n.evidence?.verdict === "PASS"),
      "plan/ledger/evd must still build nodes under a remote tracker");
    const hj = runCli(repo);
    assert(hj.status === 0 && /tracker=jira: blocked_by edges live in the tracker/.test(hj.stdout),
      "the human report must print the tracker note once");
    reds++;

    // 6. unparseable config → warning, not a crash
    put(repo, "vteam.config.yaml", "project: &anchor bad\n");
    const m5 = buildGraph(repo);
    assert(m5.warnings.some((w) => w.includes(CONFIG_NAME)), `bad config must warn: ${JSON.stringify(m5.warnings)}`);
    assert(runCli(repo).status === 0, "a bad config must still exit 0");
    reds++;

    // 7. empty repo: an honest empty report, exit 0, no invented nodes
    const empty = initRepo(path.join(tmp, "empty"));
    const me = buildGraph(empty);
    assert(me.stats.tickets === 0 && me.stats.edges === 0 && me.findings.dangling.length === 0,
      `empty repo must graph nothing: ${JSON.stringify(me.stats)}`);
    const he = runCli(empty);
    assert(he.status === 0, `empty repo must exit 0, got ${he.status}: ${he.stderr}`);
    assert(/0 tickets · 0 edges/.test(he.stdout) && /no backlog directory/.test(he.stdout),
      `empty report must say so honestly:\n${he.stdout}`);
    assert(JSON.parse(runCli(empty, "--json").stdout).nodes.length === 0, "empty --json must be an empty node list");
    assert(/digraph vteam_graph \{/.test(runCli(empty, "--dot").stdout), "empty --dot must still be a valid digraph");
    reds++;

    console.log(`graph selftest: OK (gate parity: ${gateVerdict}; 6 nodes/5 edges; ready set exactly {GRA-2}; dangling GRA-3→GHOST-9; cycle GRA-4→GRA-5→GRA-4; done_without_verdict GRA-6; plan 4h→0.5d; ledger actors An/Binh/Chi; --json byte-stable + sorted; --dot ${dotVerdict}; ${reds} mutations red — malformed ticket + stray file warned, bad plan item/cost warned, self-block = 1-cycle, 60-node dense DAG proven cycle-free in ${ms}ms, jira provider honest with 0 faked edges, bad config degraded, empty repo empty; exit 0 in every mode)`);
  } finally {
    fs.rmSync(tmp, { recursive: true, force: true });
  }
}

// ---- entrypoint ------------------------------------------------------------
const isMain = process.argv[1] &&
  import.meta.url === pathToFileURL(path.resolve(process.argv[1])).href;
if (isMain) {
  try {
    const argv = process.argv.slice(2);
    if (argv.includes("--selftest") || argv.includes("selftest")) selftest();
    else await graph({ json: argv.includes("--json"), dot: argv.includes("--dot") });
  } catch (e) {
    console.error(`graph: ${e.message}`);
    process.exit(1);
  }
}
