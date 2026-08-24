"""vteam context — the ONE place gates resolve repo root, config and env.

Replaces two bug classes from the source harness (see docs/DESIGN.md §2):
  - ROOT = Path(__file__).parents[4]  ×7 scripts — broke on any install-depth change
  - hand-rolled load_env() duplicated in 6 scripts

Config is a constrained YAML subset (what vteam.config.example.yaml uses):
scalars, nested mappings, inline [a, b] and dash lists, and flow mappings
{a: b, c: [x, y]} — same behavior as ctx.mjs, fenced by tests/conformance.mjs.
No anchors, no multiline strings, no '#' inside values, no tab indentation
(tabs inside values are fine) — the parser fails loudly on anything outside
the subset rather than guessing.

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


def _split_top(s: str, ln: int) -> list[str]:
    """Split a flow body on commas at nesting depth 0 — a comma inside [], {}
    or quotes is data, not a separator. Mirrors ctx.mjs splitTop exactly."""
    parts, buf, depth, quote = [], [], 0, ""
    for ch in s:
        if quote:
            buf.append(ch)
            if ch == quote:
                quote = ""
        elif ch in ("'", '"'):
            quote = ch
            buf.append(ch)
        elif ch in "[{":
            depth += 1
            buf.append(ch)
        elif ch in "]}":
            depth -= 1
            if depth < 0:
                _die(ln, f"unbalanced brackets in flow value: {s!r}")
            buf.append(ch)
        elif ch == "," and depth == 0:
            parts.append("".join(buf))
            buf = []
        else:
            buf.append(ch)
    if depth != 0 or quote:
        _die(ln, f"unbalanced brackets in flow value: {s!r}")
    parts.append("".join(buf))
    return parts


def _parse_scalar(s: str, ln: int):
    s = s.strip()
    if s[:1] in ("&", "*") or s in ("|", ">") or s[:2] in ("| ", "> "):
        _die(ln, f"outside the vteam YAML subset (anchors/multiline): {s!r}")
    if s.startswith("["):
        if not s.endswith("]"):
            _die(ln, f"unterminated inline list: {s!r}")
        inner = s[1:-1].strip()
        return [] if not inner else [_parse_scalar(x, ln) for x in _split_top(inner, ln)]
    if s.startswith("{"):  # flow mapping {a: b, c: [x, y]} — same as ctx.mjs
        if not s.endswith("}"):
            _die(ln, f"unterminated flow mapping: {s!r}")
        inner = s[1:-1].strip()
        obj: dict = {}
        if not inner:
            return obj
        for part in _split_top(inner, ln):
            m = re.fullmatch(r"\s*([A-Za-z_][A-Za-z0-9_-]*)\s*:\s*(.+?)\s*", part)
            if not m:
                _die(ln, f"bad flow mapping entry: {part.strip()!r}")
            obj[m.group(1)] = _parse_scalar(m.group(2), ln)
        return obj
    if ((s.startswith('"') and s.endswith('"')) or
            (s.startswith("'") and s.endswith("'"))) and len(s) >= 2:
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
        if raw.lstrip().startswith("#") or not raw.strip():
            continue
        if "\t" in raw[:len(raw) - len(raw.lstrip())]:  # tabs INSIDE values stay legal
            _die(ln, "tab indentation is not supported — use spaces")
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
            sys.exit(f"ctx: {CONFIG_NAME} not found at repo root — run `npx vteam-harness init`")
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
    if example is not None:
        sample = example.read_text(encoding="utf-8")
    else:  # installed repos don't carry the package templates — embedded sample
        sample = (
            "version: 1\nproject:\n  key: PROJ\npaths:\n  pm: docs/pm\n"
            "git:\n  branch_pattern: \"^(feat|fix)/{key}-[0-9]+-\"\n"
            "tracker:\n  done_statuses: [Done, Closed, Resolved]\n"
            "autonomy:\n  exemptions:\n    - real-money\n"
            "team:\n  capacity_per_day: 0.8\nreview:\n  high_stakes_paths: []\n"
        )
    cfg = parse_config(sample)
    assert cfg["version"] == 1
    assert cfg["project"]["key"] == "PROJ"
    assert cfg["paths"]["pm"] == "docs/pm"
    assert cfg["git"]["branch_pattern"] == "^(feat|fix)/{key}-[0-9]+-"
    assert cfg["tracker"]["done_statuses"] == ["Done", "Closed", "Resolved"]
    assert cfg["autonomy"]["exemptions"][0] == "real-money"
    assert cfg["team"]["capacity_per_day"] == 0.8
    assert cfg["review"]["high_stakes_paths"] == []
    # flow mappings — parity with ctx.mjs (H2), incl. a 2-element list inside
    # a flow map, the exact shape README's by_label ships (H3):
    flow = parse_config(
        "stack: { profile: node, package_manager: npm }\n"
        "docs:\n  task_context:\n"
        "    by_label: { payment: [a.md, b.md], auth: [c.md] }\n"
    )
    assert flow["stack"]["profile"] == "node"
    assert flow["stack"]["package_manager"] == "npm"
    assert flow["docs"]["task_context"]["by_label"]["payment"] == ["a.md", "b.md"]
    assert flow["docs"]["task_context"]["by_label"]["auth"] == ["c.md"]
    # mutation half — a gate that has never been red does not exist:
    bads = ("b: &anchor x\n", "a:\n  - 1\n - 2\n", "weird ! line\n",
            "a:\n\tb: 1\n",          # tab indentation must die loudly (H10)
            "x: { a }\n",            # flow entry without a value
            "x: { a: b\n")           # unterminated flow mapping
    for bad in bads:
        r = subprocess.run([sys.executable, __file__, "--parse-stdin"],
                           input=bad, capture_output=True, text=True)
        assert r.returncode != 0, f"selftest: should have rejected {bad!r}"
    print(f"ctx.py selftest: OK (parse green + flow mappings + {len(bads)} mutations red)")


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        _selftest()
    elif "--parse-stdin" in sys.argv:
        parse_config(sys.stdin.read())
    elif len(sys.argv) > 1:
        print(Ctx().cfg(sys.argv[1]))
    else:
        print(__doc__)
