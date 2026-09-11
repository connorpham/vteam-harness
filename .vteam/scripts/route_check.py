#!/usr/bin/env python3
"""route_check — which competencies does a ticket actually load, and what does that cost?

`competency_check` validates the `applies:` GRAMMAR (a token is `always` | `label:x`
| `path:x` | `profile:x` | `term:x`). Nothing until now checked the tokens against
reality, so two failure modes were invisible:

  UNDER-ROUTING  a ticket needs a competency and no token matches, so the lane never
                 opens it and nobody finds out.
  OVER-ROUTING   a common word appears incidentally in a ticket's prose and pulls a
                 whole competency into the lane's context. Measured on the field
                 trial: a focus-ring CSS ticket loaded `dev-mobile-craft` because the
                 word "permission" appeared, and a modal ticket loaded
                 `dev-async-work` because of "worker" — which was "Orca worker", an
                 agent, not a background job.

The second one is what makes a lane run out of context. This script prints the load
set per ticket per role, the token that pulled each file in, and the word/token cost
of the whole set, so "the skills are too long" becomes a number per ticket.

Usage:
  route_check.py                          every ticket in {paths.backlog}, summary table
  route_check.py --ticket TB-8            one ticket, every match explained
  route_check.py --role dev               restrict to one lane
  route_check.py --weak                   only the rows that look like a routing fault
  route_check.py --json                   machine-readable

Exit code is 0 unless --strict is passed, in which case a ticket/lane pair carrying a
BODY-ONLY match (over-routing) exits 1. An earlier docstring described the opposite —
under-routing — which would have wired the wrong rule into a gate. Default is a REPORT:
what counts as over-routing is a judgement the owner has not yet made (D13).
"""
import argparse, json, pathlib, re, sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
COMP = ROOT / "core" / "doctrine" / "competencies"
if not COMP.exists():                      # installed layout
    COMP = ROOT / "docs" / "team" / "competencies"


def load_competencies():
    out = {}
    for f in sorted(COMP.glob("*/*.md")):
        s = f.read_text()
        if not s.startswith("---"):
            continue
        fm, body = s.split("---", 2)[1], s.split("---", 2)[2]
        get = lambda k: (re.search(rf"^{k}:\s*(.+)$", fm, re.M) or [None, ""])[1].strip().strip('"')
        name = get("name")
        if not name:
            continue
        out[name] = {
            "role": get("role"), "loads": get("loads"), "words": len(body.split()),
            "applies": [t.strip() for t in get("applies").split(",") if t.strip()],
            "path": str(f.relative_to(ROOT)),
        }
    return out


STRUCTURAL = ("title", "labels", "summary", "criteria", "type", "profile", "code-scope")


def code_scope_for(key, root):
    """CODE-SCOPE from the ticket's tasksheet, or None when it has not been written yet."""
    for cand in (root / "evd" / key / "dev" / "tasksheet.md",):
        if cand.is_file():
            m = re.search(r"^CODE-SCOPE:\s*(.+)$", cand.read_text(encoding="utf-8", errors="replace"), re.M)
            if m:
                return m.group(1).split()
    return None


def ticket_fields(text):
    """The parts of a ticket that say what it IS, kept apart from the prose that
    merely mentions things. A term matching ONLY in `body` is the over-routing
    signature — that is where evidence paths, process notes and out-of-scope lists
    live."""
    title = text.split("\n", 1)[0].lstrip("# ").strip()
    lab = re.search(r"^- labels:\s*(.+)$", text, re.M)
    typ = re.search(r"^- type:\s*(.+)$", text, re.M)
    summ = re.search(r"\*\*30-second summary:\*\*(.*?)(?=\n## |\Z)", text, re.S)
    why = re.search(r"^## Why\s*(.*?)(?=\n## |\Z)", text, re.S | re.M)
    ac = re.search(r"^## Acceptance criteria.*?$(.*?)(?=\n## |\Z)", text, re.S | re.M)
    return {
        "title": title,
        "labels": [x.strip() for x in lab.group(1).split(",")] if lab else [],
        "type": typ.group(1).strip() if typ else "",
        "summary": " ".join(x.group(1) for x in (summ, why) if x),
        "criteria": ac.group(1) if ac else "",
        "body": text,
        "code_scope": None,
    }


