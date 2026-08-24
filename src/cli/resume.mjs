// resume.mjs — where did this ticket stop, and what is the next move?
//
// DERIVED, never stored. ops.md §1 / ops-247.md §1 are law here: all state
// lives in the artifacts that already have one owner each — the tracker file,
// the git branches, the evidence tree, the dispatch ledger. A stored
// "checkpoint" file would be a second source of truth nothing keeps honest
// (it can claim "review done" while dev/review.md does not exist). So this
// command READS the books a resuming session would open anyway and prints the
// furthest PROVEN stage plus the next dispatch — one command instead of five
// lookups. Delete nothing, write nothing; run it twice, get the same answer.
//
// The proof chain, in ticket order (each stage names the artifact that proves it):
//   claimed      — a `claimed <ts> · branch …` comment in the ticket (raci.md §2)
//   branch       — feat|fix/<KEY>-* exists (local or remote-tracking)
//   tasksheet    — {paths.evidence}/<KEY>/dev/tasksheet.md   (/dev T1 done)
//   review       — {paths.evidence}/<KEY>/dev/review.md      (/dev T4b done)
//   qa verdict   — {paths.evidence}/<KEY>/REPORT.md H1       (/qa done)
// plus the ledger rows naming the ticket (what each lane reported).
//
// Usage: vteam resume <TICKET> [--json]
// Always exits 0 when the ticket key is given (a mirror, like graph) — even
// "no trace at all" is a valid, useful answer. Exit 1 only on missing args.
import fs from "node:fs";
import path from "node:path";
import { spawnSync } from "node:child_process";
import { repoRoot } from "./util.mjs";
import { loadConfig, cfgGet } from "./config.mjs";
import { parseLedger, parseReport } from "./board.mjs";

const KEY_RE = /^[A-Za-z][A-Za-z0-9]*-\d+$/; // one grammar with tracker.py
const CLAIM_TTL_H = 2; // raci.md §2 — the one home of this number is prose; mirror it
const CLAIM_PAT = /claimed\s+(\d{4}-\d{2}-\d{2}[T ][\d:.+Z-]+)\s*·\s*(?:branch\s+)?(\S+)/gi;

const readText = (p) => { try { return fs.readFileSync(p, "utf8"); } catch { return null; } };

/** Every signal is a fact with the artifact that proves it — no guesses. */
export function collectSignals(root, cfg, key) {
  const evdRel = String(cfgGet(cfg, "paths.evidence", "evd"));
  const pmRel = String(cfgGet(cfg, "paths.pm", "docs/pm"));
  const blRel = String(cfgGet(cfg, "paths.backlog", "docs/backlog"));
  const provider = String(cfgGet(cfg, "tracker.provider", "markdown"));
  const evd = path.join(root, evdRel, key);

  // 1. the claim — readable locally only on the markdown tracker
  let claim = { checkable: provider === "markdown", found: false };
  if (claim.checkable) {
    const t = readText(path.join(root, blRel, `${key}.md`));
    claim.ticket_file = t !== null;
    if (t) {
      let last = null;
      for (const m of t.matchAll(CLAIM_PAT)) last = { at: m[1].trim(), branch: m[2] };
      if (last) {
        const age_h = (Date.now() - new Date(last.at).getTime()) / 3.6e6;
        claim = { ...claim, found: true, ...last,
          expired: Number.isFinite(age_h) ? age_h > CLAIM_TTL_H : null };
      }
    }
  }

  // 2. branches — local + remote-tracking refs already fetched
  const br = spawnSync("git", ["branch", "-a", "--list", `*${key}*`],
    { cwd: root, encoding: "utf8" });
  const branches = (br.stdout || "").split("\n")
    .map((l) => l.replace(/^[\s*+]+/, "").trim()).filter(Boolean).sort();

  // 3-5. the evidence tree
  const reportText = readText(path.join(evd, "REPORT.md"));
  return {
    key,
    claim,
    branches,
    tasksheet: fs.existsSync(path.join(evd, "dev", "tasksheet.md")),
    review_dossier: fs.existsSync(path.join(evd, "dev", "review.md")),
    report: reportText === null ? null : parseReport(reportText),
    ledger_rows: ledgerRowsFor(root, pmRel, key),
    sources: { evidence: `${evdRel}/${key}/`, ledger: `${pmRel}/log.md`,
      ticket: claim.checkable ? `${blRel}/${key}.md` : `tracker: ${provider}` },
  };
}

function ledgerRowsFor(root, pmRel, key) {
  const text = readText(path.join(root, pmRel, "log.md"));
  if (text === null) return [];
  const up = key.toUpperCase();
  return parseLedger(text)
    .filter((r) => !r.malformed && String(r.item).toUpperCase().includes(up))
    .map((r) => ({ date: r.date, lane: r.lane, actor: r.actor,
      result_kind: r.result_kind, result: r.result }));
}

/** Furthest PROVEN stage → the one next action. Later artifacts outrank
 * earlier ones; a verdict outranks everything (it is the only closure). */
