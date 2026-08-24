#!/usr/bin/env node
// external_review.mjs — a review card written by ANOTHER MODEL, held to the SAME bar.
//
// Why: reviewer diversity is only real when the reviewers don't share a brain.
// Two Claude agents reviewing a Claude diff share training data, blind spots and
// taste; a different MODEL is the cheapest independent eye available. Review
// cards are just files, so ANY tool that can write a conforming card can be a
// reviewer — Codex, Gemini CLI, a local model, a human with a keyboard. The part
// that has to be built honestly is the machinery AROUND that: the brief the tool
// receives, and the validation its card must survive BEFORE it lands anywhere.
//
// This runner reviews nothing itself. It:
//   (a) refuses LOUDLY when the setup is missing — no config for this card id, no
//       such binary on PATH, nothing staged/committed to review;
//   (b) builds the brief (review-standard.md verbatim + the card contract with
//       review_check's REAL numbers + the ticket + the diff) and pipes it to the
//       configured CLI on stdin;
//   (c) validates stdout against review_check.py's OWN bar (verdict, ≥3
//       tried-to-break bullets, ≥2 traces of which ≥1 file:line that EXISTS);
//   (d) only then writes/replaces that ONE card section in the dossier.
//
// An invalid card is never written. No card is strictly better than a junk card,
// because the push fence COUNTS cards — a junk card would count. That is the
// whole reason validation lives here and not in the reviewer's good intentions.
//
// Usage:
//   node .vteam/scripts/external_review.mjs <TICKET> <CARD_ID>     # e.g. PROJ-12 R2
//   node .vteam/scripts/external_review.mjs --selftest
//
// Config (vteam.config.yaml) — the CLI must be installed and authenticated BY YOU:
//   review:
//     external:                        # optional — cross-model reviewers by card id
//       r2:
//         command: "codex exec"        # gets the BRIEF on stdin, prints the CARD on stdout
//         model: "gpt-5-codex"         # recorded on the card — never guessed
//         timeout_s: 300               # optional, default 300
//   `command` may be a string (split on whitespace — NO shell, so quoted
//   arguments are impossible) or a list: ["codex", "exec", "--full-auto"].
//   A string containing a quote character is REFUSED rather than mis-split.
//
// Exit codes (they mean different things — automation must not collapse them):
//   0 = card written, verdict APPROVE
//   2 = card written, verdict REQUEST-CHANGES (round NOT closed — fix, re-run)
//   1 = nothing written; stdout names exactly what was missing
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import process from "node:process";
import { spawnSync } from "node:child_process";
import { fileURLToPath, pathToFileURL } from "node:url";
import { Ctx, loadEnv } from "./lib/ctx.mjs";

const SELF = fileURLToPath(import.meta.url);
const HERE = path.dirname(SELF);

// ── the card grammar — MUST MATCH core/scripts/review_check.py ────────────────
// review_check.py is the HOUSE OF RECORD for what a valid card is; this file
// only has to agree with it. Same trick src/cli/board.mjs uses for ledger.py:
// the patterns below are stored as the PYTHON literal text, the JS regexes are
// built FROM those strings, and --selftest asserts every literal still appears
// verbatim in review_check.py. Change the gate's grammar and this selftest goes
// red — the two cannot drift in silence.
const PY = {
  CARD_HEAD: String.raw`^#{2,4}\s.*\b(R\d+)\b`,
  BULLET: String.raw`^\s*[-*•]\s+\S`,
  EVIDENCE_CMD: '`[^`\\n]*[\\s/][^`\\n]*`',
  EVIDENCE_LOC: String.raw`\b[\w./-]+\.(?:ts|tsx|js|jsx|mjs|py|sh|go|rs|java|kt|rb|php|prisma|sql|md):\d+`,
  TRIED: String.raw`(tried[\s-]to[\s-]break|TRIED[\s-]TO[\s-]BREAK)(.*)`,
  REF_3B: String.raw`\b([\w./-]+\.(?:ts|tsx|js|jsx|mjs|py|sh|go|rs|java|kt|rb|php|prisma|sql)):\d+`,
  MIN_TRIED_BULLETS: "MIN_TRIED_BULLETS = 3",
  MIN_TRACES: "MIN_TRACES = 2",
  MIN_FILE_LINE: "MIN_FILE_LINE = 1",
};
const CARD_HEAD = new RegExp(PY.CARD_HEAD, "gm"); // re.M
const BULLET = new RegExp(PY.BULLET, "gm"); // re.M
const EVIDENCE_CMD = new RegExp(PY.EVIDENCE_CMD, "g");
const EVIDENCE_LOC = new RegExp(PY.EVIDENCE_LOC, "g");
const REF_3B = new RegExp(PY.REF_3B, "g");
// The ONE documented divergence: Python's re.S makes `.` swallow newlines; JS has
// no such flag, so `(.*)` becomes `([\s\S]*)`. Same language, same match.
const TRIED = new RegExp(PY.TRIED.replace("(.*)", "([\\s\\S]*)"), "i"); // re.S|re.I
const MIN_TRIED_BULLETS = 3; // ← PY.MIN_TRIED_BULLETS
const MIN_TRACES = 2; //        ← PY.MIN_TRACES
const MIN_FILE_LINE = 1; //     ← PY.MIN_FILE_LINE

const count = (re, s) => (s.match(re) || []).length;

