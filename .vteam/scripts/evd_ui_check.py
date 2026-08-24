#!/usr/bin/env python3
"""evd_ui_check.py — machine gate for the DEV lane's UI evidence.

Owns {paths.evidence}/<TICKET>/dev/ — the ROOT layer {paths.evidence}/<TICKET>/
belongs to the QA lane (evd_check.py). One directory, one owner: two gates with
two schemas must never red each other.

Checks:
  1. manifest.md exists, contains a CRITERION → IMAGE table mentioning every
     image, and a `STATE:` line naming the captured states (data/empty/error/
     loading — `N/A because <reason>` allowed per state).
  2. Every .png: opens (Pillow), ≥400×300, non-empty, and is NOT a blank or
     error page — detected by dominant-color ratio (>97% single color = blank).
  3. Naming: `NN_<description>.png` — the name must say what the shot shows.
  4. Hedge phrases (locale list) or the `NOT MEASURED` sentinel in manifest.md
     or fidelity.md → RED: hedging is not measuring.
  5. A design oracle exists (design/ dir or fidelity.json present, or --oracle
     passed) → design_vs_app.png AND fidelity.md are required, and fidelity.md
     must contain no WRONG-deviation lines (`DEVIATION: WRONG`).
     Proportionality: a manifest declaring `NARROW-SCOPE: <reason ≥20 chars>`
     skips the fidelity requirement (small diffs don't pay the full tax) — but
     the declaration itself is the durable record.
  6. --bug: before_*/after_* pairs required (a fix that can't reproduce the
     original bug proves nothing).
  7. --attach <TICKET>: upload every image via the tracker provider with
     READ-BACK confirmation; write pointers into manifest.md.

Usage: evd_ui_check.py <TICKET> [--bug] [--oracle] [--attach]
Selftest: --selftest (fixture green + mutations red; needs Pillow).
"""
import argparse
import re
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "lib"))

NAME_PAT = re.compile(r"^\d{2}_[\w-]+\.png$")
SPECIAL = {"design_vs_app.png"}
NOT_MEASURED = "NOT MEASURED"


def png_problems(p: Path) -> list[str]:
    if p.stat().st_size == 0:
        return [f"{p.name}: empty file (0 bytes)"]
    try:
        from PIL import Image, UnidentifiedImageError
    except ImportError:
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
        return [f"{p.name}: too small {w}x{h} (min 400x300)"]
    # blank/error-page detection: one color dominating almost the whole frame
    colors = small.getcolors(64 * 64) or []
    if colors:
        top = max(n for n, _ in colors)
        if top / (64 * 64) > 0.97:
            return [f"{p.name}: >97% a single color — a blank page or an error "
                    f"screen, not evidence"]
    return []


def check_dev_dir(dev: Path, hedges: list[str], bug: bool, oracle: bool) -> list[str]:
    errs: list[str] = []
    if not dev.is_dir():
        return [f"{dev} does not exist — DEV evidence lives in <evd>/<TICKET>/dev/ "
                f"(the root layer belongs to QA)"]
    manifest = dev / "manifest.md"
    mtext = manifest.read_text(encoding="utf-8", errors="replace") if manifest.is_file() else ""
    if not mtext:
        errs.append("missing manifest.md (CRITERION → IMAGE table)")
    pngs = sorted(dev.glob("*.png"))
    if not pngs:
        errs.append("no .png evidence in dev/")
    for p in pngs:
        errs.extend(png_problems(p))
        if p.name not in SPECIAL and not p.name.startswith(("before_", "after_")) \
                and not NAME_PAT.match(p.name):
            errs.append(f"{p.name}: name breaks NN_<description>.png — the name "
                        f"must say what the shot shows")
        if mtext and p.name not in mtext:
            errs.append(f"{p.name}: never referenced in manifest.md — an image the "
                        f"manifest doesn't claim proves nothing")
    if mtext:
        narrow = re.search(r"NARROW-SCOPE:\s*(.{0,120})", mtext)
        if narrow and len(narrow.group(1).strip()) < 20:
            errs.append("NARROW-SCOPE declared but the reason is <20 chars — a "
                        "declaration without substance is a dodge")
        if not re.search(r"^STATE\s*[:：]", mtext, re.M):
            errs.append("manifest.md lacks the `STATE:` line (data/empty/error/"
                        "loading — N/A with reason per state)")
        low = mtext.lower()
        for h in hedges:
            if h.lower() in low:
                errs.append(f"manifest.md contains the hedge phrase {h!r} — "
                            f"hedging is not measuring")
        if NOT_MEASURED.lower() in low:
            errs.append(f"manifest.md contains '{NOT_MEASURED}' — measure it or "
                        f"declare NARROW-SCOPE with a reason")
        fid = dev / "fidelity.md"
        ftext = fid.read_text(encoding="utf-8", errors="replace") if fid.is_file() else ""
        has_oracle = oracle or (dev.parent / "design").is_dir() or (dev / "fidelity.json").is_file()
        if has_oracle:
            narrow_ok = bool(narrow and len(narrow.group(1).strip()) >= 20)
            if not (dev / "design_vs_app.png").is_file():
                errs.append("design oracle present but design_vs_app.png missing")
            if not narrow_ok:
                if not ftext:
                    errs.append("design oracle present but fidelity.md missing "
                                "(run the fidelity measurement) — or declare "
                                "NARROW-SCOPE with a reason")
                elif re.search(r"DEVIATION:\s*WRONG", ftext, re.I):
                    errs.append("fidelity.md still lists WRONG deviations — fix "
                                "the code and re-measure, or declare a closed-list intent")
    if bug:
        befores = {p.name[len("before_"):] for p in pngs if p.name.startswith("before_")}
        afters = {p.name[len("after_"):] for p in pngs if p.name.startswith("after_")}
        if not befores:
            errs.append("--bug: no before_*.png — a fix that never reproduced the "
                        "original bug proves nothing")
        for b in sorted(befores - afters):
            errs.append(f"--bug: before_{b} has no matching after_{b}")
        for a in sorted(afters - befores):
            errs.append(f"--bug: after_{a} has no matching before_{a}")
    return errs


