#!/usr/bin/env python3
"""context_budget.py — how much doctrine a lane LOADS at start, in bytes and ≈tokens.

Why: the 2026-09 benchmark critique said "31 competencies bloat the agent's
context" and nobody could answer with a number. Skills load on demand, but a
lane's skill tells the agent to read further files before any ticket work.
This tool measures exactly that, from the rendered skill, so the claim can be
checked instead of argued (VT-33).

    python3 .vteam/scripts/context_budget.py --lane dev      # one lane
    python3 .vteam/scripts/context_budget.py --all           # every lane that exists
    python3 .vteam/scripts/context_budget.py --all --json    # for machines
    python3 .vteam/scripts/context_budget.py --selftest

What counts as MANDATORY (loaded on every run of the lane, before the ticket):
  · the lane's rendered skill itself (.claude/skills/<lane>/SKILL.md, or
    core/workflows/<lane>.md inside the framework repo);
  · every existing repo file the skill names in backticks that is a role
    playbook (docs/team/roles/*.md), an identity (…/<lane>-identity.md) or a
    competency INDEX (…/competencies/<lane>/INDEX.md);
  · every competency the INDEX marks `always` (loaded at T2/T3 on every ticket).
Everything else the skill names (docs/, .vteam/, core/doctrine/ paths that
exist) is ON DEMAND — listed with its size, NOT added to the mandatory total,
because it is read only when a ticket's labels/paths/terms match. The
SessionStart hook's few injected lines are not counted.

Tokens are ≈ bytes / 4 — a stated approximation, the same for every lane, good
enough to compare lanes and to notice a doubling. The total is compared to
`team.context_budget_tokens` (default 40000) and `⚠️  over budget` is printed
when exceeded. This is a MEASUREMENT, not a fence: exit 0 always (usage errors
exit 2, --selftest exits 1 on failure). It runs as an ADVISORY gate step.
"""
from __future__ import annotations

import json
import math
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "lib"))
from ctx import Ctx  # noqa: E402

LANES = ["dev", "ba", "pm", "qa", "verify", "team", "plan", "docs"]
DEFAULT_BUDGET = 40000
PATH_RE = re.compile(r"`((?:docs/|\.vteam/|core/doctrine/)[A-Za-z0-9_./-]*[A-Za-z0-9_-]\.[A-Za-z0-9]+)`")
# `| `dev-codebase-design` | T2 | `always` | Use when… |` — the competency INDEX row shape
INDEX_ROW = re.compile(r"^\|\s*`([A-Za-z0-9_-]+)`\s*\|\s*([^|]*?)\s*\|\s*`?([^|`]*?)`?\s*\|", re.M)


def tokens_of(nbytes: int) -> int:
    return math.ceil(nbytes / 4)


def resolve_skill(root: Path, lane: str) -> Path | None:
    for rel in (f".claude/skills/{lane}/SKILL.md", f"core/workflows/{lane}.md"):
        p = root / rel
        if p.is_file():
            return p
    return None


def referenced_paths(text: str) -> list[str]:
    seen: list[str] = []
    for m in PATH_RE.finditer(text):
        if m.group(1) not in seen:
            seen.append(m.group(1))
    return seen


def why_mandatory(rel: str, lane: str) -> str | None:
    if "/roles/" in rel and rel.endswith(".md"):
        return "role playbook"
    if rel.endswith(f"{lane}-identity.md") or rel.endswith("-identity.md"):
        return "identity"
    if "/competencies/" in rel and rel.endswith("INDEX.md"):
        return "competency index"
    return None


def always_competencies(root: Path, index_rel: str) -> list[tuple[str, str]]:
    """(rel, loads_at) for every INDEX row whose Applies cell is `always`."""
    text = (root / index_rel).read_text(encoding="utf-8", errors="replace")
    base = index_rel.rsplit("/", 1)[0]
    out = []
    for name, loads, applies in INDEX_ROW.findall(text):
        if applies.strip() == "always":
            out.append((f"{base}/{name}.md", loads.strip() or "?"))
    return out


