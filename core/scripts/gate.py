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
  · `{package_manager}` / `{project.key}` in a `run` are substituted from config
    (stack.package_manager, project.key) — manifests stay stack-agnostic.

TRUST BOUNDARY — read before editing gates.yaml: every step's `run` executes as
a SHELL COMMAND with the repo as cwd. gates.yaml is repo-committed and
agent-editable, so write access to the repo IS execute access here — the same
deal as package.json scripts or a Makefile, deliberately. Review manifest
changes like you review code, and treat a diff that touches gates.yaml in a PR
as high-stakes.

Usage: gate.py [e2e] ; wrapped by gate.sh for muscle memory.
Selftest: gate.py --selftest (green/red/skip/no-reason/substitution fixtures).
"""
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "lib"))
from ctx import Ctx, parse_config  # noqa: E402


def substitute(run: str, c: Ctx) -> str:
    """Config values into the manifest command — {package_manager}, {project.key}."""
    vals = {
        "package_manager": str(c.cfg("stack.package_manager", "npm")),
        "project.key": str(c.cfg("project.key", "PROJ")),
    }
    return re.sub(r"\{(package_manager|project\.key)\}",
                  lambda m: vals[m.group(1)], run)


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
        cmd = substitute(str(spec["run"]), c)
        print(f"▶ {name}: {cmd}", flush=True)
        # shell=True by design — the manifest IS a command file (see TRUST
        # BOUNDARY in the module docstring); the only shell exec in the framework.
        r = subprocess.run(cmd, shell=True, cwd=c.root)
        if r.returncode != 0:
            print(f"GATE: RED at {name}")
            return 1
        ran.append(name)
    for name, why in skipped:
        print(f"⚠️  skipped {name}: {why}")
    print(f"GATE: GREEN ({len(ran)} steps ran, {len(skipped)} declared skips)")
    return 0


def _selftest():
    """Driver mutation proof in a throwaway repo: green manifest passes, a red
    step stops the gate, a run-less step is a manifest error, requires-absent
    without skip_reason is red (WITH one is a loud skip), and {package_manager}
    substitutes from config."""
    import os
    import tempfile

    self_path = Path(__file__).resolve()

    def run_gate(root: Path) -> subprocess.CompletedProcess:
        return subprocess.run([sys.executable, str(self_path)],
                              cwd=root, capture_output=True, text=True)

    def setup(manifest: str) -> Path:
        root = Path(tempfile.mkdtemp())
        subprocess.run(["git", "init", "-q", str(root)], check=True)
        (root / "vteam.config.yaml").write_text(
            "version: 1\nproject:\n  key: TST\nstack:\n  profile: fixture\n"
            "  package_manager: pnpm\n", encoding="utf-8")
        d = root / ".vteam" / "profiles" / "fixture"
        d.mkdir(parents=True)
        (d / "gates.yaml").write_text(manifest, encoding="utf-8")
        return root

    import shutil
    roots = []
    try:
        # green + substitution: the pnpm from config must reach the command line
        root = setup("steps:\n  hello:\n    run: \"echo manager={package_manager} key={project.key}\"\n")
        roots.append(root)
        r = run_gate(root)
        assert r.returncode == 0 and "GATE: GREEN" in r.stdout, r.stdout + r.stderr
        assert "manager=pnpm" in r.stdout and "key=TST" in r.stdout, \
            f"substitution failed:\n{r.stdout}"

        # mutation: a failing step must stop the gate RED at that step
        root = setup("steps:\n  boom:\n    run: \"exit 3\"\n  after:\n    run: \"echo never\"\n")
        roots.append(root)
        r = run_gate(root)
        assert r.returncode == 1 and "GATE: RED at boom" in r.stdout, r.stdout
        assert "never" not in r.stdout, "steps after a red still ran"

        # mutation: a step with no `run` is a manifest error
        root = setup("steps:\n  ghost:\n    requires: \"x\"\n")
        roots.append(root)
        r = run_gate(root)
        assert r.returncode == 1 and "no `run`" in r.stdout, r.stdout

        # mutation: requires-absent with NO skip_reason is red…
        root = setup("steps:\n  maybe:\n    run: \"echo hi\"\n    requires: \"nope.json\"\n")
        roots.append(root)
        r = run_gate(root)
        assert r.returncode == 1 and "silent skips are forbidden" in r.stdout, r.stdout

        # …and WITH a skip_reason it is a LOUD skip, gate green
        root = setup("steps:\n  maybe:\n    run: \"echo hi\"\n    requires: \"nope.json\"\n"
                     "    skip_reason: \"not a widget project\"\n")
        roots.append(root)
        r = run_gate(root)
        assert r.returncode == 0 and "skipped maybe" in r.stdout \
            and "not a widget project" in r.stdout, r.stdout
        _ = os
    finally:
        for root in roots:
            shutil.rmtree(root, ignore_errors=True)
    print("gate selftest: OK (green + substitution, red stops, run-less red, "
          "silent-skip red, declared skip loud)")


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        _selftest()
        sys.exit(0)
    sys.exit(main())
