#!/usr/bin/env python3
"""change_class.py — what KIND of change is this diff? Measured, never declared.

Why this exists: the fence does not measure SIZE (red-flags #2) — an agent that
calls its own change small still gets the whole fence. But a fence that cannot
tell a README typo from a payment rewrite charges both the same toll: two fresh
reviewer agents, three "tried to break" bullets each. On a one-line copy change
there is nothing to try, so the bullets get INVENTED. That is review theatre, and
it teaches a team that cards are paperwork rather than evidence.

So the RISK CLASS is measured here, from the diff itself. Nothing in the dossier
can declare it, and the agent never gets a vote.

Four classes, escalating; every ambiguity resolves UPWARD:

  docs         every changed path is prose no tool renders — `.md`/`.txt`/`.rst`
               outside the doctrine, template, skill, hook and CI trees, plus the
               evidence directory. No executable file is touched at all.
  surface      code files changed, but each one's CODE SKELETON is byte-identical
               across the diff: only string bodies, comments and JSX text moved.
               Capped by `review.surface_max_lines` (default 40 changed lines).
  logic        anything else. The default, and where every doubt lands.
  high-stakes  the diff touches `review.high_stakes_paths` or its content matches
               `review.high_stakes_terms` — review_check's existing rule, named.

The skeleton comparison is deliberately crude and FAILS CLOSED. All of these are
`logic` without further argument: an unknown suffix, a file this scanner cannot
parse, an added or deleted code file, any change inside a template literal (it can
carry `${code}`), a lockfile, a config or data file (yaml/json/sql/prisma/env), a
migration, a Dockerfile or Makefile. Over-escalation costs a reviewer; under-
escalation costs a production incident.

A `surface` change is NOT a safe change — a string can be a shell command, a SQL
fragment, a selector a test depends on. It is a change whose blast radius one
reviewer can actually see, which is why `surface` still requires a card.

  python3 change_class.py [--base origin/<protected>] [--sha <commit>|WORKTREE] [--json]
  python3 change_class.py --selftest

Exit code is 0 for every classification — this is a measurement, not a fence.
The fence is review_check.py, which reads the class from here.
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "lib"))

DOC_SUFFIX = {".md", ".markdown", ".txt", ".rst", ".adoc"}

# Markdown in these trees is not prose — it is rendered into skills, agents,
# workflows and hooks, i.e. it is the runtime. A doctrine edit changes what every
# agent does next and is never a "docs-only" change.
RENDERED = (
    "core/doctrine/", "core/workflows/", "core/templates/", "core/agents/",
    "docs/team/", ".claude/", ".cursor/", ".windsurf/", ".github/", ".githooks/",
    ".vteam/", "profiles/", "adapters/", "providers/",
)

C_LIKE = {".js", ".mjs", ".cjs", ".jsx", ".ts", ".tsx", ".mts", ".cts", ".java",
          ".go", ".rs", ".c", ".h", ".cc", ".cpp", ".hpp", ".cs", ".swift",
          ".kt", ".scala", ".php", ".dart", ".css", ".scss", ".less"}
HASH_LIKE = {".py", ".sh", ".bash", ".zsh", ".rb", ".pl", ".r"}
JSXY = {".jsx", ".tsx", ".html", ".htm", ".vue", ".svelte", ".astro"}

# Data and configuration ARE behaviour: a threshold, a route, a permission or a
# dependency range moves the product without a single line of code changing.
NEVER_SURFACE_SUFFIX = {".yml", ".yaml", ".json", ".toml", ".ini", ".cfg", ".conf",
                        ".env", ".sql", ".prisma", ".lock", ".xml", ".gradle",
                        ".tf", ".tfvars", ".proto", ".graphql", ".csv"}
NEVER_SURFACE_NAME = {"dockerfile", "makefile", "procfile", "jenkinsfile", "package-lock.json",
                      "yarn.lock", "pnpm-lock.yaml", "gemfile.lock", "cargo.lock", "poetry.lock"}

KEYWORDS = {"return", "if", "else", "const", "let", "var", "function", "await",
            "async", "new", "typeof", "delete", "throw", "class", "import",
            "export", "for", "while", "switch", "case", "break", "continue",
            "yield", "this", "null", "undefined", "true", "false", "do", "in",
            "of", "void", "extends", "implements", "interface", "enum", "try",
            "catch", "finally", "instanceof", "super", "static"}

# A JSX/HTML text run: between `>` and `<`, carrying no bracket, operator or quote.
# `if (a > b) return <div/>` cannot match — the run holds `)` and the word `return`.
PROSE_RUN = re.compile(r">([^<>{}()\[\]=;&|!?+*/\\\"'`]*)<")


def sh(root: Path, *args: str) -> tuple[int, str]:
    r = subprocess.run(args, cwd=root, capture_output=True, text=True)
    return r.returncode, r.stdout


def is_doc(path: str, evidence_dir: str) -> bool:
    """Prose a tool does not render. The evidence directory counts: it is the record."""
    p = path.replace("\\", "/")
    ev = (evidence_dir or "evd").strip("/") + "/"
    if p.startswith(ev):
        return True
    if any(p.startswith(r) for r in RENDERED):
        return False
    return Path(p).suffix.lower() in DOC_SUFFIX


def skeleton(text: str, suffix: str) -> str | None:
    """Code with string bodies, comments and JSX text blanked, whitespace collapsed.

    None = this scanner will not judge the file, which the caller reads as `logic`.
    Template literals are kept VERBATIM on purpose: `${…}` is code wearing a string's
    clothes, so any edit inside one must move the skeleton."""
    s = suffix.lower()
    if s not in C_LIKE and s not in HASH_LIKE:
        return None
    line_c = "//" if s in C_LIKE else "#"
    block = s in C_LIKE
    triple = s == ".py"
    out: list[str] = []
    i, n = 0, len(text)
    while i < n:
        ch = text[i]
        nxt = text[i + 1] if i + 1 < n else ""
        if block and ch == "/" and nxt == "*":
            j = text.find("*/", i + 2)
            if j < 0:
                return None          # unterminated block comment: refuse to judge
            i = j + 2
            out.append(" ")
            continue
        if text.startswith(line_c, i):
            j = text.find("\n", i)
            i = n if j < 0 else j
            out.append(" ")
            continue
        if triple and (text.startswith('"""', i) or text.startswith("'''", i)):
            q = text[i:i + 3]
            j = text.find(q, i + 3)
            if j < 0:
                return None
            i = j + 3
            out.append('""')          # a docstring is a comment with quotes on
            continue
        if ch == "`" and s in C_LIKE:
            j, buf = i + 1, ["`"]     # template literal: kept, so `${x}` edits show
            while j < n:
                if text[j] == "\\":
                    buf.append(text[j:j + 2]); j += 2; continue
                buf.append(text[j])
                if text[j] == "`":
                    j += 1
                    break
                j += 1
            else:
                return None
            out.append("".join(buf))
            i = j
            continue
        if ch in ('"', "'"):
            j = i + 1
            while j < n:
                if text[j] == "\\":
                    j += 2
                    continue
                if text[j] == ch:
                    j += 1
                    break
                if text[j] == "\n":
                    return None       # unterminated literal: refuse to judge
                j += 1
            else:
                return None
            out.append(ch + ch)       # the quotes stay, the body goes
            i = j
            continue
        out.append(ch)
        i += 1
    sk = "".join(out)
    if suffix.lower() in JSXY:
        sk = PROSE_RUN.sub(
            lambda m: m.group(0) if set(re.findall(r"[A-Za-z_]+", m.group(1))) & KEYWORDS else "><",
            sk)
    return re.sub(r"\s+", " ", sk).strip()


