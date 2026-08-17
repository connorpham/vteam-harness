#!/usr/bin/env python3
"""evd_check.py — machine gate for /qa evidence (prose rules get skipped; this doesn't).

Checks, for {paths.evidence}/<TICKET>/:
  1. REPORT.md exists, has a verdict in its H1
     (PASS/FAIL/PARTIAL/NEW-BUG/BLOCKED/UNCLEAR), sections 1–4
     (5 required when blocked), a pinned `COMMIT: <sha>` line, no <placeholder>
     tokens; FAIL/NEW-BUG verdicts carry Severity + Origin lines.
  2. A top-level manifest.md exists.
  3. debate.md exists with ≥2 cards (verifier + challenger headings).
  4. Every TC_* folder has manifest.md with a RESULT: line, and — unless BLOCKED —
     ≥1 .png step screenshot that OPENS and is readable (Pillow, ≥400×300,
     non-empty); a *_boxed.png is required on FAIL/NEW-BUG TCs. A TC declaring
     `TYPE: NON-UI` may skip images but MUST have db_verify.md. A write TC
     (built-in SQL verbs / DB_VERIFY sentinel / locale write_verbs in the
     manifest) needs db_verify.md.
  5. No orphan evidence: REPORT.md §3 (that section, not anywhere) references
     every executed TC folder.
  6. --expect-tcs N: planned-vs-ran must match ("planned 5, ran 1" must red).
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

VERDICTS = ["PASS", "FAIL", "PARTIAL", "NEW-BUG", "BLOCKED", "UNCLEAR"]
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
            w, h = im.size
            im.verify()
    except (UnidentifiedImageError, OSError) as exc:
        return [f"{p.name}: does not open as an image ({exc})"]
    if w < 400 or h < 300:
        return [f"{p.name}: too small {w}x{h} (min 400x300) — captured the wrong region?"]
    return []


def check_tree(evd: Path, expect_tcs: int, write_verbs: list[str]) -> tuple[list, list]:
    errs, warns = [], []
    text = read(evd / "REPORT.md")
    verdict_h1 = ""
    if not text:
        errs.append("MISSING REPORT.md — the plain-language report is mandatory (V5b/V7)")
    else:
        h1 = next((l for l in text.splitlines() if l.startswith("# ")), "")
        verdict_h1 = norm(h1).upper()
        if not any(v in verdict_h1 for v in VERDICTS):
            errs.append(f"REPORT.md H1 lacks a verdict (PASS/FAIL/…): {h1!r}")
        for n, pat in SECTION_PATS.items():
            if not re.search(pat, text, re.M):
                errs.append(f"REPORT.md missing section {n}")
        if any(w in verdict_h1 for w in BLOCKED_WORDS):
            m = re.search(r"^##\s*5[.．][^\n]*\n(.*?)(?=^##|\Z)", text, re.M | re.S)
            if not m or len(m.group(1).strip()) < 20:
                errs.append("BLOCKED/UNCLEAR verdict but section 5 (why + what's needed) is empty")
        if re.search(r"<[a-zA-Z][^>\n]{0,40}>", text):
            errs.append("REPORT.md still contains an unfilled <placeholder>")
        if any(w in verdict_h1 for w in FAIL_WORDS):
            if not re.search(r"Severity.*?(Blocker|Critical|Major|Minor)", text, re.S | re.I):
                errs.append("Failing verdict but no 'Severity: Blocker/Critical/Major/Minor' line (section 4)")
            if not re.search(r"Origin.*?(DEV|BA|spec)", text, re.S | re.I):
                errs.append("Failing verdict but no 'Origin: DEV stage / BA-spec stage' line (section 4)")
        if not re.search(r"COMMIT\s*[:：]\s*[0-9a-f]{7,40}\b", text, re.I):
            errs.append("REPORT.md lacks 'COMMIT: <sha>' — an unpinned verdict names no code "
                        "(the stale-verdict gate needs this line)")

    if not (evd / "manifest.md").is_file():
        errs.append("MISSING manifest.md (requirement overview + TC list + per-TC verdicts)")
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
        if not blocked and not pngs and not non_ui:
            attached = re.findall(rf"{tc.name}/\S+\.png\s*·\s*md5\s+[0-9a-f]{{32}}\s*·",
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
        if non_ui and not (tc / "db_verify.md").is_file():
            errs.append(f"{tc.name}: declares TYPE: NON-UI, so db_verify.md is "
                        f"MANDATORY (the SELECTs actually run + real results)")
        if any(w in res for w in FAIL_WORDS) and not any("_boxed" in p.name for p in pngs):
            errs.append(f"{tc.name}: RESULT={res} but no *_boxed.png marking the "
                        f"divergence (annotate.py)")
        if write_pat.search(mtext) and not (tc / "db_verify.md").is_file():
            errs.append(f"{tc.name}: a WRITE TC (per its manifest) without "
                        f"db_verify.md — writing without a read-back SELECT is not verification")
        if text and not blocked and not re.search(rf"\b{tc.name}\b", sec3):
            errs.append(f"REPORT.md §3 never mentions {tc.name} — orphan evidence")
    return errs, warns


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
    with tempfile.TemporaryDirectory() as td:
        evd = Path(td) / "PROJ-1"
        tc = evd / "TC_1"
        tc.mkdir(parents=True)
        report = ("# Verification report PROJ-1 — PASS\nCOMMIT: abc1234\n"
                  "## 1. What\nx\n## 2. How\nx\n## 3. Evidence\nTC_1: db_verify.md\n## 4. Conclusion\nok\n")
        (evd / "REPORT.md").write_text(report)
        (evd / "manifest.md").write_text("overview")
        (evd / "debate.md").write_text("### verifier\nPASS\n### challenger\nagree\n")
        (tc / "manifest.md").write_text("TYPE: NON-UI\nRESULT: PASS\nDB_VERIFY\n")
        (tc / "db_verify.md").write_text("SELECT 1; -> 1")
        errs, _ = check_tree(evd, 1, [])
        assert not errs, errs
        # mutations
        (tc / "db_verify.md").unlink()
        errs, _ = check_tree(evd, 1, [])
        assert errs, "NON-UI without db_verify should red"
        (tc / "db_verify.md").write_text("SELECT 1; -> 1")
        errs, _ = check_tree(evd, 3, [])
        assert errs, "expect-tcs 3 vs 1 should red"
        (evd / "REPORT.md").write_text(report.replace("COMMIT: abc1234\n", ""))
        errs, _ = check_tree(evd, 1, [])
        assert any("COMMIT" in e for e in errs), "missing COMMIT pin should red"
        (evd / "REPORT.md").write_text(report.replace("PASS", "FAIL"))
        errs, _ = check_tree(evd, 1, [])
        assert any("Severity" in e for e in errs), "FAIL without Severity should red"
    print("evd_check selftest: OK (fixture green + 4 mutations red)")


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        _selftest()
    else:
        main()