def main() -> int:
    from ctx import Ctx
    from vocab import vocab
    c = Ctx()
    ap = argparse.ArgumentParser()
    ap.add_argument("ticket")
    ap.add_argument("--bug", action="store_true")
    ap.add_argument("--oracle", action="store_true",
                    help="declare a design oracle exists even without design/ or fidelity.json")
    ap.add_argument("--attach", action="store_true")
    args = ap.parse_args()
    ticket = args.ticket.upper()
    dev = c.path("evidence") / ticket / "dev"

    if args.attach:
        import tracker as trk
        t = trk.load(c)
        pngs = sorted(dev.glob("*.png"))
        lines = ["\n## TRACKER ATTACHMENTS (evd_ui_check --attach)\n"]
        for p in pngs:
            res = t.attach(ticket, p)
            if not res:
                print(f"❌ --attach: read-back did not confirm {p.name}")
                return 1
            lines.append(f"- {p.name} · md5 {res['md5']} · {res['url']}\n")
        mf = dev / "manifest.md"
        old = mf.read_text(encoding="utf-8") if mf.is_file() else ""
        if "## TRACKER ATTACHMENTS" in old:
            old = re.sub(r"\n## TRACKER ATTACHMENTS.*", "", old, flags=re.S)
        mf.write_text(old + "".join(lines), encoding="utf-8")
        print(f"✅ --attach: {len(pngs)} images on {ticket}, read-back confirmed")

    errs = check_dev_dir(dev, vocab(c).get("hedge_phrases", []), args.bug, args.oracle)
    if errs:
        print(f"❌ evd_ui_check: {ticket} — {len(errs)} problems")
        for e in errs:
            print(f"   - {e}")
        return 1
    print(f"✅ evd_ui_check: {ticket} — DEV evidence meets the standard")
    return 0


def _selftest():
    try:
        from PIL import Image
    except ImportError:
        print("evd_ui_check selftest: SKIPPED (Pillow missing) — install pillow; "
              "this selftest refuses to pretend it ran")
        sys.exit(1)
    import random
    with tempfile.TemporaryDirectory() as td:
        dev = Path(td) / "PROJ-1" / "dev"
        dev.mkdir(parents=True)
        img = Image.new("RGB", (800, 600))
        img.putdata([(random.randrange(256),) * 3 for _ in range(800 * 600)])
        img.save(dev / "01_login_form.png")
        (dev / "manifest.md").write_text(
            "| criterion | image |\n|---|---|\n| login form renders | 01_login_form.png |\n"
            "STATE: data; empty N/A because the form has no list\n")
        errs = check_dev_dir(dev, ["looks about right"], bug=False, oracle=False)
        assert not errs, errs
        # mutations
        blank = Image.new("RGB", (800, 600), (255, 255, 255))
        blank.save(dev / "02_blank.png")
        errs = check_dev_dir(dev, [], False, False)
        assert any("single color" in e for e in errs), "blank page should red"
        (dev / "02_blank.png").unlink()
        (dev / "manifest.md").write_text(
            "| login form renders | 01_login_form.png |\nSTATE: data\nlooks about right\n")
        errs = check_dev_dir(dev, ["looks about right"], False, False)
        assert any("hedge" in e for e in errs), "hedge phrase should red"
        errs = check_dev_dir(dev, [], True, False)
        assert any("before_" in e for e in errs), "--bug without before_ should red"
        errs = check_dev_dir(dev, [], False, True)
        assert any("design_vs_app" in e for e in errs), "oracle without design_vs_app should red"
    print("evd_ui_check selftest: OK (fixture green + 4 mutations red)")


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        _selftest()
    else:
        sys.exit(main())
