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

  6. Risk class (VT-36): `change_class.py` reads the diff and returns docs /
     surface / logic / high-stakes; the class picks the SHAPE (review_shape) —
     no cards for docs, one card with one bullet for surface, the configured
     reviewers otherwise. The class comes from the diff, never from the dossier
     or the agent. `review.proportional: false` restores the uniform fence.
  5. Round ceiling (VT-32): the initial cards are round 1, every `## Round N`
     heading in the dossier is a further fix round. rounds > `review.max_rounds`
     → RED, unless the diff is high-stakes (rule 4) or a finding is tagged
     SECURITY. Knob absent = no ceiling, said on the green line (init sets 1).
     `--ba <feature>` applies the same count to
     {paths.specs}/reviews/<feature>-backlog.md against `ba.challenger_rounds`
     (lift tag: SPEC — the draft contradicts the source).

Usage: review_check.py <TICKET | branch-name> [--base origin/<protected>] [--sha <commit>|WORKTREE]
       review_check.py --ba <feature>
Exit 0 = dossier complete; 1 = exactly what's missing.
Selftest: --selftest (valid card green + 5 mutations red + round ceiling).
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "lib"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import change_class  # noqa: E402 — the risk class is measured, not declared
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
ROUND_HEAD = re.compile(r"^#{2,4}\s*Round\s+(\d+)\b", re.M | re.I)
LIFT_TAG = {"review.max_rounds": "SECURITY", "ba.challenger_rounds": "SPEC"}


def count_rounds(text: str) -> int:
    """The initial cards are round 1; every `## Round N` heading records a further
    round (VT-32). Counted by the highest N, so one re-review recorded once is one round."""
    return max([1] + [int(n) for n in ROUND_HEAD.findall(text)])


def round_gaps(text: str, ceiling: int, lifted: bool, knob: str) -> list[str]:
    """ceiling ≤ 0 = no ceiling (knob absent). `lifted` = the diff is high-stakes.
    A finding carrying the knob's lift tag — SECURITY for review rounds, SPEC (the
    draft contradicts the source) for BA challenger rounds — lifts it too: a security
    defect gets as many rounds as it needs; a cosmetic or preference finding does not."""
    tag = LIFT_TAG.get(knob, "SECURITY")
    if ceiling <= 0 or lifted or re.search(rf"\b{tag}\b", text):
        return []
    rounds = count_rounds(text)
    if rounds <= ceiling:
        return []
    return [f"{rounds} rounds recorded (`## Round N` headings) but {knob} is {ceiling} — "
            f"answer the remaining finding in the dossier (answered, not fixed: why), do not "
            f"open another round; a {tag}-tagged finding lifts the ceiling"]


def read_ceiling(c, knob: str):
    """None = knob absent (no ceiling, said loudly); int otherwise; exits on garbage."""
    v = c.cfg(knob, None)
    if v is None:
        return None
    try:
        return int(str(v))
    except ValueError:
        print(f"❌ review_check: {knob} {v!r} is not a number")
        sys.exit(1)

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


def card_is_valid_approve(card: str, min_tried: int = MIN_TRIED_BULLETS) -> tuple[bool, list[str]]:
    probs = []
    if re.search(r"REQUEST[- ]CHANGES", card):
        return False, ["card verdict is REQUEST-CHANGES (round not closed)"]
    if not re.search(r"\bAPPROVE\b", card):
        return False, ["no APPROVE verdict yet"]
    m = TRIED.search(card)
    if not m:
        probs.append("APPROVE without a 'tried to break' section — invalid card "
                     "(review-standard §1)")
    elif len(BULLET.findall(m.group(2))) < min_tried:
        probs.append(f"'tried to break' has <{min_tried} bullets — that's not trying")
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