def blob(root: Path, ref: str, path: str) -> str | None:
    if ref == "WORKTREE":
        f = root / path
        try:
            return f.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            return None
    code, out = sh(root, "git", "show", f"{ref}:{path}")
    return out if code == 0 else None


def changed(root: Path, base: str, sha: str) -> list[tuple[str, str]] | None:
    """(status, path) pairs. Three-dot first (the merge base is what a PR shows),
    two-dot when a shallow CI clone has no merge base."""
    ref = "HEAD" if sha == "WORKTREE" else sha
    for args in ((f"{base}...{ref}",), (base, ref)):
        code, out = sh(root, "git", "diff", "--name-status", *args)
        if code == 0:
            rows = []
            for line in out.splitlines():
                parts = line.split("\t")
                if len(parts) < 2:
                    continue
                st = parts[0][0]
                if st in ("R", "C") and len(parts) >= 3:
                    # A rename has TWO sides and both count: `src/app.ts` renamed to
                    # `notes.md` deletes executable code while every remaining path
                    # looks like prose. Found by the adversarial card on this ticket.
                    rows.append(("D", parts[1]))
                    rows.append(("A", parts[2]))
                else:
                    rows.append((st, parts[-1]))
            if sha == "WORKTREE":
                code2, out2 = sh(root, "git", "status", "--porcelain")
                for line in out2.splitlines():
                    p = line[3:].split(" -> ")[-1].strip()
                    st = "A" if line[:2].strip() in ("??", "A") else "M"
                    if p and all(p != r[1] for r in rows):
                        rows.append((st, p))
            return rows
    return None


