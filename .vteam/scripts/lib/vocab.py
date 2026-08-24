"""Locale vocabulary loader for gates.

Gates check neutral sentinels; free-prose patterns (hedge phrases, write verbs)
come from locale files. Search order: <repo>/.vteam/locales/<lang>.yml (installed)
→ <this lib>/../../locales/<lang>.yml (in-repo framework dev). English is always
merged in as the base so a partial locale never silently drops a check.
"""
from __future__ import annotations

from pathlib import Path

from ctx import Ctx, parse_config


def _find(lang: str, root: Path) -> Path | None:
    for cand in (
        root / ".vteam" / "locales" / f"{lang}.yml",
        Path(__file__).resolve().parent.parent.parent / "locales" / f"{lang}.yml",
    ):
        if cand.is_file():
            return cand
    return None


def vocab(c: Ctx) -> dict:
    """Return the merged vocabulary dict for the project language (en as base)."""
    merged: dict = {}
    langs = ["en"]
    lang = str(c.cfg("project.language", "en"))
    if lang != "en":
        langs.append(lang)
    for lg in langs:
        f = _find(lg, c.root)
        if f is None:
            if lg == "en":
                raise SystemExit("locale: base en.yml not found — broken install")
            print(f"⚠️  locale: no vocabulary file for {lg!r} — using en only")
            continue
        data = parse_config(f.read_text(encoding="utf-8"))
        for k, v in data.items():
            if isinstance(v, list):
                merged.setdefault(k, [])
                merged[k] = list(dict.fromkeys(merged[k] + v))  # merge, keep order
            else:
                merged[k] = v
    return merged
