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
        requires_cmd: node -e '…'    # optional: a probe COMMAND, run silently;
                                     # nonzero exit → declared skip (same law as requires)
        skip_reason: "no package.json — not a Node project"
        tail: false                  # optional: only runs when the tail arg (e.g. e2e) is passed
Rules the driver enforces:
  · A step with no `run` is a MANIFEST error (red), not a skip.
  · A step whose `requires` file is absent is skipped LOUDLY with its declared
    skip_reason — a step absent with no skip_reason is RED. Silent skips are the
    hole this driver exists to close.
  · `requires_cmd` is probed with output CAPTURED (never printed on green);
    nonzero exit skips the step loudly with its skip_reason — no skip_reason is
    RED, exactly like `requires`. Use it where file existence can't tell the
    truth (e.g. "is package.json's scripts.test a real suite?").
  · `tail: true` steps run only when their tail name is passed (gate.py e2e).
  · `{package_manager}` / `{project.key}` in a `run` or `requires_cmd` are
    substituted from config (stack.package_manager, project.key) — manifests
    stay stack-agnostic.
  · GREEN comes in two honest flavors: a run where only bookkeeping steps
    (docs-shrink/ledger/verbatim/lockfile — they guard the ledgers, not the
    code) executed, or where the test-suite step (`unit`/`test`) was skipped,
    prints GREEN (WEAK — …) naming exactly what did NOT run.

TRUST BOUNDARY — read before editing gates.yaml: every step's `run` executes as
a SHELL COMMAND with the repo as cwd. gates.yaml is repo-committed and
agent-editable, so write access to the repo IS execute access here — the same
deal as package.json scripts or a Makefile, deliberately. Review manifest
changes like you review code, and treat a diff that touches gates.yaml in a PR
as high-stakes.