export function derive(s) {
  const v = s.report?.verdict || null;
  if (v === "PASS")
    return { stage: "qa-verdict PASS", next:
      `nothing to resume — QA passed. If the ticket is not Done yet, /qa V7.3b closes it.` };
  if (v === "FAIL" || v === "NEW-BUG")
    return { stage: `qa-verdict ${v}`, next:
      `re-dispatch /dev ${s.key} — read ${s.sources.evidence}REPORT.md FIRST (QA said why it failed).` };
  if (v)
    return { stage: `qa-verdict ${v}`, next:
      `QA stopped at ${v} — read REPORT.md section 5 and clear the blocker before any re-dispatch.` };
  if (s.review_dossier)
    return { stage: "review dossier committed (/dev T4b done)", next:
      `dispatch /qa ${s.key} — the dev side is complete through review${s.branches.length ? `; branch ${s.branches[0]} carries the code` : ""}.` };
  if (s.tasksheet)
    return { stage: "tasksheet written (/dev T1 done), no review dossier", next:
      `re-dispatch /dev ${s.key} — it resumes ${s.branches.length ? `branch ${s.branches[0]} and ` : ""}the committed tasksheet instead of restarting (dev.md T0.4).` };
  if (s.branches.length)
    return { stage: "branch exists, no tasksheet yet", next:
      `re-dispatch /dev ${s.key} on ${s.branches[0]} — it died before T1; T1 re-runs on the leftover branch.` };
  if (s.claim.found)
    return { stage: s.claim.expired === false ? "claimed, within TTL" : "claim past TTL, no trace of work",
      next: s.claim.expired === false
        ? `STOP — someone claimed this ${CLAIM_TTL_H}h TTL ago or less (${s.claim.at}). Pick other work (dev.md T0.4).`
        : `orphaned — return it to To Do or take it over, and write the \`failed: previous session died mid-work\` ledger row (pm.md P0.1c).` };
  return { stage: "no trace", next:
    `${s.key} never started — nothing to resume; dispatch it normally (/pm picks it when unblocked).` };
}

function renderHuman(s, d) {
  const yn = (b) => (b ? "✅" : "—");
  const L = [
    `${s.key} — derived from committed artifacts (nothing stored, nothing to go stale)`,
    "",
    `  claim        ${s.claim.checkable
      ? (s.claim.found ? `✅ ${s.claim.at} · ${s.claim.branch}${s.claim.expired ? "  (PAST TTL)" : "  (within TTL)"}` : "— none in the ticket file")
      : `CANNOT CHECK here (${s.sources.ticket}) — read the claim comment on the ticket`}`,
    `  branch       ${s.branches.length ? "✅ " + s.branches.join(", ") : "— none matching *" + s.key + "*"}`,
    `  tasksheet    ${yn(s.tasksheet)}  ${s.sources.evidence}dev/tasksheet.md`,
    `  review       ${yn(s.review_dossier)}  ${s.sources.evidence}dev/review.md`,
    `  qa verdict   ${s.report ? "✅ " + (s.report.verdict || "REPORT.md has NO verdict in its H1") : "—  no REPORT.md"}`,
  ];
  if (s.ledger_rows.length) {
    L.push(`  ledger       ${s.ledger_rows.length} row(s), last: ` +
      s.ledger_rows.slice(-2).map((r) => `${r.date} ${r.lane} ${r.result_kind}`).join(" · "));
  } else {
    L.push(`  ledger       —  no rows name ${s.key} in ${s.sources.ledger}`);
  }
  L.push("", `  STAGE  ${d.stage}`, `  NEXT   ${d.next}`);
  return L.join("\n");
}

export async function resume(flags) {
  if (flags.selftest) return selftest();
  const key = typeof flags.ticket === "string" ? flags.ticket.trim() : "";
  if (!key || !KEY_RE.test(key)) {
    console.error(`vteam resume: ticket key required, e.g. \`vteam resume DEMO-1\`` +
      (key ? ` — ${JSON.stringify(key)} does not match <PROJ>-<n>` : ""));
    process.exit(1);
  }
  const root = repoRoot();
  const cfg = loadConfig(root) || {};
  const s = collectSignals(root, cfg, key);
  const d = derive(s);
  if (flags.json) {
    console.log(JSON.stringify({ ...s, stage: d.stage, next: d.next }, null, 2));
    return;
  }
  console.log(renderHuman(s, d));
}

