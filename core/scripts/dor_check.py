#!/usr/bin/env python3
"""dor_check.py — Definition-of-Ready as a machine gate (/dev T0).

A ticket may be coded only when it is READY. RED → the ticket returns to the BA
lane (raci.md §2) — never "code it anyway". The one exception is a DURABLE waiver:
a ticket comment `DoR waived by <user> — reason` (scratchpads die with sessions).

Checks, via the tracker provider:
  1. Acceptance criteria present in Given/When/Then form.
  2. A spec citation (`spec §` or a path under {paths.specs}/).
  3. An out-of-scope section.
  4. UI tickets (declares a screen / not marked `no UI`) → a design link.
  5. An original estimate.
  6. Not blocked by a ticket that isn't Done.
  7. The `reopen` label → print the pointer to QA's REPORT.md FIRST (read it
     before re-reading the spec).

Usage: dor_check.py <TICKET>     — exit 0 ready / 1 with the misses
Selftest: --selftest (fixture issue green + mutations red; no tracker needed).
"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "lib"))

GWT = re.compile(r"\bGiven\b.*\bWhen\b.*\bThen\b", re.S | re.I)
OOS = re.compile(r"(out of scope|out-of-scope)", re.I)
NO_UI = re.compile(r"\bno UI\b", re.I)
DESIGN_LINK = re.compile(r"(figma\.com/(design|file)/|design node:|design-node:|mockup:)", re.I)
WAIVER = re.compile(r"DoR waived by\s+\S+", re.I)


def check_issue(issue: dict, specs_dir: str, blockers_done: dict[str, bool]) -> tuple[list, list]:
    """Return (errors, notes). blockers_done: {key: is_done} for links.blocked_by."""
    errs, notes = [], []
    desc = issue.get("description", "") or ""
    for c in issue.get("comments", []):
        if WAIVER.search(c):
            return [], [f"DoR WAIVED by durable ticket comment: {WAIVER.search(c).group(0)!r} — gate passes on the waiver"]
    if "reopen" in [l.lower() for l in issue.get("labels", [])]:
        notes.append("label `reopen`: QA returned this ticket — read its REPORT.md "
                     "BEFORE re-reading the spec")
    if not GWT.search(desc):
        errs.append("no Given/When/Then acceptance criteria")
    if "spec §" not in desc and specs_dir not in desc:
        errs.append(f"no spec citation (`spec §x.y` or a {specs_dir}/ path)")
    if not OOS.search(desc):
        errs.append("no out-of-scope section — the dev will self-expand")
    if not NO_UI.search(desc) and re.search(r"\b(screen|page|UI)\b", desc, re.I):
        if not DESIGN_LINK.search(desc):
            errs.append("UI ticket without a design link (and not marked `no UI`)")
    if not issue.get("estimate"):
        errs.append("no original estimate — an unestimated ticket is not created yet (BA debt)")
    for k, done in blockers_done.items():
        if not done:
            errs.append(f"blocked by {k} which is not Done")
    return errs, notes


def main() -> int:
    from ctx import Ctx
    import tracker as trk
    c = Ctx()
    if len(sys.argv) < 2:
        print("usage: dor_check.py <TICKET>")
        return 2
    key = sys.argv[1].upper()
    t = trk.load(c)
    issue = t.get_issue(key)
    blockers = {}
    for bk in issue.get("links", {}).get("blocked_by", []):
        try:
            blockers[bk] = t.get_issue(bk)["status_category"] == "done"
        except SystemExit:
            blockers[bk] = False
    errs, notes = check_issue(issue, str(c.cfg("paths.specs")), blockers)
    for n in notes:
        print(f"ℹ️  {n}")
    if errs:
        print(f"❌ dor_check: {key} is NOT ready — return to the BA lane (raci §2)")
        for e in errs:
            print(f"   - {e}")
        return 1
    print(f"✅ dor_check: {key} is ready to code")
    return 0


def _selftest():
    good = {
        "description": ("30s summary…\nSpec: spec §2.1 (docs/specs/auth.md)\n"
                        "AC: Given a signed-in STAFF / When they submit / Then order PENDING\n"
                        "Out of scope: refunds\nno UI\n"),
        "estimate": "1d", "labels": [], "comments": [], "links": {},
    }
    errs, _ = check_issue(good, "docs/specs", {})
    assert not errs, errs
    mutations = {
        "no GWT": {**good, "description": good["description"].replace("Given", "If")},
        "no spec cite": {**good, "description": good["description"].replace("spec §2.1 (docs/specs/auth.md)", "somewhere")},
        "no out-of-scope": {**good, "description": good["description"].replace("Out of scope: refunds\n", "")},
        "no estimate": {**good, "estimate": ""},
        "ui no design": {**good, "description": good["description"].replace("no UI", "the login screen")},
    }
    for name, issue in mutations.items():
        errs, _ = check_issue(issue, "docs/specs", {})
        assert errs, f"mutation {name!r} should red"
    errs, _ = check_issue(good, "docs/specs", {"PROJ-9": False})
    assert errs, "un-Done blocker should red"
    waived = {**good, "estimate": "", "comments": ["DoR waived by owner — ad-hoc hotfix"]}
    errs, notes = check_issue(waived, "docs/specs", {})
    assert not errs and notes, "durable waiver should pass with a note"
    print("dor_check selftest: OK (fixture green + 6 mutations red + waiver path)")


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        _selftest()
    else:
        sys.exit(main())
