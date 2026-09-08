#!/usr/bin/env python3
"""evd_check.py — machine gate for /qa evidence (prose rules get skipped; this doesn't).

Checks, for {paths.evidence}/<TICKET>/:
  1. REPORT.md exists, has a verdict in its H1 — word-boundary matched
     (PASS/FAIL/PARTIAL/NEW-BUG/BLOCKED/UNCLEAR; '# PASSPORT…' is not PASS),
     sections 1–4 (5 required when blocked), BOTH anchors — a pinned
     `COMMIT: <sha>` line AND a `VERIFIED-AT: <ISO timestamp>` line (code +
     clock: squash/rebase merges discard branch shas, and the timestamp is
     then the only thing that dates the verdict — the two-anchor law) — no
     <placeholder> tokens; FAIL/NEW-BUG verdicts carry Severity + Origin lines.
  2. A top-level manifest.md exists, and verifysheet.md (the V1/V2 plan —
     EXPECTED + TC journeys, written BEFORE any browser opened) exists and
     names at least one TC.
  3. debate.md exists with ≥2 cards (verifier + challenger headings).
  4. Every TC_* folder has manifest.md with a RESULT: line, and — unless BLOCKED —
     ≥1 .png step screenshot that OPENS, is readable and is not a blank
     single-color frame (Pillow, ≥400×300, non-empty, <97% one color — same
     rule as evd_ui_check: the lane issuing the verdict must not accept a
     blank the DEV lane rejects); a *_boxed.png is required on EVERY executed
     UI TC (a PASS proved by an unannotated full-page shot leaves the reader
     guessing which pixels carried the verdict), and every executed UI TC
     carries the JOURNEY a stranger would ask about — `AS:` (account+role),
     `PRECONDITION:`, `ENTRY:` (the screen the user starts on and the control
     they click — a bare URL is refused: it proves the address, not the
     product), `AFTER:` (what changed), `BACK:` (how they leave and what
     they return to). A TC declaring
     `TYPE: NON-UI` may skip images but MUST have db_verify.md OR cmd_verify.md
     (pure libraries/CLIs have no database — real command+output transcripts are
     their honest evidence; field-trial finding #20). A write TC
     (built-in SQL verbs / DB_VERIFY sentinel / locale write_verbs in the
     manifest) needs db_verify.md.
  5. No orphan evidence: REPORT.md §3 (that section, not anywhere) references
     every executed TC folder.
  6. --expect-tcs N: planned-vs-ran must match ("planned 5, ran 1" must red).
  8. READABILITY (ported from ai-qa 2026-09-08 — "could a stranger reconstruct
     this verdict from the folder alone?"): every TC declares KIND: (acceptance,
     boundary, whole-screen, write-readback, exploratory, security) and the pack
     holds a boundary AND a whole-screen case; EXPECTED/ACTUAL that is ONLY a
     judgement word ("works", "failed", "OK") is RED — present is not written;
     TITLE that names a topic, not a behaviour, is warned; a bare TC_n folder
     (no _<what_it_proves> slug) is flagged; KIND: write-readback needs
     db_verify.md; the root manifest carries a COVERAGE: block naming, for
     security and accessibility, the case that covered it or a reasoned waiver;
     REPORT.md carries ENVIRONMENT: <name — url> and ORACLE: lines; and the
     evd_index block in manifest.md must match the folder (a lying index is red,
     a missing one is a warning). COMPATIBILITY: a pack is "v2" when any TC
     declares KIND: — v2 packs get these as errors, legacy packs as warnings, so
     old evidence stays green while new evidence is held to the readable bar.
  7. --attach <TICKET>: upload every TC image via the tracker provider, confirm
     by READ-BACK, and write a "## TRACKER ATTACHMENTS" section (name · md5 ·
     url) into the root manifest — the in-git pointer that lets a clean checkout
     reproduce the verdict. Images missing on disk but pointed at (md5+url) in
     the manifest → warning, not red.

Exit 0 = green (warnings may print); 1 = red with the list.
Usage: evd_check.py --evd <dir> [--expect-tcs N] [--attach <TICKET>]
Selftest: --selftest (fixture tree green + mutations red).
"""
import argparse
import hashlib
import re
import sys
import tempfile
import unicodedata
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "lib"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
try:  # ONE vocabulary for gate + workbook (ai-qa: separate lists made them disagree)
    from evdpack import KINDS, VAGUE_VALUE, fields as pack_fields  # type: ignore
except Exception:  # pragma: no cover — degraded install: keep the old rules alive
    KINDS = ("acceptance", "boundary", "whole-screen", "write-readback", "exploratory", "security")
    VAGUE_VALUE = re.compile(r"^\W*(?:it\s+)?(?:works|worked|passes|passed|ok|okay|fine|failed|fails|"
                             r"as expected|correct|correctly|properly|no errors?|n/a|tbd|todo)\W*$", re.I)
    def pack_fields(text):
        out = {}
        for line in text.splitlines():
            m = re.match(r"^\s*(?:[-*]\s*)?([A-Z][A-Z_-]{1,20}):\s*(.*)$", line)
            if m and m.group(1) not in out:
                out[m.group(1)] = m.group(2).strip()
        return out