// ---- selftest ---------------------------------------------------------------
// The derivation table IS the feature — every row of it gets a fixture, and
// the precedence (verdict > review > tasksheet > branch > claim > nothing)
// is proven, not assumed.
function selftest() {
  let failed = 0;
  const check = (cond, ...why) => { if (!cond) { failed++; console.error("❌", ...why); } };
  const os = { tmpdir: () => process.env.TMPDIR || "/tmp" };
  const tmp = fs.mkdtempSync(path.join(os.tmpdir(), "vteam-resume-"));
  const root = path.join(tmp, "repo");
  fs.mkdirSync(root, { recursive: true });
  spawnSync("git", ["init", "-q", root]);
  const cfg = { paths: { evidence: "evd", pm: "docs/pm", backlog: "docs/backlog" },
    tracker: { provider: "markdown" } };
  const evd = path.join(root, "evd", "DEMO-1");

  // stage 0: no trace
  let d = derive(collectSignals(root, cfg, "DEMO-1"));
  check(d.stage === "no trace", "empty repo must derive 'no trace'", d);

  // stage: live claim → STOP; expired claim → orphaned
  fs.mkdirSync(path.join(root, "docs", "backlog"), { recursive: true });
  const now = new Date().toISOString();
  fs.writeFileSync(path.join(root, "docs", "backlog", "DEMO-1.md"),
    `# DEMO-1\n\nclaimed ${now} · branch feat/DEMO-1-x\n`);
  let s = collectSignals(root, cfg, "DEMO-1");
  check(s.claim.found && s.claim.expired === false, "fresh claim parses + within TTL", s.claim);
  check(/STOP/.test(derive(s).next), "fresh claim must say STOP", derive(s));
  fs.writeFileSync(path.join(root, "docs", "backlog", "DEMO-1.md"),
    `# DEMO-1\n\nclaimed 2026-01-01T00:00:00Z · branch feat/DEMO-1-x\n`);
  s = collectSignals(root, cfg, "DEMO-1");
  check(s.claim.expired === true && /orphaned/.test(derive(s).next),
    "old claim must derive orphaned", derive(s));

  // each artifact promotes the stage — precedence proven in order
  spawnSync("git", ["-C", root, "branch", "feat/DEMO-1-x"], {}); // may fail (no commit) — fake via ref
  fs.mkdirSync(path.join(root, ".git", "refs", "heads", "feat"), { recursive: true });
  fs.writeFileSync(path.join(root, ".git", "refs", "heads", "feat", "DEMO-1-x"),
    "0000000000000000000000000000000000000001\n");
  s = collectSignals(root, cfg, "DEMO-1");
  check(s.branches.some((b) => b.includes("DEMO-1")), "branch listed", s.branches);
  check(/died before T1/.test(derive(s).next), "branch-only → re-run T1", derive(s));

  fs.mkdirSync(path.join(evd, "dev"), { recursive: true });
  fs.writeFileSync(path.join(evd, "dev", "tasksheet.md"), "# tasksheet\n");
  d = derive(collectSignals(root, cfg, "DEMO-1"));
  check(/tasksheet written/.test(d.stage) && /resumes/.test(d.next), "tasksheet → resume /dev", d);

  fs.writeFileSync(path.join(evd, "dev", "review.md"), "# review cards\n");
  d = derive(collectSignals(root, cfg, "DEMO-1"));
  check(/review dossier committed/.test(d.stage) && /\/qa DEMO-1/.test(d.next),
    "review dossier → hand to QA", d);

  fs.writeFileSync(path.join(evd, "REPORT.md"), "# DEMO-1 — FAIL\n\nCOMMIT: abc1234\n");
  d = derive(collectSignals(root, cfg, "DEMO-1"));
  check(d.stage === "qa-verdict FAIL" && /re-dispatch \/dev/.test(d.next), "FAIL → back to dev", d);
  fs.writeFileSync(path.join(evd, "REPORT.md"), "# DEMO-1 — PASS\n\nCOMMIT: abc1234\n");
  d = derive(collectSignals(root, cfg, "DEMO-1"));
  check(/PASS/.test(d.stage) && /nothing to resume/.test(d.next), "PASS → nothing to resume", d);
  // the H1-only word-boundary law holds here too
  fs.writeFileSync(path.join(evd, "REPORT.md"), "# DEMO-1 — PASSPORT check\n");
  s = collectSignals(root, cfg, "DEMO-1");
  check(s.report.verdict === null && /NO verdict/.test(renderHuman(s, derive(s))),
    "PASSPORT is not PASS", s.report);

  // ledger rows attach
  fs.mkdirSync(path.join(root, "docs", "pm"), { recursive: true });
  fs.writeFileSync(path.join(root, "docs", "pm", "log.md"),
    "| Date | Lane | Actor | Item | Result | Link |\n|---|---|---|---|---|---|\n" +
    "| 2026-08-20 | DEV | An | DEMO-1 | failed: session died | - |\n");
  s = collectSignals(root, cfg, "DEMO-1");
  check(s.ledger_rows.length === 1 && s.ledger_rows[0].result_kind === "failed",
    "ledger rows found for the key", s.ledger_rows);

  // non-markdown tracker: claim is a LOUD cannot-check, never a silent no
  const s2 = collectSignals(root, { ...cfg, tracker: { provider: "jira" } }, "DEMO-1");
  check(s2.claim.checkable === false && /CANNOT CHECK/.test(renderHuman(s2, derive(s2))),
    "jira claim must be a loud skip", s2.claim);

  fs.rmSync(tmp, { recursive: true, force: true });
  if (failed) { console.error(`resume selftest: ${failed} FAILED`); process.exit(1); }
  console.log("resume selftest: OK (9 derivation rows + precedence + H1 law + loud jira skip)");
}
