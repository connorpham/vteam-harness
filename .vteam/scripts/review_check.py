#!/usr/bin/env python3
"""review_check.py — the review dossier must EXIST, be COMPLETE, and carry EVIDENCE
before code leaves the machine.

Why: "2 reviewers APPROVE before push, R3 on high-stakes diffs" as prose measured
out to: R3 run once ever despite qualifying diffs, and review.md living gitignored
so nobody could re-audit "both approved". This gate makes the law red-able.

Checks {paths.evidence}/<TICKET>/dev/review.md:
  1. The file exists IN THE PUSHED COMMIT (`git show <sha>:path`, never the
     worktree — uncommitted is nonexistent to this gate). Drafting at T4b? run
     with `--sha WORKTREE` to self-check first.
  2. Cards for R1..RN — N is `review.reviewers` (default 2; the config knob is
     read HERE, not just rendered into prose) — each with ≥1 valid APPROVE.
  3. A valid APPROVE has a "tried to break" section with ≥3 bullets, and the card
     carries ≥2 verifiable traces (a `command` in backticks or a file:line ref) —
     of which ≥1 MUST be file:line (backtick-only cards can't be cross-checked).
  3b. Every file:line ref must point at a file that EXISTS in the worktree —
     citing imaginary files marks a card written from imagination.
  3c. Verdict APPROVE-WITH-QUESTIONS → review.md must contain an
     "Answered QUESTIONS" block — questions never evaporate silently pre-merge.
  4. The diff vs base touches `review.high_stakes_paths` OR its content matches
     `review.high_stakes_terms` → ONE MORE card (R{N+1}, the architecture
     reviewer) is REQUIRED, and it must compare options ("option" / "A vs B") —
     an extra reviewer that only praises did no work.

Usage: review_check.py <TICKET | branch-name> [--base origin/<protected>] [--sha <commit>|WORKTREE]
Exit 0 = dossier complete; 1 = exactly what's missing.
Selftest: --selftest (valid card green + 5 mutations red).
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "lib"))
from ctx import Ctx  # noqa: E402

CARD_HEAD = re.compile(r"^#{2,4}\s.*\b(R\d+)\b", re.M)
BULLET = re.compile(r"^\s*[-*•]\s+\S", re.M)
# A "command" trace must look like a command (whitespace or ./path inside), not a
# lone word in backticks — the loose version let 8-line fabricated cards through.
EVIDENCE_CMD = re.compile(r"`[^`\n]*[\s/][^`\n]*`")
EVIDENCE_LOC = re.compile(r"\b[\w./-]+\.(?:ts|tsx|js|jsx|mjs|py|sh|go|rs|java|kt|rb|php|prisma|sql|md):\d+")
TRIED = re.compile(r"(tried[\s-]to[\s-]break|TRIED[\s-]TO[\s-]BREAK)(.*)", re.S | re.I)

# Card thresholds — the machine's HOUSE OF RECORD (review-standard.md describes
# what is checked; the exact numbers live here and only here — audit M13):
MIN_TRIED_BULLETS = 3   # "tried to break" bullets per card
MIN_TRACES = 2          # `command` / file:line traces per card
MIN_FILE_LINE = 1       # …of which at least this many must be file:line


def sh(root: Path, *args: str) -> tuple[int, str]:
    r = subprocess.run(args, cwd=root, capture_output=True, text=True)
    return r.returncode, r.stdout


def changed_files(root: Path, base: str, sha: str) -> list[str]:
    """Diff base↔sha. Three-dot needs a merge-base — CI shallow clones lack it and
    fail SILENTLY, which once made R3 evaporate. Fallback: two-dot compares the two
    trees directly; both failing means RED, never 'touched nothing'."""
    ref = sha if sha != "WORKTREE" else "HEAD"
    code, out = sh(root, "git", "diff", "--name-only", f"{base}...{ref}")
    if code == 0:
        return out.splitlines()
    code, out = sh(root, "git", "diff", "--name-only", base, ref)
    if code == 0:
        return out.splitlines()
    print(f"❌ review_check: cannot compute diff {base}↔{ref} (shallow clone lacks "
          f"both paths) — refusing to skip R3 blind; treating as missing dossier")
    sys.exit(1)


def parse_cards(text: str) -> dict[str, list[str]]:
    cards: dict[str, list[str]] = {}
    matches = list(CARD_HEAD.finditer(text))
    for i, m in enumerate(matches):
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        cards.setdefault(m.group(1), []).append(text[m.start():end])
    return cards


def card_is_valid_approve(card: str) -> tuple[bool, list[str]]:
    probs = []
    if re.search(r"REQUEST[- ]CHANGES", card):
        return False, ["card verdict is REQUEST-CHANGES (round not closed)"]
    if not re.search(r"\bAPPROVE\b", card):
        return False, ["no APPROVE verdict yet"]
    m = TRIED.search(card)
    if not m:
        probs.append("APPROVE without a 'tried to break' section — invalid card "
                     "(review-standard §1)")
    elif len(BULLET.findall(m.group(2))) < MIN_TRIED_BULLETS:
        probs.append(f"'tried to break' has <{MIN_TRIED_BULLETS} bullets — that's not trying")
    n_cmd, n_loc = len(EVIDENCE_CMD.findall(card)), len(EVIDENCE_LOC.findall(card))
    if n_cmd + n_loc < MIN_TRACES:
        probs.append(f"card has <{MIN_TRACES} verifiable traces (`command` / file:line) — "
                     f"testimony without commands is just prose")
    if n_loc < MIN_FILE_LINE:
        probs.append("card has no file:line trace — bare backticks can't be "
                     "cross-checked against the code (anti-fabrication rule 3b)")
    return len(probs) == 0, probs


def required_cards(n_reviewers: int, need_extra: bool) -> list[str]:
    """R1..RN from review.reviewers; a high-stakes diff adds one more (R{N+1})."""
    return [f"R{i}" for i in range(1, n_reviewers + (2 if need_extra else 1))]


def card_gaps(cards: dict[str, list[str]], required: list[str],
              hs_card: str | None) -> list[str]:
    """Missing/invalid cards against the required list. hs_card names the extra
    high-stakes (architecture) card, or None when the diff doesn't need one."""
    errs: list[str] = []
    for r in required:
        if r not in cards:
            why = (" (diff hits high-stakes paths/terms — the architecture card "
                   "is mandatory)") if r == hs_card else ""
            errs.append(f"missing card {r}{why}")
            continue
        ok_any, probs_last = False, []
        for card in cards[r]:
            ok, probs = card_is_valid_approve(card)
            if ok:
                ok_any = True
                break
            probs_last = probs
        if not ok_any:
            errs.extend(f"{r}: {p}" for p in (probs_last or ["no valid APPROVE card"]))
        if r == hs_card and ok_any and not re.search(r"option|\bA vs B\b", " ".join(cards[r]), re.I):
            errs.append(f"{hs_card}: card compares no options (A vs B) — an extra "
                        f"reviewer that only praises did no work")
    return errs