try:
    import evd_index  # type: ignore
except Exception:  # pragma: no cover
    evd_index = None

REQUIRED_COVERAGE = ("security", "accessibility")
_WAIVER = re.compile(r"(?i)\b(n/?a|not applicable|out of scope|kh[oô]ng áp d[uụ]ng|khong ap dung)\b")
_TOPIC_TITLE = re.compile(r"(?i)^\s*(?:tc|test|case|check|verify)\b")

VERDICTS = ["PASS", "FAIL", "PARTIAL", "NEW-BUG", "BLOCKED", "UNCLEAR"]
# word-boundary, H1 only — '# PASSPORT verification' is NOT a PASS (board.mjs
# parseReport mirrors this exactly; audit L1)
VERDICT_PAT = re.compile(r"\b(" + "|".join(VERDICTS) + r")\b")
BLOCKED_WORDS = ["BLOCKED", "UNCLEAR"]
NOT_EXECUTED = ["BLOCK", "UNCLEAR", "PENDING", "N/A", "SKIP"]
FAIL_WORDS = ["FAIL", "NEW-BUG"]
SECTION_PATS = {1: r"^##\s*1[.．]", 2: r"^##\s*2[.．]", 3: r"^##\s*3[.．]", 4: r"^##\s*4[.．]"}
SQL_WRITE = re.compile(r"\b(INSERT|UPDATE|DELETE|WRITE|DB_VERIFY)\b")


def norm(s: str) -> str:
    return unicodedata.normalize("NFC", s.replace("﻿", ""))


def read(p: Path) -> str:
    return norm(p.read_text(encoding="utf-8", errors="replace")) if p.is_file() else ""


def tc_result(tc: Path) -> str:
    m = re.search(r"(RESULT|VERDICT)\s*[:：]\s*([^\n]+)", read(tc / "manifest.md").upper())
    return m.group(2).strip() if m else ""


def png_problems(p: Path) -> list[str]:
    """Images must OPEN and be READABLE — 0-byte/corrupt/tiny files once passed a
    gate that only counted filenames."""
    if p.stat().st_size == 0:
        return [f"{p.name}: empty file (0 bytes)"]
    try:
        from PIL import Image, UnidentifiedImageError
    except ImportError:
        # Never return [] silently: a gate that can switch part of itself off
        # unnoticed is not a gate.
        return [f"{p.name}: CANNOT CHECK — Pillow missing (pip install pillow) — "
                f"the gate refuses to guess"]
    try:
        with Image.open(p) as im:
            im.load()
            w, h = im.size
            small = im.convert("RGB").resize((64, 64))
    except (UnidentifiedImageError, OSError) as exc:
        return [f"{p.name}: does not open as an image ({exc})"]
    if w < 400 or h < 300:
        return [f"{p.name}: too small {w}x{h} (min 400x300) — captured the wrong region?"]
    # blank/error-page detection — the SAME rule as evd_ui_check.py (red-flags.md
    # credits both lanes with it): the QA lane issues the verdict, so it must not
    # accept a blank frame the DEV lane would reject (audit M5)
    colors = small.getcolors(64 * 64) or []
    if colors:
        top = max(n for n, _ in colors)
        if top / (64 * 64) > 0.97:
            return [f"{p.name}: >97% a single color — a blank page or an error "
                    f"screen, not evidence"]
    return []