/** Mirror of review_check.parse_cards — split text into card fragments by id. */
function parseCards(text) {
  const cards = {};
  const heads = [...text.matchAll(CARD_HEAD)];
  for (let i = 0; i < heads.length; i++) {
    const end = i + 1 < heads.length ? heads[i + 1].index : text.length;
    (cards[heads[i][1]] ??= []).push(text.slice(heads[i].index, end));
  }
  return cards;
}

/** Sections of an existing dossier, preserving bytes: preamble + one span per
 * card heading (heading through the next heading). Rejoining the spans
 * reproduces the file exactly — that is how OTHER cards survive untouched. */
function splitSections(text) {
  const heads = [...text.matchAll(CARD_HEAD)];
  const preamble = heads.length ? text.slice(0, heads[0].index) : text;
  const spans = heads.map((h, i) => ({
    id: h[1],
    text: text.slice(h.index, i + 1 < heads.length ? heads[i + 1].index : text.length),
  }));
  return { preamble, spans };
}

/** review_check.card_is_valid_approve + rule 3b, with REQUEST-CHANGES treated as
 * a legitimate verdict (it is an honest review outcome — it just doesn't close
 * the round). Returns the verdict and every reason the gate would reject. */
function cardProblems(card, root) {
  const probs = [];
  const rc = /REQUEST[- ]CHANGES/.test(card);
  const ap = /\bAPPROVE\b/.test(card);
  if (!rc && !ap) {
    probs.push("no verdict line — the card must say APPROVE or REQUEST-CHANGES");
  }
  if (!rc) {
    // the APPROVE bar, verbatim from review_check
    const m = TRIED.exec(card);
    if (!m) {
      probs.push("APPROVE without a 'tried to break' section — invalid card "
        + "(review-standard §1); the words 'Tried to break:' must appear");
    } else {
      const n = count(BULLET, m[2]);
      if (n < MIN_TRIED_BULLETS) {
        probs.push(`'tried to break' has ${n} bullet(s), needs ≥${MIN_TRIED_BULLETS} `
          + "— that's not trying");
      }
    }
  }
  const nCmd = count(EVIDENCE_CMD, card);
  const nLoc = count(EVIDENCE_LOC, card);
  if (nCmd + nLoc < MIN_TRACES) {
    probs.push(`card has ${nCmd + nLoc} verifiable trace(s) (\`command\` / file:line), `
      + `needs ≥${MIN_TRACES} — testimony without commands is just prose`);
  }
  if (nLoc < MIN_FILE_LINE) {
    probs.push("card has no file:line trace — bare backticks can't be cross-checked "
      + "against the code (anti-fabrication rule 3b)");
  }
  for (const m of card.matchAll(REF_3B)) {
    if (!fs.existsSync(path.join(root, m[1]))) {
      probs.push(`card cites ${m[1]} — no such file in the worktree; a fabricated `
        + "citation voids the whole card");
    }
  }
  return { verdict: rc ? "REQUEST-CHANGES" : "APPROVE", probs };
}

// ── environment probes ───────────────────────────────────────────────────────
/** `command -v` without a shell: absolute/relative paths are checked directly,
 * bare names are resolved against PATH. POSIX layout (vteam's hooks are bash). */
function whichBin(bin, env = process.env) {
  const executable = (p) => {
    try { return fs.statSync(p).isFile() && (fs.accessSync(p, fs.constants.X_OK), true); }
    catch { return false; }
  };
  if (bin.includes("/")) return executable(path.resolve(bin)) ? path.resolve(bin) : null;
  for (const dir of (env.PATH || "").split(path.delimiter)) {
    if (dir && executable(path.join(dir, bin))) return path.join(dir, bin);
  }
  return null;
}

/** command: string | [argv...] → argv. No shell, ever: a config value that
 * reaches a shell is a config value that can run anything. A string is split on
 * whitespace, which CANNOT express a quoted argument — so a string carrying a
 * quote is refused instead of silently mis-split. Use the list form for those. */