def main() -> int:
    c = Ctx()
    key = str(c.cfg("project.key"))
    protected = str(c.cfg("git.protected_branch", "main"))
    hs_paths = c.cfg("review.high_stakes_paths", [])
    hs_terms = c.cfg("review.high_stakes_terms", [])
    hs_paths = [str(p) for p in ([hs_paths] if isinstance(hs_paths, str) else hs_paths)]
    hs_terms = [str(t) for t in ([hs_terms] if isinstance(hs_terms, str) else hs_terms)]
    # ^ scalar config value = ONE entry, never its characters (H5)
    try:
        n_rev = int(str(c.cfg("review.reviewers", 2)))
    except ValueError:
        print(f"❌ review_check: review.reviewers "
              f"{c.cfg('review.reviewers')!r} is not a number")
        return 1
    if n_rev < 1:
        print(f"❌ review_check: review.reviewers must be ≥ 1 (got {n_rev})")
        return 1

    ap = argparse.ArgumentParser()
    ap.add_argument("ticket_or_branch")
    ap.add_argument("--base", default=f"origin/{protected}")
    ap.add_argument("--sha", default="HEAD")
    args = ap.parse_args()

    m = re.search(rf"((?:{re.escape(key)}|PR)-\d+)", args.ticket_or_branch, re.I)
    if not m:
        print(f"❌ review_check: cannot extract a ticket key from "
              f"{args.ticket_or_branch!r} (feat|fix branches must contain {key}-nn)")
        return 1
    ticket = m.group(1).upper()

    ev = str(c.cfg("paths.evidence", "evd"))
    relpath = f"{ev}/{ticket}/dev/review.md"
    if args.sha == "WORKTREE":
        review = c.root / relpath
        if not review.is_file():
            print(f"❌ review_check: {relpath} missing from the worktree")
            return 1
        text = review.read_text(encoding="utf-8", errors="replace")
    else:
        # Read FROM THE COMMIT — outside git is nonexistent to this gate (the first
        # version read the worktree, so an untracked review.md passed "COMMITTED").
        code, text = sh(c.root, "git", "show", f"{args.sha}:{relpath}")
        if code != 0 or not text:
            print(f"❌ review_check: {relpath} NOT in commit {args.sha[:12]} — the "
                  f"review dossier commits with the code; a file on one machine is "
                  f"a fabricated report (drafting? self-check with --sha WORKTREE)")
            return 1
    cards = parse_cards(text)

    errs: list[str] = []
    changed = changed_files(c.root, args.base, args.sha)
    need_r3 = any(any(f.startswith(p) for p in hs_paths) for f in changed) if hs_paths else False
    if not need_r3 and hs_terms:
        # content trigger: money/irreversible flows live where they live, not
        # where the path map says — the trigger follows the diff CONTENT
        ref = "HEAD" if args.sha == "WORKTREE" else args.sha
        code, diff_text = sh(c.root, "git", "diff", f"{args.base}...{ref}")
        if code != 0:
            code, diff_text = sh(c.root, "git", "diff", args.base, ref)
        if code == 0 and re.search("|".join(re.escape(t) for t in hs_terms), diff_text or "", re.I):
            need_r3 = True
    required = required_cards(n_rev, need_r3)
    hs_card = f"R{n_rev + 1}" if need_r3 else None

    for ref in re.findall(r"\b([\w./-]+\.(?:ts|tsx|js|jsx|mjs|py|sh|go|rs|java|kt|rb|php|prisma|sql)):\d+", text):
        if not (c.root / ref).is_file():
            errs.append(f"card cites {ref} — file doesn't exist in the worktree; "
                        f"a fabricated citation voids the whole card")
    if "APPROVE-WITH-QUESTIONS" in text and not re.search(r"Answered QUESTIONS", text, re.I):
        errs.append("APPROVE-WITH-QUESTIONS present but no 'Answered QUESTIONS' "
                    "block — reviewer questions never evaporate silently")

    errs.extend(card_gaps(cards, required, hs_card))

    if errs:
        print(f"❌ review_check: {ticket} — {len(errs)} gaps")
        for e in errs:
            print(f"   - {e}")
        return 1
    print(f"✅ review_check: {ticket} — dossier complete ({', '.join(required)}"
          f"{'' if need_r3 else f'; R{n_rev + 1} (high-stakes) not required for this diff'})")
    return 0