def classify(root: Path, base: str, sha: str, hs_paths: list[str], hs_terms: list[str],
             evidence_dir: str = "evd", max_lines: int = 40) -> tuple[str, list[str]]:
    rows = changed(root, base, sha)
    if rows is None:
        return "logic", [f"cannot compute the diff {base}↔{sha} — classifying as logic, "
                         f"the strictest reading"]
    if not rows:
        return "docs", ["no files changed"]

    paths = [p for _, p in rows]
    hit = [p for p in paths if any(p.startswith(h) for h in hs_paths)]
    if hit:
        return "high-stakes", [f"{hit[0]} is under review.high_stakes_paths"]
    if hs_terms:
        ref = "HEAD" if sha == "WORKTREE" else sha
        code, dt = sh(root, "git", "diff", f"{base}...{ref}")
        if code != 0:
            code, dt = sh(root, "git", "diff", base, ref)
        if code == 0:
            m = re.search("|".join(re.escape(t) for t in hs_terms), dt or "", re.I)
            if m:
                return "high-stakes", [f"the diff content matches the high-stakes term "
                                       f"{m.group(0)!r}"]

    code_rows = [(st, p) for st, p in rows if not is_doc(p, evidence_dir)]
    if not code_rows:
        return "docs", [f"{len(rows)} changed path(s), all prose no tool renders"]

    reasons, why_not = [], []
    for st, p in code_rows:
        name = Path(p).name.lower()
        suf = Path(p).suffix.lower()
        if st not in ("M",):
            why_not.append(f"{p}: {'added' if st == 'A' else 'deleted/renamed'} code file "
                           f"(a file that appears or disappears has no skeleton to compare)")
            continue
        if name in NEVER_SURFACE_NAME or suf in NEVER_SURFACE_SUFFIX:
            why_not.append(f"{p}: configuration, data or a lockfile — behaviour moves here "
                           f"without a line of code changing")
            continue
        old, new = blob(root, base, p), blob(root, sha, p)
        if old is None or new is None:
            why_not.append(f"{p}: cannot read both sides of the diff")
            continue
        sk_old, sk_new = skeleton(old, suf), skeleton(new, suf)
        if sk_old is None or sk_new is None:
            why_not.append(f"{p}: this scanner does not parse {suf or 'files without a suffix'}")
            continue
        if sk_old != sk_new:
            why_not.append(f"{p}: the code skeleton moved — this is not a text change")
            continue
        reasons.append(f"{p}: strings, comments or JSX text only (skeleton identical)")

    if why_not:
        return "logic", why_not[:5]

    code_paths = {p for _, p in code_rows}
    ref = "HEAD" if sha == "WORKTREE" else sha
    code, stat = sh(root, "git", "diff", "--numstat", f"{base}...{ref}")
    if code != 0:
        code, stat = sh(root, "git", "diff", "--numstat", base, ref)
    total = 0
    for line in (stat or "").splitlines():
        parts = line.split("\t")
        if len(parts) == 3 and parts[2] in code_paths:
            total += sum(int(x) for x in parts[:2] if x.isdigit())
    if total > max_lines:
        return "logic", [f"{total} changed lines in code files is over "
                         f"review.surface_max_lines={max_lines} — volume of text is its own risk"]
    reasons.append(f"{total} changed line(s) in code, within review.surface_max_lines={max_lines}")
    return "surface", reasons


