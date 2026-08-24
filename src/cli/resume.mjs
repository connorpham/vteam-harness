// resume.mjs — continue a ticket that was paused/crashed mid-lane.
//
// When a lane (typically /dev) crashes or pauses, a checkpoint is saved:
// {completed_lanes: [plan, dor, dev], next_lane: "review", code_sha: "abc123"}.
// This command reads that checkpoint and prints the next lane to dispatch to.
//
// Usage: vteam resume <TICKET> [--quiet]
// Outputs (default): human-readable message
// Outputs (--quiet): JSON {ticket, next_lane, completed_lanes, code_sha}
//
// The PM then re-dispatches TICKET to the next lane, skipping earlier ones.
import fs from "node:fs";
import path from "node:path";
import { cfgGet, loadConfig } from "./config.mjs";
import { repoRoot } from "./util.mjs";

export async function resume(flags) {
  if (flags.selftest) return selftest();
  const root = repoRoot();
  const cfg = loadConfig(root) || {};
  const ticket = flags.ticket || flags._?.[0];

  if (!ticket) {
    console.error("vteam resume: ticket name required (e.g. vteam resume DEMO-1)");
    process.exit(1);
  }

  const evdRel = String(cfgGet(cfg, "paths.evidence", "docs/qa"));
  const checkpointFile = path.join(root, evdRel, ticket, ".checkpoint");

  let checkpoint;
  try {
    checkpoint = JSON.parse(fs.readFileSync(checkpointFile, "utf8"));
  } catch (e) {
    if (e.code === "ENOENT") {
      console.error(`vteam resume: no checkpoint found for ${ticket} — has it started?`);
    } else {
      console.error(`vteam resume: could not read checkpoint: ${e.message}`);
    }
    process.exit(1);
  }

  // Validation: checkpoint must have the expected shape
  if (!checkpoint.ticket || !checkpoint.next_lane || !Array.isArray(checkpoint.completed_lanes)) {
    console.error(`vteam resume: checkpoint malformed (missing ticket, next_lane, or completed_lanes)`);
    process.exit(1);
  }

  const msg = `${checkpoint.ticket}: completed [${checkpoint.completed_lanes.join(" → ")}], ready for ${checkpoint.next_lane} (code ${(checkpoint.code_sha || "").slice(0, 7) || "—"}). ` +
              `Re-dispatch ${checkpoint.ticket} to /${checkpoint.next_lane} and it will skip earlier lanes.`;

  if (flags.quiet || flags.json) {
    console.log(JSON.stringify({
      ticket: checkpoint.ticket,
      next_lane: checkpoint.next_lane,
      completed_lanes: checkpoint.completed_lanes,
      code_sha: checkpoint.code_sha,
    }, null, 2));
  } else {
    console.log(msg);
  }
}

// ---- selftest ----
function selftest() {
  import("node:child_process").then(({ execSync }) => {
    const fs = require("node:fs");
    const path = require("node:path");
    const os = require("node:os");
    const tmp = fs.mkdtempSync(path.join(os.tmpdir(), "vteam-resume-"));
    const evd = path.join(tmp, "docs", "qa");
    fs.mkdirSync(path.join(evd, "DEMO-1"), { recursive: true });
    fs.writeFileSync(path.join(evd, "DEMO-1", ".checkpoint"), JSON.stringify({
      ticket: "DEMO-1",
      completed_lanes: ["plan", "dor", "dev"],
      next_lane: "qa",
      code_sha: "abc12345",
      saved_at: "2026-08-24T00:00:00Z",
    }));
    // test: missing checkpoint
    try {
      const r = execSync(`node -e "import('./src/cli/resume.mjs').then(m=>m.resume({ticket:'DEMO-2'}))" 2>&1`, {
        cwd: tmp, encoding: "utf8", stdio: "pipe",
      });
      throw new Error("should have exited 1, got: " + r);
    } catch (e) {
      if (!e.message.includes("no checkpoint")) throw e;
    }
    // test: valid checkpoint, human output
    const out = execSync(`node -e "import('./src/cli/resume.mjs').then(m=>m.resume({ticket:'DEMO-1'}))" 2>&1`, {
      cwd: tmp, encoding: "utf8",
    });
    console.assert(out.includes("DEMO-1") && out.includes("qa") && out.includes("abc1234"), `unexpected output: ${out}`);
    // test: --json
    const json = execSync(`node -e "import('./src/cli/resume.mjs').then(m=>m.resume({ticket:'DEMO-1',json:true}))" 2>&1`, {
      cwd: tmp, encoding: "utf8",
    });
    const obj = JSON.parse(json);
    console.assert(obj.ticket === "DEMO-1" && obj.next_lane === "qa", `bad json: ${json}`);
    fs.rmSync(tmp, { recursive: true, force: true });
    console.log("resume selftest: OK (missing checkpoint, human output, --json)");
  });
}
