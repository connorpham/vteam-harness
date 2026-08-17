#!/usr/bin/env python3
"""verbatim_gate.py — spec shards must be byte-identical to their source documents.

Each shard in {paths.specs}/ claims its numbered sections are VERBATIM extracts of
the source spec documents. This gate proves it by machine: every table row carrying
a requirement code (FR-xxx-nn, VAL-nn, MSG-nn, BR-nn, DR-nn, SYS-xxx-nn, …) in a
shard must be byte-identical to the same-coded row in the sources.

Why: extracting by line number that drifts one row is a SILENT error — the wrongly
grabbed content is still a plausible, well-formatted sentence, so eyeballs miss it.

Sources come from config: `specs.sources` (list of repo-relative paths). Files in
the shard dir that are NOT shards: INDEX.md, changes.md, anything ending in
-draft.md or -plan.*, and the reviews/ subdir.

Only the section headed "BA NOTES" (## … BA NOTES) may deviate — everything after
that heading is interpretation and is skipped.

Run: python3 .vteam/scripts/verbatim_gate.py     (0 = all rows match)
Selftest: --selftest (in-memory truth + one drifted row must red).
"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "lib"))
from ctx import Ctx  # noqa: E402

ROW = re.compile(r"^\| \*\*([A-Z][A-Z0-9]*(?:-[A-Z]{2,4})?-\d+)\*\* \|")
SKIP_NAMES = {"INDEX.md", "changes.md"}
BA_NOTES = re.compile(r"^##.*BA NOTES", re.I)


def build_truth(sources: list[Path]) -> tuple[dict, list]:
    truth, dupes = {}, []
    for src in sources:
        if not src.exists():
            sys.exit(f"verbatim_gate: source document missing: {src}")
        for line in src.read_text(encoding="utf-8").split("\n"):
            m = ROW.match(line)
            if not m:
                continue
            code = m.group(1)
            if code in truth and truth[code] != line:
                dupes.append(code)
            truth[code] = line
    return truth, dupes


def check_shard(name: str, text: str, truth: dict) -> tuple[list, int]:
    problems, checked = [], 0
    in_notes = False
    for i, line in enumerate(text.split("\n"), 1):
        if BA_NOTES.match(line):
            in_notes = True
        if in_notes:
            continue
        m = ROW.match(line)
        if not m:
            continue
        code = m.group(1)
        checked += 1
        where = f"{name}:{i}"
        if code not in truth:
            problems.append(f"{where}  {code}: code absent from the source documents")
        elif truth[code] != line:
            g = truth[code]
            j = next((k for k in range(min(len(line), len(g))) if line[k] != g[k]),
                     min(len(line), len(g)))
            problems.append(
                f"{where}  {code}: verbatim drift at char {j}\n"
                f"      shard : …{line[max(0, j - 45):j + 45]}\n"
                f"      source: …{g[max(0, j - 45):j + 45]}")
    return problems, checked


def main() -> int:
    c = Ctx()
    sources = [c.root / s for s in c.cfg("specs.sources", [])]
    if not sources:
        print("⚠️  verbatim_gate: no `specs.sources` configured — nothing to compare "
              "(configure it, or this gate guards nothing)")
        return 0
    truth, dupes = build_truth(sources)
    shard_dir = c.path("specs")
    problems, checked, files = [], 0, 0
    for f in sorted(shard_dir.glob("*.md")):
        if f.name in SKIP_NAMES or f.name.endswith("-draft.md") or "-plan" in f.name:
            continue
        files += 1
        p, n = check_shard(str(f.relative_to(c.root)), f.read_text(encoding="utf-8"), truth)
        problems += p
        checked += n
    print(f"verbatim_gate: {checked} coded rows across {files} shards")
    if dupes:
        print(f"  warning: {len(set(dupes))} codes appear in the sources more than "
              f"once with different content: {sorted(set(dupes))[:8]}")
    if problems:
        print(f"RESULT: {len(problems)} DEVIATIONS ❌\n")
        for p in problems:
            print("  -", p)
        print("\nFix: re-extract the row BY CODE (regex), never by line number.")
        return 1
    print("RESULT: every coded row matches the sources verbatim ✅")
    return 0


def _selftest():
    truth = {"FR-AUT-01": "| **FR-AUT-01** | Sign in by username | High |"}
    ok, n = check_shard("s.md", "| **FR-AUT-01** | Sign in by username | High |", truth)
    assert not ok and n == 1, ok
    drifted, _ = check_shard("s.md", "| **FR-AUT-01** | Sign in by email | High |", truth)
    assert drifted, "drifted row should red"
    unknown, _ = check_shard("s.md", "| **FR-ZZZ-99** | ghost | High |", truth)
    assert unknown, "unknown code should red"
    notes, n2 = check_shard("s.md", "## §9 BA NOTES\n| **FR-AUT-01** | reworded freely |", truth)
    assert not notes and n2 == 0, "BA NOTES section must be exempt"
    print("verbatim_gate selftest: OK (match green + drift/ghost red + notes exempt)")


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        _selftest()
    else:
        sys.exit(main())