def _selftest():
    good = """## R1 — spec reviewer
APPROVE
Tried to break:
- ran `npm test -- auth` — 12 passed
- sent duplicate username via `curl -X POST /api/register`
- flipped the guard at src/auth.ts:42 — test went red as expected
Traces: src/auth.ts:42
"""
    ok, probs = card_is_valid_approve(good)
    assert ok, probs
    mutations = {
        "request-changes": good.replace("APPROVE", "REQUEST-CHANGES"),
        "no tried-to-break": good.replace("Tried to break:", "Notes:"),
        "two bullets": good.replace("- flipped the guard at src/auth.ts:42 — test went red as expected\n", ""),
        "no file:line": good.replace("src/auth.ts:42", "the auth guard").replace("Traces: the auth guard", "x"),
    }
    for name, card in mutations.items():
        ok, _ = card_is_valid_approve(card)
        assert not ok, f"mutation {name!r} should have gone red"
    cards = parse_cards(good + "\n### R2 challenger\nAPPROVE\n")
    assert set(cards) == {"R1", "R2"}, cards

    # H6: review.reviewers drives the required list — it is READ, not prose.
    # A two-card dossier under reviewers=3 must RED on the missing R3…
    two_valid = good + "\n" + good.replace("## R1 — spec reviewer", "## R2 — challenger")
    cards = parse_cards(two_valid)
    assert required_cards(2, False) == ["R1", "R2"]
    assert required_cards(3, False) == ["R1", "R2", "R3"]
    assert required_cards(3, True) == ["R1", "R2", "R3", "R4"], \
        "high-stakes adds ONE MORE card on top of review.reviewers"
    gaps = card_gaps(cards, required_cards(3, False), None)
    assert any("missing card R3" in g for g in gaps), \
        f"reviewers=3 + 2-card dossier must RED: {gaps}"
    # …and the same dossier under reviewers=2 is complete
    assert not card_gaps(cards, required_cards(2, False), None), \
        card_gaps(cards, required_cards(2, False), None)
    # the extra high-stakes card must compare options, whatever its number
    r3 = good.replace("## R1 — spec reviewer", "## R3 — architecture")
    gaps = card_gaps(parse_cards(two_valid + "\n" + r3), required_cards(2, True), "R3")
    assert any("compares no options" in g for g in gaps), gaps
    print("review_check selftest: OK (valid card green + 4 mutations red + parser "
          "+ reviewers=3 dossier red)")


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        _selftest()
    else:
        sys.exit(main())
