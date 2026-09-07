#!/usr/bin/env python3
"""competency_check.py — a role's craft files must have the SHAPE that lets a
reviewer check them, and the lane must be able to find them.

Why: doctrine without competencies gave the team a rulebook and a supervisor
but no worker — the DEV lane knew WHEN to do things and nothing about HOW a
senior does them. Competencies fix that, but prose about craft is decoration
unless (a) each one ends in a "Reviewer lens" the R1/R2 brief can pull in, so
the craft is CHECKED by review, and (b) the lane can route to the right file
from a small index instead of reading every file. This gate makes both red-able.

Checks {paths.team}/competencies/<role>/*.md:
  1. Frontmatter: name (== filename, prefixed by the role), description (starts
     with "Use when" — describes the PROBLEM, never the procedure: a description
     that summarizes the workflow gets followed INSTEAD of the file), role,
     loads (a lane step), applies (routing tokens).
  2. `applies` grammar: `always` | `label:<x>` | `path:<prefix>` |
     `profile:<name>` | `term:<word>` — anything else is a typo the lane will
     silently never match.
  3. Required sections: Identity · When this applies · Decide · Rules ·
     Reviewer lens · Sources. Missing "Reviewer lens" = craft nobody can check.
  4. Body ≤ MAX_WORDS — a competency that needs more moves the bulk to a
     sibling reference file (progressive disclosure), or it eats the context
     budget the lane needs for the actual ticket.
  5. INDEX.md in each role dir lists exactly the files present (name ·
     loads · applies · description) — the lane reads THIS, not the tree.
     `--write-index` regenerates it.

Usage: competency_check.py [--write-index] [--root <dir>]
Exit 0 = every competency well-formed and indexed; 1 = exactly what's off.
Selftest: --selftest (valid file green + 6 mutations red, no repo needed).
"""
from __future__ import annotations

import re
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "lib"))

MAX_WORDS = 1100
REQUIRED_SECTIONS = ["Identity", "When this applies", "Decide", "Rules", "Reviewer lens", "Sources"]
REQUIRED_META = ["name", "description", "role", "loads", "applies"]
APPLIES = re.compile(r"^(always|label:[\w-]+|path:[\w./-]+|profile:[\w-]+|term:[\w-]+)$")
# A description that narrates the procedure ("first X, then Y → Z") is the
# failure mode superpowers measured: agents follow the summary and skip the body.
PROCEDURAL = re.compile(r"(→|\bthen\b|\bstep \d|\bfirst,|\bfinally\b)", re.I)
FM = re.compile(r"^---\n(.*?)\n---\n(.*)$", re.S)


def parse(text: str) -> tuple[dict[str, str], str]:
    m = FM.match(text)
    if not m:
        return {}, text
    meta: dict[str, str] = {}
    for line in m.group(1).splitlines():
        if ":" in line:
            k, v = line.split(":", 1)
            meta[k.strip()] = v.strip().strip('"').strip("'")
    return meta, m.group(2)


def check_file(path_name: str, text: str, role: str) -> list[str]:
    errs: list[str] = []
    meta, body = parse(text)
    if not meta:
        return [f"{path_name}: no frontmatter block"]
    for k in REQUIRED_META:
        if not meta.get(k):
            errs.append(f"{path_name}: frontmatter lacks `{k}`")
    name = meta.get("name", "")
    stem = Path(path_name).stem
    if name and name != stem:
        errs.append(f"{path_name}: name `{name}` != filename `{stem}` — the skill renderer keys on the name")
    if name and not name.startswith(f"{role}-"):
        errs.append(f"{path_name}: name must start with `{role}-` (the role owns its competencies)")
    if meta.get("role") and meta["role"] != role:
        errs.append(f"{path_name}: role `{meta['role']}` but the file lives under `{role}/`")
    desc = meta.get("description", "")
    if desc and not desc.startswith("Use when"):
        errs.append(f"{path_name}: description must start with `Use when` — it is the trigger, "
                    f"not the summary")
    if desc and PROCEDURAL.search(desc):
        errs.append(f"{path_name}: description narrates a procedure ({PROCEDURAL.search(desc).group(0)!r}) "
                    f"— agents follow the summary and skip the body; describe the PROBLEM")
    if len(desc) > 1024:
        errs.append(f"{path_name}: description > 1024 chars")
    for tok in [t.strip() for t in meta.get("applies", "").split(",") if t.strip()]:
        if not APPLIES.match(tok):
            errs.append(f"{path_name}: applies token {tok!r} is not always|label:|path:|profile:|term:")
    heads = {h.strip() for h in re.findall(r"^##\s+(.+)$", body, re.M)}
    for sec in REQUIRED_SECTIONS:
        if not any(h == sec or h.startswith(sec + " ") or h.startswith(sec + " —") for h in heads):
            errs.append(f"{path_name}: missing section `## {sec}`")
    words = len(body.split())
    if words > MAX_WORDS:
        errs.append(f"{path_name}: body is {words} words > {MAX_WORDS} — move the bulk to a reference file")
    return errs