def where(term, fields):
    """Every field this term appears in, structural fields first."""
    # A word, and its ordinary inflections — nothing more.
    #
    # Two mistakes were made here in two rounds and both are worth keeping in view. A
    # bare leading `\b` made every token a PREFIX match (`lock` hit "lockfile",
    # `api` hit "apiary"), inflating every body-only count. Adding only `(?:s|es)?`
    # then over-corrected: a reviewer showed it loses the verb forms English tickets
    # actually use — "the row is locked", "we are locking", "the value is cached",
    # "synced nightly" — and on this repo's own backlog it lost `term:concurrent`
    # against "concurrently", a TRUE match for dev-concurrency-and-transactions.
    # Under-routing is the silent direction, so it is the more expensive one to be
    # wrong in (VT-16 rejected its own narrowing on exactly that reasoning).
    #
    # THE SUFFIX SET WAS CHOSEN BY MEASUREMENT, not by intuition. Counting term-driven
    # matches across both real backlogs:
    #
    #   (?:s|es)?            92 — recovers nothing the prefix version had
    #   (?:s|es|ly)?         93 — recovers "concurrently" (a TRUE match for
    #                             dev-concurrency-and-transactions on VT-5) and nothing false
    #   (?:s|es|d|ed|ing|ly)? 97 — recovers that one TRUE match and FOUR false ones,
    #                             all of them `term:form` against the word "formed"
    #
    # So `-ed`/`-ing` is rejected on evidence: it turns a noun into an unrelated word
    # more often than it catches a verb. The reviewer's cases — "the row is locked",
    # "the value is cached" — are real English and would be true matches, but they occur
    # in neither backlog; widen the day one appears, with the same split published.
    #
    # A `y` stem also takes `-ies` ("query" → "queries"), which a suffix list cannot express.
    stem = re.escape(term)
    if term.endswith("y"):
        stem = f"(?:{re.escape(term)}|{re.escape(term[:-1])}ies)"
    pat = re.compile(r"\b" + stem + r"(?:s|es|ly)?\b", re.I)
    hits = [f for f in STRUCTURAL if f != "labels" and pat.search(fields.get(f) or "")]
    if any(pat.search(l) for l in fields["labels"]):
        hits.insert(0, "labels")
    if pat.search(fields["body"]):
        hits.append("body")
    return hits


def route(fields, comps, role, profile=None):
    always, routed = [], []
    for name, c in sorted(comps.items()):
        if role and c["role"] != role:
            continue
        if "always" in c["applies"]:
            always.append(name)
            continue
        hits = []
        for tok in c["applies"]:
            # Case-folded, like `type:` below. The two kinds had OPPOSITE case rules —
            # `type: bug` matched `type:Bug` while `labels: UI` missed `label:ui` — which
            # nobody decided; it was two lines in one function, failing in the silent
            # under-routing direction. Whether label matching should be looser than this
            # is D13's call; an accidental asymmetry is not.
            if tok.startswith("label:") and tok[6:].lower() in {l.lower() for l in fields["labels"]}:
                hits.append((tok, ["labels"]))
            elif tok.startswith("profile:"):
                # the repo's stack profile — constant for a repo, so it either applies to
                # every ticket or to none. Omitting it (as the first version of this script
                # did) makes every measurement an UNDERCOUNT, which is worse than noisy.
                if profile and tok[8:].strip().lower() == profile.lower():
                    hits.append((tok, ["profile"]))
            elif tok.startswith("path:"):
                # `path:` means the ticket's CODE-SCOPE, which /dev T2 names explicitly —
                # not "the string appears somewhere in the prose". The tasksheet carrying
                # it is written at T1, before the lane loads competencies at T2, so the
                # real value IS available. Measured against 5 tickets that have one, the
                # prose proxy over-counted by 5 of 19 matches (TB-5 alone: 6 vs 2).
                # Where no tasksheet exists yet, fall back to the prose mention and SAY SO,
                # so a reader can tell a measured row from an estimated one.
                pre = tok[5:].strip().lower()
                if fields.get("code_scope"):
                    if any(pre in sc.lower() for sc in fields["code_scope"]):
                        hits.append((tok, ["code-scope"]))
                elif pre in fields["body"].lower():
                    hits.append((tok, ["path-mentioned-no-tasksheet"]))
            elif tok.startswith("type:"):
                want = tok[5:].strip().lower()
                if (fields.get("type") or "").strip().lower() == want:
                    hits.append((tok, ["type"]))
            elif tok.startswith("term:"):
                w = where(tok[5:], fields)
                if w:
                    hits.append((tok, w))
        if hits:
            structural = any(f in STRUCTURAL for _, ws in hits for f in ws)
            routed.append({"name": name, "hits": hits, "structural": structural})
    return always, routed


