#!/usr/bin/env python3
"""bdd_report_check.py — an AI's BDD report must read like a person wrote it:
Given/When/Then, complete (every scenario ends in an observable outcome), and
concise (no rambling, no code-speak in the human body).

Why: vteam demands plain-language reports, but "plain" and "not rambling" were
style wishes a gate couldn't hold. A BDD report (`*.bdd.md` under the evidence
tree) is a structured human account — each thing the AI did or verified as a
`Scenario:` with Given/When/Then in ordinary words. This gate makes it red-able:
structure present, the Then is a real outcome (not "works"/"OK"), no code-speak
(file paths, function() calls, SQL, HTTP verb+route) in the scenario body — that
belongs in an appendix — and every step and scenario stays under a length cap so
"đầy đủ nhưng không dài dòng" is enforced, not hoped for.

OPT-IN: scans `{paths.evidence}/**/*.bdd.md`; inert-green when none exist.

Usage: bdd_report_check.py [--root <dir>] [<file.bdd.md> ...]
Exit 0 = every BDD report is readable/complete/concise (or none); 1 = what's off.
Selftest: --selftest (good report green + each rule proved red).
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

MAX_STEP_WORDS = 30       # a Given/When/Then step longer than this is rambling
MAX_SCENARIO_LINES = 15   # non-blank lines in one scenario

# A Then that is ONLY one of these says nothing — same discipline as evd_check.
FILLER = {"works", "work", "works fine", "works correctly", "correct", "correctly",
          "properly", "ok", "okay", "fine", "success", "successful", "successfully",
          "passes", "passed", "pass", "no errors", "no error", "no issues", "done",
          "as expected", "behaves as expected", "good", "great"}

# Code-speak that does not belong in a human scenario (it goes in an appendix).
CODE_SPEAK = [
    (re.compile(r"\b[\w./-]+\.(?:ts|tsx|js|jsx|mjs|py|sh|go|rs|java|kt|rb|php|prisma|sql|json|ya?ml|css|scss|html)\b"),
     "a file path"),
    (re.compile(r"\b[A-Za-z_]\w*\([^)]*\)"), "a function() call"),
    (re.compile(r"\b(?:SELECT|INSERT|UPDATE|DELETE|FROM|WHERE|JOIN)\b\s"), "an SQL keyword"),
    (re.compile(r"\b(?:GET|POST|PUT|PATCH|DELETE)\s+/"), "an HTTP verb + route"),
]

STEP = re.compile(r"^\s*(?:[-*]\s*)?(Given|When|Then|And|But)\b[:\s]*(.*)$", re.I)
SCENARIO = re.compile(r"^\s*#{0,4}\s*Scenario\b[:\s]*(.*)$", re.I)


def parse_scenarios(text: str) -> list[dict]:
    """Split into scenarios; each keeps its title, steps [(kw, text)], line count."""
    scs: list[dict] = []
    cur: dict | None = None
    for line in text.splitlines():
        m = SCENARIO.match(line)
        if m:
            cur = {"title": m.group(1).strip(), "steps": [], "lines": 1}
            scs.append(cur)
            continue
        if cur is None:
            continue
        if line.strip():
            cur["lines"] += 1
        s = STEP.match(line)
        if s:
            cur["steps"].append((s.group(1).lower(), s.group(2).strip()))
    return scs


def _kw_set(steps):
    """And/But inherit the previous real keyword, so a scenario with
    Given/And/And/Then/When still counts as having all three anchors."""
    seen, last = set(), None
    for kw, _ in steps:
        if kw in ("given", "when", "then"):
            seen.add(kw); last = kw
        elif kw in ("and", "but") and last:
            seen.add(last)
    return seen


def check_scenario(sc: dict) -> list[str]:
    errs = []
    tag = f"Scenario '{sc['title'] or '(untitled)'}'"
    if not sc["title"]:
        errs.append(f"{tag}: no title — name what this scenario is about")
    kws = _kw_set(sc["steps"])
    for need in ("given", "when", "then"):
        if need not in kws:
            errs.append(f"{tag}: missing a {need.capitalize()} step")
    # the Then(s) must be observable outcomes, not filler
    thens = [t for kw, t in sc["steps"] if kw == "then"]
    for t in thens:
        bare = re.sub(r"[^\w ]", "", t).strip().lower()
        # strip filler stopwords so "it works" / "the result is OK" reduce to the
        # empty claim they really are
        reduced = " ".join(w for w in bare.split()
                           if w not in {"it", "the", "this", "that", "everything",
                                        "all", "is", "are", "now", "then", "result", "a"})
        if not bare:
            errs.append(f"{tag}: a Then is empty — state what actually happens")
        elif not reduced or reduced in FILLER or bare in FILLER:
            errs.append(f"{tag}: Then says nothing observable ({t!r}) — state what a person would SEE, not '{t}'")
    # plain language: no code-speak in any step body
    for kw, t in sc["steps"]:
        for rx, what in CODE_SPEAK:
            hit = rx.search(t)
            if hit:
                errs.append(f"{tag}: {kw.capitalize()} contains {what} ({hit.group(0)!r}) — "
                            f"keep code out of the human scenario; put it in an appendix")
                break
    # conciseness
    for kw, t in sc["steps"]:
        n = len(t.split())
        if n > MAX_STEP_WORDS:
            errs.append(f"{tag}: the {kw.capitalize()} step is {n} words (> {MAX_STEP_WORDS}) — too long-winded; split or trim")
    if sc["lines"] > MAX_SCENARIO_LINES:
        errs.append(f"{tag}: {sc['lines']} lines (> {MAX_SCENARIO_LINES}) — a scenario should be scannable, not a wall")
    return errs


def check_report(text: str) -> list[str]:
    scs = parse_scenarios(text)
    if not scs:
        return ["no `Scenario:` found — a BDD report is one or more Given/When/Then scenarios"]
    errs = []
    for sc in scs:
        errs.extend(check_scenario(sc))
    return errs


def main() -> int:
    args = [a for a in sys.argv[1:] if a != "--root" and not a.startswith("--")]
    files: list[Path]
    if "--root" in sys.argv:
        root = Path(sys.argv[sys.argv.index("--root") + 1])
    else:
        sys.path.insert(0, str(Path(__file__).resolve().parent / "lib"))
        from ctx import Ctx  # noqa: E402
        root = Ctx().root
    if args:
        files = [Path(a) for a in args]
    else:
        ev = "evd"
        try:
            sys.path.insert(0, str(Path(__file__).resolve().parent / "lib"))
            from ctx import Ctx  # noqa: E402
            ev = str(Ctx().cfg("paths.evidence", "evd"))
        except Exception:
            pass
        files = sorted((root / ev).rglob("*.bdd.md")) if (root / ev).is_dir() else []
    if not files:
        print("✅ bdd_report_check: no *.bdd.md reports — nothing to check")
        return 0
    total = 0
    for f in files:
        errs = check_report(f.read_text(encoding="utf-8", errors="replace"))
        if errs:
            print(f"❌ bdd_report_check: {f} — {len(errs)} problems")
            for e in errs:
                print(f"   - {e}")
            total += len(errs)
    if total:
        return 1
    print(f"✅ bdd_report_check: {len(files)} BDD report(s) readable, complete and concise")
    return 0


def _selftest() -> None:
    good = """## Scenario: The discount applies at checkout
