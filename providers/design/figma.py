"""Figma design-source provider for vteam (installed as .vteam/providers/design_figma.py).

Env: FIGMA_ACCESS_TOKEN + FIGMA_FILE_KEY. The Figma API is read-only — the
machine can never create frames, which is exactly why the DESIGN lane has a
mockup fallback.

learn_styles() generates the design-language file FROM THE PROJECT'S OWN design
source — tolerance tables are derived, never shipped as constants (a generic
4px-grid rule would grade a real design as wrong). The file carries
`file-version:` so check_version() can detect staleness.
"""
from __future__ import annotations

import collections
import json
import sys
import urllib.parse
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts" / "lib"))
from design import Design  # noqa: E402


class Provider(Design):
    def __init__(self, c):
        super().__init__(c)
        self.token = c.env("FIGMA_ACCESS_TOKEN")
        self.key = c.env("FIGMA_FILE_KEY")
        if not self.token:
            raise SystemExit("design(figma): FIGMA_ACCESS_TOKEN missing from .env")
        if not self.key:
            raise SystemExit("design(figma): FIGMA_FILE_KEY missing — paste the file link's key into .env")

    def _get(self, path: str):
        req = urllib.request.Request(f"https://api.figma.com{path}",
                                     headers={"X-Figma-Token": self.token})
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.load(r)

    def ping(self):
        try:
            me = self._get("/v1/me")
        except Exception as exc:
            return False, f"token invalid ({exc})"
        try:
            meta = self._get(f"/v1/files/{self.key}?depth=1")
        except Exception:
            return False, f"file {self.key} unreadable — wrong key or no view permission"
        return True, f"file “{meta.get('name')}” readable as {me.get('email', '?')}"

    def node_link(self, node_id: str) -> str:
        return f"https://www.figma.com/design/{self.key}/?node-id={node_id.replace(':', '-')}"

    def frames(self):
        d = self._get(f"/v1/files/{self.key}?depth=3")
        out = []

        def walk(node, page):
            t = node.get("type")
            if t in ("FRAME", "COMPONENT", "COMPONENT_SET"):
                out.append({"page": page, "name": node.get("name", ""), "id": node["id"],
                            "link": self.node_link(node["id"])})
                return  # top-level frames only; don't dive inside frames
            for ch in node.get("children", []) or []:
                walk(ch, page)

        for page in d.get("document", {}).get("children", []) or []:
            walk(page, page.get("name", "?"))
        return out

    def match(self, query: str):
        q = query.lower()
        return [f for f in self.frames() if q in f["name"].lower() or q in f["page"].lower()]

    def node_exists(self, node_id: str):
        node = node_id.replace("-", ":")
        d = self._get(f"/v1/files/{self.key}/nodes?ids={urllib.parse.quote(node)}")
        doc = (d.get("nodes") or {}).get(node, {}).get("document")
        return doc  # None when absent; dict (with name) when real

    # -- design language -------------------------------------------------------
    def _stored_version(self, out_path: Path) -> str:
        if out_path.is_file():
            for line in out_path.read_text(encoding="utf-8").splitlines()[:8]:
                if line.startswith("file-version:"):
                    return line.split(":", 1)[1].strip()
        return ""

    def check_version(self, out_path: Path):
        meta = self._get(f"/v1/files/{self.key}?depth=1")
        stored = self._stored_version(out_path)
        if stored and meta.get("version") == stored:
            return True, "design-language file matches the design file version"
        return False, (f"design language STALE (file version {meta.get('version')} ≠ "
                       f"learned {stored or 'none'}) — re-run learn_styles")

    def learn_styles(self, out_path: Path) -> str:
        d = self._get(f"/v1/files/{self.key}")
        colors, texts = collections.Counter(), collections.Counter()
        radii, spacings = collections.Counter(), collections.Counter()

        def to_hex(c):
            return "#{:02X}{:02X}{:02X}".format(round(c["r"] * 255), round(c["g"] * 255), round(c["b"] * 255))

        def walk(node):
            for f in node.get("fills", []) or []:
                if f.get("type") == "SOLID" and f.get("visible", True) and "color" in f:
                    colors[to_hex(f["color"])] += 1
            if node.get("type") == "TEXT" and "style" in node:
                s = node["style"]
                texts[(s.get("fontFamily", "?"), s.get("fontWeight", "?"),
                       s.get("fontSize", "?"), round(s.get("lineHeightPx", 0)))] += 1
            r = node.get("cornerRadius")
            if isinstance(r, (int, float)) and r > 0:
                radii[round(r)] += 1
            if node.get("layoutMode") in ("HORIZONTAL", "VERTICAL"):
                for k in ("itemSpacing", "paddingLeft", "paddingTop"):
                    v = node.get(k)
                    if isinstance(v, (int, float)) and v > 0:
                        spacings[round(v)] += 1
            for ch in node.get("children", []) or []:
                walk(ch)

        walk(d.get("document", {}))
        comps = self._get(f"/v1/files/{self.key}/components")
        comp_names = sorted({c.get("name", "?") for c in (comps.get("meta", {}).get("components") or [])})
        styles = self._get(f"/v1/files/{self.key}/styles")
        named = [(s.get("name", "?"), s.get("style_type", "?"))
                 for s in (styles.get("meta", {}).get("styles") or [])]

        lines = [
            "# Design language — LEARNED from the project's design file",
            "",
            f"file-version: {d.get('version')}",
            f"file-name: {d.get('name')}",
            "",
            "> Generated by the figma design provider — do NOT hand-edit (re-learn when",
            "> the design file changes). Mockups and UI code take colors/type/radii FROM",
            "> HERE for consistency. Spacing: only when the table below HAS data — a file",
            "> without auto-layout leaves it empty, and spacing then has exactly one",
            "> source: the frame's node data. The UI quality rules decide only what this",
            "> file doesn't specify; the only sanctioned deviation is accessibility",
            "> (contrast 4.5:1, touch 44px).",
            "",
            "## Palette (by real usage frequency)",
            "| Hex | Uses |", "|---|---|",
        ]
        lines += [f"| `{h}` | {n} |" for h, n in colors.most_common(16)]
        lines += ["", "## Type scale (family / weight / size / line-height)",
                  "| Font | Weight | Size | LH | Uses |", "|---|---|---|---|---|"]
        lines += [f"| {f} | {w} | {s} | {lh} | {n} |" for (f, w, s, lh), n in texts.most_common(12)]
        lines += ["", "## Common radii", "| Radius | Uses |", "|---|---|"]
        lines += [f"| {r}px | {n} |" for r, n in radii.most_common(6)]
        lines += ["", "## Common auto-layout spacing", "| px | Uses |", "|---|---|"]
        lines += [f"| {s}px | {n} |" for s, n in spacings.most_common(8)]
        lines += ["", "## Named styles", "| Name | Type |", "|---|---|"]
        lines += [f"| {n} | {t} |" for n, t in named[:20]] or ["| (none) | |"]
        lines += ["", "## Existing components (reuse, don't redraw)", ""]
        lines += [f"- {c}" for c in comp_names[:30]] or ["- (none)"]
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return (f"learned: {len(colors)} colors, {len(texts)} type styles, "
                f"{len(comp_names)} components → {out_path}")
