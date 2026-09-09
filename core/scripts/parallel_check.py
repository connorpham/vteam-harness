#!/usr/bin/env python3
"""parallel_check.py — in /team parallel mode, no two in-flight DEV branches may
share edit territory.

Why: `/team` parallel mode runs up to `team.parallel` DEV agents at once, each in
its own worktree/branch. Parallel is only SAFE when their scopes are disjoint —
two branches writing the same files produce a merge the gates can't arbitrate,
and a review that passed on one is stale the moment the other lands. This makes
"disjoint scope" red-able instead of a promise, and caps concurrency as DATA.

OPT-IN: `team.parallel <= 1` (the default) → the feature is off and this gate is
inert-green. It only bites once the owner turns parallel mode on.

When on, the IN-FLIGHT set = local branches matching `git.branch_pattern`
(feat|fix/<KEY>-nn-*), minus the protected branch, minus branches whose work has
already LANDED on it (finished work lingers locally until someone deletes it —
and a worktree may still have one checked out, which `git branch` decorates with
"+"; counting those would refuse the next dispatch for work that already
shipped). "Landed" is strategy-aware, because `git.merge_strategy` allows all
three: a true merge leaves the tip reachable from protected, a rebase leaves
every commit with an upstream twin, a squash leaves one commit carrying the
branch's whole diff — `has_landed` recognises each by content, not by sha. It
deliberately does NOT include a branch that has not diverged yet: a freshly
dispatched worker's tip sits AT the protected tip, and treating that as "merged"
made the concurrency cap stop firing in the very window it exists for. For each,
the ticket key → its `CODE-SCOPE:` line in {paths.evidence}/<TICKET>/dev/
tasksheet.md — read from GIT, not from this filesystem: parallel DEV agents each
own a separate worktree, so a sibling's evd/ is never on this disk, but every
worktree shares one object store, so `git show <branch>:<path>` sees it. That is
also why /dev commits the tasksheet FIRST in parallel mode; a tasksheet that is
only in someone's working tree is invisible to every sibling's gate, and the red
says exactly that instead of inventing an empty scope.

Bookkeeping homes ({paths.pm}, {paths.evidence}, {paths.qa}) are SHARED BY
DESIGN — coord_check orders every handoff to append to {paths.pm}/coordination.md,
so counting that file as edit territory would make the two gates contradict each
other. They are listed as ignored and excluded from the overlap test; a real
overlap under code paths still reds.

RED when:
  · more than `team.parallel` branches are in flight (concurrency cap, like
    loop_budget — MAST 1.5 termination-as-data);
  · an in-flight branch has no CODE-SCOPE to check (can't prove it's disjoint) —
    distinguishing "no such line" from "tasksheet not committed on that branch"
    and from "only bookkeeping paths declared", because the remedies differ;
  · any two in-flight scopes intersect on CODE paths (a path in one equals or
    nests under a path in the other).

Usage: parallel_check.py [--root <dir>]
Exit 0 = safe (or off); 1 = exactly which branches collide.
Selftest: --selftest (disjoint green + overlap/over-cap/missing-scope red;
bookkeeping ignored with the real-overlap boundary still red; off-disk git
fixture for the sibling tasksheet; merged branches not in flight).
"""
from __future__ import annotations

import posixpath
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "lib"))

SCOPE = re.compile(r"^\s*CODE-SCOPE:\s*(.+)$", re.M)


def norm(p: str) -> str:
    """A scope path, CANONICALISED to one spelling per location.

    Trailing slash stripped so a dir and its own name compare; backslashes
    folded to slashes; and `.` / `..` segments RESOLVED. Resolution is not
    tidiness — a raw string-prefix test made the spelling of a path decide its
    meaning: `docs/pm/../x` was classified as living under the bookkeeping home
    `docs/pm` (it does not) and `./docs/pm/x` was missed as one (it does), so a
    scope could be hidden from the overlap check by how it was typed.

    The repo root (`.`) normalises to `""`, which `paths_touch` treats as
    covering every path — a ticket claiming the whole repo must collide with
    everyone, not with no one.
    """
    p = posixpath.normpath(p.strip().replace("\\", "/"))
    return "" if p in (".", "/") else p.strip("/")