def cost(comps, names):
    w = sum(comps[n]["words"] for n in names)
    return w, int(w * 1.35)          # ~1.35 tokens per word, the ratio vteam's own docs use


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ticket")
    ap.add_argument("--role", choices=["dev", "qa", "ba", "pm", "docs", "design", "devops", "sa"])
    ap.add_argument("--backlog", default="docs/backlog")
    ap.add_argument("--weak", action="store_true", help="only rows that look like a routing fault")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--strict", action="store_true")
    a = ap.parse_args()

    comps = load_competencies()
    # The profile belongs to the repo whose BACKLOG is being measured, not to the repo
    # the script happens to run from. Reading the wrong one silently drops every
    # `profile:` match and undercounts the load — which is how the first version of this
    # measurement understated the real figure by 14%.
    # resolve() FIRST, so a relative --backlog pointing at another repo finds that
    # repo's config too. The first version keyed on is_absolute(), so the same
    # directory measured by a relative path silently lost every `profile:` match —
    # the very undercount VT-20 was written to correct, surviving in half the inputs.
    bl_arg = pathlib.Path(a.backlog).resolve()
    target_root = bl_arg.parent.parent
    profile = None
    for cfg in (target_root / "vteam.config.yaml", ROOT / "vteam.config.yaml"):
        if cfg.is_file():
            m = re.search(r"^\s*profile:\s*([\w-]+)", cfg.read_text(), re.M)
            if m:
                profile = m.group(1)
                break
    if not comps:
        print(f"route_check: no competencies found under {COMP}", file=sys.stderr)
        return 2
    bl = ROOT / a.backlog
    files = sorted(bl.glob("*.md"))
    if a.ticket:
        files = [f for f in files if f.stem == a.ticket]
        if not files:
            print(f"route_check: no ticket {a.ticket} in {bl}", file=sys.stderr)
            return 2
    roles = [a.role] if a.role else sorted({c["role"] for c in comps.values() if c["role"]})

    report, bad = [], 0
    for f in files:
        fields = ticket_fields(f.read_text())
        fields["code_scope"] = code_scope_for(f.stem, bl.parent.parent)
        for role in roles:
            always, routed = route(fields, comps, role, profile)
            if not always and not routed:
                continue
            names = always + [r["name"] for r in routed]
            w, tk = cost(comps, names)
            incidental = [r["name"] for r in routed if not r["structural"]]
            row = {"ticket": f.stem, "role": role, "always": always,
                   "routed": routed, "files": len(names), "words": w, "tokens": tk,
                   "body_only": incidental}
            if incidental:
                bad += 1
            if a.weak and not incidental:
                continue
            report.append(row)

    if a.json:
        print(json.dumps(report, indent=2))
        return 0

    for row in report:
        print(f"\n{row['ticket']} / {row['role']}: {row['files']} files, "
              f"{row['words']} words ≈ {row['tokens']} tokens")
        print(f"  always ({len(row['always'])}): {', '.join(row['always']) or '—'}")
        for r in row["routed"]:
            flag = "" if r["structural"] else "   ⚠ body-only"
            toks = "; ".join(f"{t} in {'+'.join(ws)}" for t, ws in r["hits"])
            print(f"  routed: {r['name']:<34} ← {toks}{flag}")
        if row["body_only"]:
            print(f"  ⚠ pulled in by a word appearing ONLY in the prose, not in the title, "
                  f"labels, summary or criteria: {', '.join(row['body_only'])}")

    if report and not a.json:
        tf = sum(r["files"] for r in report)
        tt = sum(r["tokens"] for r in report)
        print(f"\n{len(report)} ticket/lane pairs · {tf} competency files · ≈{tt} tokens total")
        print(f"{bad} pair(s) load at least one competency matched only in the prose.")
        print("A body-only match is a SIGNAL, not a verdict: a ticket may legitimately "
              "describe its subject only in the body. Read the token before deleting it.")
    return 1 if (a.strict and bad) else 0