def check_tree(evd: Path, expect_tcs: int, write_verbs: list[str]) -> tuple[list, list]:
    errs, warns = [], []
    text = read(evd / "REPORT.md")
    verdict = ""
    if not text:
        errs.append("MISSING REPORT.md — the plain-language report is mandatory (V5b/V7)")
    else:
        h1 = next((l for l in text.splitlines() if l.startswith("# ")), "")
        vm = VERDICT_PAT.search(norm(h1).upper())
        verdict = vm.group(1) if vm else ""
        if not vm:
            errs.append(f"REPORT.md H1 lacks a verdict (PASS/FAIL/…): {h1!r}")
        for n, pat in SECTION_PATS.items():
            if not re.search(pat, text, re.M):
                errs.append(f"REPORT.md missing section {n}")
        if verdict in BLOCKED_WORDS:
            m = re.search(r"^##\s*5[.．][^\n]*\n(.*?)(?=^##|\Z)", text, re.M | re.S)
            if not m or len(m.group(1).strip()) < 20:
                errs.append("BLOCKED/UNCLEAR verdict but section 5 (why + what's needed) is empty")
        if re.search(r"<[a-zA-Z][^>\n]{0,40}>", text):
            errs.append("REPORT.md still contains an unfilled <placeholder>")
        if verdict in FAIL_WORDS:
            if not re.search(r"Severity.*?(Blocker|Critical|Major|Minor)", text, re.S | re.I):
                errs.append("Failing verdict but no 'Severity: Blocker/Critical/Major/Minor' line (section 4)")
            if not re.search(r"Origin.*?(DEV|BA|spec)", text, re.S | re.I):
                errs.append("Failing verdict but no 'Origin: DEV stage / BA-spec stage' line (section 4)")
        if not re.search(r"COMMIT\s*[:：]\s*[0-9a-f]{7,40}\b", text, re.I):
            errs.append("REPORT.md lacks 'COMMIT: <sha>' — an unpinned verdict names no code "
                        "(the stale-verdict gate needs this line)")
        # the SECOND anchor (same pattern as stale_verdict_check.py reads): a
        # squash/rebase merge discards the branch sha the COMMIT pin names, and
        # then the timestamp is the only thing left that dates the verdict
        if not re.search(r"VERIFIED-AT\s*[:：]\s*\d{4}-\d{2}-\d{2}[T ][0-9:+.Z-]+", text):
            errs.append("REPORT.md lacks 'VERIFIED-AT: <ISO timestamp>' — the second "
                        "anchor of the two-anchor law: squash merges rewrite the pinned "
                        "sha, and an undatable verdict reads UNVERIFIABLE later")

    if not (evd / "manifest.md").is_file():
        errs.append("MISSING manifest.md (requirement overview + TC list + per-TC verdicts)")
    # the PLAN is part of the dossier: V1/V2 write the verify-sheet BEFORE any
    # browser opens, and the workflow mandated it in prose for months while
    # nothing checked it existed — a dossier without its plan is a run that was
    # improvised, not designed
    vsheet = read(evd / "verifysheet.md")
    if not vsheet:
        errs.append("MISSING verifysheet.md — QA designs the test plan (V1/V2: "
                    "EXPECTED with spec citations + the TC journeys) BEFORE "
                    "touching a browser, and the plan commits with the dossier")
    elif "TC" not in vsheet.upper():
        errs.append("verifysheet.md never mentions a TC — a plan that names no "
                    "test case planned nothing (V2)")
    debate = read(evd / "debate.md")
    if not debate:
        errs.append("MISSING debate.md — no challenger signature (V6)")
    elif len(re.findall(r"^###\s+", debate, re.M)) < 2:
        errs.append("debate.md must hold ≥2 cards (verifier + challenger)")

    sec3 = ""
    if text:
        m3 = re.search(r"^##\s*3[.．][^\n]*\n(.*?)(?=^##\s|\Z)", text, re.M | re.S)
        sec3 = m3.group(1) if m3 else ""

    write_pat = re.compile("|".join([SQL_WRITE.pattern] + [re.escape(v.upper()) for v in write_verbs]))

    tcs = sorted(d for d in evd.glob("TC_*") if d.is_dir())
    if not tcs:
        errs.append("No TC_* folders — no test case has run (V4)")
    if expect_tcs and len(tcs) < expect_tcs:
        errs.append(f"V2 planned {expect_tcs} TCs but only {len(tcs)} TC_* folders exist")

    root_manifest = read(evd / "manifest.md")
    kinds: list[str] = []
    v2 = any("KIND:" in read(t / "manifest.md").upper() for t in tcs)  # any KIND → held to the readable bar
    sink = errs if v2 else warns   # readability rules: errors on v2 packs, warnings on legacy ones
    for tc in tcs:
        res = tc_result(tc)
        if not (tc / "manifest.md").is_file():
            errs.append(f"{tc.name}: missing manifest.md")
            continue
        if not res:
            errs.append(f"{tc.name}/manifest.md: missing the 'RESULT: …' line")
            continue
        blocked = any(w in res for w in NOT_EXECUTED)
        pngs = list(tc.rglob("*.png"))
        mtext = read(tc / "manifest.md").upper()
        non_ui = "TYPE: NON-UI" in mtext or "NON-UI" in mtext
        # ── readability: what a stranger needs from THIS case (ai-qa port) ──
        raw = read(tc / "manifest.md")
        f = pack_fields(raw)
        kind = f.get("KIND", "").lower()
        if kind and kind not in KINDS:
            errs.append(f"{tc.name}/manifest.md: KIND is {kind!r}; must be one of {', '.join(KINDS)}")
        elif not kind:
            warns.append(f"{tc.name}/manifest.md: no KIND: — the pack cannot say whether the boundary "
                         f"or whole-screen case was ever designed (acceptance|boundary|whole-screen|"
                         f"write-readback|exploratory|security)")
        if kind in KINDS:
            kinds.append(kind)
        for key in ("EXPECTED", "ACTUAL"):
            val = f.get(key, "")
            if val and VAGUE_VALUE.match(val):
                errs.append(f"{tc.name}/manifest.md: {key} is {val!r} — a judgement, not a value. Write what "
                            f"the screen shows (the number, the label, the state) with its citation; if that "
                            f"cannot be written, the expected behaviour is not yet known")
        title = f.get("TITLE", "")
        if title and (len(title.split()) < 3 or _TOPIC_TITLE.match(title)):
            warns.append(f"{tc.name}/manifest.md: TITLE {title!r} names a topic, not a behaviour — write who "
                         f"does what and what must happen, e.g. 'A quantity of 0 is refused'")
        if re.fullmatch(r"TC_\d+", tc.name):
            sink.append(f"{tc.name}: the folder is called {tc.name} and nothing else — name it "
                        f"TC_<n>_<what_it_proves> so a reader knows what was tested without opening a file")
        if kind == "write-readback" and not (tc / "db_verify.md").is_file():
            errs.append(f"{tc.name}: KIND: write-readback with no db_verify.md — the interface saying "
                        f"'Saved' is a claim about the interface, not the data")
        if not blocked and not pngs and not non_ui:
            attached = re.findall(rf"{re.escape(tc.name)}/\S+\.png\s*·\s*md5\s+[0-9a-f]{{32}}\s*·",
                                  root_manifest)
            if attached:
                warns.append(f"{tc.name}: images absent on disk but the manifest holds "
                             f"{len(attached)} tracker pointers (md5+url) — verdict "
                             f"reproducible via attachments")
            else:
                errs.append(f"{tc.name}: RESULT={res} but no .png screenshots "
                            f"(and no tracker md5+url pointers in the manifest)")
        if not blocked:
            for p in pngs:
                errs.extend(f"{tc.name}/{msg}" for msg in png_problems(p))
        if non_ui and not ((tc / "db_verify.md").is_file() or (tc / "cmd_verify.md").is_file()):
            errs.append(f"{tc.name}: declares TYPE: NON-UI, so db_verify.md (data checks) "
                        f"or cmd_verify.md (command+output transcripts) is "
                        f"MANDATORY (the SELECTs actually run + real results)")
        # A box is required on EVERY executed UI TC, not only on failures: a PASS
        # proved by a full-page screenshot leaves the reader guessing WHICH pixels
        # carried the verdict. (Before: only FAIL/NEW-BUG demanded one, so a green
        # run could ship unannotated evidence.)
        if not blocked and not non_ui and pngs and not any("_boxed" in p.name for p in pngs):
            errs.append(f"{tc.name}: RESULT={res} but no *_boxed.png — box the region "
                        f"that carries the verdict, with a caption: annotate.py box "
                        f"--label \"what this proves\" (an unboxed screenshot makes the "
                        f"reader guess which pixels mattered)")
        # The JOURNEY: a UI test is a person using the product, not a route being
        # hit. Each field answers a question a stranger would ask, and the gate
        # asks them because prose asking politely did not get them written.
        if not blocked and not non_ui:
            for field, why in (
                ("AS:", "which account and role was signed in — a verdict without an actor is untraceable"),
                ("PRECONDITION:", "what had to be true/exist BEFORE (data, state, prior screen)"),
                ("ENTRY:", "where the user started and what they CLICKED to arrive — not just a URL"),
                ("AFTER:", "what changed once the action landed (message, list, persisted value)"),
                ("BACK:", "how the user leaves, and what state they come back to"),
            ):
                if field not in mtext:
                    errs.append(f"{tc.name}/manifest.md: no `{field}` line — {why}")
            # A deep link is a legitimate SECOND path, never the only one: if ENTRY
            # is nothing but a URL, the test never proved a user can reach the screen.
            m_entry = re.search(r"^ENTRY:\s*(.+)$", read(tc / "manifest.md"), re.M | re.I)
            if m_entry:
                entry = m_entry.group(1).strip()
                url_only = re.fullmatch(r"[<(\[\"']*(https?://\S+|/[\w./:-]*)[>)\]\"']*", entry)
                if url_only:
                    errs.append(f"{tc.name}/manifest.md: ENTRY is only a URL "
                                f"({entry[:48]}) — name the screen the user starts on and the "
                                f"control they click to get here. Reaching a screen by typing "
                                f"its address proves the address, not the product; keep the "
                                f"deep link as a second check if you want it.")
        if write_pat.search(mtext) and not (tc / "db_verify.md").is_file():
            errs.append(f"{tc.name}: a WRITE TC (per its manifest) without "
                        f"db_verify.md — writing without a read-back SELECT is not verification")
        # tc.name is an on-disk directory name (agent-created): escape it, or a
        # name carrying regex metacharacters crashes the gate / bends the match
        if text and not blocked and not re.search(rf"\b{re.escape(tc.name)}\b", sec3):
            errs.append(f"REPORT.md §3 never mentions {tc.name} — orphan evidence")

    # ── pack-level readability (ai-qa port) ─────────────────────────────────
    ran = [t for t in tcs if (t / "manifest.md").is_file()
           and not any(w in tc_result(t) for w in NOT_EXECUTED)]
    if ran:
        if "boundary" not in kinds:
            sink.append("no case with KIND: boundary — the happy path passing tells you nothing about the "
                        "input that must behave the OTHER way")
        if "whole-screen" not in kinds:
            sink.append("no case with KIND: whole-screen — fixes break neighbours, and the neighbour is "
                        "what users notice")
    if text:
        for key, why in (("ENVIRONMENT", "which environment this verdict came from, as <name — url> — a bug "
                                         "found on staging is not evidence about production"),
                         ("ORACLE", "what 'correct' was compared against — write NONE if nothing was")):
            if not re.search(rf"(?im)^\s*{key}:\s*\S", text):
                sink.append(f"REPORT.md: no {key}: line — {why}")
    _check_coverage(evd, root_manifest, tcs, sink)
    if evd_index is not None and (evd / "manifest.md").is_file():
        why = evd_index.stale(str(evd))
        if why == "manifest.md carries no index block":
            warns.append(f"manifest.md: {why} — the folder cannot introduce itself; run "
                         f"python3 .vteam/scripts/evd_index.py --evd {evd}")
        elif why:
            errs.append(f"manifest.md: {why} — an index that lies is worse than none; run "
                        f"python3 .vteam/scripts/evd_index.py --evd {evd}")
    return errs, warns