def parse_scope(text: str) -> list[str]:
    """The paths on the CODE-SCOPE line, whitespace-separated."""
    m = SCOPE.search(text or "")
    if not m:
        return []
    return [norm(p) for p in m.group(1).split() if p.strip()]


def paths_touch(a: str, b: str) -> bool:
    """True when two paths cover overlapping ground: equal, or one nests the
    other (a file under a dir, either direction). Normalizes internally so the
    spelling of a path never changes the answer (parity with coord_check).

    The repo root (`""` after norm — written `.` in a CODE-SCOPE) covers every
    path: a scope of `.` claims the entire repository, so it overlaps whatever
    anyone else declared. Before this, the containment test looked for a `./`
    prefix that no repo-relative path ever carries, so whole-repo scope
    collided with nothing at all — the one scope that should collide with
    everything.
    """
    a, b = norm(a), norm(b)
    if a == "" or b == "":
        return True
    if a == b:
        return True
    return b.startswith(a + "/") or a.startswith(b + "/")


def scopes_overlap(a: list[str], b: list[str]) -> str | None:
    """The first pair of paths (one from each scope) that touch, or None."""
    for pa in a:
        for pb in b:
            if paths_touch(pa, pb):
                return f"{pa} ∩ {pb}"
    return None


def find_conflicts(scope_map: dict[str, list[str]],
                   sources: dict[str, str] | None = None,
                   ev: str = "evd") -> list[str]:
    """Every colliding pair among the in-flight tickets, plus any with no scope.

    `sources` (ticket → where its tasksheet was read from) only sharpens the
    message, never the verdict. An empty scope has three different causes with
    three different remedies, and a red that names the wrong one costs a round:
      · "missing on <branch>" — the tasksheet is not COMMITTED, so it is
        invisible to every sibling worktree's gate → commit it;
      · "bookkeeping-only"    — the line exists but declares only shared homes,
        so there is no code territory to prove disjoint → name the code paths;
      · anything else         — the tasksheet has no CODE-SCOPE line → add one.
    """
    errs: list[str] = []
    for t, paths in sorted(scope_map.items()):
        if not paths:
            src = (sources or {}).get(t, "")
            if src.startswith("missing"):
                errs.append(f"{t}: no CODE-SCOPE readable — tasksheet {src}, not committed "
                            f"(commit {ev}/{t}/dev/tasksheet.md on that branch so sibling "
                            f"worktrees' gates can read it via git)")
            elif src == "bookkeeping-only":
                errs.append(f"{t}: CODE-SCOPE declares only bookkeeping paths — those are "
                            f"shared by design, so nothing here proves this ticket is "
                            f"disjoint from the others (name the CODE paths it edits)")
            else:
                errs.append(f"{t}: no CODE-SCOPE in its tasksheet — can't prove it is "
                            f"disjoint from the others (add CODE-SCOPE at /dev T1)")
    tickets = sorted(k for k, v in scope_map.items() if v)
    for i, t1 in enumerate(tickets):
        for t2 in tickets[i + 1:]:
            hit = scopes_overlap(scope_map[t1], scope_map[t2])
            if hit:
                errs.append(f"{t1} and {t2} share edit territory ({hit}) — "
                            f"serialize them; parallel branches on one file merge blind")
    return errs


def sh(root: Path, *args: str) -> str:
    r = subprocess.run(args, cwd=root, capture_output=True, text=True)
    return r.stdout if r.returncode == 0 else ""


def split_bookkeeping(scope_map: dict[str, list[str]], *homes: str) -> tuple[dict, dict]:
    """Separate CODE territory from BOOKKEEPING homes.

    The bookkeeping homes ({paths.pm}: the coordination log, ledger, minutes;
    {paths.evidence}: each ticket's own evd/; {paths.qa}: the knowledge base and
    known-issues every lane appends a lesson to) are shared by design.
    coord_check REQUIRES every agent that hands a path off to append a row to
    {paths.pm}/coordination.md, and graph_check already treats these homes as
    always-legal for derailment — so counting them as edit territory made two
    agents obeying the handoff protocol collide on the protocol's own log.
    Listing one in a CODE-SCOPE stays harmless; it just proves nothing about
    disjointness.

    Returns (code_scope_map, ignored_map) — ignored_map only holds the tickets
    that actually listed one, so the caller can print what it discounted.
    """
    # norm() FIRST, then drop empties: a home that normalises to the repo root
    # (`paths.pm: .`, a misconfiguration) would otherwise make every path
    # "bookkeeping" and disarm the gate completely. Ignoring it keeps the gate
    # strict and lets the real overlap check speak.
    hs = [h for h in (norm(x) for x in homes) if h]

    def is_book(p: str) -> bool:
        p = norm(p)
        # `p == h` is the home declared EXACTLY (`CODE-SCOPE: docs/pm`); the
        # prefix arm is a path under it. Both count — AC 3 says "any path under
        # paths.pm", and the home itself is the broadest such path.
        return any(p == h or p.startswith(h + "/") for h in hs)

    code = {t: [p for p in ps if not is_book(p)] for t, ps in scope_map.items()}
    ignored = {t: [p for p in ps if is_book(p)]
               for t, ps in scope_map.items() if any(is_book(p) for p in ps)}
    return code, ignored