function resolveCommand(raw, cardKey) {
  if (Array.isArray(raw)) {
    const argv = raw.map(String).filter((s) => s.length);
    if (!argv.length) throw new Error(`review.external.${cardKey}.command is an empty list`);
    return argv;
  }
  const s = String(raw ?? "").trim();
  if (!s) throw new Error(`review.external.${cardKey}.command is empty`);
  if (/["']/.test(s)) {
    throw new Error(`review.external.${cardKey}.command contains a quote character. `
      + "This runner never uses a shell, so quotes cannot be honoured — write the "
      + `command as a LIST instead:  command: ["codex", "exec", "--flag=a b"]`);
  }
  return s.split(/\s+/);
}

const git = (root, ...args) => {
  const r = spawnSync("git", args, { cwd: root, encoding: "utf8", maxBuffer: 64 << 20 });
  return { code: r.status ?? 1, out: r.stdout ?? "" };
};

/** Diff base, fail-closed exactly like .githooks/pre-push's scan_base: prefer
 * origin/<protected>, fall back to the local branch, and finally to the EMPTY
 * TREE so the FULL content gets reviewed — never silently "nothing to review". */
function diffBase(root, protectedBranch) {
  for (const ref of [`origin/${protectedBranch}`, protectedBranch]) {
    if (git(root, "rev-parse", "--verify", "-q", `${ref}^{commit}`).code === 0) {
      return { base: ref, how: `${ref} (merge-base, three-dot)` };
    }
  }
  const empty = git(root, "hash-object", "-t", "tree", "/dev/null").out.trim();
  return { base: empty, how: `the EMPTY TREE — neither origin/${protectedBranch} nor `
    + `${protectedBranch} exists here, so the FULL branch content is under review` };
}

/** Three-dot first, two-dot fallback — same convention as
 * review_check.changed_files: a shallow clone lacking the merge-base must not
 * come back "nothing changed". Both failing yields "" and the caller refuses. */
function diffCommitted(root, base, ...extra) {
  for (const args of [[`${base}...HEAD`], [base, "HEAD"]]) {
    const r = git(root, "diff", ...extra, ...args);
    if (r.code === 0) return r.out;
  }
  return "";
}

/** The diff reviewers can actually see: committed + whatever is STAGED. Unstaged
 * work is invisible on purpose; T4b says so, and a reviewer approving code that
 * isn't in the index approved the wrong code. */
function collectDiff(root, base) {
  const committed = diffCommitted(root, base);
  const staged = git(root, "diff", "--cached").out;
  const unstaged = git(root, "diff", "--name-only").out.split("\n").filter(Boolean);
  const files = new Set([
    ...diffCommitted(root, base, "--name-only").split("\n").filter(Boolean),
    ...git(root, "diff", "--cached", "--name-only").out.split("\n").filter(Boolean),
  ]);
  let text = committed;
  if (staged.trim()) {
    text += `\n--- STAGED, NOT YET COMMITTED (git diff --cached) ---\n${staged}`;
  }
  return { text, files: [...files], unstaged };
}

// ── the brief ────────────────────────────────────────────────────────────────
function buildBrief({ ticket, cardId, root, standardPath, standardText, diff, diffHow }) {
  return `=== VTEAM EXTERNAL REVIEW BRIEF — reviewer ${cardId}, ticket ${ticket} ===

You are reviewer ${cardId} on ticket ${ticket}, in the repository at ${root}.
You did NOT write this code. Your job is to try to BREAK it and to say, on the
record, what you tried. You are the strictest engineer in the room, and every
statement you make must be true and checkable.

OUTPUT CONTRACT — read it twice; vteam VALIDATES your output and refuses to file
an invalid card, so a card that ignores this contract is simply discarded:
  * Print the review card on STDOUT and NOTHING else — no preamble, no "here is
    my review", no fence around the whole card, no trailing commentary.
  * Do NOT create, edit or delete any file, and do not run anything that changes
    the worktree. vteam writes the card itself, and stamps the model on it.
  * Do NOT print a "## ${cardId}" heading — vteam owns the heading.
  * The card MUST contain:
      - a verdict: exactly APPROVE or REQUEST-CHANGES
      - the line "Tried to break:" followed by ≥${MIN_TRIED_BULLETS} markdown bullets, each
        naming the exact command, input or mutation you actually ran
      - ≥${MIN_TRACES} verifiable traces, of which ≥${MIN_FILE_LINE} must be file:line —
        and every file:line you cite MUST EXIST in this repo (a citation of a
        file that isn't there voids the entire card)
  * Every finding is CONFIRMED (evidence attached: file:line + a reproducing
    command or a violated spec quote) or QUESTION (unverified suspicion).
    Hedge words inside a CONFIRMED are banned. REQUEST-CHANGES needs ≥1
    CONFIRMED; a card of questions only is APPROVE with the questions listed.
  * Large findings are comparative: "option A (as built) vs option B — why A".

Card skeleton — fill it in, keep the section names:

    APPROVE
    Tried to break:
    - ran <exact command> — <what actually happened>
    - fed <exact input/role/boundary> — <what actually happened>
    - flipped <mutation> at path/to/file.ts:42 — <which test went red>
    Findings:
    - CONFIRMED: path/to/file.ts:42 — <what is wrong> (repro: \`<command>\`)
    - QUESTION: <what you could not verify, and why>
    Traces: path/to/file.ts:42, \`<command you ran>\`

=== REVIEW STANDARD (${standardPath}) — the bar every reviewer in this repo is held to ===

${standardText.trimEnd()}

=== DIFF UNDER REVIEW (base: ${diffHow}) ===

${diff.trimEnd()}

=== END OF BRIEF ===
`;
}

// ── card assembly ────────────────────────────────────────────────────────────
/** Tools love wrapping output in a fence, and love repeating the heading we told
 * them not to print. Strip exactly those two wrappers, announce it, touch
 * nothing else — reformatting a reviewer's words is not this runner's business. */
function unwrap(body, notes) {
  let lines = body.replace(/\r\n/g, "\n").split("\n");
  const firstIdx = lines.findIndex((l) => l.trim());
  if (firstIdx >= 0 && /^```/.test(lines[firstIdx].trim())) {
    let lastIdx = -1;
    for (let i = lines.length - 1; i > firstIdx; i--) {
      if (lines[i].trim()) { lastIdx = i; break; }
    }
    if (lastIdx > firstIdx && lines[lastIdx].trim() === "```") {
      lines = lines.slice(firstIdx + 1, lastIdx);
      notes.push("stripped an outer ``` fence from the tool output");
    }
  }
  const h = lines.findIndex((l) => l.trim());
  if (h >= 0 && /^#{1,6}\s/.test(lines[h]) && /\bR\d+\b/.test(lines[h])) {
    lines = lines.slice(h + 1);
    notes.push("stripped the tool's own card heading (vteam owns the heading)");
  }
  return lines.join("\n").trim();
}

/** The card section vteam files. The stamp lines deliberately carry NO
 * backticks-with-space and NO file:line: a header must never manufacture the
 * traces the card is required to EARN, or validation would grade its own text. */
