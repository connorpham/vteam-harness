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

Exit code is 0 unless --strict is passed, in which case a ticket whose routed set is
empty for a lane that has routable competencies exits 1. Default is a REPORT, not a
gate: what counts as over-routing is a judgement the owner has not yet made.
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


STRUCTURAL = ("title", "labels", "summary", "criteria")


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
    }


def where(term, fields):
    """Every field this term appears in, structural fields first."""
    pat = re.compile(r"\b" + re.escape(term), re.I)
    hits = [f for f in STRUCTURAL if f != "labels" and pat.search(fields.get(f) or "")]
    if any(pat.search(l) for l in fields["labels"]):
        hits.insert(0, "labels")
    if pat.search(fields["body"]):
        hits.append("body")
    return hits


def route(fields, comps, role):
    always, routed = [], []
    for name, c in sorted(comps.items()):
        if role and c["role"] != role:
            continue
        if "always" in c["applies"]:
            always.append(name)
            continue
        hits = []
        for tok in c["applies"]:
            if tok.startswith("label:") and tok[6:] in fields["labels"]:
                hits.append((tok, ["labels"]))
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
        for role in roles:
            always, routed = route(fields, comps, role)
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


if __name__ == "__main__":
    sys.exit(main())