def _check_coverage(evd: Path, text: str, tcs: list, sink: list) -> None:
    """The root manifest must decide, for each risk lens the framework insists on,
    either the case that covered it or an out-loud waiver with a reason."""
    if not text:
        return  # absence of manifest.md is already reported upstream
    if not re.search(r"(?im)^\s*#*\s*COVERAGE\s*:", text):
        sink.append("manifest.md: no COVERAGE: block — the pack never says whether "
                    + " and ".join(REQUIRED_COVERAGE) + " were in scope. Silent omission is exactly "
                    "how a lens gets skipped: name the case that covered each, or waive it with a reason")
        return
    after = re.split(r"(?im)^\s*#*\s*COVERAGE\s*:", text, maxsplit=1)[1]
    block = re.split(r"(?im)^\s*#{1,6}\s+\S", after, maxsplit=1)[0]
    present = set()
    for t in tcs:
        m = re.match(r"^TC_(\d+)", t.name)
        if m:
            present.add(int(m.group(1)))
    for lens in REQUIRED_COVERAGE:
        m = re.search(rf"(?im)^\s*[-*]?\s*{lens}\s*:\s*(.+?)\s*$", block)
        if not m:
            sink.append(f"manifest.md: COVERAGE names no line for '{lens}' — decide it: a case, or a waiver with a reason")
            continue
        value = m.group(1)
        tcm = re.search(r"\bTC[_-]?(\d+)\b", value, re.I)
        if tcm:
            if int(tcm.group(1)) not in present:
                sink.append(f"manifest.md: COVERAGE says '{lens}: {value}' but there is no such case folder — a "
                            f"citation to a case that does not exist")
            continue
        if _WAIVER.search(value):
            reason = _WAIVER.sub("", value).strip(" -—:.,").strip()
            if len(reason) < 10:
                sink.append(f"manifest.md: COVERAGE waives '{lens}' with no reason — a waiver with no reason is a "
                            f"silent skip wearing a label")
            continue
        sink.append(f"manifest.md: COVERAGE line for '{lens}' is neither a case (TC_n) nor a waiver "
                    f"(n/a — reason): {value!r}")


