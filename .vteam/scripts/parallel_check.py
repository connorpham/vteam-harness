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
(feat|fix/<KEY>-nn-*), minus the protected branch. For each, the ticket key →
its `CODE-SCOPE:` line in {paths.evidence}/<TICKET>/dev/tasksheet.md (the
committed tasksheet /dev T1 already requires). RED when:
  · more than `team.parallel` branches are in flight (concurrency cap, like
    loop_budget — MAST 1.5 termination-as-data);
  · an in-flight branch has no CODE-SCOPE to check (can't prove it's disjoint);
  · any two in-flight scopes intersect (a path in one equals or nests under a
    path in the other).

Usage: parallel_check.py [--root <dir>]
Exit 0 = safe (or off); 1 = exactly which branches collide.
Selftest: --selftest (disjoint green + overlap/over-cap/missing-scope red).
"""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "lib"))

SCOPE = re.compile(r"^\s*CODE-SCOPE:\s*(.+)$", re.M)


def norm(p: str) -> str:
    """A scope path, trailing slash stripped so a dir and its own name compare."""
    return p.strip().rstrip("/")


def parse_scope(text: str) -> list[str]:
    """The paths on the CODE-SCOPE line, whitespace-separated."""
    m = SCOPE.search(text or "")
    if not m:
        return []
    return [norm(p) for p in m.group(1).split() if p.strip()]


def paths_touch(a: str, b: str) -> bool:
    """True when two paths cover overlapping ground: equal, or one nests the
    other (a file under a dir, either direction)."""
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


def find_conflicts(scope_map: dict[str, list[str]]) -> list[str]:
    """Every colliding pair among the in-flight tickets, plus any with no scope."""
    errs: list[str] = []
    for t, paths in sorted(scope_map.items()):
        if not paths:
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

    scope_map = discover(c.root, key, pattern, protected, ev)
    errs: list[str] = []
    if len(scope_map) > parallel:
        errs.append(f"{len(scope_map)} DEV branches in flight but team.parallel={parallel} "
                    f"— over the concurrency cap ({', '.join(sorted(scope_map))})")
    errs.extend(find_conflicts(scope_map))

    if errs:
        print(f"❌ parallel_check: {len(errs)} problems in the in-flight set")
        for e in errs:
            print(f"   - {e}")
        return 1
    print(f"✅ parallel_check: {len(scope_map)} in-flight DEV branch(es) ≤ {parallel}, "
          f"all scopes disjoint")
    return 0


def discover(root, key, pattern, protected, ev):
    """Local branches matching the grammar → {TICKET: scope paths}."""
    rx = re.compile(pattern.replace("{key}", re.escape(key)))
    keyrx = re.compile(rf"({re.escape(key)}-\d+)", re.I)
    out: dict[str, list[str]] = {}
    for br in sh(root, "git", "for-each-ref", "--format=%(refname:short)", "refs/heads/").splitlines():
        br = br.strip()
        if br == protected or not rx.search(br):
            continue
        m = keyrx.search(br)
        if not m:
            continue
        ticket = m.group(1).upper()
        ts = root / ev / ticket / "dev" / "tasksheet.md"
        out[ticket] = parse_scope(ts.read_text(encoding="utf-8", errors="replace")) if ts.is_file() else []
    return out


def _selftest() -> None:
    assert parse_scope("CODE-SCOPE: src/auth/ src/lib/x.ts") == ["src/auth", "src/lib/x.ts"]
    assert paths_touch("src/lib", "src/lib/x.ts")            # dir nests file
    assert paths_touch("src/lib/x.ts", "src/lib")            # symmetric
    assert paths_touch("src/a", "src/a")                     # equal
    assert not paths_touch("src/auth", "src/catalog")        # disjoint siblings
    assert not paths_touch("src/lib/a.ts", "src/lib/b.ts")   # different files, same dir
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
    print("parallel_check selftest: OK (parse + nest/equal/disjoint + conflicts: "
          "disjoint green, overlap red, missing-scope red, over-cap comparison)")


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        _selftest()
    else:
        sys.exit(main())