def mark_bookkeeping_only(code: dict, ignored: dict, sources: dict) -> dict:
    """Tickets whose scope became EMPTY only because of the bookkeeping split
    get the `bookkeeping-only` source marker, so find_conflicts names the right
    remedy instead of blaming a missing CODE-SCOPE line.

    This is a function rather than three lines inside main() so it can be
    asserted: main() has no selftest, and a reviewer's mutation of the inline
    version survived green.
    """
    for t in ignored:
        if not code.get(t):
            sources[t] = "bookkeeping-only"
    return sources


def main() -> int:
    from ctx import Ctx  # noqa: E402
    c = Ctx()
    try:
        parallel = int(str(c.cfg("team.parallel", 1)))
    except ValueError:
        print(f"❌ parallel_check: team.parallel {c.cfg('team.parallel')!r} is not a number")
        return 1
    if parallel <= 1:
        print(f"✅ parallel_check: parallel mode off (team.parallel={parallel}) — nothing to check")
        return 0

    key = str(c.cfg("project.key"))
    protected = str(c.cfg("git.protected_branch", "main"))
    pattern = str(c.cfg("git.branch_pattern", r"^(feat|fix)/{key}-[0-9]+-"))
    ev = str(c.cfg("paths.evidence", "evd"))

    scope_map, sources = discover(c.root, key, pattern, protected, ev, with_sources=True)
    # bookkeeping homes are shared by design → never edit territory (see
    # split_bookkeeping). A scope left EMPTY by the split still has a line, so
    # mark it for find_conflicts' message instead of blaming a missing line.
    scope_map, ignored = split_bookkeeping(scope_map, str(c.cfg("paths.pm", "docs/pm")), ev,
                                           str(c.cfg("paths.qa", "docs/qa")))
    sources = mark_bookkeeping_only(scope_map, ignored, sources)
    for t, ps in sorted(ignored.items()):
        print(f"   · {t}: bookkeeping paths not counted as edit territory: {', '.join(ps)}")

    errs: list[str] = []
    if len(scope_map) > parallel:
        errs.append(f"{len(scope_map)} DEV branches in flight but team.parallel={parallel} "
                    f"— over the concurrency cap ({', '.join(sorted(scope_map))})")
    errs.extend(find_conflicts(scope_map, sources, ev))

    if errs:
        print(f"❌ parallel_check: {len(errs)} problems in the in-flight set")
        for e in errs:
            print(f"   - {e}")
        return 1
    print(f"✅ parallel_check: {len(scope_map)} unmerged in-flight DEV branch(es) ≤ {parallel}, "
          f"all code scopes disjoint")
    return 0


def tasksheet_text(root: Path, ev: str, ticket: str, branch: str) -> tuple[str, str]:
    """The in-flight branch's tasksheet, and WHERE it was read from.

    Worktree-safe: parallel DEV agents each have their own tree on disk, so a
    SIBLING's evd/ is not on this filesystem — reading it from disk was
    structurally red for every worker in parallel mode. Every worktree shares
    one object store, so the sibling's COMMITTED tasksheet is readable as
    `git show <branch>:<path>`.

    Order, and why: this branch's own working tree first (my own tasksheet may
    legitimately still be uncommitted while I write it) → git on the named
    branch (the sibling case) → the working tree as a last resort (single-tree
    mode, where a sibling branch exists but its sheet is not committed yet) →
    ("", "missing on <branch>"), which find_conflicts turns into "not committed".
    """
    rel = f"{ev}/{ticket}/dev/tasksheet.md"
    ts = Path(root) / rel
    cur = sh(root, "git", "rev-parse", "--abbrev-ref", "HEAD").strip()
    if branch == cur and ts.is_file():
        return ts.read_text(encoding="utf-8", errors="replace"), "working tree"
    txt = sh(root, "git", "show", f"{branch}:{rel}")
    if txt:
        return txt, f"git {branch}"
    if ts.is_file():
        return ts.read_text(encoding="utf-8", errors="replace"), "working tree (fallback)"
    return "", f"missing on {branch}"