function buildSection({ cardId, model, argv, body, ticket, diffHow, nFiles }) {
  return `## ${cardId} — external (${model})\n`
    + `MODEL: ${model}\n`
    + `TOOL: external\n`
    + `COMMAND: ${argv.join(" ")}\n`
    + `TICKET: ${ticket}\n`
    + `DIFF: ${nFiles} file(s) vs ${diffHow.split(" (")[0]}\n`
    + `GENERATED: ${new Date().toISOString().replace(/\.\d+Z$/, "Z")}\n`
    + `\n${body}\n\n`;
}

/** Replace the same-id card(s), leave every other card's bytes ALONE. Spans are
 * rejoined verbatim; the only characters this function may ADD are newlines in
 * front of the new section when the file wasn't newline-terminated. */
function mergeCard(existing, cardId, section) {
  const { preamble, spans } = splitSections(existing);
  const parts = [preamble];
  let slot = -1; // where the new section goes: the first same-id card's place
  for (const s of spans) {
    if (s.id === cardId) { if (slot < 0) slot = parts.length; continue; }
    parts.push(s.text);
  }
  if (slot < 0) slot = parts.length;
  const before = parts.slice(0, slot).join("");
  // Only ADD newlines, never reformat: a card that was already there must come
  // out byte-identical, so the separator is padding in FRONT of the new section.
  const pad = before === "" ? "" : "\n".repeat(Math.max(0, 2 - /\n*$/.exec(before)[0].length));
  parts.splice(slot, 0, pad + section);
  return { text: parts.join(""), replaced: spans.some((s) => s.id === cardId) };
}

// ── main ─────────────────────────────────────────────────────────────────────
function die(msg, ...more) {
  console.log(`❌ external_review: ${msg}`);
  for (const l of more) console.log(`   ${l}`);
  return 1;
}