def _selftest() -> None:
    import os
    import tempfile

    # ── pure functions first ────────────────────────────────────────────────
    assert skeleton('const a = "hi"; // note\n', ".ts") == 'const a = "";', \
        skeleton('const a = "hi"; // note\n', ".ts")
    assert skeleton('const a = "hi";\n', ".ts") == skeleton('const a = "bye";\n', ".ts"), \
        "a string body is not the skeleton"
    assert skeleton('const a = "hi";\n', ".ts") != skeleton('const b = "hi";\n', ".ts"), \
        "an identifier IS the skeleton"
    assert skeleton('x(`a ${p} b`)\n', ".ts") != skeleton('x(`a ${q} b`)\n', ".ts"), \
        "a template literal carries code — an edit inside one must move the skeleton"
    assert skeleton("<button>Submit</button>", ".tsx") == skeleton("<button>Gửi</button>", ".tsx"), \
        "JSX text is prose"
    assert skeleton("if (a > b) return <i/>", ".tsx") != skeleton("if (a > c) return <i/>", ".tsx"), \
        "`a > b) return <` must not be mistaken for a prose run"
    assert skeleton("x = 1\n", ".rb") is not None and skeleton("x", ".unknownsuffix") is None
    assert skeleton('a = "no end\n', ".ts") is None, "an unterminated literal must refuse to judge"
    assert is_doc("README.md", "evd") and is_doc("evd/VT-1/dev/proof.md", "evd")
    assert not is_doc("core/doctrine/red-flags.md", "evd"), "doctrine is rendered — it is runtime"
    assert not is_doc("docs/team/roles/dev.md", "evd") and not is_doc("src/a.ts", "evd")

    # ── the classifier, against real git diffs ──────────────────────────────
    def git(root, *a):
        subprocess.run(["git", *a], cwd=root, check=True, capture_output=True)

    def commit(root, msg):
        git(root, "add", "-A")
        subprocess.run(["git", "commit", "-qm", msg], cwd=root, check=True, capture_output=True,
                       env={**os.environ, "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t",
                            "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t"})

    def case(root, name, expect, mutate):
        git(root, "checkout", "-q", "-B", name, "base")
        mutate()
        commit(root, name)
        got, why = classify(root, "base", "HEAD", ["src/billing/"], ["charge_card"])
        assert got == expect, f"{name}: expected {expect}, got {got} — {why}"
        return why

    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        git(root, "init", "-q", "-b", "base", str(root))
        (root / "src").mkdir()
        (root / "src" / "billing").mkdir()
        (root / "docs").mkdir()
        (root / "src" / "form.tsx").write_text(
            'const label = "Phone";\nexport function F() {\n'
            '  return <button>Submit</button>;\n}\n', encoding="utf-8")
        (root / "src" / "rate.ts").write_text("export const MAX = 5;\n", encoding="utf-8")
        (root / "src" / "billing" / "pay.ts").write_text("export const pay = () => 1;\n",
                                                         encoding="utf-8")
        (root / "config.yaml").write_text("limit: 5\n", encoding="utf-8")
        (root / "src" / "copy.ts").write_text(
            "".join(f'export const s{i} = "line {i}";\n' for i in range(60)), encoding="utf-8")
        (root / "README.md").write_text("# hi\n", encoding="utf-8")
        commit(root, "init")

        case(root, "docs-only", "docs",
             lambda: (root / "README.md").write_text("# hi there\n", encoding="utf-8"))
        case(root, "copy-in-a-string", "surface",
             lambda: (root / "src" / "form.tsx").write_text(
                 'const label = "Phone number";\nexport function F() {\n'
                 '  return <button>Submit</button>;\n}\n', encoding="utf-8"))
        case(root, "jsx-button-text", "surface",
             lambda: (root / "src" / "form.tsx").write_text(
                 'const label = "Phone";\nexport function F() {\n'
                 '  return <button>Send</button>;\n}\n', encoding="utf-8"))
        case(root, "a-constant-moved", "logic",
             lambda: (root / "src" / "rate.ts").write_text("export const MAX = 50;\n",
                                                           encoding="utf-8"))
        case(root, "config-value", "logic",
             lambda: (root / "config.yaml").write_text("limit: 500\n", encoding="utf-8"))
        case(root, "new-code-file", "logic",
             lambda: (root / "src" / "new.ts").write_text('export const x = "a";\n',
                                                          encoding="utf-8"))
        case(root, "high-stakes-path", "high-stakes",
             lambda: (root / "src" / "billing" / "pay.ts").write_text(
                 "export const pay = () => 1; // note\n", encoding="utf-8"))
        case(root, "high-stakes-term", "high-stakes",
             lambda: (root / "src" / "form.tsx").write_text(
                 'const label = "charge_card";\nexport function F() {\n'
                 '  return <button>Submit</button>;\n}\n', encoding="utf-8"))
        # 60 string bodies rewritten: the skeleton never moves, the volume alone escalates
        why = case(root, "over-the-cap", "logic", lambda: (root / "src" / "copy.ts").write_text(
            "".join(f'export const s{i} = "dòng {i}";\n' for i in range(60)), encoding="utf-8"))
        assert "surface_max_lines" in why[0], why
        # a deleted test is never surface, however textual the rest looks
        (root / "src" / "form.test.ts").write_text('it("x", () => {});\n', encoding="utf-8")
        git(root, "checkout", "-q", "base")
        commit(root, "add a test")   # committed ON base, so base already points here
        case(root, "deleted-test", "logic",
             lambda: (root / "src" / "form.test.ts").unlink())
        # a rename has two sides: code renamed to prose still deletes code
        # (git does not track an empty directory, so docs/ has to be re-made each time)
        case(root, "code-renamed-to-prose", "logic",
             lambda: ((root / "docs").mkdir(exist_ok=True),
                      (root / "src" / "rate.ts").rename(root / "docs" / "rate.md")))
        case(root, "prose-renamed-to-prose", "docs",
             lambda: ((root / "docs").mkdir(exist_ok=True),
                      (root / "README.md").rename(root / "docs" / "README.md")))

    print("change_class selftest: OK (skeleton: strings/comments/JSX text vs identifiers, "
          "template literals and unparsable files refuse to judge · classes: docs, surface "
          "(string + JSX copy), logic (constant, config, new file, deleted test, over the cap), "
          "high-stakes (path + term))")