def _patch_ids(root: Path, diff_text: str) -> set:
    """The stable patch-ids in a diff stream (one per commit), or an empty set.

    `git patch-id` is content-addressed, so it recognises the same change after
    a squash or a rebase rewrote its sha."""
    if not diff_text.strip():
        return set()
    r = subprocess.run(["git", "patch-id", "--stable"], cwd=root,
                       input=diff_text, capture_output=True, text=True)
    return {ln.split()[0] for ln in r.stdout.splitlines() if ln.strip()}


def has_landed(root: Path, protected: str, branch: str, merged: set) -> bool:
    """Is this branch's work already ON the protected branch?

    `git.merge_strategy` allows merge, squash and rebase, and each leaves a
    DIFFERENT trace. A filter that only knows the first counts finished work as
    in-flight forever — the branch lingers locally, holds a `team.parallel`
    slot, and keeps its stale CODE-SCOPE in the overlap check until a human
    deletes it:
      · merge   → the tip is an ancestor of protected (the precomputed
                  `--merged` set) AND protected has moved past it;
      · rebase / cherry-pick / single-commit squash → every commit has an
                  upstream twin, so `git cherry` prints no `+` line;
      · multi-commit squash → no single commit matches, but the branch's
                  COMBINED diff IS the squash commit, so its patch-id is on
                  protected.

    **Not-yet-diverged is not landed, and stays that way.** A branch created and
    not yet committed to has its tip AT the protected tip, so it is trivially
    "reachable from protected" — `--merged` alone hid every freshly dispatched
    worker and the concurrency cap stopped firing in exactly the window it
    exists for. The separation must be TOPOLOGICAL, not positional: asking
    whether protected has merely moved past the branch works only until the
    day's first serial merge, after which every idle worker is hidden again.

    So: a branch that landed through a merge commit has its tip on that merge's
    SECOND parent, which makes it reachable from protected but never a member of
    protected's first-parent chain. A branch that was only created — or
    fast-forwarded — sits ON that chain. That property does not change when
    protected advances, which is the whole point.

    A fast-forwarded branch is therefore read as IN FLIGHT: it is
    indistinguishable from a fresh one, and a false red the PM clears with
    `git branch -d` is the safe direction. Every other leg fails safe the same
    way — an unanswerable question leaves the branch in flight.
    """
    if branch in merged:
        tip = sh(root, "git", "rev-parse", branch).strip()
        mainline = sh(root, "git", "rev-list", "--first-parent", protected).split()
        if not tip or not mainline:
            return False                  # cannot tell → in flight
        return tip not in mainline
    base = sh(root, "git", "merge-base", protected, branch).strip()
    if not base:
        return False                      # unrelated histories — cannot tell
    cherry = sh(root, "git", "cherry", protected, branch).strip()
    if cherry and not any(ln.startswith("+") for ln in cherry.splitlines()):
        return True
    want = _patch_ids(root, sh(root, "git", "diff", base, branch))
    if not want:
        return False                      # no cumulative change to find; not started
    have = _patch_ids(root, sh(root, "git", "log", "-200", "-p", "--no-color",
                               f"{base}..{protected}"))
    return want <= have


