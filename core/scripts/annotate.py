#!/usr/bin/env python3
"""annotate.py — box evidence regions on screenshots (needs Pillow only).

Commands:
  box  --img shot.png --rect X,Y,W,H [--rect ...] --label "TC_2: what this proves" --out out.png
       Draw a RED box around the region under test + an in-image caption, so a
       viewer understands what is being shown without reading anything else.

  diff --old oracle.png --new app.png --out design_vs_app.png [--label "…"] [--min 40]
       Place the two images side by side, AUTO-DETECT differing regions and box
       them in red on both sides.
"""
import argparse
import sys
from collections import deque

from PIL import Image, ImageChops, ImageDraw, ImageFont

RED = (220, 30, 30)
PAD = 6

# Unicode-capable fonts first — captions are written in project.language.
FONT_CANDIDATES = (
    "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",
    "/Library/Fonts/Arial Unicode.ttf",
    "/usr/share/fonts/truetype/noto/NotoSans-Regular.ttf",
    "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/System/Library/Fonts/Supplemental/Arial.ttf",
    "C:/Windows/Fonts/arial.ttf",
)


def _font(size=20):
    for p in FONT_CANDIDATES:
        try:
            return ImageFont.truetype(p, size)
        except OSError:
            continue
    return ImageFont.load_default()


def _caption(img, text):
    """Caption band at the top of the image."""
    if not text:
        return img
    f = _font(20)
    d0 = ImageDraw.Draw(img)
    tw = d0.textbbox((0, 0), text, font=f)
    band_h = (tw[3] - tw[1]) + 16
    out = Image.new("RGB", (img.width, img.height + band_h), (17, 17, 17))
    out.paste(img, (0, band_h))
    ImageDraw.Draw(out).text((10, 8), text, fill=(255, 255, 255), font=f)
    return out


def cmd_box(args):
    img = Image.open(args.img).convert("RGB")
    d = ImageDraw.Draw(img)
    for rect in args.rect:
        x, y, w, h = [int(v) for v in rect.split(",")]
        d.rectangle([x - PAD, y - PAD, x + w + PAD, y + h + PAD], outline=RED, width=4)
    img = _caption(img, args.label)
    img.save(args.out)
    print(f"[box] {args.out} ({len(args.rect)} region(s))")


def _diff_boxes(a, b, thresh=32, min_px=40, scale_w=240):
    """Full-res bboxes for clusters of differing pixels between a and b."""
    if a.size != b.size:
        b = b.resize(a.size)
    W, H = a.size
    # max channel difference → catches color-only changes, not just brightness
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
    a = Image.open(args.old).convert("RGB")
    b = Image.open(args.new).convert("RGB")
    boxes, b = _diff_boxes(a, b, min_px=args.min)
    for img in (a, b):
        d = ImageDraw.Draw(img)
        for (x0, y0, x1, y1) in boxes:
            d.rectangle([x0 - PAD, y0 - PAD, x1 + PAD, y1 + PAD], outline=RED, width=4)
    a = _caption(a, f"ORACLE — {len(boxes)} differing region(s)")
    b = _caption(b, "APP")
    H = max(a.height, b.height)
    gap = 12
    canvas = Image.new("RGB", (a.width + gap + b.width, H), (255, 255, 255))
    canvas.paste(a, (0, 0))
    canvas.paste(b, (a.width + gap, 0))
    if args.label:
        canvas = _caption(canvas, args.label)
    canvas.save(args.out)
    print(f"[diff] {args.out}: {len(boxes)} differing region(s) boxed")


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("box")
    b.add_argument("--img", required=True)
    b.add_argument("--rect", action="append", required=True)
    b.add_argument("--label", default="")
    b.add_argument("--out", required=True)
    d = sub.add_parser("diff")
    d.add_argument("--old", required=True)
    d.add_argument("--new", required=True)
    d.add_argument("--label", default="")
    d.add_argument("--min", type=int, default=40)
    d.add_argument("--out", required=True)
    a = ap.parse_args()
    {"box": cmd_box, "diff": cmd_diff}[a.cmd](a)


if __name__ == "__main__":
    sys.exit(main())
