"""Design-source provider interface + the built-in `none` provider.

Selected by `design.provider` in vteam.config.yaml:
    none   — built in: every call reports "no design source"; the DESIGN lane
             falls back to approved mockups, fidelity gates collapse to the
             screenshot-evidence layer.
    figma  — loaded from .vteam/providers/design_figma.py (or the framework
             repo's providers/design/figma.py in dev).

Interface:
    ping()                       -> (ok, message)
    frames()                     -> [{page, name, id, link}]
    match(query)                 -> frames filtered by name/page substring
    node_link(node_id)           -> canonical share link for a node
    learn_styles(out_path)       -> generate the design-language file; returns summary
    check_version(out_path)      -> (fresh: bool, message)  vs the stored version
"""
from __future__ import annotations

import importlib.util
from pathlib import Path

from ctx import Ctx


class Design:
    def __init__(self, c: Ctx):
        self.c = c

    def ping(self): return True, "no design source configured"
    def frames(self): return []
    def match(self, query: str): return []
    def node_link(self, node_id: str) -> str: raise SystemExit("design(none): no design source")
    def learn_styles(self, out_path: Path) -> str:
        raise SystemExit("design(none): no design source to learn from — the UI "
                         "quality rules decide alone (record that in the minutes)")
    def check_version(self, out_path: Path):
        return True, "no design source — nothing to be stale against"


def load(c: Ctx) -> Design:
    name = str(c.cfg("design.provider", "none"))
    if name == "none":
        return Design(c)
    mod_path = c.root / ".vteam" / "providers" / f"design_{name}.py"
    if not mod_path.is_file():
        dev = Path(__file__).resolve().parents[3] / "providers" / "design" / f"{name}.py"
        if dev.is_file():
            mod_path = dev
        else:
            raise SystemExit(f"design: provider {name!r} not installed ({mod_path} missing)")
    spec = importlib.util.spec_from_file_location(f"design_{name}", mod_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod.Provider(c)