def discover(root, key, pattern, protected, ev, with_sources: bool = False):
    """Local branches matching the grammar → {TICKET: scope paths}
    (+ {TICKET: where the tasksheet was read from} when with_sources)."""
    rx = re.compile(pattern.replace("{key}", re.escape(key)))
    keyrx = re.compile(rf"({re.escape(key)}-\d+)", re.I)
    out: dict[str, list[str]] = {}
    sources: dict[str, str] = {}
    # A branch whose work already LANDED on the protected branch is finished,
    # not in-flight: it lingers locally until someone deletes it, and a worktree
    # may still have it checked out (`git branch --merged` decorates that one
    # with "+ ", the string that fooled the live run — for-each-ref yields plain
    # names). Counting it refuses the next dispatch over work that already
    # shipped. `has_landed` decides, because "landed" looks different under each
    # git.merge_strategy and does NOT include "branch not started yet".
    # If `protected` does not resolve (fresh clone, renamed default branch), git
    # errors and sh() returns "" → nothing is filtered out and every branch
    # counts. That is deliberate: an empty filter makes the GATE stricter, never
    # laxer, so an unknown merge state can only over-report, never wave work through.
    merged = {b.strip() for b in
              sh(root, "git", "for-each-ref", "--format=%(refname:short)",
                 f"--merged={protected}", "refs/heads/").splitlines() if b.strip()}
    for br in sh(root, "git", "for-each-ref", "--format=%(refname:short)", "refs/heads/").splitlines():
        br = br.strip()
        if br == protected or not rx.search(br):
            continue
        if has_landed(Path(root), protected, br, merged):
            continue
        m = keyrx.search(br)
        if not m:
            continue
        ticket = m.group(1).upper()
        text, src = tasksheet_text(Path(root), ev, ticket, br)
        out[ticket] = parse_scope(text)
        sources[ticket] = src
    return (out, sources) if with_sources else out