def index_text(role: str, files: list[tuple[str, dict[str, str]]]) -> str:
    rows = [f"| `{m.get('name','')}` | {m.get('loads','')} | `{m.get('applies','')}` | {m.get('description','')} |"
            for _, m in sorted(files, key=lambda f: f[1].get("name", ""))]
    return ("# Competencies — " + role.upper() + " (index; the lane reads THIS, not the tree)\n\n"
            "Generated by `competency_check.py --write-index`; the gate reds a stale row.\n"
            "Load `always` rows at the step named in `loads`; load the others when a token\n"
            "matches the ticket's labels, the touched paths, the stack profile, or a term in\n"
            "the ticket/spec text. Every loaded file's **Reviewer lens** goes into the R1/R2 brief.\n\n"
            "| Competency | Loads at | Applies | Use when… |\n|---|---|---|---|\n"
            + "\n".join(rows) + "\n")


def check_dir(root: Path, write_index: bool) -> list[str]:
    errs: list[str] = []
    if not root.is_dir():
        return [f"{root} missing — run `vteam update` (competencies ship with the doctrine)"]
    roles = [d for d in sorted(root.iterdir()) if d.is_dir()]
    if not roles:
        return [f"{root} has no role directories"]
    for rd in roles:
        role = rd.name
        files: list[tuple[str, dict[str, str]]] = []
        for f in sorted(rd.glob("*.md")):
            if f.name == "INDEX.md":
                continue
            text = f.read_text(encoding="utf-8", errors="replace")
            errs.extend(check_file(f"{role}/{f.name}", text, role))
            files.append((f.name, parse(text)[0]))
        if not files:
            errs.append(f"{role}/: no competency files")
            continue
        want = index_text(role, files)
        idx = rd / "INDEX.md"
        if write_index:
            idx.write_text(want, encoding="utf-8")
            print(f"wrote {idx}")
        elif not idx.is_file():
            errs.append(f"{role}/INDEX.md missing — run `competency_check.py --write-index`")
        elif idx.read_text(encoding="utf-8") != want:
            errs.append(f"{role}/INDEX.md is stale — run `competency_check.py --write-index`")
    return errs


def main() -> int:
    args = sys.argv[1:]
    write_index = "--write-index" in args
    if "--root" in args:
        root = Path(args[args.index("--root") + 1])
    else:
        from ctx import Ctx  # noqa: E402
        c = Ctx()
        root = c.root / str(c.cfg("paths.team", "docs/team")) / "competencies"
    errs = check_dir(root, write_index)
    if errs:
        print(f"❌ competency_check: {len(errs)} problems under {root}")
        for e in errs:
            print(f"   - {e}")
        return 1
    n = sum(1 for _ in root.glob("*/*.md")) - sum(1 for _ in root.glob("*/INDEX.md"))
    print(f"✅ competency_check: {n} competencies well-formed and indexed under {root}")
    return 0


def _selftest() -> None:
    good = """---
name: dev-thing
description: "Use when a ticket touches the thing, or when the thing looks wrong."
role: dev
loads: T2
applies: always, label:thing, path:src/thing/
---

# Thing

## Identity
Who you are.
## When this applies
- symptom
## Decide
| a | b |
## Rules
- **Rule.** *Otherwise:* consequence.
## Reviewer lens
- try X
## Sources
somewhere
"""
    assert check_file("dev/dev-thing.md", good, "dev") == [], check_file("dev/dev-thing.md", good, "dev")
    mutations = {
        "no reviewer lens": (good.replace("## Reviewer lens", "## Notes"), "Reviewer lens"),
        "description is a summary": (good.replace("Use when a ticket", "Read the spec, then fix"), "Use when"),
        "procedural description": (good.replace("or when the thing looks wrong", "then run tests → commit"), "narrates a procedure"),
        "bad applies token": (good.replace("path:src/thing/", "paths:src"), "applies token"),
        "name != filename": (good.replace("name: dev-thing", "name: dev-other"), "!= filename"),
        "wrong role prefix": (good.replace("name: dev-thing", "name: qa-thing").replace("dev-thing.md", "x"), "must start with"),
        "too long": (good + ("word " * (MAX_WORDS + 1)), f"> {MAX_WORDS}"),
    }
    for label, (text, needle) in mutations.items():
        fname = "dev/dev-thing.md" if label != "wrong role prefix" else "dev/qa-thing.md"
        errs = check_file(fname, text, "dev")
        assert any(needle in e for e in errs), f"mutation {label!r} should have gone red: {errs}"
    # INDEX: missing → red; written → green; edited → red
    with tempfile.TemporaryDirectory() as td:
        root = Path(td) / "competencies"
        (root / "dev").mkdir(parents=True)
        (root / "dev" / "dev-thing.md").write_text(good)
        errs = check_dir(root, False)
        assert any("INDEX.md missing" in e for e in errs), errs
        assert check_dir(root, True) == []
        assert check_dir(root, False) == []
        idx = root / "dev" / "INDEX.md"
        idx.write_text(idx.read_text() + "| `dev-ghost` | T2 | `always` | Use when… |\n")
        errs = check_dir(root, False)
        assert any("stale" in e for e in errs), errs
    assert check_dir(Path("/nonexistent/competencies"), False)[0].startswith("/nonexistent")
    print("competency_check selftest: OK (valid file green + 7 mutations red + index missing/stale red)")


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        _selftest()
    else:
        sys.exit(main())