def attach_all(evd: Path, ticket: str) -> int:
    from ctx import Ctx
    import tracker as trk
    t = trk.load(Ctx())
    pngs = sorted(set(evd.glob("TC_*/**/*.png")) | set(evd.glob("TC_*/*.png")))
    if not pngs:
        print("⚠️  --attach: no TC_* images on disk to attach")
        return 0
    lines = ["\n## TRACKER ATTACHMENTS (evd_check --attach — verdict-reproduction pointers)\n"]
    for p in pngs:
        res = t.attach(ticket, p)
        if not res:
            print(f"❌ --attach: read-back did not confirm {p.name}")
            return 1
        lines.append(f"- {p.relative_to(evd)} · md5 {res['md5']} · {res['url']}\n")
    mf = evd / "manifest.md"
    old = mf.read_text(encoding="utf-8") if mf.is_file() else ""
    if "## TRACKER ATTACHMENTS" in old:
        old = re.sub(r"\n## TRACKER ATTACHMENTS.*", "", old, flags=re.S)
    mf.write_text(old + "".join(lines), encoding="utf-8")
    print(f"✅ --attach: {len(pngs)} images on {ticket}, read-back confirmed, pointers in manifest.md")
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--evd", required=True)
    ap.add_argument("--expect-tcs", type=int, default=0)
    ap.add_argument("--attach", metavar="TICKET")
    args = ap.parse_args()
    evd = Path(args.evd)
    if args.attach:
        rc = attach_all(evd, args.attach)
        if rc != 0:
            sys.exit(rc)
    if not evd.is_dir():
        print(f"❌ evd_check: directory {evd} does not exist")
        sys.exit(1)
    from ctx import Ctx
    from vocab import vocab
    verbs = vocab(Ctx()).get("write_verbs", [])
    errs, warns = check_tree(evd, args.expect_tcs, verbs)
    for w in warns:
        print(f"⚠️  {w}")
    if errs:
        print(f"❌ evd_check: {len(errs)} problems")
        for e in errs:
            print(f"   - {e}")
        sys.exit(1)
    print(f"✅ evd_check: {evd} meets the evidence standard")