function main(argv) {
  const [ticketArg, cardArg] = argv;
  if (!ticketArg || !cardArg) {
    console.log("usage: node .vteam/scripts/external_review.mjs <TICKET> <CARD_ID>   "
      + "(e.g. PROJ-12 R2)\n       node .vteam/scripts/external_review.mjs --selftest");
    return 1;
  }
  const c = new Ctx();
  const key = String(c.cfg("project.key"));
  const cardId = String(cardArg).toUpperCase();
  if (!/^R\d+$/.test(cardId)) {
    return die(`card id ${JSON.stringify(String(cardArg))} is not R<n> — `
      + "review_check reads card ids as R1, R2, R3…");
  }
  const tm = new RegExp(`((?:${key}|PR)-\\d+)`, "i").exec(String(ticketArg));
  if (!tm) {
    return die(`cannot extract a ticket key from ${JSON.stringify(ticketArg)} `
      + `— expected ${key}-<n> (project.key)`);
  }
  const ticket = tm[1].toUpperCase();

  // (a1) config for THIS card id — named, never inferred
  const ext = c.cfg("review.external", {});
  const table = (ext && typeof ext === "object" && !Array.isArray(ext)) ? ext : {};
  const found = Object.keys(table).find((k) => k.toUpperCase() === cardId);
  if (!found) {
    const known = Object.keys(table);
    return die(`no config key review.external.${cardId.toLowerCase()} in vteam.config.yaml`,
      known.length ? `configured external reviewers: ${known.join(", ")}`
        : "review.external is absent — no card is delegated to an external tool yet",
      `Add it (the CLI must be installed and authenticated by YOU):`,
      `  review:`, `    external:`, `      ${cardId.toLowerCase()}:`,
      `        command: "codex exec"`, `        model: "gpt-5-codex"`,
      `${cardId} stays a Claude reviewer until that key exists (dev.md T4b).`);
  }
  const spec = table[found] && typeof table[found] === "object" ? table[found] : {};
  const model = String(spec.model ?? "").trim();
  if (!model) {
    return die(`review.external.${found}.model is missing — the model is RECORDED on `
      + "the card, so it is never guessed. Write the exact model id you route to.");
  }
  let argvCmd;
  try { argvCmd = resolveCommand(spec.command, found); }
  catch (e) { return die(e.message); }
  const timeoutS = Number(spec.timeout_s ?? 300);
  if (!Number.isFinite(timeoutS) || timeoutS <= 0) {
    return die(`review.external.${found}.timeout_s must be a positive number `
      + `(got ${JSON.stringify(spec.timeout_s)})`);
  }

  // (a2) the binary must actually be here — `command -v`, no shell.
  // The child inherits the process env with .env filling the gaps — the same
  // credential contract every other vteam gate uses (ctx.loadEnv, inert: values
  // are text, never executed). Nothing from it is ever printed.
  const childEnv = loadEnv(c.root);
  const bin = whichBin(argvCmd[0], childEnv);
  if (!bin) {
    return die(`${argvCmd[0]}: no such executable on PATH`,
      `review.external.${found}.command = ${JSON.stringify(argvCmd.join(" "))}`,
      "vteam does not install or authenticate external CLIs — install it, log in,",
      `then re-run. Until then ${cardId} has no card and the push fence stays shut.`);
  }

  // (a3) something to review
  const protectedBranch = String(c.cfg("git.protected_branch", "main"));
  const { base, how } = diffBase(c.root, protectedBranch);
  const diff = collectDiff(c.root, base);
  if (!diff.text.trim()) {
    return die(`no staged or committed diff against ${how.split(" (")[0]} — there is `
      + "nothing to review",
      "Commit or `git add -A` your work first: an unstaged diff is a diff no",
      "reviewer can see (dev.md T4b), and reviewing an empty diff is theatre.");
  }
  if (diff.unstaged.length) {
    console.log(`⚠  ${diff.unstaged.length} file(s) have UNSTAGED changes — they are NOT `
      + `in the brief:\n     ${diff.unstaged.slice(0, 5).join(", ")}`
      + `${diff.unstaged.length > 5 ? ", …" : ""}\n   Run \`git add -A\` first (T4b) or `
      + "the reviewer approves a version you already changed.");
  }

  // (b) the brief
  const teamDir = String(c.cfg("paths.team", "docs/team"));
  const standardRel = path.join(teamDir, "review-standard.md");
  const standardAbs = path.join(c.root, standardRel);
  if (!fs.existsSync(standardAbs)) {
    return die(`${standardRel} is missing — every reviewer brief MUST carry the review `
      + "standard (dev.md T4b)",
      "Restore it with `npx vteam-harness update`; a reviewer briefed without the",
      "standard is a reviewer inventing its own bar.");
  }
  const brief = buildBrief({
    ticket, cardId, root: c.root, standardPath: standardRel,
    standardText: fs.readFileSync(standardAbs, "utf8"),
    diff: diff.text, diffHow: how,
  });
  console.log(`▶ ${cardId} → ${argvCmd.join(" ")} (model ${model}) · brief `
    + `${brief.length} bytes · diff ${diff.files.length} file(s) vs ${how}`);

  // (c) pipe it in, capture stdout, no shell
  const started = Date.now();
  const r = spawnSync(bin, argvCmd.slice(1), {
    cwd: c.root, input: brief, encoding: "utf8", shell: false,
    timeout: Math.round(timeoutS * 1000), maxBuffer: 32 << 20, env: childEnv,
  });
  const secs = ((Date.now() - started) / 1000).toFixed(1);
  const tail = (s) => (s || "").trim().split("\n").slice(-8).join("\n   ");
  if (r.error && (r.error.code === "ETIMEDOUT" || /timed?\s?out/i.test(r.error.message))) {
    return die(`${argvCmd[0]} exceeded review.external.${found}.timeout_s = ${timeoutS}s `
      + `(killed at ${secs}s)`, "Raise timeout_s, or point it at a faster model.",
      r.stderr ? `stderr tail:\n   ${tail(r.stderr)}` : "no stderr");
  }
  if (r.error) return die(`${argvCmd[0]} could not be run: ${r.error.message}`);
  if (r.status !== 0) {
    return die(`${argvCmd[0]} exited ${r.status} after ${secs}s — no card was produced`,
      "Usually authentication or quota. Run the command by hand once; vteam does",
      "not manage external CLI credentials.",
      r.stderr ? `stderr tail:\n   ${tail(r.stderr)}` : "no stderr");
  }
  const notes = [];
  const body = unwrap(r.stdout ?? "", notes);
  for (const n of notes) console.log(`   note: ${n}`);
  if (!body) {
    return die(`${argvCmd[0]} printed nothing on stdout after ${secs}s`,
      "The card must go to STDOUT — a tool that writes files or only logs to",
      "stderr cannot be a vteam reviewer as configured.",
      r.stderr ? `stderr tail:\n   ${tail(r.stderr)}` : "no stderr");
  }

  // (d) VALIDATE the composed section exactly as review_check will parse it —
  // including the split-by-heading behaviour, so a stray "### R3 notes" inside
  // the body cannot quietly shear the card in half at push time.
  const section = buildSection({
    cardId, model, argv: argvCmd, body, ticket, diffHow: how, nFiles: diff.files.length,
  });
  const parsed = parseCards(section);
  const foreign = Object.keys(parsed).filter((k) => k !== cardId);
  if (foreign.length) {
    return die(`the ${cardId} output contains card heading(s) for ${foreign.join(", ")} `
      + "— one run writes ONE card",
      "Headings matching review_check's card pattern (## … R<n>) split the card.",
      "Ask the tool for a single card with no R-numbered sub-headings.");
  }
  const frags = parsed[cardId] ?? [section];
  let best = null;
  for (const f of frags) {
    const res = cardProblems(f, c.root);
    if (!res.probs.length) { best = res; break; }
    if (!best || res.probs.length < best.probs.length) best = res;
  }
  if (best.probs.length) {
    console.log(`❌ external_review: ${argvCmd[0]} (${model}) returned an INVALID `
      + `${cardId} card — ${best.probs.length} gap(s), nothing was written:`);
    for (const p of best.probs) console.log(`   - ${p}`);
    console.log("   The card is discarded on purpose: the push fence COUNTS cards, so a");
    console.log("   junk card would count as a review. Re-run, or review this card by hand.");
    console.log(`   What the tool printed (${body.length} bytes):`);
    for (const l of body.split("\n").slice(0, 20)) console.log(`   | ${l}`);
    if (body.split("\n").length > 20) console.log("   | …");
    return 1;
  }

  // (e) file it — this card only
  const evd = String(c.cfg("paths.evidence", "evd"));
  const rel = `${evd}/${ticket}/dev/review.md`;
  const abs = path.join(c.root, rel);
  fs.mkdirSync(path.dirname(abs), { recursive: true });
  const existed = fs.existsSync(abs);
  const before = existed ? fs.readFileSync(abs, "utf8") : `# Review dossier — ${ticket}\n\n`;
  const { text, replaced } = mergeCard(before, cardId, section);
  fs.writeFileSync(abs, text);

  // (f)
  console.log(`✅ ${replaced ? "replaced" : "wrote"} card ${cardId} (${best.verdict}, `
    + `model ${model}, ${secs}s) in ${rel}${existed ? "" : " (created)"}`);
  if (best.verdict === "REQUEST-CHANGES") {
    console.log("⚠  verdict is REQUEST-CHANGES — the round is NOT closed. Fix the");
    console.log("   findings, re-run the T4 gate, then re-run this reviewer.");
  }
  console.log(`   Now run the gate — it does not care who wrote the card:`);
  console.log(`     python3 .vteam/scripts/review_check.py ${ticket} --sha WORKTREE`);
  console.log(`   and commit ${rel} with the code (pre-push reads it from the COMMIT).`);
  return best.verdict === "APPROVE" ? 0 : 2;
}

