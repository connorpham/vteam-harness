#!/usr/bin/env python3
"""annotate.py — draw the box, write the caption. (Needs Pillow.)

A screenshot is not evidence until a stranger can tell, without asking, WHICH
pixels carried the verdict and WHAT they prove. A red rectangle with no words
explains nothing; a full-page capture with no rectangle makes the reader hunt.
Both are the normal output of a hurried verification — so this is gated, not
suggested (evd_check demands a *_boxed.png on every executed UI case).

Two rules this tool holds, learned the hard way:
  · the box HUGS the rectangle you name — a 4-px border drawn exactly on
    X,Y,W,H, never inflated by padding, so the box proves that region and no
    other ("khoanh vùng đúng");
  · the caption is burned in on a bar BELOW the image, word-wrapped, font scaled
    to the width — below, not above, so every pixel coordinate of the original
    stays where it was (a caption band on top shifts the whole picture down and
    silently breaks any rect computed against the original).

Commands:
  box  --img shot.png --rect X,Y,W,H [--rect ...] --label "TC_2: what this proves" --out out.png
       --label is REQUIRED (an unexplained box is not evidence); --rect may repeat.
  diff --old oracle.png --new app.png --out design_vs_app.png [--label "…"] [--min 40]
       (aliases: --left/--right, --left-label/--right-label)
       Side by side; AUTO-DETECTS differing regions and boxes them exactly on
       both sides; caption below names the count.

Prove it:  python3 annotate.py --selftest
Python 3.9 compatible. Needs Pillow — degrades with a BLOCKED message, never a stack trace.
"""
import argparse
import os
import sys
from collections import deque

BOX = (220, 38, 38)          # a red that survives being printed in greyscale
CAPTION_BG = (17, 17, 17)
CAPTION_FG = (255, 255, 255)
PAD = 10                     # caption padding only — NEVER applied to the box
BORDER = 4

# Unicode-capable faces first — captions are written in project.language
# (Vietnamese diacritics must render), then bold Latin faces, then Pillow's default.
FONT_CANDIDATES = (
    "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",
    "/Library/Fonts/Arial Unicode.ttf",
    "/usr/share/fonts/truetype/noto/NotoSans-Regular.ttf",
    "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/System/Library/Fonts/Helvetica.ttc",
    "/System/Library/Fonts/Supplemental/Arial.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    "C:\\Windows\\Fonts\\arial.ttf",
    "C:\\Windows\\Fonts\\arialbd.ttf",
)


def need_pillow():
    try:
        from PIL import Image, ImageDraw, ImageFont  # noqa: F401
        return True
    except ImportError:
        print("ANNOTATE: BLOCKED — Pillow is not installed")
        print("  unblock: pip install pillow")
        print("  Do NOT submit an unannotated screenshot instead; evd_check will red it,")
        print("  and a reader could not use it anyway.")
        return False


def _font(size):
    from PIL import ImageFont
    for path in FONT_CANDIDATES:
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size)
            except Exception:
                continue
    return ImageFont.load_default()


def _text_size(draw, text, font):
    try:
        box = draw.textbbox((0, 0), text, font=font)
        return box[2] - box[0], box[3] - box[1]
    except AttributeError:  # very old Pillow
        return draw.textsize(text, font=font)


