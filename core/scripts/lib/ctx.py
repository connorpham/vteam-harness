"""vteam context — the ONE place gates resolve repo root, config and env.

Replaces two bug classes from the source harness (see docs/DESIGN.md §2):
  - ROOT = Path(__file__).parents[4]  ×7 scripts — broke on any install-depth change
  - hand-rolled load_env() duplicated in 6 scripts

Config is a constrained YAML subset (what vteam.config.example.yaml uses):
scalars, nested mappings, inline [a, b] and dash lists. No anchors, no
multiline strings, no '#' inside values — the parser fails loudly on anything
outside the subset rather than guessing.

Usage:
    from ctx import Ctx
    c = Ctx()                       # resolves root via `git rev-parse`
    c.root                          # Path to repo root
    c.cfg("project.key")            # "PROJ" (raises if missing)
    c.cfg("project.go_live", None)  # default when absent
    c.path("pm")                    # Path to the configured docs/pm dir
    c.env("JIRA_API_TOKEN")         # .env-then-os lookup

Selftest:  python3 ctx.py --selftest   (includes a mutation: bad syntax must red)
"""
from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path

CONFIG_NAME = "vteam.config.yaml"
_MISSING = object()


def repo_root(start: Path | None = None) -> Path:
    out = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        cwd=str(start or Path.cwd()), capture_output=True, text=True,
    )
    if out.returncode != 0:
        sys.exit("ctx: not inside a git repository (git rev-parse failed)")
    return Path(out.stdout.strip())


def _die(ln: int, msg: str):
    sys.exit(f"ctx: {CONFIG_NAME}:{ln}: {msg}")


def _parse_scalar(s: str, ln: int):
    s = s.strip()
    if s[:1] in ("&", "*") or s in ("|", ">") or s[:2] in ("| ", "> "):
        _die(ln, f"outside the vteam YAML subset (anchors/multiline): {s!r}")
    if s.startswith("[") and s.endswith("]"):
        inner = s[1:-1].strip()
        return [] if not inner else [_parse_scalar(x, ln) for x in inner.split(",")]
    if (s.startswith('"') and s.endswith('"')) or (s.startswith("'") and s.endswith("'")):
        return s[1:-1]
    if s in ("true", "True"):
        return True
    if s in ("false", "False"):
        return False
    if re.fullmatch(r"-?\d+", s):
        return int(s)
    if re.fullmatch(r"-?\d+(\.\d+)?", s):
        return float(s)
    return s


def parse_config(text: str) -> dict:
    """Parse the vteam YAML subset. Fails loudly on anything outside it."""
    lines: list[tuple[int, int, str]] = []  # (lineno, indent, stripped)
    for ln, raw in enumerate(text.splitlines(), 1):
        if raw.lstrip().startswith("#"):
            continue
        s = re.sub(r"\s#.*$", "", raw).rstrip()  # subset: '#' never appears in values
        if s.strip():
            lines.append((ln, len(s) - len(s.lstrip(" ")), s.strip()))

    pos = 0

    def block(indent: int) -> dict:
        nonlocal pos
        d: dict = {}
        while pos < len(lines):
            ln, ind, s = lines[pos]
            if ind < indent:
                break
            if ind > indent:
                _die(ln, "bad indentation")
            if s.startswith("- "):
                _die(ln, "dash-list item without a parent key")
            m = re.fullmatch(r"([A-Za-z_][A-Za-z0-9_-]*):(?:\s*(.*))?", s)
            if not m:
                _die(ln, f"outside the vteam YAML subset: {s!r}")
            key, val = m.group(1), (m.group(2) or "").strip()
            pos += 1
            if val:
                d[key] = _parse_scalar(val, ln)
            elif pos < len(lines) and lines[pos][1] > ind:
                child_ind = lines[pos][1]
                if lines[pos][2].startswith("- "):
                    items = []
                    while (pos < len(lines) and lines[pos][1] == child_ind
                           and lines[pos][2].startswith("- ")):
                        items.append(_parse_scalar(lines[pos][2][2:], lines[pos][0]))
                        pos += 1
                    d[key] = items
                else:
                    d[key] = block(child_ind)
            else:
                d[key] = {}
        return d

    return block(lines[0][1]) if lines else {}


class Ctx:
    def __init__(self, start: Path | None = None):
        self.root = repo_root(start)
        cfg_file = self.root / CONFIG_NAME
        if not cfg_file.exists():
            sys.exit(f"ctx: {CONFIG_NAME} not found at repo root — run `npx vteam init`")
        self._cfg = parse_config(cfg_file.read_text(encoding="utf-8"))
        self._env = dict(os.environ)
        env_file = self.root / ".env"
        if env_file.exists():
            for raw in env_file.read_text(encoding="utf-8").splitlines():
                raw = raw.strip()
                if raw and not raw.startswith("#") and "=" in raw:
                    k, v = raw.split("=", 1)
                    self._env.setdefault(k.strip(), v.strip().strip('"').strip("'"))

    def cfg(self, dotted: str, default=_MISSING):
        node = self._cfg
        for part in dotted.split("."):
            if not isinstance(node, dict) or part not in node:
                if default is _MISSING:
                    sys.exit(f"ctx: missing config key {dotted!r} in {CONFIG_NAME}")
                return default
            node = node[part]
        return node

    def path(self, name: str) -> Path:
        return self.root / str(self.cfg(f"paths.{name}"))

    def env(self, key: str, default=None):
        return self._env.get(key, default)


def _selftest():
    here = Path(__file__).resolve()
    example = next(
        (p / "core" / "templates" / "vteam.config.example.yaml"
         for p in here.parents
         if (p / "core" / "templates" / "vteam.config.example.yaml").exists()),
        None,
    )
    assert example, "selftest: example config not found"
    cfg = parse_config(example.read_text(encoding="utf-8"))
    assert cfg["version"] == 1
    assert cfg["project"]["key"] == "PROJ"
    assert cfg["paths"]["pm"] == "docs/pm"
    assert cfg["git"]["branch_pattern"] == "^(feat|fix)/{key}-[0-9]+-"
    assert cfg["tracker"]["done_statuses"] == ["Done", "Closed", "Resolved"]
    assert cfg["autonomy"]["exemptions"][0] == "real-money"
    assert cfg["team"]["capacity_per_day"] == 0.8
    assert cfg["review"]["high_stakes_paths"] == []
    # mutation half — a gate that has never been red does not exist:
    for bad in ("b: &anchor x\n", "a:\n  - 1\n - 2\n", "weird ! line\n"):
        r = subprocess.run([sys.executable, __file__, "--parse-stdin"],
                           input=bad, capture_output=True, text=True)
        assert r.returncode != 0, f"selftest: should have rejected {bad!r}"
    print("ctx.py selftest: OK (parse green + 3 mutations red)")


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        _selftest()
    elif "--parse-stdin" in sys.argv:
        parse_config(sys.stdin.read())
    elif len(sys.argv) > 1:
        print(Ctx().cfg(sys.argv[1]))
    else:
        print(__doc__)