def measure_lane(root: Path, lane: str, budget: int) -> dict | None:
    skill = resolve_skill(root, lane)
    if skill is None:
        return None
    text = skill.read_text(encoding="utf-8", errors="replace")
    skill_rel = str(skill.relative_to(root))
    mandatory: list[dict] = [{"path": skill_rel, "bytes": skill.stat().st_size, "why": "the lane skill"}]
    on_demand: list[dict] = []
    listed = {skill_rel}

    def add(bucket: list[dict], rel: str, why: str) -> None:
        p = root / rel
        if rel in listed or not p.is_file():
            return  # a path that does not exist cannot be loaded; a repeat is one load
        listed.add(rel)
        bucket.append({"path": rel, "bytes": p.stat().st_size, "why": why})

    indexes: list[str] = []
    for rel in referenced_paths(text):
        why = why_mandatory(rel, lane)
        if why:
            add(mandatory, rel, why)
            if why == "competency index" and (root / rel).is_file():
                indexes.append(rel)
        else:
            add(on_demand, rel, "named by the skill; read when the ticket matches")
    for idx in indexes:
        for rel, loads in always_competencies(root, idx):
            add(mandatory, rel, f"INDEX `always`, loads at {loads}")

    for row in mandatory + on_demand:
        row["tokens"] = tokens_of(row["bytes"])
    m_bytes = sum(r["bytes"] for r in mandatory)
    d_bytes = sum(r["bytes"] for r in on_demand)
    return {
        "lane": lane,
        "skill": skill_rel,
        "mandatory": mandatory,
        "on_demand": on_demand,
        "mandatory_bytes": m_bytes,
        "mandatory_tokens": tokens_of(m_bytes),
        "on_demand_bytes": d_bytes,
        "on_demand_tokens": tokens_of(d_bytes),
        "budget_tokens": budget,
        "over_budget": tokens_of(m_bytes) > budget,
    }


def render(lane: dict) -> str:
    out = [f"── {lane['lane']}: {lane['skill']}"]
    out.append(f"   {'MANDATORY (every run)':<58} {'bytes':>7} {'≈tok':>6}")
    for r in lane["mandatory"]:
        out.append(f"   {r['path']:<58} {r['bytes']:>7} {r['tokens']:>6}   {r['why']}")
    flag = "  ⚠️  over budget" if lane["over_budget"] else ""
    out.append(f"   {'= mandatory total':<58} {lane['mandatory_bytes']:>7} {lane['mandatory_tokens']:>6}"
               f"   budget {lane['budget_tokens']}{flag}")
    if lane["on_demand"]:
        out.append(f"   {'ON DEMAND (when the ticket matches)':<58} {'bytes':>7} {'≈tok':>6}")
        for r in lane["on_demand"]:
            out.append(f"   {r['path']:<58} {r['bytes']:>7} {r['tokens']:>6}")
        out.append(f"   {'= on-demand total':<58} {lane['on_demand_bytes']:>7} {lane['on_demand_tokens']:>6}")
    return "\n".join(out)


def read_budget(c: Ctx) -> int:
    raw = c.cfg("team.context_budget_tokens", DEFAULT_BUDGET)
    try:
        return int(str(raw))
    except ValueError:
        print(f"context_budget: team.context_budget_tokens {raw!r} is not a number — using {DEFAULT_BUDGET}")
        return DEFAULT_BUDGET


def main(argv: list[str]) -> int:
    if "--lane" in argv:
        i = argv.index("--lane")
        lanes = [argv[i + 1]] if i + 1 < len(argv) else []
        if not lanes or lanes[0] not in LANES:
            print(f"context_budget: --lane needs one of {', '.join(LANES)}")
            return 2
    elif "--all" in argv:
        lanes = LANES
    else:
        print(__doc__)
        return 2
    c = Ctx()
    budget = read_budget(c)
    results = [r for r in (measure_lane(c.root, ln, budget) for ln in lanes) if r]
    if "--json" in argv:
        print(json.dumps({"tokens_are": "bytes / 4 (approximation)", "budget_tokens": budget,
                          "lanes": results}, indent=2, ensure_ascii=False))
        return 0
    if not results:
        print("context_budget: no lane skill found (.claude/skills/<lane>/SKILL.md or core/workflows/<lane>.md)")
        return 0
    print("context_budget — doctrine each lane loads at start (≈tokens = bytes / 4)")
    for r in results:
        print(render(r))
    over = [r["lane"] for r in results if r["over_budget"]]
    worst = max(results, key=lambda r: r["mandatory_tokens"])
    if over:
        print(f"⚠️  over budget ({budget} tokens): {', '.join(over)} — the lane loads more than team.context_budget_tokens before any ticket work")
    else:
        print(f"✅ context_budget: every lane within {budget} tokens at start "
              f"(heaviest: {worst['lane']} ≈ {worst['mandatory_tokens']} tokens mandatory)")
    return 0