def review_shape(cls: str, n_reviewers: int) -> tuple[list[str], str | None, int]:
    """Risk class → the shape of the evidence: (required cards, the architecture card,
    minimum 'tried to break' bullets).

    Why the shape moves at all (VT-36): the fence still does not measure SIZE, and no
    agent gets to call its own change small — `change_class.py` measures the RISK from
    the diff. But charging a README typo the same two-reviewer, three-bullets-each toll
    as a payment rewrite does not buy safety; it buys INVENTED bullets, because on a
    text change there is nothing to try. Cards that get written to satisfy a counter
    stop being evidence, and then they stop being read.

      docs        no executable file moved → no dossier. The gate, the ledger and the
                  evidence pack still apply; only the reviewer agents are spared.
      surface     one card, one bullet — but a real one: a string can be a shell
                  command, a selector, an i18n key a test asserts on.
      logic       `review.reviewers` cards, three bullets each. Unchanged.
      high-stakes one card more, and it must compare options. Unchanged."""
    if cls == "docs":
        return [], None, 0
    if cls == "surface":
        return ["R1"], None, 1
    need_extra = cls == "high-stakes"
    return (required_cards(n_reviewers, need_extra),
            f"R{n_reviewers + 1}" if need_extra else None, MIN_TRIED_BULLETS)