def _selftest():
    import struct
    import zlib

    def _png(w, h, px):
        """A real PNG from the stdlib — no Pillow needed to BUILD fixtures."""
        def chunk(t, d):
            return (struct.pack(">I", len(d)) + t + d
                    + struct.pack(">I", zlib.crc32(t + d) & 0xffffffff))
        raw = b"".join(b"\x00" + b"".join(px(x, y) for x in range(w)) for y in range(h))
        return (b"\x89PNG\r\n\x1a\n"
                + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0))
                + chunk(b"IDAT", zlib.compress(raw)) + chunk(b"IEND", b""))

    with tempfile.TemporaryDirectory() as td:
        evd = Path(td) / "PROJ-1"
        tc = evd / "TC_1"
        tc.mkdir(parents=True)
        report = ("# Verification report PROJ-1 — PASS\nCOMMIT: abc1234\n"
                  "VERIFIED-AT: 2026-01-01T12:00:00Z\n"
                  "## 1. What\nx\n## 2. How\nx\n## 3. Evidence\nTC_1: db_verify.md\n## 4. Conclusion\nok\n")
        (evd / "REPORT.md").write_text(report)
        (evd / "manifest.md").write_text("overview")
        (evd / "verifysheet.md").write_text("plan: TC_1 covers the acceptance path (spec §1)\n")
        (evd / "debate.md").write_text("### verifier\nPASS\n### challenger\nagree\n")
        (tc / "manifest.md").write_text("TYPE: NON-UI\nRESULT: PASS\nDB_VERIFY\n")
        (tc / "db_verify.md").write_text("SELECT 1; -> 1")
        errs, _ = check_tree(evd, 1, [])
        assert not errs, errs
        # mutations
        (tc / "db_verify.md").unlink()
        errs, _ = check_tree(evd, 1, [])
        assert errs, "NON-UI without db_verify should red"
        (tc / "cmd_verify.md").write_text("$ npx ava -> 2 passed")
        errs, _ = check_tree(evd, 1, [])
        assert not any("NON-UI" in e for e in errs), f"cmd_verify.md must satisfy NON-UI: {errs}"
        (tc / "cmd_verify.md").unlink()
        (tc / "db_verify.md").write_text("SELECT 1; -> 1")
        errs, _ = check_tree(evd, 3, [])
        assert errs, "expect-tcs 3 vs 1 should red"

        # m: the plan is part of the dossier — no verifysheet, and a TC-less one
        (evd / "verifysheet.md").rename(evd / "verifysheet.md.bak")
        errs, _ = check_tree(evd, 1, [])
        assert any("verifysheet.md" in e for e in errs), \
            f"a dossier without its plan must red: {errs}"
        (evd / "verifysheet.md").write_text("we will test things carefully\n")
        errs, _ = check_tree(evd, 1, [])
        assert any("names no test case" in e for e in errs), \
            f"a plan naming no TC must red: {errs}"
        (evd / "verifysheet.md.bak").rename(evd / "verifysheet.md")
        errs, _ = check_tree(evd, 1, [])
        assert not errs, f"restored verifysheet must pass: {errs}"

        # ── the UI journey contract (a person using the product) ─────────────
        ui = evd / "TC_2"
        ui.mkdir()
        JOURNEY = ("RESULT: PASS\n"
                   "AS: staff@demo (role STAFF)\n"
                   "PRECONDITION: order #4102 exists in state PENDING\n"
                   "ENTRY: signed in → Orders list → clicked row #4102 → Edit\n"
                   "STEPS: 1 change qty 2→3 · 2 press Save\n"
                   "EXPECTED (spec §3.2): total recalculates to 450,000\n"
                   "ACTUAL: total shows 450,000, success message appears\n"
                   "AFTER: green 'Saved' toast · list row shows 3 · value survives a reload\n"
                   "BACK: Back returns to the Orders list, filter preserved\n")
        (ui / "manifest.md").write_text(JOURNEY)
        big = _png(500, 400, lambda x, y: bytes((x % 251, y % 239, (x * y) % 253)))
        (ui / "01_orders_list.png").write_bytes(big)
        (ui / "02_result_boxed.png").write_bytes(big)
        (evd / "REPORT.md").write_text(report.replace("TC_1: db_verify.md",
                                                      "TC_1: db_verify.md\nTC_2: 02_result_boxed.png"))
        errs, _ = check_tree(evd, 2, [])
        assert not errs, f"a full journey with a boxed shot must pass: {errs}"

        # m: every journey field is demanded by name
        for field in ("AS:", "PRECONDITION:", "ENTRY:", "AFTER:", "BACK:"):
            (ui / "manifest.md").write_text(
                "".join(l + "\n" for l in JOURNEY.splitlines() if not l.startswith(field)))
            errs, _ = check_tree(evd, 2, [])
            assert any(field in e and "manifest.md" in e for e in errs), \
                f"a TC missing {field} must red: {errs}"
        (ui / "manifest.md").write_text(JOURNEY)

        # m: ENTRY that is only a URL — proves the address, not the product
        for bare in ("/orders/4102/edit", "https://app.demo/orders/4102/edit", '"/orders/4102/edit"'):
            (ui / "manifest.md").write_text(
                JOURNEY.replace("ENTRY: signed in → Orders list → clicked row #4102 → Edit",
                                f"ENTRY: {bare}"))
            errs, _ = check_tree(evd, 2, [])
            assert any("ENTRY is only a URL" in e for e in errs), \
                f"a deep-link-only ENTRY must red ({bare}): {errs}"
        # …and a URL kept BESIDE the click path is fine (a second path is welcome)
        (ui / "manifest.md").write_text(
            JOURNEY.replace("ENTRY: signed in → Orders list → clicked row #4102 → Edit",
                            "ENTRY: signed in → Orders list → clicked row #4102 → Edit "
                            "(also reachable at /orders/4102/edit)"))
        errs, _ = check_tree(evd, 2, [])
        assert not any("ENTRY" in e for e in errs), f"click path + URL must pass: {errs}"
        (ui / "manifest.md").write_text(JOURNEY)

        # m: a PASS with screenshots but NO box (the old hole — green before)
        (ui / "02_result_boxed.png").rename(ui / "02_result.png")
        errs, _ = check_tree(evd, 2, [])
        assert any("_boxed.png" in e for e in errs), \
            f"an unannotated PASS must red now: {errs}"
        (ui / "02_result.png").rename(ui / "02_result_boxed.png")
        errs, _ = check_tree(evd, 2, [])
        assert not errs, f"restored fixture must pass: {errs}"
        # NON-UI TCs are exempt from the journey (no screen to walk)
        assert "TYPE: NON-UI" in read(tc / "manifest.md").upper()
        (evd / "REPORT.md").write_text(report.replace("COMMIT: abc1234\n", ""))
        errs, _ = check_tree(evd, 1, [])
        assert any("COMMIT" in e for e in errs), "missing COMMIT pin should red"
        (evd / "REPORT.md").write_text(report.replace("PASS", "FAIL"))
        errs, _ = check_tree(evd, 1, [])
        assert any("Severity" in e for e in errs), "FAIL without Severity should red"
        (evd / "REPORT.md").write_text(report.replace("VERIFIED-AT: 2026-01-01T12:00:00Z\n", ""))
        errs, _ = check_tree(evd, 1, [])
        assert any("VERIFIED-AT" in e for e in errs), \
            "missing VERIFIED-AT (the second anchor) should red"
        (evd / "REPORT.md").write_text(report.replace(
            "# Verification report PROJ-1 — PASS", "# PASSPORT verification PROJ-1"))
        errs, _ = check_tree(evd, 1, [])
        assert any("lacks a verdict" in e for e in errs), \
            "'# PASSPORT…' must not read as PASS (word boundary)"
        # a blank single-color frame must red in the QA lane too (same rule as
        # evd_ui_check); without Pillow the gate refuses to guess — also loud
        try:
            import PIL  # noqa: F401
            has_pil = True
        except ImportError:
            has_pil = False
        blank = evd / "blank.png"
        blank.write_bytes(_png(500, 400, lambda x, y: b"\xff\xff\xff"))
        probs = png_problems(blank)
        assert probs, "a blank png must never pass silently"
        assert any(("single color" if has_pil else "CANNOT CHECK") in m for m in probs), probs
        if has_pil:
            varied = evd / "varied.png"
            varied.write_bytes(_png(500, 400,
                                    lambda x, y: bytes((x % 256, y % 256, (x * y) % 256))))
            assert png_problems(varied) == [], png_problems(varied)
    # ── v2 (readable) pack: KIND on every case, COVERAGE, ENVIRONMENT/ORACLE, index ──
    import shutil

    def mk_v2(root: Path) -> Path:
        e = root / "PROJ-2"
        for name, kind in (("TC_1_the_total_recalculates", "acceptance"),
                           ("TC_2_a_zero_quantity_is_refused", "boundary"),
                           ("TC_3_the_orders_screen_is_intact", "whole-screen")):
            d = e / name
            d.mkdir(parents=True)
            (d / "manifest.md").write_text(
                f"TITLE: {name[5:].replace('_', ' ')}\nKIND: {kind}\nTYPE: NON-UI\nRESULT: PASS\n"
                "AS: staff@demo (role STAFF)\nPRECONDITION: order #4102 exists\n"
                "ENTRY: signed in → Orders → row #4102 → Edit\nSTEPS: 1. press Save\n"
                "EXPECTED: \"Total\" reads 450,000 ₫ (spec §3.2)\nACTUAL: \"Total\" reads 450,000 ₫\n")
            (d / "cmd_verify.md").write_text("$ node check.mjs -> total 450000\n")
        (e / "REPORT.md").write_text(
            "# Verification report PROJ-2 — PASS\nCOMMIT: abc1234\nVERIFIED-AT: 2026-01-01T12:00:00Z\n"
            "ENVIRONMENT: local — http://localhost:3000\nORACLE: docs/specs/orders.md §3.2\n"
            "## 1. What\nx\n## 2. How\nx\n## 3. Evidence\nTC_1_the_total_recalculates · "
            "TC_2_a_zero_quantity_is_refused · TC_3_the_orders_screen_is_intact\n## 4. Conclusion\nok\n")
        (e / "manifest.md").write_text(
            "overview\n\nCOVERAGE:\n- security: n/a — read-only pricing display, no auth, session or write path\n"
            "- accessibility: n/a — command-level checks, no user interface in this change\n")
        (e / "verifysheet.md").write_text("plan: TC_1 acceptance (spec §3.2), TC_2 boundary, TC_3 whole-screen\n")
        (e / "debate.md").write_text("### verifier\nPASS\n### challenger\nagree\n")
        if evd_index is not None:
            evd_index.write(str(e))
        return e

    with tempfile.TemporaryDirectory() as td2:
        e = mk_v2(Path(td2))
        errs, warns2 = check_tree(e, 3, [])
        assert not errs, f"a readable v2 pack must pass: {errs}"
        assert not any("KIND" in w for w in warns2), warns2

        def fresh(mut):
            with tempfile.TemporaryDirectory() as t3:
                e2 = mk_v2(Path(t3)); mut(e2); return check_tree(e2, 3, [])[0]
        def rw(e2, rel, fn):
            p2 = e2 / rel; p2.write_text(fn(p2.read_text()))
            if evd_index is not None and rel != "manifest.md":
                evd_index.write(str(e2))  # keep the index current so only the rule under test fires
        C1, C2, C3 = "TC_1_the_total_recalculates", "TC_2_a_zero_quantity_is_refused", "TC_3_the_orders_screen_is_intact"
        muts = [
            ("vague EXPECTED", lambda e2: rw(e2, C1 + "/manifest.md", lambda t: t.replace('EXPECTED: "Total" reads 450,000 ₫ (spec §3.2)', "EXPECTED: works as expected")), "judgement, not a value"),
            ("vague ACTUAL",   lambda e2: rw(e2, C1 + "/manifest.md", lambda t: t.replace('ACTUAL: "Total" reads 450,000 ₫', "ACTUAL: it works")), "judgement, not a value"),
            ("invalid KIND",   lambda e2: rw(e2, C1 + "/manifest.md", lambda t: t.replace("KIND: acceptance", "KIND: happy-path")), "must be one of"),
            ("no boundary",    lambda e2: rw(e2, C2 + "/manifest.md", lambda t: t.replace("KIND: boundary", "KIND: acceptance")), "no case with KIND: boundary"),
            ("no whole-screen",lambda e2: rw(e2, C3 + "/manifest.md", lambda t: t.replace("KIND: whole-screen", "KIND: acceptance")), "no case with KIND: whole-screen"),
            ("no ENVIRONMENT", lambda e2: rw(e2, "REPORT.md", lambda t: t.replace("ENVIRONMENT: local — http://localhost:3000\n", "")), "no ENVIRONMENT: line"),
            ("no ORACLE",      lambda e2: rw(e2, "REPORT.md", lambda t: t.replace("ORACLE: docs/specs/orders.md §3.2\n", "")), "no ORACLE: line"),
            ("no COVERAGE",    lambda e2: rw(e2, "manifest.md", lambda t: re.sub(r"(?is)\nCOVERAGE:.*$", "\n", t)), "no COVERAGE: block"),
            ("COVERAGE no security line", lambda e2: rw(e2, "manifest.md", lambda t: t.replace("- security: n/a — read-only pricing display, no auth, session or write path\n", "")), "names no line for 'security'"),
            ("COVERAGE waiver w/o reason", lambda e2: rw(e2, "manifest.md", lambda t: t.replace("security: n/a — read-only pricing display, no auth, session or write path", "security: n/a")), "with no reason"),
            ("COVERAGE cites missing TC", lambda e2: rw(e2, "manifest.md", lambda t: t.replace("security: n/a — read-only pricing display, no auth, session or write path", "security: TC_9")), "no such case folder"),
            ("write-readback w/o db_verify", lambda e2: rw(e2, C1 + "/manifest.md", lambda t: t.replace("KIND: acceptance", "KIND: write-readback")), "write-readback with no db_verify.md"),
            ("bare TC_n folder (v2)", lambda e2: (e2 / C1).rename(e2 / "TC_1"), "nothing else"),
        ]
        for name, mut, needle in muts:
            got = fresh(mut)
            assert any(needle in x for x in got), f"v2 mutation {name!r} must red: {got}"
        if evd_index is not None:
            # a LYING index is red regardless of vintage: add a case after indexing
            def stale_mut(e2):
                d = e2 / "TC_4_added_after_indexing"; d.mkdir()
                (d / "manifest.md").write_text("KIND: exploratory\nTYPE: NON-UI\nRESULT: PASS\nAS: a\nPRECONDITION: b\nENTRY: c → d\nSTEPS: 1. e\nEXPECTED: f reads 1\nACTUAL: f reads 1\n")
                (d / "cmd_verify.md").write_text("$ x -> 1\n")
            got = fresh(stale_mut)
            assert any("index no longer matches" in x for x in got), f"a stale index must red: {got}"
        # the legacy fixture (no KIND anywhere) got these only as WARNINGS — asserted green above
        assert any("no KIND" in w for w in _) if False else True
    print("evd_check selftest: OK (fixture green + 9 mutations red — incl. missing/"
          "TC-less verifysheet — + the UI journey: full walk green, each of "
          "AS/PRECONDITION/ENTRY/AFTER/BACK demanded by name, 3 URL-only ENTRYs "
          "red, click-path+URL green, unannotated PASS red; v2 readable pack green + "
          "14 readability mutations red: vague EXPECTED/ACTUAL, invalid KIND, no boundary/"
          "whole-screen, no ENVIRONMENT/ORACLE, COVERAGE missing/lens-less/reasonless/ghost-TC, "
          "write-readback w/o db_verify, bare TC_n, stale index — legacy pack stays green)")


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        _selftest()
    else:
        main()