def _selftest() -> None:
    import subprocess
    import tempfile

    self_path = Path(__file__).resolve()
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        subprocess.run(["git", "init", "-q", str(root)], check=True)
        (root / "vteam.config.yaml").write_text("version: 1\nteam:\n  context_budget_tokens: 40000\n",
                                                encoding="utf-8")
        skill = root / ".claude" / "skills" / "dev" / "SKILL.md"
        skill.parent.mkdir(parents=True)
        skill.write_text(
            "# dev\n\nread `docs/team/roles/dev.md` first, then "
            "`docs/team/competencies/dev/dev-identity.md` (missing on purpose).\n"
            "Load from `docs/team/competencies/dev/INDEX.md`; the brief includes "
            "`docs/team/review-standard.md`; `docs/team/roles/dev.md` again (a repeat is one load).\n",
            encoding="utf-8")
        (root / "docs" / "team" / "roles").mkdir(parents=True)
        (root / "docs" / "team" / "roles" / "dev.md").write_bytes(b"r" * 400)
        (root / "docs" / "team" / "review-standard.md").write_bytes(b"s" * 1000)
        comp = root / "docs" / "team" / "competencies" / "dev"
        comp.mkdir(parents=True)
        (comp / "INDEX.md").write_text(
            "| Competency | Loads at | Applies | Use when… |\n|---|---|---|---|\n"
            "| `dev-x` | T2 | `always` | always |\n"
            "| `dev-y` | T3 | `label:data, term:lock` | sometimes |\n", encoding="utf-8")
        (comp / "dev-x.md").write_bytes(b"x" * 200)
        (comp / "dev-y.md").write_bytes(b"y" * 300)

        r = measure_lane(root, "dev", 40000)
        assert r is not None, "the fake skill must resolve"
        paths = [m["path"] for m in r["mandatory"]]
        assert paths == [".claude/skills/dev/SKILL.md", "docs/team/roles/dev.md",
                         "docs/team/competencies/dev/INDEX.md",
                         "docs/team/competencies/dev/dev-x.md"], paths
        assert not any("dev-identity" in p for p in paths), "a missing file cannot be loaded"
        assert next(m for m in r["mandatory"] if m["path"].endswith("roles/dev.md"))["bytes"] == 400
        assert [d["path"] for d in r["on_demand"]] == ["docs/team/review-standard.md"], r["on_demand"]
        assert not any(d["path"].endswith("dev-y.md") for d in r["on_demand"]), \
            "a competency the INDEX does not mark always is neither mandatory nor named"
        skill_bytes = skill.stat().st_size
        assert r["mandatory_bytes"] == skill_bytes + 400 + (comp / "INDEX.md").stat().st_size + 200
        assert r["mandatory_tokens"] == math.ceil(r["mandatory_bytes"] / 4)
        assert r["over_budget"] is False

        out = subprocess.run([sys.executable, str(self_path), "--lane", "dev"], cwd=root,
                             capture_output=True, text=True)
        assert out.returncode == 0 and "= mandatory total" in out.stdout and "✅ context_budget" in out.stdout, out.stdout
        (root / "vteam.config.yaml").write_text("version: 1\nteam:\n  context_budget_tokens: 10\n",
                                                encoding="utf-8")
        out = subprocess.run([sys.executable, str(self_path), "--all"], cwd=root,
                             capture_output=True, text=True)
        assert out.returncode == 0 and "⚠️  over budget" in out.stdout, \
            f"a tiny budget must print the over-budget line and still exit 0:\n{out.stdout}"
        js = subprocess.run([sys.executable, str(self_path), "--all", "--json"], cwd=root,
                            capture_output=True, text=True)
        data = json.loads(js.stdout)
        assert data["budget_tokens"] == 10 and data["lanes"][0]["over_budget"] is True
        bad = subprocess.run([sys.executable, str(self_path), "--lane", "nope"], cwd=root,
                             capture_output=True, text=True)
        assert bad.returncode == 2, "an unknown lane is a usage error"
    print("context_budget selftest: OK (skill + role + INDEX + always-competency mandatory, missing file "
          "ignored, repeat counted once, on-demand listed apart, over-budget line at a tiny budget, "
          "json, unknown lane refused)")


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        _selftest()
    else:
        sys.exit(main(sys.argv[1:]))