Given a member has a cart worth 500,000 ₫
When they enter a valid discount code and press Pay
Then the total drops to 450,000 ₫ and the order confirmation shows the saving
"""
    assert check_report(good) == [], check_report(good)
    muts = {
        "missing When": (good.replace("When they enter a valid discount code and press Pay\n", ""), "missing a When"),
        "filler Then": (good.replace("Then the total drops to 450,000 ₫ and the order confirmation shows the saving", "Then it works"), "says nothing observable"),
        "code-speak": (good.replace("they enter a valid discount code and press Pay", "they call applyDiscount(cart) on the server"), "function() call"),
        "file path": (good.replace("the order confirmation shows the saving", "src/checkout.ts updates the total"), "a file path"),
        "rambling step": (good.replace("Given a member has a cart worth 500,000 ₫",
                          "Given " + "a very long ".join(["member"] * 20)), "words"),
        "no scenario": ("Just some prose with no Given When Then at all.", "no `Scenario:`"),
    }
    for name, (text, needle) in muts.items():
        errs = check_report(text)
        assert any(needle in e for e in errs), f"mutation {name!r} should red: {errs}"
    # And/But inheritance: Given/And/Then/When still counts
    andbut = """## Scenario: A staff member is refused another branch's order
Given a staff account is signed in
And it belongs to the north branch
When it opens a south-branch order by its link
Then the screen refuses with a not-allowed message and shows nothing else
"""
    assert check_report(andbut) == [], check_report(andbut)
    print("bdd_report_check selftest: OK (good green + 6 mutations red + And/But inheritance)")


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        _selftest()
    else:
        sys.exit(main())