def _wrap(draw, text, font, max_width):
    words = str(text).split()
    lines, cur = [], ""
    for w in words:
        trial = (cur + " " + w).strip()
        if _text_size(draw, trial, font)[0] <= max_width or not cur:
            cur = trial
        else:
            lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def caption_strip(img, label):
    """Burn the caption INTO the image, on a bar under it — below, so the
    original's coordinates are untouched; in-image, because evidence is copied
    into tickets, chat and decks one file at a time and a sidecar caption is a
    caption nobody reads."""
    from PIL import Image, ImageDraw
    if not label:
        return img
    draw = ImageDraw.Draw(img)
    size = max(14, min(26, img.width // 55))
    font = _font(size)
    lines = _wrap(draw, label, font, img.width - 2 * PAD)
    line_h = _text_size(draw, "Ag", font)[1] + 6
    strip_h = line_h * len(lines) + 2 * PAD
    out = Image.new("RGB", (img.width, img.height + strip_h), CAPTION_BG)
    out.paste(img.convert("RGB"), (0, 0))
    d = ImageDraw.Draw(out)
    y = img.height + PAD
    for line in lines:
        d.text((PAD, y), line, fill=CAPTION_FG, font=font)
        y += line_h
    return out


def _exact_box(draw, x0, y0, x1, y1):
    """A BORDER-px frame drawn exactly on the rectangle — no PAD inflation."""
    for i in range(BORDER):
        draw.rectangle([x0 - i, y0 - i, x1 + i, y1 + i], outline=BOX)


def _parse_rect(rect):
    try:
        x, y, w, h = [int(p.strip()) for p in rect.split(",")]
    except (ValueError, AttributeError):
        return None
    if w <= 0 or h <= 0:
        return None
    return x, y, w, h


def cmd_box(args):
    from PIL import Image, ImageDraw
    if not os.path.exists(args.img):
        print("ANNOTATE: no such image: {}".format(args.img))
        return 1
    img = Image.open(args.img).convert("RGB")
    rects = args.rect or []
    if not rects and not args.label:
        print("ANNOTATE: pass --rect, --label, or both — an untouched copy is not an annotation")
        return 1
    d = ImageDraw.Draw(img)
    for r in rects:
        p = _parse_rect(r)
        if p is None:
            print("ANNOTATE: --rect must be X,Y,W,H in pixels with W,H > 0 (got {!r})".format(r))
            return 1
        x, y, w, h = p
        _exact_box(d, x, y, x + w, y + h)
    out = caption_strip(img, args.label)
    os.makedirs(os.path.dirname(os.path.abspath(args.out)) or ".", exist_ok=True)
    out.save(args.out)
    print("ANNOTATE: OK  {}  ({} region(s) boxed, caption below)".format(args.out, len(rects)))
    return 0


def _diff_boxes(a, b, thresh=32, min_px=40, scale_w=240):
    """Full-res bboxes for clusters of differing pixels between a and b (vteam's
    auto-detect: connected components on a downscaled max-channel diff mask)."""
    from PIL import ImageChops
    if a.size != b.size:
        b = b.resize(a.size)
    W, H = a.size
    dr, dg, db = ImageChops.difference(a.convert("RGB"), b.convert("RGB")).split()
    mx = ImageChops.lighter(ImageChops.lighter(dr, dg), db)
    mask = mx.point(lambda p: 255 if p > thresh else 0)
    sw = min(scale_w, W)
    sh = max(1, int(H * sw / W))
    small = mask.resize((sw, sh))
    px = small.load()
    seen = [[False] * sw for _ in range(sh)]
    boxes = []
    fx, fy = W / sw, H / sh
    for yy in range(sh):
        for xx in range(sw):
            if px[xx, yy] and not seen[yy][xx]:
                q = deque([(xx, yy)])
                seen[yy][xx] = True
                x0 = x1 = xx
                y0 = y1 = yy
                n = 0
                while q:
                    cx, cy = q.popleft()
                    n += 1
                    x0, x1 = min(x0, cx), max(x1, cx)
                    y0, y1 = min(y0, cy), max(y1, cy)
                    for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                        nx, ny = cx + dx, cy + dy
                        if 0 <= nx < sw and 0 <= ny < sh and not seen[ny][nx] and px[nx, ny]:
                            seen[ny][nx] = True
                            q.append((nx, ny))
                if n * fx * fy >= min_px:
                    boxes.append((int(x0 * fx), int(y0 * fy), int((x1 + 1) * fx), int((y1 + 1) * fy)))
    return boxes, b


def cmd_diff(args):
    from PIL import Image, ImageDraw
    left_p = args.old or args.left
    right_p = args.new or args.right
    for p in (left_p, right_p):
        if not p or not os.path.exists(p):
            print("ANNOTATE: no such image: {}".format(p))
            return 1
    a = Image.open(left_p).convert("RGB")
    b = Image.open(right_p).convert("RGB")
    boxes, b = _diff_boxes(a, b, min_px=args.min)
    for img in (a, b):
        d = ImageDraw.Draw(img)
        for (x0, y0, x1, y1) in boxes:
            _exact_box(d, x0, y0, x1, y1)
    h = max(a.height, b.height)
    gap = 16
    canvas = Image.new("RGB", (a.width + b.width + gap, h), (245, 245, 245))
    canvas.paste(a, (0, 0))
    canvas.paste(b, (a.width + gap, 0))
    d = ImageDraw.Draw(canvas)
    font = _font(max(14, min(24, canvas.width // 70)))
    d.text((PAD, PAD), args.left_label, fill=BOX, font=font)
    d.text((a.width + gap + PAD, PAD), args.right_label, fill=BOX, font=font)
    label = (args.label + " — " if args.label else "") + "{} differing region(s) boxed".format(len(boxes))
    out = caption_strip(canvas, label)
    os.makedirs(os.path.dirname(os.path.abspath(args.out)) or ".", exist_ok=True)
    out.save(args.out)
    print("ANNOTATE: OK  {}  ({} differing region(s) boxed)".format(args.out, len(boxes)))
    return 0


def selftest():
    import tempfile
    import shutil
    from PIL import Image

    tmp = tempfile.mkdtemp(prefix="vteam-annotate-")
    fails = []
    try:
        src = os.path.join(tmp, "shot.png")
        Image.new("RGB", (400, 300), (255, 255, 255)).save(src)

        # box + caption: pixels change, image grows DOWNWARD only (coords intact)
        out = os.path.join(tmp, "shot_boxed.png")
        rc = cmd_box(argparse.Namespace(img=src, rect=["50,50,120,40"],
                                        label="TC_1: total recalculated to 450,000 ₫", out=out))
        if rc != 0 or not os.path.exists(out):
            fails.append("box did not produce an output file")
        else:
            a, b = Image.open(src), Image.open(out)
            if b.height <= a.height:
                fails.append("caption strip did not grow the image — the caption is not in the file")
            if b.width != a.width:
                fails.append("caption changed the width — coordinates would shift")
            top = b.crop((0, 0, 400, 300))
            if list(top.getdata()) == list(a.getdata()):
                fails.append("the box was never drawn — pixels are unchanged")
            # the box HUGS the rect: red exactly on the frame, white just outside it
            if top.getpixel((50, 50)) != BOX:
                fails.append("box corner is not on the rect — the frame does not hug the region")
            if top.getpixel((50 - BORDER - 1, 70)) == BOX:
                fails.append("red found outside the border — the box is padded/inflated")
            if top.getpixel((110, 70)) != (255, 255, 255):
                fails.append("interior of the rect was painted — a box, not a fill")

        # multiple rects are all drawn
        out2 = os.path.join(tmp, "two_boxed.png")
        rc = cmd_box(argparse.Namespace(img=src, rect=["10,10,50,30", "200,150,60,60"], label="two", out=out2))
        if rc != 0 or Image.open(out2).crop((0, 0, 400, 300)).getpixel((200, 150)) != BOX:
            fails.append("second --rect was not drawn")

        # neither box nor caption must be refused; a malformed / zero-size rect must be refused
        if cmd_box(argparse.Namespace(img=src, rect=None, label=None, out=os.path.join(tmp, "noop.png"))) == 0:
            fails.append("an empty annotation was accepted — that is just a copy")
        if cmd_box(argparse.Namespace(img=src, rect=["not,a,rect,x"], label="x", out=os.path.join(tmp, "bad.png"))) == 0:
            fails.append("a malformed --rect was accepted")
        if cmd_box(argparse.Namespace(img=src, rect=["10,10,0,5"], label="x", out=os.path.join(tmp, "zero.png"))) == 0:
            fails.append("a zero-size --rect was accepted")

        # diff: two images differing in one patch → side by side, ≥1 region auto-boxed
        right = os.path.join(tmp, "app.png")
        img_r = Image.new("RGB", (400, 300), (255, 255, 255))
        for x in range(120, 220):
            for y in range(100, 160):
                img_r.putpixel((x, y), (0, 0, 200))
        img_r.save(right)
        dout = os.path.join(tmp, "diff.png")
        rc = cmd_diff(argparse.Namespace(old=src, new=right, left=None, right=None, out=dout,
                                         label="design vs build", left_label="design",
                                         right_label="build", min=40))
        if rc != 0 or not os.path.exists(dout):
            fails.append("diff did not produce an output")
        else:
            dimg = Image.open(dout)
            if dimg.width <= 400:
                fails.append("diff did not place the two images side by side")
            # a red frame must appear around the changed patch on the RIGHT panel
            if not any(dimg.getpixel((400 + 16 + x, 100)) == BOX for x in range(118, 124)):
                fails.append("auto-detected region was not boxed on the right panel")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    if fails:
        print("annotate --selftest FAILED")
        for f in fails:
            print("  x {}".format(f))
        return 1
    print("annotate --selftest passed  (exact-fit box, caption below w/ width intact, multi-rect, "
          "empty/malformed/zero-size refused, auto-diff boxed side by side)")
    return 0


def main():
    ap = argparse.ArgumentParser(description="annotate evidence images")
    ap.add_argument("--selftest", action="store_true")
    sub = ap.add_subparsers(dest="cmd")

    b = sub.add_parser("box", help="draw exact-fit box(es) and burn a caption in below")
    b.add_argument("--img", required=True)
    b.add_argument("--rect", action="append", help="X,Y,W,H in pixels; may repeat")
    # a red rectangle with no caption explains nothing to the stranger the
    # evidence is FOR — the caption is the point, not decoration
    b.add_argument("--label", required=True,
                   help="in-image caption: what this region proves, in project.language")
    b.add_argument("--out", required=True)

    d = sub.add_parser("diff", help="two images side by side, differing regions auto-boxed, captioned")
    d.add_argument("--old", help="oracle/design image (alias: --left)")
    d.add_argument("--new", help="app/build image (alias: --right)")
    d.add_argument("--left", help=argparse.SUPPRESS)
    d.add_argument("--right", help=argparse.SUPPRESS)
    d.add_argument("--label", default="")
    d.add_argument("--left-label", default="expected", dest="left_label")
    d.add_argument("--right-label", default="actual", dest="right_label")
    d.add_argument("--min", type=int, default=40, help="min differing pixels to count as a region")
    d.add_argument("--out", required=True)

    args = ap.parse_args()
    if args.selftest:
        return selftest() if need_pillow() else 1
    if not args.cmd:
        ap.print_help()
        return 2
    if not need_pillow():
        return 1
    return cmd_box(args) if args.cmd == "box" else cmd_diff(args)


if __name__ == "__main__":
    sys.exit(main())