// ── selftest ─────────────────────────────────────────────────────────────────
function selftest() {
  const fails = [];
  const ok = (cond, msg) => { if (!cond) fails.push(msg); };

  // 1. MIRROR CONFORMANCE — review_check.py is the house of record. Every pattern
  // and threshold above must still exist there, verbatim.
  const rcPath = path.join(HERE, "review_check.py");
  ok(fs.existsSync(rcPath), `canonical grammar file missing: ${rcPath}`);
  if (fs.existsSync(rcPath)) {
    const rc = fs.readFileSync(rcPath, "utf8");
    for (const [name, lit] of Object.entries(PY)) {
      ok(rc.includes(lit), `MIRROR DRIFT: ${name} = ${JSON.stringify(lit)} no longer `
        + "appears in review_check.py — the gate's grammar changed, update PY here");
    }
  }

  const sh = (cwd, ...args) => {
    const r = spawnSync(args[0], args.slice(1), { cwd, encoding: "utf8" });
    if (r.status !== 0) throw new Error(`${args.join(" ")}: ${r.stderr || r.stdout}`);
    return (r.stdout || "").trim();
  };
  const run = (cwd, ...args) =>
    spawnSync(process.execPath, [SELF, ...args], { cwd, encoding: "utf8" });

  const tmp = fs.mkdtempSync(path.join(os.tmpdir(), "vteam-extrev-selftest-"));
  try {
    // ── fixture repo: a real branch with a real diff vs main ─────────────────
    const root = tmp;
    sh(root, "git", "init", "-q", "-b", "main", ".");
    sh(root, "git", "config", "user.email", "t@t.t");
    sh(root, "git", "config", "user.name", "t");
    fs.mkdirSync(path.join(root, "src"));
    fs.mkdirSync(path.join(root, "docs", "team"), { recursive: true });
    fs.writeFileSync(path.join(root, "src", "a.js"), "export const a = 1;\n");
    fs.writeFileSync(path.join(root, "docs", "team", "review-standard.md"),
      "# Reviewer standard\nAPPROVE means I tried to break it and failed.\n");
    // the fake external tools — each CONSUMES stdin (a reviewer that ignores the
    // brief is exactly the failure mode we must be able to see) and prints a card
    const tools = path.join(root, "tools");
    fs.mkdirSync(tools);
    const fake = (name, cardBody, { sleep = 0, exit = 0 } = {}) => {
      const p = path.join(tools, name);
      fs.writeFileSync(p, "const fs=require('fs');\n"
        + "const brief=fs.readFileSync(0,'utf8');\n"
        + "if(!brief.includes('VTEAM EXTERNAL REVIEW BRIEF')){console.error('no brief on stdin');process.exit(9);}\n"
        + "if(!brief.includes('Reviewer standard')){console.error('brief lacks the review standard');process.exit(9);}\n"
        + "if(!brief.includes('src/a.js')){console.error('brief lacks the diff');process.exit(9);}\n"
        + (sleep ? `const t=Date.now();while(Date.now()-t<${sleep}){}\n` : "")
        + `process.stdout.write(${JSON.stringify(cardBody)});\n`
        + `process.exit(${exit});\n`);
      return ["node", p];
    };
    const GOOD = "APPROVE\nTried to break:\n"
      + "- ran `node --check src/a.js` — clean\n"
      + "- fed an empty export via `node -e` at src/a.js:1 — no throw\n"
      + "- grepped every caller of `a` — single definition\n"
      + "Traces: src/a.js:1, `node --check src/a.js`\n";
    const TWO_BULLETS = "APPROVE\nTried to break:\n"
      + "- ran `node --check src/a.js` — clean\n"
      + "- read src/a.js:1 — fine\n"
      + "Traces: src/a.js:1, `node --check src/a.js`\n";
    const GHOST = GOOD.replace(/src\/a\.js/g, "src/imaginary.js");
    const NO_LOC = "APPROVE\nTried to break:\n- ran `node --check src/a.js`\n"
      + "- ran `node -e 1 + 1`\n- ran `ls -la src/`\nTraces: `node --check src/a.js`\n";
    const SMUGGLED = GOOD + "\n### R3 — architecture\nAPPROVE\n";
    const FENCED = "```markdown\n## R2 — my own heading\n" + GOOD + "```\n";
    const CHANGES = "REQUEST-CHANGES\nFindings:\n"
      + "- CONFIRMED: src/a.js:1 — exports a constant nobody reads "
      + "(repro: `grep -rn \"a\" src/`)\nTraces: src/a.js:1, `grep -rn a src/`\n";

    const cfg = (external) => fs.writeFileSync(path.join(root, "vteam.config.yaml"),
      "version: 1\nproject:\n  key: PROJ\n"
      + "paths:\n  evidence: evd\n  team: docs/team\n"
      + "git:\n  protected_branch: main\n"
      + "review:\n  reviewers: 2\n" + external);
    const extBlock = (id, argv, extra = "") =>
      `  external:\n    ${id}:\n      command: [${argv.join(", ")}]\n`
      + `      model: fake-model-1\n${extra}`;

    cfg(extBlock("r2", fake("good.js", GOOD)));
    sh(root, "git", "add", "-A");
    sh(root, "git", "commit", "-qm", "init");

    // (i) NOTHING TO REVIEW — main == base, empty index
    let r = run(root, "PROJ-1", "R2");
    ok(r.status === 1, `empty diff must exit 1, got ${r.status}\n${r.stdout}${r.stderr}`);
    ok(/nothing to review/.test(r.stdout), `empty diff must say so:\n${r.stdout}`);

    // give the fixture a reviewable diff on a ticket branch
    sh(root, "git", "switch", "-q", "-c", "feat/PROJ-1-thing");
    fs.writeFileSync(path.join(root, "src", "a.js"), "export const a = 2;\n");
    sh(root, "git", "add", "-A");
    sh(root, "git", "commit", "-qm", "feat(PROJ-1): bump");

    const reviewMd = path.join(root, "evd", "PROJ-1", "dev", "review.md");

    // (ii) GREEN — a valid card is written, stamped, and exits 0
    r = run(root, "PROJ-1", "R2");
    ok(r.status === 0, `valid card must exit 0, got ${r.status}\n${r.stdout}${r.stderr}`);
    ok(fs.existsSync(reviewMd), "card file was not created");
    let text = fs.existsSync(reviewMd) ? fs.readFileSync(reviewMd, "utf8") : "";
    ok(/^## R2 — external \(fake-model-1\)$/m.test(text), `heading missing:\n${text}`);
    ok(/^MODEL: fake-model-1$/m.test(text), "MODEL stamp missing");
    ok(/^TOOL: external$/m.test(text), "TOOL stamp missing");
    ok(/now run/i.test(r.stdout) && /review_check\.py/.test(r.stdout),
      `must point at review_check:\n${r.stdout}`);
    // the stamps must not manufacture traces: strip the tool body, and what is
    // left must FAIL the trace bar on its own
    const stampsOnly = text.slice(text.indexOf("## R2")).split("\nAPPROVE")[0];
    ok(cardProblems(stampsOnly, root).probs.length > 0,
      "the stamp block alone passes validation — the header is grading itself");

    // (iii) an OTHER card must survive byte-for-byte
    const r1 = "## R1 — spec reviewer (claude)\nAPPROVE\nTried to break:\n"
      + "- ran `node --check src/a.js`\n- flipped the export at src/a.js:1\n"
      + "- grepped callers of `a` in src/\nTraces: src/a.js:1\n\n";
    fs.writeFileSync(reviewMd, `# Review dossier — PROJ-1\n\n${r1}`);
    const beforeSpans = splitSections(fs.readFileSync(reviewMd, "utf8"));
    r = run(root, "PROJ-1", "R2");
    ok(r.status === 0, `second write must exit 0:\n${r.stdout}${r.stderr}`);
    text = fs.readFileSync(reviewMd, "utf8");
    const afterSpans = splitSections(text);
    const r1Of = (t) => (splitSections(t).spans.find((s) => s.id === "R1") || { text: "" }).text;
    const beforeR1 = beforeSpans.spans.find((s) => s.id === "R1").text;
    const afterR1 = (afterSpans.spans.find((s) => s.id === "R1") || { text: "" }).text;
    ok(afterR1 === beforeR1, "R1 card changed while writing R2 — "
      + `byte-for-byte survival broken:\n${JSON.stringify(beforeR1)}\n`
      + `${JSON.stringify(afterR1)}`);
    ok(text.includes("# Review dossier — PROJ-1"), "file preamble was dropped");
    ok(Object.keys(parseCards(text)).sort().join(",") === "R1,R2",
      `dossier should hold exactly R1+R2, got ${Object.keys(parseCards(text))}`);

    // (iv) IDEMPOTENT REPLACE — re-running R2 replaces, never duplicates
    r = run(root, "PROJ-1", "R2");
    ok(r.status === 0 && /replaced card R2/.test(r.stdout),
      `re-run must REPLACE the R2 card:\n${r.stdout}`);
    text = fs.readFileSync(reviewMd, "utf8");
    ok((parseCards(text).R2 || []).length === 1,
      `R2 duplicated: ${(parseCards(text).R2 || []).length} fragments`);
    ok(r1Of(text) === beforeR1, "R1 changed during an R2 replace");

    // ── mutations: every one of these must go RED and write NOTHING ──────────
    const snapshot = fs.readFileSync(reviewMd, "utf8");
    const mustRed = (label, external, cardArg = "R2", expect = null) => {
      cfg(external);
      const rr = run(root, "PROJ-1", cardArg);
      ok(rr.status === 1, `${label}: expected exit 1, got ${rr.status}\n${rr.stdout}${rr.stderr}`);
      if (expect) ok(expect.test(rr.stdout), `${label}: message must name the cause:\n${rr.stdout}`);
      ok(fs.readFileSync(reviewMd, "utf8") === snapshot,
        `${label}: the dossier was modified by a REFUSED run`);
      return rr;
    };
    mustRed("2 tried-bullets", extBlock("r2", fake("two.js", TWO_BULLETS)),
      "R2", /needs ≥3/);
    mustRed("no file:line trace", extBlock("r2", fake("noloc.js", NO_LOC)),
      "R2", /no file:line trace/);
    mustRed("fabricated citation", extBlock("r2", fake("ghost.js", GHOST)),
      "R2", /src\/imaginary\.js/);
    mustRed("smuggled second card", extBlock("r2", fake("smug.js", SMUGGLED)),
      "R2", /R3/);
    mustRed("empty stdout", extBlock("r2", fake("mute.js", "")),
      "R2", /printed nothing on stdout/);
    mustRed("tool exits non-zero", extBlock("r2", fake("boom.js", GOOD, { exit: 3 })),
      "R2", /exited 3/);
    mustRed("binary absent", extBlock("r2", ["vteam-no-such-reviewer-binary"]),
      "R2", /no such executable on PATH/);
    mustRed("no external config for the id", extBlock("r2", fake("good.js", GOOD)),
      "R3", /review\.external\.r3/);
    mustRed("model not declared",
      `  external:\n    r2:\n      command: [node, ${path.join(tools, "good.js")}]\n`,
      "R2", /model is missing/);
    mustRed("quoted command string",
      `  external:\n    r2:\n      command: "codex exec --x \\"a b\\""\n      model: m\n`,
      "R2", /quote character/);
    mustRed("timeout", extBlock("r2", fake("slow.js", GOOD, { sleep: 1500 }),
      "      timeout_s: 1\n"), "R2", /timeout_s = 1s/);
    // a brief without the review standard is not a brief — refuse, don't improvise
    cfg(extBlock("r2", fake("good.js", GOOD)));
    const stdAbs = path.join(root, "docs", "team", "review-standard.md");
    const stdText = fs.readFileSync(stdAbs, "utf8");
    fs.rmSync(stdAbs);
    r = run(root, "PROJ-1", "R2");
    ok(r.status === 1 && /review-standard\.md is missing/.test(r.stdout),
      `a missing review standard must refuse, not brief without it:\n${r.stdout}`);
    ok(fs.readFileSync(reviewMd, "utf8") === snapshot,
      "missing review standard: the dossier was modified by a REFUSED run");
    fs.writeFileSync(stdAbs, stdText);

    // (v) REQUEST-CHANGES is a legitimate verdict: card written, exit 2 (distinct)
    cfg(extBlock("r2", fake("nope.js", CHANGES)));
    r = run(root, "PROJ-1", "R2");
    ok(r.status === 2, `REQUEST-CHANGES must exit 2 (card written, round open), `
      + `got ${r.status}\n${r.stdout}${r.stderr}`);
    ok(/REQUEST-CHANGES/.test(fs.readFileSync(reviewMd, "utf8")),
      "REQUEST-CHANGES card was not filed");

    // (vi) fenced output + the tool's own heading are unwrapped, not rejected
    cfg(extBlock("r2", fake("fenced.js", FENCED)));
    r = run(root, "PROJ-1", "R2");
    ok(r.status === 0, `fenced output should be unwrapped:\n${r.stdout}${r.stderr}`);
    text = fs.readFileSync(reviewMd, "utf8");
    ok(!/```/.test(text), "the outer fence leaked into the dossier");
    ok(parseCards(text).R2.length === 1, "unwrapping left a duplicate heading");

    // (vii) STAGED-only work is reviewable (no commit needed), unstaged is flagged
    cfg(extBlock("r2", fake("good.js", GOOD)));
    sh(root, "git", "add", "vteam.config.yaml"); // keep the fixture's own churn out of the assertion
    fs.writeFileSync(path.join(root, "src", "a.js"), "export const a = 4;\n");
    r = run(root, "PROJ-1", "R2");
    ok(/UNSTAGED/.test(r.stdout) && /src\/a\.js/.test(r.stdout),
      `the unstaged file must be NAMED:\n${r.stdout}`);
    fs.writeFileSync(path.join(root, "src", "b.js"), "export const b = 3;\n");
    sh(root, "git", "add", "src/a.js", "src/b.js");
    r = run(root, "PROJ-1", "R2");
    ok(r.status === 0 && !/UNSTAGED/.test(r.stdout),
      `staged-only work must review clean:\n${r.stdout}${r.stderr}`);
    ok(/DIFF: 2 file\(s\)/.test(fs.readFileSync(reviewMd, "utf8")),
      `the staged-only file never reached the reviewed diff:\n${r.stdout}`);
  } finally {
    fs.rmSync(tmp, { recursive: true, force: true });
  }

  if (fails.length) {
    console.log(`external_review selftest: FAILED (${fails.length})`);
    for (const f of fails) console.log(`  - ${f}`);
    process.exit(1);
  }
  console.log("external_review selftest: OK (grammar mirrors review_check.py verbatim; "
    + "valid card written + stamps + R1 survives byte-for-byte + idempotent replace + "
    + "fence/heading unwrap + staged-only diff green; 12 mutations red — 2-bullet card, "
    + "no file:line, fabricated citation, smuggled R3, empty stdout, non-zero exit, "
    + "missing binary, unconfigured card id, undeclared model, quoted command string, "
    + "timeout, missing review-standard; every refusal left the dossier byte-identical)");
}

const isMain = process.argv[1]
  && import.meta.url === pathToFileURL(path.resolve(process.argv[1])).href;
if (isMain) {
  try {
    if (process.argv.includes("--selftest")) selftest();
    else process.exit(main(process.argv.slice(2)));
  } catch (e) {
    console.log(`❌ external_review: ${e.message}`);
    process.exit(1);
  }
}

export { PY, parseCards, splitSections, cardProblems, resolveCommand, whichBin, mergeCard };
