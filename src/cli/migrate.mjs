import fs from "node:fs";
import path from "node:path";
import { repoRoot } from "./util.mjs";
import { loadConfig, cfgGet, CONFIG_NAME } from "./config.mjs";

/** Legacy-sentinel rewriter (`vteam doctor --migrate [--apply]`).
 *
 * Rewrites machine-checked sentinels from the source harness's Vietnamese
 * vocabulary to vteam's neutral sentinels, so the gates can read pre-vteam
 * artifacts. PROSE IS NEVER TOUCHED — only the exact strings the gates match.
 * Dry-run by default; --apply writes. Scope: the ledgers + evidence text files.
 */

// [regex, replacement] — ordered; longest/most-specific first.
const RULES = [
  // ledger table header (log_check anchors on "| Date |")
  [/^\| Ngày \| Lane \| Việc \| Kết quả \| Link \|$/gm, "| Date | Lane | Item | Result | Link |"],
  // ledger results (log_check)
  [/\bhoàn thành\b/g, "done"],
  [/\bchặn:\s*/g, "blocked: "],
  [/\bhỏng:\s*/g, "failed: "],
  // decision-queue statuses (schedule_check)
  [/🔴 MỞ/g, "🔴 OPEN"],
  [/🟡 TẠM CHỐT \(máy\)/g, "🟡 PROVISIONAL (machine)"],
  [/✅ ĐÃ CHỐT/g, "✅ DECIDED"],
  // QA verdicts + manifest sentinels (evd_check / evd_ui_check)
  [/KẾT QUẢ\s*[:：]/g, "RESULT:"],
  [/LOẠI\s*[:：]\s*KHÔNG-UI/g, "TYPE: NON-UI"],
  [/TRẠNG THÁI\s*[:：]/g, "STATE:"],
  [/PHẠM VI HẸP\s*[:：]/g, "NARROW-SCOPE:"],
  [/ĐẠT MỘT PHẦN/g, "PARTIAL"],
  [/KHÔNG ĐẠT/g, "FAIL"],
  [/GÂY LỖI MỚI/g, "NEW-BUG"],
  [/BỊ CHẶN/g, "BLOCKED"],
  [/CHƯA RÕ/g, "UNCLEAR"],
  [/(^|[^A-ZĐ])ĐẠT\b/gm, "$1PASS"],
  [/Mức độ\s*[:：]/g, "Severity:"],
  [/Nguồn gốc\s*[:：]/g, "Origin:"],
  [/CHƯA ĐO/g, "NOT MEASURED"],
  // review cards (review_check)
  [/đã[\s-]thử[\s-]phá/gi, "Tried to break"],
  [/Trả lời QUESTION/gi, "Answered QUESTIONS"],
  [/LỆCH CỐ Ý/g, "INTENDED"],
  [/LỆCH SAI/g, "DEVIATION: WRONG"],
  // report-comment markers (comment_check)
  [/【Đã làm gì】/g, "[R1]"],
  [/【Phạm vi ảnh hưởng】/g, "[R2]"],
  [/【Kỹ thuật】/g, "[R3]"],
  [/【Đã test】/g, "[R4]"],
  [/【Bằng chứng】/g, "[R5]"],
  [/【Lưu ý cho QA】/g, "[R6]"],
  [/【JIRA ATTACHMENTS/g, "[TRACKER ATTACHMENTS"],
  [/## JIRA ATTACHMENTS/g, "## TRACKER ATTACHMENTS"],
  [/【Vướng mắc còn lại】/g, "[R7]"],
];

// dd/mm/yyyy → yyyy-mm-dd, ONLY inside ledger-style table rows (| … |)
function isoDates(line) {
  if (!line.startsWith("|")) return line;
  // day ranges first ("07-08/08/2026" → "2026-08-07/08"), then plain dates
  return line
    .replace(/\b(\d{2})-(\d{2})\/(\d{2})\/(\d{4})\b/g, "$4-$3-$1/$2")
    .replace(/\b(\d{2})\/(\d{2})\/(\d{4})\b/g, "$3-$2-$1");
}

function targets(root, cfg) {
  const out = [];
  const push = (p) => { if (fs.existsSync(p)) out.push(p); };
  push(path.join(root, cfg.pm, "log.md"));
  push(path.join(root, cfg.pm, "decisions.md"));
  const evd = path.join(root, cfg.evidence);
  if (fs.existsSync(evd)) {
    const walk = (d) => {
      for (const e of fs.readdirSync(d, { withFileTypes: true })) {
        const p = path.join(d, e.name);
        if (e.isDirectory()) walk(p);
        else if (e.name.endsWith(".md")) out.push(p);
      }
    };
    walk(evd);
  }
  return out;
}

export function migrate(flags) {
  const root = repoRoot();
  // ONE parser behavior everywhere: read config through config.mjs (= ctx.mjs),
  // never a first-match regex — trailing comments and flow maps parse the same
  // here as in every gate (a regex grab once false-cleaned the shipped example).
  const cfg = loadConfig(root);
  if (cfg === null) {
    throw new Error(`${CONFIG_NAME} not found at repo root — run \`npx vteam init\` before migrating`);
  }
  const dirs = {
    pm: String(cfgGet(cfg, "paths.pm", "docs/pm")),
    evidence: String(cfgGet(cfg, "paths.evidence", "evd")),
  };
  const apply = !!flags.apply;
  let totalHits = 0, changedFiles = 0;

  for (const file of targets(root, dirs)) {
    const before = fs.readFileSync(file, "utf8");
    let after = before;
    let hits = 0;
    for (const [re, rep] of RULES) {
      after = after.replace(re, (...a) => { hits++; return typeof rep === "string" ? rep.replace("$1", a[1] ?? "") : rep; });
    }
    // date normalization only in the two ledgers (table rows)
    if (file.endsWith("log.md") || file.endsWith("decisions.md")) {
      const lines = after.split("\n").map(isoDates);
      const joined = lines.join("\n");
      if (joined !== after) hits++;
      after = joined;
    }
    if (after !== before) {
      changedFiles++;
      totalHits += hits;
      console.log(`${apply ? "✎" : "would rewrite"} ${path.relative(root, file)} (${hits} sentinel hits)`);
      if (apply) fs.writeFileSync(file, after);
    }
  }
  if (!changedFiles) {
    console.log("migrate: nothing to rewrite — no legacy sentinels found.");
    return;
  }
  console.log(`\nmigrate: ${changedFiles} files, ~${totalHits} rewrites ${apply ? "APPLIED" : "(dry run — add --apply)"}.`);
  if (!apply) console.log("Review the list, then: vteam doctor --migrate --apply");
  else console.log("Re-run the gates (vteam doctor) to confirm the ledgers now parse.");
}