Usage: gate.py [e2e] ; wrapped by gate.sh for muscle memory.
Selftest: gate.py --selftest (green/red/skip/no-reason/substitution fixtures +
requires_cmd green/skip/red + both WEAK banners + the echo-test tripwire).
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
        req_cmd = spec.get("requires_cmd")
        if req_cmd:
            # probe SILENTLY (output captured); the trust boundary above applies —
            # a probe is a shell command from the repo like every `run`
            probe = subprocess.run(substitute(str(req_cmd), c), shell=True,
                                   cwd=c.root, capture_output=True)
            if probe.returncode != 0:
                reason = spec.get("skip_reason")
                if not reason:
                    print(f"GATE: RED at {name} — requires_cmd probe exited "
                          f"{probe.returncode}, and the manifest declares no "
                          f"skip_reason (silent skips are forbidden)")
                    return 1
                skipped.append((name, f"requires_cmd probe failed — {reason}"))
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
    # Bookkeeping steps guard the ledgers, not the code. A green where ONLY they
    # ran is honest but weak — say so, loudly (field-trial finding #19: a Go repo
    # on the generic profile read as plain GREEN with zero verification run).
    # lockfile guards the dependency ledger, not behavior — it counts as
    # bookkeeping too (audit L5).
    BOOKKEEPING = {"docs-shrink", "ledger", "verbatim", "lockfile"}
    skipped_names = {s for s, _ in skipped}
    if all(s in BOOKKEEPING for s in ran):
        print(f"GATE: GREEN (WEAK — only bookkeeping steps ran, ZERO verification "
              f"of the code; {len(skipped)} declared skips). Declare test/build "
              f"entrypoints or switch to a stack profile that runs them.")
    elif skipped_names & {"unit", "test"}:
        # other real steps ran, but the SUITE didn't — a green that verified no
        # behavior must never read like one that did (Q3: legacy repos with no
        # tests get an honest weak green, not a fake full one)
        print(f"GATE: GREEN (WEAK — no test suite ran; this repo has no automated "
              f"verification of behavior. {len(ran)} steps ran, "
              f"{len(skipped)} declared skips)")
    else:
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

        # requires_cmd: probe exit 0 → the step RUNS, probe output stays SILENT
        root = setup("steps:\n  probed:\n    run: \"echo probed-ran\"\n"
                     "    requires_cmd: \"echo probe-noise\"\n")
        roots.append(root)
        r = run_gate(root)
        assert r.returncode == 0 and "probed-ran" in r.stdout, r.stdout
        assert "probe-noise" not in r.stdout, f"probe output must be captured:\n{r.stdout}"

        # requires_cmd probe fails + skip_reason → LOUD declared skip
        root = setup("steps:\n  real:\n    run: \"echo real-ran\"\n"
                     "  probed:\n    run: \"echo never\"\n"
                     "    requires_cmd: \"exit 7\"\n"
                     "    skip_reason: \"probe says the tool is absent\"\n")
        roots.append(root)
        r = run_gate(root)
        assert r.returncode == 0 and "skipped probed" in r.stdout \
            and "probe says the tool is absent" in r.stdout, r.stdout
        assert "never" not in r.stdout, "a skipped step still ran"

        # requires_cmd probe fails with NO skip_reason → RED, same law as requires
        root = setup("steps:\n  probed:\n    run: \"echo never\"\n"
                     "    requires_cmd: \"exit 7\"\n")
        roots.append(root)
        r = run_gate(root)
        assert r.returncode == 1 and "silent skips are forbidden" in r.stdout, r.stdout

        # WEAK banner: the unit step skipped while another real step ran must
        # say plainly that no test suite ran (Q3 honesty)
        root = setup("steps:\n  lint:\n    run: \"echo lint-ok\"\n"
                     "  unit:\n    run: \"echo tests\"\n"
                     "    requires_cmd: \"exit 1\"\n"
                     "    skip_reason: \"no real test script\"\n")
        roots.append(root)
        r = run_gate(root)
        assert r.returncode == 0 and "no test suite ran" in r.stdout, r.stdout

        # WEAK banner: lockfile counts as bookkeeping (L5) — a lockfile-plus-
        # ledgers run is still ZERO verification of the code
        root = setup("steps:\n  docs-shrink:\n    run: \"echo ok\"\n"
                     "  lockfile:\n    run: \"echo ok\"\n")
        roots.append(root)
        r = run_gate(root)
        assert r.returncode == 0 and "only bookkeeping steps ran" in r.stdout, r.stdout

        # the echo-test TRIPWIRE: the node profile's unit probe must reject the
        # obvious no-op scripts and accept a real one (heuristic, not proof —
        # the manifest comment says so; this proves the tripwire itself works)
        node_manifest = next((p for p in (
            self_path.parents[2] / "profiles" / "node" / "gates.yaml",
            self_path.parents[1] / "profiles" / "node" / "gates.yaml",
        ) if p.is_file()), None)
        if node_manifest is None:
            print("gate selftest: note — node profile manifest not installed here; "
                  "echo-test tripwire fixtures not exercised")
        else:
            assert shutil.which("node"), \
                "node not on PATH — cannot prove the unit-probe tripwire"
            unit = parse_config(node_manifest.read_text(encoding="utf-8"))["steps"]["unit"]
            probe = str(unit.get("requires_cmd") or "")
            assert probe, "node profile unit step must carry a requires_cmd probe"
            assert "no real test script" in str(unit.get("skip_reason") or ""), unit
            for pkg, must_fail in (
                ('{"scripts":{"test":"echo fake-green && exit 0"}}', True),
                ('{"scripts":{"test":"true"}}', True),
                ('{"scripts":{"test":"exit 0"}}', True),
                ('{"scripts":{}}', True),
                ('{"scripts":{"test":"node --test"}}', False),
            ):
                root = Path(tempfile.mkdtemp())
                roots.append(root)
                (root / "package.json").write_text(pkg, encoding="utf-8")
                pr = subprocess.run(probe, shell=True, cwd=root, capture_output=True)
                assert (pr.returncode != 0) == must_fail, \
                    f"tripwire wrong on {pkg}: exit {pr.returncode}"
        _ = os
    finally:
        for root in roots:
            shutil.rmtree(root, ignore_errors=True)
    print("gate selftest: OK (green + substitution, red stops, run-less red, "
          "silent-skip red, declared skip loud, requires_cmd green/skip/red, "
          "2 WEAK banners, echo-test tripwire)")


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        _selftest()
        sys.exit(0)
    sys.exit(main())
