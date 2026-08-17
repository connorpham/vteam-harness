#!/usr/bin/env python3
"""gate.py — the verification-gate driver: runs the stack profile's step manifest.

Reads profiles/<stack.profile>/gates.yaml (installed at .vteam/profiles/…), runs
the steps IN ORDER, stops at the first red, prints `GATE: RED at <step>` or
`GATE: GREEN`. The order philosophy (cheapest & most blind-spot-covering first)
lives in the manifest; this driver only enforces it.

Manifest step shape (vteam YAML subset):
    steps:
      lint:
        run: "npm run lint"
        requires: "package.json"     # optional: skip-with-declared-reason when absent
        skip_reason: "no package.json — not a Node project"
        tail: false                  # optional: only runs when the tail arg (e.g. e2e) is passed
Rules the driver enforces:
  · A step with no `run` is a MANIFEST error (red), not a skip.
  · A step whose `requires` file is absent is skipped LOUDLY with its declared
    skip_reason — a step absent with no skip_reason is RED. Silent skips are the
    hole this driver exists to close.
  · `tail: true` steps run only when their tail name is passed (gate.py e2e).
Usage: gate.py [e2e] ; wrapped by gate.sh for muscle memory.
"""
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "lib"))
from ctx import Ctx, parse_config  # noqa: E402


def find_manifest(c: Ctx, profile: str) -> Path:
    for cand in (
        c.root / ".vteam" / "profiles" / profile / "gates.yaml",
        Path(__file__).resolve().parent.parent.parent / "profiles" / profile / "gates.yaml",
    ):
        if cand.is_file():
            return cand
    sys.exit(f"gate: no gates.yaml for profile {profile!r} — broken install")


def main() -> int:
    c = Ctx()
    tails = {a for a in sys.argv[1:]}
    profile = str(c.cfg("stack.profile", "generic"))
    manifest = parse_config(find_manifest(c, profile).read_text(encoding="utf-8"))
    steps = manifest.get("steps", {})
    if not steps:
        print(f"GATE: RED at manifest — profile {profile!r} declares no steps")
        return 1
    ran, skipped = [], []
    for name, spec in steps.items():
        if not isinstance(spec, dict) or not spec.get("run"):
            print(f"GATE: RED at {name} — manifest step has no `run` (a step that "
                  f"cannot run is a manifest error, not a skip)")
            return 1
        tail = spec.get("tail", False)
        if tail and "e2e" not in tails and name not in tails:
            skipped.append((name, "tail step — run `gate e2e` to include it"))
            continue
        req = spec.get("requires")
        if req and not (c.root / str(req)).exists():
            reason = spec.get("skip_reason")
            if not reason:
                print(f"GATE: RED at {name} — requires {req} which is absent, and "
                      f"the manifest declares no skip_reason (silent skips are forbidden)")
                return 1
            skipped.append((name, f"{req} absent — {reason}"))
            continue
        print(f"▶ {name}: {spec['run']}", flush=True)
        r = subprocess.run(spec["run"], shell=True, cwd=c.root)
        if r.returncode != 0:
            print(f"GATE: RED at {name}")
            return 1
        ran.append(name)
    for name, why in skipped:
        print(f"⚠️  skipped {name}: {why}")
    print(f"GATE: GREEN ({len(ran)} steps ran, {len(skipped)} declared skips)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
