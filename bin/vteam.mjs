#!/usr/bin/env node
import { parseArgs } from "../src/cli/util.mjs";

const HELP = `vteam — a virtual AI team (PM·BA·SA·DEV·QA) for any repo, any agent tool.

Usage:
  npx vteam-harness audit     grade any repo's AI-agent accountability 0-100 (works without vteam installed)
  npx vteam-harness init      install into the current repo (interactive; --yes for defaults)
  npx vteam-harness doctor    preflight + install integrity + gate selftests
  npx vteam-harness update    refresh framework files (never touches your ledgers/config)
  npx vteam-harness board     read-only local dashboard: tickets, ledger, evidence verdicts, decision queue
  npx vteam-harness graph     the work graph made visible: what can start now, what is blocked, what is broken
  npx vteam-harness usage     MEASURED AI usage for this repo: who ran which model, when, at what token
                              cost — read from the agent CLIs' own session logs, not from self-reports

audit flags:  --json  machine-readable {score, grade, dimensions} on stdout

usage flags:  --since <YYYY-MM-DD>  window start (default: last 90 days)
              --json                machine-readable {models, daily, sessions, cross_check}
              --sync                publish counts to {paths.pm}/usage/<you>.md — one file per
                                    person (conflict-free); commit it so the lead sees the team.
                                    Counts only: models, tokens, times. NEVER chat content.
              cross-checks the ledger: done rows on days with no recorded session, and heavy
              AI days with no ledger row, are flagged. Sources: Claude Code + Codex.

board flags:  --port <n>  listen port (default 4177; 127.0.0.1 only — never exposed off-host)
              read-only by construction: GET / and GET /api/state, no write endpoint at all

graph flags:  --json  {generated_at_commit, nodes, edges, findings} on stdout — sorted, no timestamp, diffable
              --dot   Graphviz digraph: npx vteam-harness graph --dot | dot -Tsvg > graph.svg
              read-only, ALWAYS exits 0 — graph is a mirror; the gate is .vteam/scripts/graph_check.py

init flags (all optional; any given flag skips its prompt):
  --yes                      accept defaults for everything not flagged
  --name <str> --key <PROJ> --language <en|vi|…>
  --profile <generic|node|python|nextjs-prisma|go|rust>
  --tracker <markdown|jira|github>  --design <none|figma>
  --autonomy <off|assisted|full>
  --tools <csv of: claude-code,cursor,windsurf,codex,copilot>

doctor flags: --backend (design legs warn only)
              --json     machine-readable {ok, checks} on stdout
              --migrate  rewrite legacy pre-vteam sentinels in ledgers/evidence
                         (dry-run by default; add --apply to write)
`;

const { flags, positional } = parseArgs(process.argv.slice(2));
const cmd = positional[0];

try {
  if (cmd === "audit") {
    const { audit } = await import("../src/cli/audit.mjs");
    await audit(flags);
  } else if (cmd === "init") {
    const { init } = await import("../src/cli/init.mjs");
    await init(flags);
  } else if (cmd === "doctor") {
    const { doctor } = await import("../src/cli/doctor.mjs");
    await doctor(flags);
  } else if (cmd === "board") {
    const { board } = await import("../src/cli/board.mjs");
    await board(flags);
  } else if (cmd === "graph") {
    const { graph } = await import("../src/cli/graph.mjs");
    await graph(flags);
  } else if (cmd === "update") {
    const { update } = await import("../src/cli/update.mjs");
    await update(flags);
  } else if (cmd === "usage") {
    const { usage } = await import("../src/cli/usage.mjs");
    await usage(flags);
  } else {
    console.log(HELP);
    process.exit(cmd ? 1 : 0);
  }
} catch (e) {
  console.error(`vteam: ${e.message}`);
  process.exit(1);
}