def card_gaps(cards: dict[str, list[str]], required: list[str],
              hs_card: str | None, min_tried: int = MIN_TRIED_BULLETS) -> list[str]:
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
            ok, probs = card_is_valid_approve(card, min_tried)
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
    if "--ba" in sys.argv:
        # BA challenger rounds: {paths.specs}/reviews/<feature>-backlog.md, read from the
        # worktree (the BA lane commits it with the draft) — VT-32.
        i = sys.argv.index("--ba")
        feature = sys.argv[i + 1] if i + 1 < len(sys.argv) else ""
        if not feature:
            print("❌ review_check: --ba needs a feature name (the <feature>-backlog.md file)")
            return 1
        specs = str(c.cfg("paths.specs", "docs/specs"))
        rel = f"{specs}/reviews/{feature}-backlog.md"
        f = c.root / rel
        if not f.is_file():
            print(f"❌ review_check: {rel} missing — B3 records the challenger card there")
            return 1
        ceiling = read_ceiling(c, "ba.challenger_rounds")
        text = f.read_text(encoding="utf-8", errors="replace")
        gaps = round_gaps(text, ceiling or 0, False, "ba.challenger_rounds")
        if gaps:
            print(f"❌ review_check: {feature} — {gaps[0]}")
            return 1
        print(f"✅ review_check: {feature} — {count_rounds(text)} challenger round(s)"
              + (" (ba.challenger_rounds not set — no ceiling; init sets 1)" if ceiling is None
                 else f" within ba.challenger_rounds={ceiling}"))
        return 0
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

    # WHAT KIND of change is this? change_class.py measures it FROM THE DIFF — the
    # agent never declares it and the dossier never claims it (VT-36). `docs` spares
    # the reviewer agents entirely; `surface` asks for one card with one real bullet;
    # `logic` and `high-stakes` are exactly the fence that was here before.
    proportional = str(c.cfg("review.proportional", True)).strip().lower() \
        not in ("false", "0", "no", "off")
    try:
        surface_max = int(str(c.cfg("review.surface_max_lines", 40)))
    except ValueError:
        print(f"❌ review_check: review.surface_max_lines "
              f"{c.cfg('review.surface_max_lines')!r} is not a number")
        return 1
    cls, why = change_class.classify(c.root, args.base, args.sha, hs_paths, hs_terms,
                                     ev, surface_max)
    if not proportional and cls != "high-stakes":
        cls = "logic"          # one config line puts the uniform fence back
    class_line = f"change class `{cls}`" + (f" — {why[0]}" if why else "")
    required, hs_card, min_tried = review_shape(cls, n_rev)
    if not required:
        print(f"✅ review_check: {ticket} — {class_line}. No reviewer card required: no "
              f"executable file moved in this diff. The verification gate, the evidence "
              f"pack and the ledger row are untouched by this; only the reviewer agents "
              f"are spared. Restore the uniform fence with `review.proportional: false`.")
        return 0
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
    # high-stakes is one of the classes now: the path and content triggers moved into
    # change_class.classify, so one reader decides what this diff is.
    need_r3 = cls == "high-stakes"

    for ref in re.findall(r"\b([\w./-]+\.(?:ts|tsx|js|jsx|mjs|py|sh|go|rs|java|kt|rb|php|prisma|sql)):\d+", text):
        if not (c.root / ref).is_file():
            errs.append(f"card cites {ref} — file doesn't exist in the worktree; "
                        f"a fabricated citation voids the whole card")
    if "APPROVE-WITH-QUESTIONS" in text and not re.search(r"Answered QUESTIONS", text, re.I):
        errs.append("APPROVE-WITH-QUESTIONS present but no 'Answered QUESTIONS' "
                    "block — reviewer questions never evaporate silently")

    errs.extend(card_gaps(cards, required, hs_card, min_tried))
    max_rounds = read_ceiling(c, "review.max_rounds")
    errs.extend(round_gaps(text, max_rounds or 0, need_r3, "review.max_rounds"))
    ceiling_note = (" · review.max_rounds not set — no ceiling on fix rounds (init sets 1)"
                    if max_rounds is None else f" · {count_rounds(text)} round(s) within max_rounds={max_rounds}")

    if errs:
        print(f"❌ review_check: {ticket} — {len(errs)} gaps")
        for e in errs:
            print(f"   - {e}")
        return 1
    print(f"✅ review_check: {ticket} — dossier complete ({', '.join(required)}"
          f"{'' if need_r3 else f'; R{n_rev + 1} (high-stakes) not required for this diff'})"
          f" · {class_line}"
          f"{ceiling_note}")
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

    # VT-36: the RISK CLASS picks the shape. docs spares the cards; surface asks for
    # one real bullet; logic and high-stakes are the fence exactly as it was.
    assert review_shape("docs", 2) == ([], None, 0)
    assert review_shape("surface", 2) == (["R1"], None, 1)
    assert review_shape("logic", 2) == (["R1", "R2"], None, MIN_TRIED_BULLETS)
    assert review_shape("high-stakes", 2) == (["R1", "R2", "R3"], "R3", MIN_TRIED_BULLETS)
    assert review_shape("logic", 3) == (["R1", "R2", "R3"], None, MIN_TRIED_BULLETS), \
        "the class must not override review.reviewers"
    one_bullet = """## R1 — copy review
APPROVE
Tried to break:
- grepped the old string out of the built bundle, not just the source: `npm run build && grep -r "Submit" .next` — no hit left; the assertion that named it is src/auth.ts:42
Traces: src/auth.ts:42
"""
    ok, probs = card_is_valid_approve(one_bullet, 1)
    assert ok, probs
    ok, probs = card_is_valid_approve(one_bullet, MIN_TRIED_BULLETS)
    assert not ok, "a logic-class change still needs three bullets"
    # …and a surface card still has to carry traces: one bullet is not no evidence
    ok, probs = card_is_valid_approve("## R1\nAPPROVE\nTried to break:\n- looked at it\n", 1)
    assert not ok and any("traces" in x for x in probs), probs

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
    # VT-32: the round ceiling is READ from config and COUNTED from the dossier.
    two_rounds = two_valid + "\n## Round 2 — re-review after REQUEST-CHANGES\nAPPROVE\n"
    assert count_rounds(two_valid) == 1 and count_rounds(two_rounds) == 2
    assert round_gaps(two_rounds, 1, False, "review.max_rounds"), \
        "2 rounds under max_rounds=1 must RED"
    assert not round_gaps(two_valid, 1, False, "review.max_rounds"), "1 round under max_rounds=1 is fine"
    assert not round_gaps(two_rounds, 0, False, "review.max_rounds"), "0/absent = no ceiling"
    assert not round_gaps(two_rounds, 1, True, "review.max_rounds"), "a high-stakes diff lifts the ceiling"
    assert not round_gaps(two_rounds.replace("APPROVE\n", "CONFIRMED SECURITY: forged Origin accepted\nAPPROVE\n", 1), 1, False, "review.max_rounds"), \
        "a SECURITY-tagged finding lifts the ceiling"
    assert round_gaps(two_rounds.replace("Round 2", "Round 3"), 2, False, "ba.challenger_rounds"), \
        "Round N counts by N, not by heading count"
    print("review_check selftest: OK (valid card green + 4 mutations red + parser "
          "+ reviewers=3 dossier red + round ceiling read/counted/lifted)")


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        _selftest()
    else:
        sys.exit(main())