def _selftest() -> None:
    assert parse_scope("CODE-SCOPE: src/auth/ src/lib/x.ts") == ["src/auth", "src/lib/x.ts"]
    assert paths_touch("src/lib", "src/lib/x.ts")            # dir nests file
    assert paths_touch("src/lib/x.ts", "src/lib")            # symmetric
    assert paths_touch("src/a", "src/a")                     # equal
    assert not paths_touch("src/auth", "src/catalog")        # disjoint siblings
    assert not paths_touch("src/lib/a.ts", "src/lib/b.ts")   # different files, same dir
    assert paths_touch("src/lib/", "src/lib/x.ts")           # trailing slash normalized (Q1)
    assert not paths_touch("src", "src2")                    # prefix, not nested — must NOT overlap
    assert not paths_touch("src/a", "src/ab")                # prefix, not nested
    # --- one spelling per location: `.`/`..`/`./` resolved, not compared raw ---
    assert norm("docs/pm/../src/x.ts") == "docs/src/x.ts", norm("docs/pm/../src/x.ts")
    assert norm("./src/a") == "src/a" and norm("src/a/") == "src/a"
    assert norm(".") == "" and norm("./") == ""               # the repo root
    assert paths_touch("./src/lib", "src/lib/x.ts")           # spelling must not matter
    # whole-repo scope must collide with EVERYONE, not with no one
    assert paths_touch(".", "src/anything")
    assert paths_touch("src/anything", ".")
    assert scopes_overlap(["."], ["src/anything/x.ts"]) is not None
    e = find_conflicts({"VT-1": [norm(".")], "VT-2": [norm("src/a.ts")]})
    assert any("share edit territory" in x for x in e), ("a `.` scope claims the repo", e)
    # disjoint set → no conflicts
    disjoint = {"VT-1": ["src/auth/"], "VT-2": ["src/catalog/"]}
    assert find_conflicts({k: [norm(p) for p in v] for k, v in disjoint.items()}) == [], "disjoint must be clean"
    # overlapping → red
    over = {"VT-1": ["src/lib/"], "VT-2": ["src/lib/session.ts"]}
    e = find_conflicts({k: [norm(p) for p in v] for k, v in over.items()})
    assert any("share edit territory" in x for x in e), e
    # missing scope → red
    miss = {"VT-1": ["src/a/"], "VT-2": []}
    e = find_conflicts(miss)
    assert any("no CODE-SCOPE" in x for x in e), e
    # over-cap logic (count vs parallel) is checked in main(); prove the comparison:
    scope_map = {"VT-1": ["src/a/"], "VT-2": ["src/b/"], "VT-3": ["src/c/"]}
    assert len(scope_map) > 2, "3 branches must exceed a cap of 2"

    # --- bookkeeping homes are shared by design → never edit territory --------
    # BOUNDARY PAIR: the same shape must be green on a bookkeeping path and red
    # on a code path, or the exclusion has quietly disarmed the whole gate.
    both = {"VT-1": ["src/a/", "docs/pm/coordination.md"],
            "VT-2": ["src/b/", "docs/pm/coordination.md", "evd/VT-2/dev"]}
    code, ignored = split_bookkeeping({k: [norm(p) for p in v] for k, v in both.items()},
                                      "docs/pm", "evd")
    assert find_conflicts(code) == [], "the coordination log must not collide two agents"
    assert ignored == {"VT-1": ["docs/pm/coordination.md"],
                       "VT-2": ["docs/pm/coordination.md", "evd/VT-2/dev"]}, ignored
    still = {"VT-1": ["src/a/", "docs/pm/x"], "VT-2": ["src/a/x.ts"]}
    code, _ = split_bookkeeping({k: [norm(p) for p in v] for k, v in still.items()},
                                "docs/pm", "evd")
    assert any("share edit territory" in x for x in find_conflicts(code)), \
        "real overlap under code paths must STILL red"
    # a home is matched as a path prefix, not a string prefix
    code, ignored = split_bookkeeping({"VT-1": ["docs/pmx/a.ts"]}, "docs/pm", "evd")
    assert code == {"VT-1": ["docs/pmx/a.ts"]} and ignored == {}, (code, ignored)
    # the home declared EXACTLY is bookkeeping too (the broadest path under it) —
    # without this, two tickets both declaring `docs/pm` collided on the log
    code, ignored = split_bookkeeping({"VT-1": [norm("docs/pm")], "VT-2": [norm("docs/pm/")]},
                                      "docs/pm", "evd")
    assert code == {"VT-1": [], "VT-2": []}, code
    assert not any("share edit territory" in x for x in find_conflicts(code)), \
        "the bookkeeping home itself must never be a collision"
    # they are still each RED — for the honest reason (no code territory declared)
    e = find_conflicts(code, mark_bookkeeping_only(code, ignored, {}))
    assert len(e) == 2 and all("only bookkeeping paths" in x for x in e), e
    # a path that only LOOKS like it lives in a home (resolved away) is code…
    code, ignored = split_bookkeeping({"VT-1": [norm("docs/pm/../src/x.ts")]}, "docs/pm", "evd")
    assert code == {"VT-1": ["docs/src/x.ts"]} and ignored == {}, (code, ignored)
    # …and one that only looks like it does NOT (a `./` spelling) is bookkeeping
    code, ignored = split_bookkeeping({"VT-1": [norm("./docs/pm/coordination.md")]},
                                      "docs/pm", "evd")
    assert code == {"VT-1": []} and ignored == {"VT-1": ["docs/pm/coordination.md"]}, (code, ignored)
    # two tickets colliding through such a spelling must STILL red
    both2 = {"VT-1": [norm("docs/pm/../src/x.ts")], "VT-2": [norm("docs/src/x.ts")]}
    code, _ = split_bookkeeping(both2, "docs/pm", "evd")
    assert any("share edit territory" in x for x in find_conflicts(code)), code
    # a home that normalises to the repo root is a misconfiguration, and must NOT
    # swallow every path (which would disarm the gate entirely)
    code, ignored = split_bookkeeping({"VT-1": [norm("src/a.ts")]}, ".", "evd")
    assert code == {"VT-1": ["src/a.ts"]} and ignored == {}, (code, ignored)
    # a scope of ONLY bookkeeping paths proves nothing — and says so precisely
    code, ignored = split_bookkeeping({"VT-7": ["docs/pm/coordination.md"]}, "docs/pm", "evd")
    assert code == {"VT-7": []} and "VT-7" in ignored, (code, ignored)
    # the marker is WIRED by mark_bookkeeping_only (main() has no selftest, so an
    # inline version of this was mutable without any assertion noticing)
    src_map = mark_bookkeeping_only(code, ignored, {"VT-7": "working tree"})
    assert src_map["VT-7"] == "bookkeeping-only", src_map
    e = find_conflicts(code, src_map)
    assert any("only bookkeeping paths" in x for x in e), e
    # …and a ticket that kept real code territory keeps its original source
    keep = mark_bookkeeping_only({"VT-8": ["src/a"]}, {"VT-8": ["evd/VT-8"]},
                                 {"VT-8": "git feat/VT-8-x"})
    assert keep["VT-8"] == "git feat/VT-8-x", keep

    # --- worktree mode: a sibling's tasksheet lives only in GIT ---------------
    # An off-disk fixture: the sheet is committed on its branch and absent from
    # the checkout that runs the gate — exactly the live parallel-mode layout.
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        r = Path(tmp)

        def g(*a):
            subprocess.run(["git", *a], cwd=r, capture_output=True, text=True, check=True)

        g("init", "-q", "-b", "main")
        g("config", "user.email", "t@t")
        g("config", "user.name", "t")
        (r / "README").write_text("x")
        g("add", "-A")
        g("commit", "-qm", "init")

        g("checkout", "-qb", "feat/VT-2-other")
        (r / "evd/VT-2/dev").mkdir(parents=True)
        (r / "evd/VT-2/dev/tasksheet.md").write_text("CODE-SCOPE: src/other/\n")
        g("add", "-A")
        g("commit", "-qm", "tasksheet")
        g("checkout", "-q", "main")
        assert not (r / "evd/VT-2/dev/tasksheet.md").exists(), \
            "fixture: the sibling's sheet must be OFF DISK or this proves nothing"
        txt, src = tasksheet_text(r, "evd", "VT-2", "feat/VT-2-other")
        assert parse_scope(txt) == ["src/other"] and src.startswith("git "), (txt, src)
        # …and step 1 of the documented order: MY OWN branch is read from the
        # WORKING TREE, so a scope I am still editing is the one that counts.
        # (Deleting that branch survived every assertion until this one existed.)
        g("checkout", "-q", "feat/VT-2-other")
        (r / "evd/VT-2/dev/tasksheet.md").write_text("CODE-SCOPE: src/edited-not-committed/\n")
        txt, src = tasksheet_text(r, "evd", "VT-2", "feat/VT-2-other")
        assert parse_scope(txt) == ["src/edited-not-committed"] and src == "working tree", \
            f"my own branch must be read from disk, not from git: {(txt, src)}"
        (r / "evd/VT-2/dev/tasksheet.md").write_text("CODE-SCOPE: src/other/\n")
        g("checkout", "-q", "main")
        # …and a branch whose sheet was never committed is named as such, not as
        # a phantom empty scope
        txt, src = tasksheet_text(r, "evd", "VT-9", "feat/VT-9-none")
        assert txt == "" and src.startswith("missing"), src
        e = find_conflicts({"VT-9": []}, {"VT-9": src})
        assert any("not committed" in x for x in e), e
        # the remedy path follows paths.evidence, not a hardcoded "evd"
        e = find_conflicts({"VT-9": []}, {"VT-9": src}, "evidence")
        assert any("evidence/VT-9/dev/tasksheet.md" in x for x in e), e

        # --- a MERGED branch is finished work, not in flight -----------------
        # including one checked out in a worktree (`git branch` decorates it
        # "+ feat/…"), which is what pushed the live run over its cap.
        g("checkout", "-qb", "feat/VT-3-merged")
        (r / "landed.txt").write_text("done\n")
        g("add", "-A")
        g("commit", "-qm", "VT-3 landed")
        g("checkout", "-q", "main")
        g("merge", "-q", "--no-ff", "-m", "merge VT-3", "feat/VT-3-merged")
        g("worktree", "add", "-q", str(r / "wt-vt3"), "feat/VT-3-merged")
        decorated = subprocess.run(["git", "branch", "--merged", "main"], cwd=r,
                                   capture_output=True, text=True).stdout
        assert "+ feat/VT-3-merged" in decorated, \
            f"fixture: the worktree branch must be '+'-decorated: {decorated!r}"
        pat = r"^(feat|fix)/VT-[0-9]+-"
        found, srcs = discover(r, "VT", pat, "main", "evd", with_sources=True)
        assert sorted(found) == ["VT-2"], \
            f"merged VT-3 (checked out in a worktree) must not be in flight: {found}"
        assert found["VT-2"] == ["src/other"] and srcs["VT-2"].startswith("git "), (found, srcs)
        # boundary: the SAME branch counts the moment it is not merged
        g("checkout", "-q", "-B", "feat/VT-4-live", "feat/VT-3-merged")
        (r / "wip.txt").write_text("wip\n")
        g("add", "-A")
        g("commit", "-qm", "VT-4 wip")
        g("checkout", "-q", "main")
        found = discover(r, "VT", pat, "main", "evd")
        assert sorted(found) == ["VT-2", "VT-4"], f"unmerged branches must count: {found}"
        g("worktree", "remove", "--force", str(r / "wt-vt3"))

        # NOT-YET-DIVERGED IS NOT LANDED. A just-dispatched worker's tip sits AT
        # the protected tip, so it is trivially "reachable from protected" —
        # filtering on `--merged` alone hid every fresh worker and the
        # concurrency cap stopped firing in the window it exists for. This is
        # the regression guard for that.
        g("branch", "feat/VT-5-fresh", "main")
        g("branch", "feat/VT-6-fresh", "main")
        found = discover(r, "VT", pat, "main", "evd")
        assert "VT-5" in found and "VT-6" in found, \
            f"a branch created but not yet committed to is IN FLIGHT: {found}"
        assert found["VT-5"] == [] and found["VT-6"] == [], found
        assert len(found) > 2, f"three-plus in flight must be able to exceed a cap of 2: {found}"
        # …AND IT MUST STAY IN FLIGHT once the protected branch advances. This is
        # the /team steady state — code in parallel, merge serially, dispatch
        # again — so a rule that only holds until the day's first merge hides
        # every idle worker from the cap for the rest of the day. A positional
        # test ("has protected moved past me?") passes the two lines above and
        # fails here; only the topological test survives both.
        g("commit", "--allow-empty", "-qm", "chore: unrelated work lands on main")
        found = discover(r, "VT", pat, "main", "evd")
        assert "VT-5" in found and "VT-6" in found, \
            f"a fresh worker branch stays IN FLIGHT after main advances: {found}"
        assert len(found) > 2, f"the cap must still be able to fire: {found}"
        # and the genuinely merged branch is STILL excluded after main advanced
        assert "VT-3" not in found, f"a merged branch stays landed: {found}"
        g("branch", "-D", "feat/VT-5-fresh")
        g("branch", "-D", "feat/VT-6-fresh")

        # SQUASH-merged work has landed too, though no commit sha survives:
        # `git.merge_strategy` allows squash, and a squashed branch is never
        # `--merged`, so it would hold a team.parallel slot forever.
        g("checkout", "-qb", "feat/VT-7-squashed", "main")
        (r / "sq1.txt").write_text("one\n")
        g("add", "-A")
        g("commit", "-qm", "VT-7 first")
        (r / "sq2.txt").write_text("two\n")
        g("add", "-A")
        g("commit", "-qm", "VT-7 second")
        g("checkout", "-q", "main")
        g("merge", "-q", "--squash", "feat/VT-7-squashed")
        g("commit", "-qm", "feat(VT-7): squashed (#12)")
        assert "feat/VT-7-squashed" not in sh(
            r, "git", "for-each-ref", "--format=%(refname:short)",
            "--merged=main", "refs/heads/"), "fixture: a squash must NOT look merged to git"
        found = discover(r, "VT", pat, "main", "evd")
        assert "VT-7" not in found, f"a squash-merged branch has landed: {found}"
        # boundary: new work on top of the squashed branch is in flight again
        g("checkout", "-q", "feat/VT-7-squashed")
        (r / "sq3.txt").write_text("three\n")
        g("add", "-A")
        g("commit", "-qm", "VT-7 more work after the squash")
        g("checkout", "-q", "main")
        found = discover(r, "VT", pat, "main", "evd")
        assert "VT-7" in found, f"work added after a squash is in flight again: {found}"

    print("parallel_check selftest: OK (parse + nest/equal/disjoint + `.`/`..`/`./` "
          "canonicalised + whole-repo scope collides with everyone; conflicts: "
          "disjoint green, overlap red, missing-scope red, over-cap comparison; "
          "bookkeeping homes ignored (home itself included, spelling-proof), real "
          "overlap still red, bookkeeping-only marked and named, root home not "
          "swallowing the repo; worktree: sibling tasksheet read from git, own branch "
          "read from the working tree, uncommitted one named; landed: merged branch — "
          "even '+'-decorated in a worktree — and squash-merged branch not in flight, "
          "while a NOT-YET-DIVERGED branch and post-squash work still are)")


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        _selftest()
    else:
        sys.exit(main())