def _selftest() -> None:
    """The file that produced four different answers for one measurement, guarded.

    Every branch below is a mistake this script actually shipped: a prefix match, a
    profile dropped on a relative path, an ignored token kind, and a `--strict`
    contract documented backwards.
    """
    import tempfile, textwrap
    fails = []

    def comp(name, role, applies, words=100):
        return {name: {"role": role, "loads": "T2", "words": words,
                       "applies": [t.strip() for t in applies.split(",")], "path": name}}

    # term: must match a whole word, not a prefix — `lock` is not `lockfile`
    f = ticket_fields("# T-1: a\n- type: Bug\n- labels: x\n\nthe lockfile_check step passes\n")
    a, r = route(f, comp("c", "dev", "term:lock"), "dev")
    if r: fails.append("term:lock matched 'lockfile' — the trailing boundary is missing")
    # …but a real occurrence, and its plural, must match
    for body, why in (("we take a row lock here", "singular"), ("two locks are taken", "plural")):
        f = ticket_fields(f"# T-1: a\n- labels: x\n\n{body}\n")
        if not route(f, comp("c", "dev", "term:lock"), "dev")[1]:
            fails.append(f"term:lock missed the {why} occurrence")

    # inflections the second round lost, and the prefixes the first round wrongly kept
    for term, body, want in (
        # -ly and plurals are in; -ed/-ing are OUT, measured: on both real backlogs they
        # recover one true match and four false ones ("form" vs "formed"). These two
        # assert the rejected direction stays rejected, so a future widening is deliberate.
        ("lock", "the row is locked", False), ("cache", "the value is cached", False),
        ("concurrent", "it runs concurrently", True), ("query", "two queries per request", True),
        ("retry", "three retries later", True), ("form", "the criteria are formed", False),
        ("lock", "lockfile_check passes", False), ("form", "the output format", False),
        ("api", "an apiary of bees", False),
    ):
        f = ticket_fields(f"# T: a\n- labels: x\n\n{body}\n")
        got = bool(route(f, comp("c", "dev", f"term:{term}"), "dev")[1])
        if got != want:
            fails.append(f"term:{term} vs {body!r}: expected {want}, got {got}")

    # label: is case-folded, like type: — the asymmetry was an accident, not a policy
    f = ticket_fields("# T: a\n- labels: UI, Backend\n\nb\n")
    if not route(f, comp("c", "dev", "label:ui"), "dev")[1]:
        fails.append("label:ui missed a ticket labelled UI — the case asymmetry is back")

    # type: reads the ticket's own field, and only that
    f = ticket_fields("# T-2: a\n- type: Bug\n- labels: x\n\nno such word here\n")
    if not route(f, comp("c", "dev", "type:Bug"), "dev")[1]:
        fails.append("type:Bug did not match a ticket whose type field is Bug")
    f = ticket_fields("# T-3: a\n- type: Story\n- labels: x\n\nthis mentions a bug in prose\n")
    if route(f, comp("c", "dev", "type:Bug"), "dev")[1]:
        fails.append("type:Bug matched a Story that merely says 'bug'")

    # profile: matches the measured repo's profile, and is not silently dropped
    f = ticket_fields("# T-4: a\n- labels: x\n\nbody\n")
    if not route(f, comp("c", "dev", "profile:nextjs-prisma"), "dev", "nextjs-prisma")[1]:
        fails.append("profile: did not match when the profile was supplied")
    if route(f, comp("c", "dev", "profile:nextjs-prisma"), "dev", None)[1]:
        fails.append("profile: matched with no profile resolved — that is the undercount bug")

    # path: prefers CODE-SCOPE and says so; falls back to a labelled estimate
    f = ticket_fields("# T-5: a\n- labels: x\n\ntouches src/api/thing.ts\n")
    f["code_scope"] = ["apps/web/src/api/"]
    _, r = route(f, comp("c", "dev", "path:src/api/"), "dev")
    if not r or r[0]["hits"][0][1] != ["code-scope"]:
        fails.append("path: did not resolve through CODE-SCOPE when one exists")
    f["code_scope"] = None
    _, r = route(f, comp("c", "dev", "path:src/api/"), "dev")
    if not r or "path-mentioned-no-tasksheet" not in r[0]["hits"][0][1]:
        fails.append("path: fallback is not labelled as an estimate")

    # a body-only match is flagged, a structural one is not
    f = ticket_fields("# T-6: a\n- labels: ui\n\nbody\n")
    _, r = route(f, comp("c", "dev", "label:ui"), "dev")
    if not r[0]["structural"]:
        fails.append("a label match was not counted as structural")

    if fails:
        for x in fails:
            print(f"  ✗ {x}")
        raise SystemExit("route_check selftest: FAILED")
    print("route_check selftest: OK (term whole-word + plural, type from the field not the prose, "
          "profile present/absent, path via CODE-SCOPE vs labelled estimate, structural vs body-only)")


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        _selftest()
    else:
        sys.exit(main())