def main() -> int:
    args = sys.argv[1:]
    if "--selftest" in args:
        _selftest()
        return 0
    from ctx import Ctx  # noqa: E402 — the selftest must run without a config
    c = Ctx()
    protected = str(c.cfg("git.protected_branch", "main"))
    base, sha = f"origin/{protected}", "HEAD"
    if "--base" in args:
        base = args[args.index("--base") + 1]
    if "--sha" in args:
        sha = args[args.index("--sha") + 1]

    def as_list(v):
        return [str(x) for x in ([v] if isinstance(v, str) else (v or []))]

    try:
        max_lines = int(str(c.cfg("review.surface_max_lines", 40)))
    except ValueError:
        print(f"❌ change_class: review.surface_max_lines "
              f"{c.cfg('review.surface_max_lines')!r} is not a number")
        return 2
    cls, why = classify(c.root, base, sha, as_list(c.cfg("review.high_stakes_paths", [])),
                        as_list(c.cfg("review.high_stakes_terms", [])),
                        str(c.cfg("paths.evidence", "evd")), max_lines)
    if "--json" in args:
        print(json.dumps({"class": cls, "base": base, "sha": sha, "why": why}, indent=2))
        return 0
    print(f"change-class: {cls} ({base}…{sha})")
    for w in why:
        print(f"  · {w}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
