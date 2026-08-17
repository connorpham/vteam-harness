#!/usr/bin/env python3
"""model_route.py — resolve role → tier → the concrete model THIS tool wants.

The routing doctrine (model-routing.md) speaks in abstract tiers so it never
rots; this resolver turns a tier — or a pipeline role like `dev-r1` — into the
exact model name for the agent tool in use, from model-routing.data.yaml
(machine home of the mapping; docs/team copy first, package copy as fallback).

Usage:
  model_route.py dev-r2 --tool claude-code            → sonnet
  model_route.py dev-r2 --tool claude-code --high-stakes  → opus  (money/state diffs)
  model_route.py workhorse --tool cursor              → claude-opus-5
  model_route.py --table --tool claude-code           → markdown block for adapters
  model_route.py --selftest

Rules enforced here:
  · an unknown role/tier is an ERROR, not a guess;
  · a tool mapping of SET-ME fails LOUDLY (codex/copilot ship unset — set your
    models in the data file rather than trusting a rotting default);
  · `frontier` resolves but prints a stderr warning: never a default — it needs
    the failed-twice + owner-approved-spend trail (model-routing §2).
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "lib"))

TIERS = ("frontier", "workhorse", "standard", "utility")


def load_data(root: Path | None) -> dict:
    from ctx import parse_config
    cands = []
    if root is not None:
        cands.append(root / "docs" / "team" / "model-routing.data.yaml")
    cands.append(Path(__file__).resolve().parent.parent / "doctrine" / "model-routing.data.yaml")
    for c in cands:
        if c.is_file():
            return parse_config(c.read_text(encoding="utf-8"))
    sys.exit("model_route: model-routing.data.yaml not found — broken install")


def resolve(data: dict, what: str, tool: str, high_stakes: bool = False) -> str:
    routing = data.get("routing", {})
    tier = what if what in TIERS else routing.get(what)
    if tier is None:
        sys.exit(f"model_route: unknown role/tier {what!r} — known roles: "
                 f"{', '.join(sorted(routing))}; tiers: {', '.join(TIERS)}")
    if high_stakes:
        tier = data.get("high_stakes", {}).get(what, tier)
    tools = data.get("tools", {})
    if tool not in tools:
        sys.exit(f"model_route: no mapping for tool {tool!r} in model-routing.data.yaml "
                 f"(have: {', '.join(sorted(tools))})")
    model = tools[tool].get(tier)
    if not model or model == "SET-ME":
        sys.exit(f"model_route: tool {tool!r} tier {tier!r} is SET-ME — open "
                 f"model-routing.data.yaml and set your tool's real model names "
                 f"(refusing to guess a rotting default)")
    if tier == "frontier":
        print("⚠️  frontier: never a default — requires failed-twice + owner-approved "
              "spend, logged in the decision queue (model-routing §2)", file=sys.stderr)
    return str(model)


def table(data: dict, tool: str) -> str:
    tools = data.get("tools", {}).get(tool, {})
    routing = data.get("routing", {})
    hs = data.get("high_stakes", {})
    tier_row = " · ".join(f"`{t}` → **{tools.get(t, '?')}**" for t in TIERS)
    role_bits = []
    for role in sorted(routing):
        bit = f"{role}: {routing[role]}"
        if role in hs and hs[role] != routing[role]:
            bit += f" (high-stakes: {hs[role]})"
        role_bits.append(bit)
    warn = ("\n> ⚠️ Some tiers above are **SET-ME** — this tool's model names are not "
            "configured yet. Edit `model-routing.data.yaml` (tools section), then "
            "re-run `vteam update`; `model_route.py` refuses to resolve SET-ME."
            if any(tools.get(t) in (None, "SET-ME") for t in TIERS) else "")
    return (f"> **Model routing for this tool** (from `model-routing.data.yaml`, "
            f"snapshot {data.get('snapshot_date', '?')}):\n"
            f"> {tier_row}\n"
            f"> Roles → tiers: {' · '.join(role_bits)}\n"
            f"> Resolve at runtime: `python3 .vteam/scripts/model_route.py <role> "
            f"--tool {tool} [--high-stakes]` — high-stakes diffs "
            f"(review.high_stakes_*) bump dev-r2 to the workhorse tier." + warn)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("what", nargs="?", help="a role (dev-r1, qa-challenger, …) or a tier")
    ap.add_argument("--tool", default="claude-code")
    ap.add_argument("--high-stakes", action="store_true")
    ap.add_argument("--table", action="store_true")
    args = ap.parse_args()

    root = None
    try:
        from ctx import repo_root
        root = repo_root()
    except SystemExit:
        pass
    data = load_data(root)
    if args.table:
        print(table(data, args.tool))
        return 0
    if not args.what:
        print(__doc__)
        return 1
    print(resolve(data, args.what, args.tool, args.high_stakes))
    return 0


def _selftest():
    data = {
        "snapshot_date": "2026-01-01",
        "routing": {"dev-r1": "workhorse", "dev-r2": "standard", "explore": "utility"},
        "high_stakes": {"dev-r2": "workhorse"},
        "tools": {"claude-code": {"frontier": "fable", "workhorse": "opus",
                                  "standard": "sonnet", "utility": "haiku"},
                  "codex": {"workhorse": "SET-ME"}},
    }
    assert resolve(data, "dev-r1", "claude-code") == "opus"
    assert resolve(data, "dev-r2", "claude-code") == "sonnet"
    assert resolve(data, "dev-r2", "claude-code", high_stakes=True) == "opus"
    assert resolve(data, "standard", "claude-code") == "sonnet"  # bare tier works
    for bad in [("nonsense", "claude-code", {}), ("dev-r1", "unknown-tool", {}),
                ("dev-r1", "codex", {})]:  # unknown role / unknown tool / SET-ME
        try:
            resolve(data, bad[0], bad[1])
            raise AssertionError(f"{bad} should have exited")
        except SystemExit:
            pass
    tbl = table(data, "claude-code")
    assert "**opus**" in tbl and "dev-r2: standard (high-stakes: workhorse)" in tbl, tbl
    real = load_data(None)  # the shipped data file itself must resolve
    assert resolve(real, "dev-r1", "claude-code") == "opus"
    assert resolve(real, "qa-challenger", "cursor") == "claude-sonnet-5"
    print("model_route selftest: OK (resolve + high-stakes bump + 3 loud failures + table + shipped data)")


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        _selftest()
    else:
        sys.exit(main())
