#!/usr/bin/env node
import { parseArgs } from "../src/cli/util.mjs";

const HELP = `vteam — a virtual AI team (PM·BA·SA·DEV·QA) for any repo, any agent tool.

Usage:
  npx vteam audit     grade any repo's AI-agent accountability 0-100 (works without vteam installed)
  npx vteam init      install into the current repo (interactive; --yes for defaults)
  npx vteam doctor    preflight + install integrity + gate selftests
  npx vteam update    refresh framework files (never touches your ledgers/config)

audit flags:  --json  machine-readable {score, grade, dimensions} on stdout

init flags (all optional; any given flag skips its prompt):
  --yes                      accept defaults for everything not flagged
  --name <str> --key <PROJ> --language <en|vi|…>
  --profile <generic|node|python|nextjs-prisma>
  --tracker <markdown|jira>  --design <none|figma>
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
  } else if (cmd === "update") {
    const { update } = await import("../src/cli/update.mjs");
    await update(flags);
  } else {
    console.log(HELP);
    process.exit(cmd ? 1 : 0);
  }
} catch (e) {
  console.error(`vteam: ${e.message}`);
  process.exit(1);
}
