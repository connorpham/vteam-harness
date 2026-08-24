// checkpoint.mjs — manually save or query ticket checkpoint.
//
// Usage:
//   vteam checkpoint save <TICKET> <LANE> — save checkpoint after lane succeeds
//   vteam checkpoint query <TICKET>      — read current checkpoint (same as resume)
//
// Skills can call this after a lane completes to mark progress:
//   npx vteam-harness checkpoint save DEMO-1 dev
//   # → {paths.evidence}/DEMO-1/.checkpoint written
//
// When /dev crashes, PM runs:
//   vteam resume DEMO-1
//   # → "DEMO-1: completed [plan → dor → dev], ready for review…"
//
// Then re-dispatch from review lane, skipping plan/dor/dev.
import { spawnSync } from "node:child_process";
import { repoRoot } from "./util.mjs";

export async function checkpoint(flags) {
  const root = repoRoot();
  const subCmd = flags._?.[0];

  if (subCmd === "save") {
    return checkpointSave(root, flags._ || []);
  } else if (subCmd === "query") {
    return checkpointQuery(root, flags._ || []);
  } else if (flags.selftest) {
    return selftest();
  } else {
    console.log("vteam checkpoint save <TICKET> <LANE> — save after lane success");
    console.log("vteam checkpoint query <TICKET>      — read current checkpoint");
    process.exit(1);
  }
}

function checkpointSave(root, args) {
  const ticket = args[1];
  const lane = args[2];

  if (!ticket || !lane) {
    console.error("vteam checkpoint save: ticket and lane required");
    process.exit(1);
  }

  const r = spawnSync("python3", [
    ".vteam/scripts/lib/checkpoint.py",
    "--save", ticket, lane,
  ], { cwd: root, encoding: "utf8" });

  if (r.status !== 0) {
    console.error(r.stderr || r.stdout);
    process.exit(1);
  }
  console.log(r.stdout);
}

function checkpointQuery(root, args) {
  const ticket = args[1];

  if (!ticket) {
    console.error("vteam checkpoint query: ticket required");
    process.exit(1);
  }

  const r = spawnSync("python3", [
    ".vteam/scripts/lib/checkpoint.py",
    "--query", ticket,
  ], { cwd: root, encoding: "utf8" });

  if (r.status !== 0) {
    console.error(r.stderr || r.stdout);
    process.exit(1);
  }
  console.log(r.stdout);
}

function selftest() {
  console.log("checkpoint selftest: defer to checkpoint.py selftest");
  const r = spawnSync("python3", [".vteam/scripts/lib/checkpoint.py"], {
    stdio: "inherit",
  });
  process.exit(r.status);
}
