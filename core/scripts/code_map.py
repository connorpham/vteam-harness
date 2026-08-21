#!/usr/bin/env python3
"""code_map.py — the code map (CPG-lite): files, symbols, import edges, doc anchors.

Why: an agent that opens a ticket and then reads the directory tree pays for the
WHOLE repo to find three files. The map is a cheap index, built once per commit,
that answers "which files does this ticket live in?" with **paths and line
ranges — never file content**. Token discipline is the whole point: the map's
job is to shrink what gets read, so it never prints a single line of source.

HONEST SCOPE — this is NOT a Code Property Graph. A real CPG (Joern & co) ships
a per-language compiler frontend and gives you AST + CFG + data-flow. This gives
you three cheap things, stdlib only:
  · python   — a REAL parse (`ast`): top-level + class-level defs, classes, imports
  · js/ts    — CONSERVATIVE REGEXES over text: **lexical, not semantic**. A name
               inside a comment or a template literal can be recorded; a symbol
               produced by a factory/HOF/decorator is missed; no type resolution,
               no path aliases beyond `@/` and root-absolute. Never treat a
               js/ts symbol here as a compiler's answer — treat it as a lead.
  · markdown — headings, ticket/requirement keys (PROJ-123, FR-AUT-01), and
               backticked file paths (which become real doc→code edges)
No data-flow, no call graph, no cross-file type inference. Say "code map", or
"CPG-lite" — never "CPG".

Scan roots come from config, NO new keys: `git.code_paths` (loud error when
empty/missing — the map needs to be told where product code lives) plus
`paths.specs` when it exists. Output: `.vteam/map.json`, fully sorted so a
rebuild diffs clean.

Staleness is first-class: `query` compares the map's build commit against
commits that have since touched `git.code_paths`. Stale prints a loud ⚠ header
and STILL returns results (advisory tool, not a gate) — `--strict` turns that
into exit 1 for CI/workflow use.

Usage:
  python3 .vteam/scripts/code_map.py build
  python3 .vteam/scripts/code_map.py query PROJ-42 wallet topup balance
  python3 .vteam/scripts/code_map.py query manifest guard --max 20
  python3 .vteam/scripts/code_map.py query wallet --strict     # 1 if the map is stale
Selftest: --selftest (tmpdir fixture repo: map content + reverse index + ranking
+ one-hop expansion + loud truncation + staleness warn/--strict red + a python
file with a syntax error recorded, never a crash).
"""
from __future__ import annotations

import argparse
import ast
import json
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "lib"))
from ctx import Ctx  # noqa: E402

MAP_REL = ".vteam/map.json"
REBUILD = "python3 .vteam/scripts/code_map.py build"

LANG_BY_EXT = {
    ".py": "py", ".pyi": "py",
    ".js": "js", ".mjs": "js", ".cjs": "js", ".jsx": "js",
    ".ts": "ts", ".tsx": "ts", ".mts": "ts", ".cts": "ts",
    ".md": "md", ".markdown": "md",
}
JS_EXTS = [".ts", ".tsx", ".mts", ".cts", ".js", ".mjs", ".cjs", ".jsx"]
SKIP_DIRS = {
    ".git", "node_modules", "__pycache__", ".venv", "venv", ".tox", ".mypy_cache",
    ".pytest_cache", ".ruff_cache", "dist", "build", "out", ".next", ".nuxt",
    "coverage", ".coverage", "vendor", ".cache", ".idea", ".vscode", ".vteam",
    ".turbo", ".svelte-kit", "target", "site-packages",
}
SKIP_EXTS = {
    ".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg", ".ico", ".pdf", ".zip",
    ".gz", ".tgz", ".bz2", ".xz", ".woff", ".woff2", ".ttf", ".otf", ".eot",
    ".mp4", ".mov", ".mp3", ".wav", ".pyc", ".pyo", ".so", ".dylib", ".dll",
    ".class", ".jar", ".wasm", ".db", ".sqlite", ".lock", ".pdf", ".xlsx",
}
MAX_BYTES = 1 << 20  # a 1 MB source file is generated; indexing it buys nothing

# ── js/ts lexical patterns (deliberately conservative — see the scope note) ──
JS_FROM = re.compile(r"""\bfrom\s*['"]([^'"\n]+)['"]""")
JS_SIDE_EFFECT = re.compile(r"""(?:^|[\s;])import\s*['"]([^'"\n]+)['"]""", re.M)
JS_REQUIRE = re.compile(r"""\brequire\s*\(\s*['"]([^'"\n]+)['"]\s*\)""")
JS_DYNAMIC = re.compile(r"""\bimport\s*\(\s*['"]([^'"\n]+)['"]\s*\)""")
JS_FUNC_CLASS = re.compile(
    r"^\s*(?:export\s+(?:default\s+)?)?(?:declare\s+)?"
    r"(async\s+function\s*\*?|function\s*\*?|class)\s+([A-Za-z_$][\w$]*)")
JS_TOP_BINDING = re.compile(  # column 0 (or `export`) only: nested consts are noise
    r"^(?:export\s+(?:default\s+)?)?(?:declare\s+)?"
    r"(const|let|var|interface|type|enum)\s+([A-Za-z_$][\w$]*)")

# ── markdown patterns ────────────────────────────────────────────────────────
MD_HEADING = re.compile(r"^(#{1,6})\s+(.+?)\s*#*\s*$")
MD_FENCE = re.compile(r"^\s*(```|~~~)")
MD_KEY = re.compile(r"\b([A-Z][A-Z0-9]{1,9}(?:-[A-Z]{2,5})?-\d{1,6})\b")
MD_CODE_SPAN = re.compile(r"`([^`\n]{2,200})`")
# not tickets, just text that happens to look like one:
KEY_DENY = {"UTF", "ISO", "SHA", "RFC", "AES", "RSA", "HTTP", "HTTPS", "IPV",
            "RGB", "RGBA", "WCAG", "ES", "CSS", "HTML", "MD", "SP", "AA", "AAA",
            "COVID", "GPT", "SSE", "TLS", "SSL", "PBKDF", "BASE"}
STOP = {"the", "and", "for", "with", "that", "this", "from", "into", "not",
         "are", "was", "were", "its", "your", "you", "our", "all", "any", "but",
         "how", "why", "what", "when", "who", "one", "two", "per", "via", "use",
         "used", "uses", "can", "does", "will", "must", "may", "then", "than",
         "each", "also", "only", "very", "more", "most", "some", "such", "here"}


def sh(root: Path, *args: str) -> str:
    return subprocess.run(["git", "-C", str(root), *args],
                          capture_output=True, text=True).stdout.strip()


def head_sha(root: Path) -> str:
    """`rev-parse HEAD` ECHOES "HEAD" on a repo with no commits (it only errors
    on stderr) — always --verify, or the map pins a sha that is a literal word."""
    return sh(root, "rev-parse", "--verify", "HEAD^{commit}")


def code_paths(c: Ctx) -> list[str]:
    """The map's scan roots come from the same key the review fence and the
    stale-verdict scan use — one declaration of "where product code lives"."""
    raw = c.cfg("git.code_paths", [])
    if isinstance(raw, str):
        raw = [raw]
    paths = [str(p).strip().rstrip("/") for p in (raw or []) if str(p).strip()]
    if not paths:
        sys.exit("code_map: the map needs git.code_paths — vteam.config.yaml has no "
                 "`git.code_paths` (or it is empty), so there is nothing to index.\n"
                 "  Declare where product code lives, e.g.\n"
                 "    git:\n      code_paths: [src/, prisma/]")
    return paths


def scan_roots(c: Ctx) -> tuple[list[str], list[str]]:
    """(roots, notes) — code_paths plus paths.specs when configured."""
    roots, notes = code_paths(c), []
    specs = c.cfg("paths.specs", None)
    if specs:
        roots.append(str(specs).rstrip("/"))
    else:
        notes.append("paths.specs is not configured — docs are NOT in the map "
                     "(headings/ticket keys won't be searchable)")
    seen, out = set(), []
    for r in roots:
        if r in seen:
            continue
        seen.add(r)
        if (c.root / r).exists():
            out.append(r)
        else:
            notes.append(f"scan root {r!r} does not exist on disk — skipped")
    if not out:
        sys.exit(f"code_map: none of the configured scan roots exist: {roots}\n"
                 "  Fix git.code_paths (and paths.specs) in vteam.config.yaml.")
    return sorted(out), notes


def _ident_parts(name: str) -> set[str]:
    """camelCase / snake_case / kebab / dotted → lowercase word parts."""
    s = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", name)
    s = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1 \2", s)
    return {p for p in re.split(r"[^A-Za-z0-9]+", s.lower()) if p}


def _words(text: str) -> set[str]:
    return {w for w in re.split(r"[^A-Za-z0-9]+", text.lower()) if w}


# ── per-language extraction ──────────────────────────────────────────────────

def parse_python(text: str) -> dict:
    """Real parse. A syntax error is RECORDED, never fatal: an un-parsable file
    still exists and its path still matters."""
    try:
        tree = ast.parse(text)
    except SyntaxError as e:
        return {"parse_error": f"{e.msg} (line {e.lineno})"}
    syms, imps = [], set()
    def add(node, name, kind):
        syms.append({"name": name, "kind": kind, "line": node.lineno,
                     "end_line": getattr(node, "end_lineno", None) or node.lineno})
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            add(node, node.name, "func")
        elif isinstance(node, ast.ClassDef):
            add(node, node.name, "class")
            for sub in node.body:
                if isinstance(sub, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    add(sub, f"{node.name}.{sub.name}", "method")
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imps.update(a.name for a in node.names)
        elif isinstance(node, ast.ImportFrom):
            imps.add("." * (node.level or 0) + (node.module or ""))
    return {"symbols": syms, "imports": sorted(t for t in imps if t)}


def parse_jsts(text: str) -> dict:
    """LEXICAL scan — regexes over text, not a parser. See the module scope note."""
    syms, imps = [], set()
    for rx in (JS_FROM, JS_SIDE_EFFECT, JS_REQUIRE, JS_DYNAMIC):
        imps.update(m.group(1).strip() for m in rx.finditer(text))
    for i, line in enumerate(text.split("\n"), 1):
        if len(line) > 400:  # minified/generated: regexes would only invent symbols
            continue
        m = JS_FUNC_CLASS.match(line)
        if m:
            kw = " ".join(m.group(1).split())
            kind = "class" if kw == "class" else ("func*" if "*" in kw else "func")
            syms.append({"name": m.group(2), "kind": kind, "line": i, "end_line": i})
            continue
        m = JS_TOP_BINDING.match(line)
        if m:
            kw = m.group(1)
            kind = "const" if kw in ("const", "let", "var") else kw
            syms.append({"name": m.group(2), "kind": kind, "line": i, "end_line": i})
    return {"symbols": syms, "imports": sorted(t for t in imps if t)}


def _looks_like_path(s: str) -> bool:
    if " " in s or len(s) > 160 or s.startswith(("http", "-", "$")):
        return False
    return ("/" in s and "." in s.rsplit("/", 1)[-1]) or Path(s).suffix in LANG_BY_EXT


def parse_markdown(text: str) -> dict:
    """Headings + ticket/requirement keys + backticked paths (doc→code edges)."""
    heads, fence = [], False
    for i, line in enumerate(text.split("\n"), 1):
        if MD_FENCE.match(line):
            fence = not fence
            continue
        if fence:
            continue
        m = MD_HEADING.match(line)
        if m:
            heads.append({"text": m.group(2).strip(), "level": len(m.group(1)), "line": i})
    keys = sorted({k for k in MD_KEY.findall(text)
                   if k.split("-")[0] not in KEY_DENY})
    refs = sorted({s.strip() for s in MD_CODE_SPAN.findall(text)
                   if _looks_like_path(s.strip())})
    return {"symbols": [], "imports": refs, "headings": heads, "keys": keys}


# ── build ───────────────────────────────────────────────────────────────────

def walk(c: Ctx, roots: list[str]) -> list[Path]:
    out: list[Path] = []
    for r in roots:
        base = c.root / r
        if base.is_file():
            out.append(base)
            continue
        for p in base.rglob("*"):
            if not p.is_file() or p.is_symlink():
                continue
            if any(part in SKIP_DIRS for part in p.relative_to(c.root).parts):
                continue
            if p.suffix.lower() in SKIP_EXTS or p.name.endswith(".min.js"):
                continue
            out.append(p)
    return sorted(set(out))


def resolve_python(target: str, rel: str, by_stem: dict[str, list[str]],
                   all_files: set[str]) -> str | None:
    if target.startswith("."):
        level = len(target) - len(target.lstrip("."))
        mod = target.lstrip(".")
        base = Path(rel).parent
        for _ in range(level - 1):
            base = base.parent
        for cand in ([str(base / (mod.replace(".", "/") + ".py"))] if mod else []) + \
                    [str(base / "__init__.py")]:
            if cand in all_files:
                return cand
        target = mod
    if not target:
        return None
    last = target.split(".")[-1]
    cands = by_stem.get(last, [])
    if len(cands) == 1:
        return cands[0]
    if len(cands) > 1:
        parts = target.split(".")
        narrowed = [p for p in cands if all(x in Path(p).parts or x == Path(p).stem
                                            for x in parts)]
        if len(narrowed) == 1:
            return narrowed[0]
    return None  # ambiguous or external — an unresolved import is still a term


def resolve_jsts(spec: str, rel: str, all_files: set[str]) -> str | None:
    if spec.startswith("."):
        base = (Path(rel).parent / spec)
    elif spec.startswith("@/"):
        base = Path(spec[2:])
    elif spec.startswith("/"):
        base = Path(spec[1:])
    else:
        return None  # bare package specifier — external
    # collapse ./ and ../ TEXTUALLY — never via resolve(): the map must not
    # depend on the cwd the build ran from, nor follow symlinks out of the repo
    norm: list[str] = []
    for part in base.as_posix().split("/"):
        if part == "..":
            if norm:
                norm.pop()
        elif part not in ("", "."):
            norm.append(part)
    cand = "/".join(norm)
    if cand in all_files:
        return cand
    stem = cand
    if Path(cand).suffix in JS_EXTS:  # ./x.js often means x.ts on disk
        stem = cand[: -len(Path(cand).suffix)]
    for ext in JS_EXTS:
        if stem + ext in all_files:
            return stem + ext
    for ext in JS_EXTS:
        if f"{cand}/index{ext}" in all_files:
            return f"{cand}/index{ext}"
    return None


def resolve_doc_ref(ref: str, all_files: set[str]) -> str | None:
    ref = ref.lstrip("./")
    if ref in all_files:
        return ref
    hits = [p for p in all_files if p.endswith("/" + ref)]
    return hits[0] if len(hits) == 1 else None


def build_index(files: dict) -> dict[str, list[str]]:
    idx: dict[str, set[str]] = {}
    def put(term: str, path: str):
        term = term.lower()
        if len(term) >= 2:
            idx.setdefault(term, set()).add(path)
    for path, rec in files.items():
        for part in re.split(r"[^A-Za-z0-9]+", path):
            put(part, path)
        for s in rec.get("symbols", []):
            put(s["name"], path)
            for p in _ident_parts(s["name"]):
                if len(p) >= 3:
                    put(p, path)
        for k in rec.get("keys", []):
            put(k, path)
        for h in rec.get("headings", []):
            for w in _words(h["text"]):
                if len(w) >= 4 and w not in STOP:
                    put(w, path)
        for imp in rec.get("imports", []):
            for p in _ident_parts(imp.split("/")[-1]):
                if len(p) >= 3:
                    put(p, path)
    return {k: sorted(v) for k, v in sorted(idx.items())}


def build(c: Ctx) -> int:
    roots, notes = scan_roots(c)
    files: dict[str, dict] = {}
    errors: list[str] = []
    skipped_big = 0
    for p in walk(c, roots):
        rel = p.relative_to(c.root).as_posix()
        lang = LANG_BY_EXT.get(p.suffix.lower(), p.suffix.lower().lstrip(".") or "none")
        if p.stat().st_size > MAX_BYTES:
            skipped_big += 1
            continue
        rec: dict = {"lang": lang}
        if lang in ("py", "js", "ts", "md"):
            text = p.read_text(encoding="utf-8", errors="replace")
            parsed = (parse_python(text) if lang == "py"
                      else parse_markdown(text) if lang == "md"
                      else parse_jsts(text))
            if "parse_error" in parsed:
                rec["parse_error"] = True
                errors.append(f"{rel}: {parsed['parse_error']}")
            else:
                rec.update(parsed)
        files[rel] = rec

    all_files = set(files)
    by_stem: dict[str, list[str]] = {}
    for rel in sorted(all_files):
        if files[rel]["lang"] == "py":
            by_stem.setdefault(Path(rel).stem, []).append(rel)
    edge_count = 0
    for rel, rec in files.items():
        lang, edges = rec["lang"], set()
        for target in rec.get("imports", []):
            hit = (resolve_python(target, rel, by_stem, all_files) if lang == "py"
                   else resolve_jsts(target, rel, all_files) if lang in ("js", "ts")
                   else resolve_doc_ref(target, all_files) if lang == "md"
                   else None)
            if hit and hit != rel:
                edges.add(hit)
        if edges:
            rec["edges"] = sorted(edges)
            edge_count += len(edges)

    # sorted end to end: a rebuild that found nothing new must diff to nothing
    out = {
        "generated_at_commit": head_sha(c.root) or "unknown",
        "roots": roots,
        "files": {k: files[k] for k in sorted(files)},
        "index": build_index(files),
    }
    dst = c.root / MAP_REL
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_text(json.dumps(out, indent=1, sort_keys=False) + "\n", encoding="utf-8")

    nsym = sum(len(r.get("symbols", [])) for r in files.values())
    print(f"code map: {len(files)} files · {nsym} symbols · {edge_count} import edges "
          f"· {len(out['index'])} index terms")
    print(f"  roots: {' · '.join(roots)}")
    for n in notes:
        print(f"  ⚠ {n}")
    if skipped_big:
        print(f"  ⚠ {skipped_big} file(s) over {MAX_BYTES // 1024}KB skipped (generated?)")
    if errors:
        print(f"  ⚠ {len(errors)} python file(s) failed to parse — recorded with "
              f"parse_error, NOT silently dropped:")
        for e in errors[:10]:
            print(f"      {e}")
    print(f"  wrote {MAP_REL} @ {out['generated_at_commit'][:7]}")
    print("  js/ts symbols are lexical (regex), not semantic — leads, not proof")
    return 0


# ── staleness ───────────────────────────────────────────────────────────────

def staleness(c: Ctx, m: dict) -> tuple[list[str], list[str]]:
    """(hard, soft) — hard = the map is behind committed code (⚠ + --strict red);
    soft = advisory only (uncommitted edits: normal mid-ticket, never a red)."""
    built = m.get("generated_at_commit", "")
    paths = [p for p in m.get("roots", []) or code_paths(c)]
    hard, soft = [], []
    head = head_sha(c.root)
    if not built or built == "unknown":
        # built before the repo had any commit. Only a red once commits exist —
        # a --strict that a rebuild cannot satisfy is a broken gate.
        if head:
            hard.append("the map was built before this repo had any commit — rebuild "
                        "so staleness becomes checkable")
        else:
            soft.append("this repo has no commits yet — the map was built from the "
                        "working tree and staleness cannot be judged")
    elif subprocess.run(["git", "-C", str(c.root), "cat-file", "-e", f"{built}^{{commit}}"],
                        capture_output=True).returncode != 0:
        hard.append(f"the map was built at {built[:7]}, a commit this repo no longer has "
                    f"(rebase/squash?) — its ages cannot be compared")
    elif built != head:
        moved = [ln for ln in sh(c.root, "log", f"{built}..HEAD", "--format=%h %s",
                                 "--", *paths).split("\n") if ln.strip()]
        if moved:
            hard.append(f"built at {built[:7]}, code moved since — "
                        f"{len(moved)} commit(s) touched the scan roots:")
            hard += [f"    {ln}" for ln in moved[:5]]
            if len(moved) > 5:
                hard.append(f"    … and {len(moved) - 5} more")
    dirty = [ln for ln in sh(c.root, "status", "--porcelain", "--", *paths).split("\n")
             if ln.strip()]
    if dirty:
        soft.append(f"{len(dirty)} uncommitted change(s) under the scan roots — "
                    f"the map cannot see edits you have not committed")
    return hard, soft


# ── query ───────────────────────────────────────────────────────────────────

def _lines_of(sym: dict) -> str:
    a, b = sym["line"], sym.get("end_line") or sym["line"]
    return f"{a}-{b}" if b > a else str(a)


def score(path: str, rec: dict, terms: list[str]) -> tuple[int, list[str], list[str]]:
    """(score, why-reasons, line-hints). 0 → not a hit."""
    total, matched, reasons, lines = 0, 0, [], []
    path_parts = {p.lower() for p in re.split(r"[^A-Za-z0-9]+", path) if p}
    for t in terms:
        hits: list[tuple[int, str, str]] = []
        for k in rec.get("keys", []):
            if k.lower() == t:
                hits.append((18, f"key {k}", ""))
        for s in rec.get("symbols", []):
            low = s["name"].lower()
            if low == t:
                hits.append((14, f"{s['kind']} {s['name']}", _lines_of(s)))
            elif t in _ident_parts(low):
                hits.append((9, f"{s['kind']} {s['name']}", _lines_of(s)))
            elif len(t) >= 4 and t in low:
                hits.append((6, f"{s['kind']} {s['name']}", _lines_of(s)))
        for h in rec.get("headings", []):
            if t in _words(h["text"]):
                hits.append((8, f"§ {h['text'][:44]}", str(h["line"])))
            elif len(t) >= 4 and t in h["text"].lower():
                hits.append((5, f"§ {h['text'][:44]}", str(h["line"])))
        if t in path_parts:
            hits.append((7, f"path ·{t}·", ""))
        elif len(t) >= 3 and t in path.lower():
            hits.append((3, f"path ~{t}", ""))
        edge_verb = "cites" if rec.get("lang") == "md" else "imports"
        for imp in rec.get("imports", []):
            if t in _ident_parts(imp.split("/")[-1]):
                hits.append((2, f"{edge_verb} {imp}", ""))
                break
        if not hits:
            continue
        hits.sort(key=lambda h: (-h[0], h[1]))
        total += hits[0][0]
        matched += 1
        if hits[0][1] not in reasons:
            reasons.append(hits[0][1])
        if hits[0][2] and hits[0][2] not in lines:
            lines.append(hits[0][2])
    if not matched:
        return 0, [], []
    return total + 15 * (matched - 1), reasons, lines  # covering MORE terms wins


def candidates(m: dict, terms: list[str]) -> set[str]:
    """The reverse index is the prefilter — exact term, then substring on terms."""
    idx, out = m.get("index", {}), set()
    for t in terms:
        out.update(idx.get(t, []))
        if len(t) >= 4:
            for k, paths in idx.items():
                if t in k:
                    out.update(paths)
    for path in m.get("files", {}):
        low = path.lower()
        if any(len(t) >= 3 and t in low for t in terms):
            out.add(path)
    return out


def query(c: Ctx, terms: list[str], cap: int, strict: bool) -> int:
    dst = c.root / MAP_REL
    if not dst.is_file():
        print(f"⚠  NO CODE MAP at {MAP_REL} — nothing to select from.\n"
              f"   build it first (one command, seconds):  {REBUILD}")
        return 1 if strict else 0
    try:
        m = json.loads(dst.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        sys.exit(f"code_map: {MAP_REL} is not valid JSON ({e}) — rebuild: {REBUILD}")

    hard, soft = staleness(c, m)
    if hard:
        print("=" * 72)
        print("⚠⚠  THE CODE MAP IS STALE — results below may point at moved code")
        for ln in hard:
            print(f"    {ln}")
        print(f"    rebuild:  {REBUILD}")
        print("=" * 72)
    for s in soft:
        print(f"ℹ  {s}")

    files = m.get("files", {})
    ranked = []
    for path in sorted(candidates(m, terms)):
        sc, why, lines = score(path, files.get(path, {}), terms)
        if sc:
            ranked.append((sc, path, why, lines))
    ranked.sort(key=lambda r: (-r[0], r[1]))

    hit_paths = {r[1] for r in ranked}
    importers: dict[str, list[str]] = {}
    for path, rec in files.items():
        for e in rec.get("edges", []):
            importers.setdefault(e, []).append(path)
    neighbors: list[tuple[str, str]] = []          # ONE hop, both directions
    seen = set(hit_paths)
    def verbs(src: str) -> tuple[str, str]:
        """A backticked path in a doc is a CITATION, not an import — say so."""
        return ("cites", "cited") if files.get(src, {}).get("lang") == "md" \
            else ("imports", "imported")
    for _, path, _, _ in ranked:
        base = path.rsplit("/", 1)[-1]
        for e in files.get(path, {}).get("edges", []):
            if e not in seen:
                seen.add(e)
                neighbors.append((e, f"1-hop: {verbs(path)[1]} by {base}"))
        for imp in sorted(importers.get(path, [])):
            if imp not in seen:
                seen.add(imp)
                neighbors.append((imp, f"1-hop: {verbs(imp)[0]} {base}"))

    rows = [(p, " + ".join(w[:2]), ",".join(ln[:2]) or "-") for _, p, w, ln in ranked]
    rows += [(p, w, "-") for p, w in neighbors]
    total = len(rows)
    shown = rows[:max(1, cap)]

    print(f"\ncode map · terms: {' '.join(terms)} · map @ "
          f"{str(m.get('generated_at_commit', '?'))[:7]}")
    if not shown:
        print("  no file matched. Try fewer/other terms (domain nouns, symbol "
              "names, the ticket key), or rebuild if the code is new.")
        print("\nread THESE, not the tree")
        return 1 if (strict and hard) else 0
    wp = min(52, max(len(r[0]) for r in shown))
    ww = min(46, max(len(r[1]) for r in shown))
    print(f"  {'path'.ljust(wp)}  {'why'.ljust(ww)}  lines")
    print(f"  {'-' * wp}  {'-' * ww}  -----")
    for p, w, ln in shown:
        print(f"  {p.ljust(wp)}  {w[:ww].ljust(ww)}  {ln}")
    print(f"\n  {len(shown)} of {total} candidates shown "
          f"({len(ranked)} ranked hits + {len(neighbors)} one-hop neighbors)"
          + (f"  ⚠ TRUNCATED at --max {cap} — rerun with --max {total} for all"
             if total > len(shown) else ""))
    print("read THESE, not the tree")
    return 1 if (strict and hard) else 0


def main() -> int:
    ap = argparse.ArgumentParser(prog="code_map.py", description=(
        "code map (CPG-lite): lexical symbols + import edges, so an agent reads "
        "paths instead of the tree. Not a Code Property Graph."))
    ap.add_argument("cmd", choices=["build", "query"])
    ap.add_argument("terms", nargs="*", help="query terms: ticket key + 2-4 domain words")
    ap.add_argument("--max", type=int, default=12, help="max rows printed (default 12)")
    ap.add_argument("--strict", action="store_true",
                    help="exit 1 when the map is stale/absent (CI + workflow use)")
    args = ap.parse_args()
    c = Ctx()
    if args.cmd == "build":
        return build(c)
    terms = [t.lower() for t in args.terms if t.strip()]
    tiny = [t for t in terms if len(t) < 2]
    if tiny:
        print(f"ℹ  ignoring 1-character term(s) {' '.join(tiny)} — the index keys "
              f"on words of 2+ characters")
        terms = [t for t in terms if len(t) >= 2]
    if not terms:
        sys.exit("code_map: query needs at least one term — e.g. "
                 "`query PROJ-42 wallet topup`. Terms are ANDed softly: a file "
                 "matching more of them ranks higher.")
    return query(c, terms, args.max, args.strict)


# ── selftest ────────────────────────────────────────────────────────────────

def _selftest():
    """Mutation proof in a throwaway repo: the map must contain what the parsers
    claim, the ranking must put the symbol hit above its one-hop neighbor,
    truncation must be LOUD, a stale map must warn (and red under --strict), and
    a python file with a syntax error must be recorded — never crash the build."""
    import os
    import tempfile

    me = Path(__file__).resolve()
    SENTINEL = "SENTINEL_BODY_9f3"  # file CONTENT must never reach query output

    def git(cwd: Path, *args: str) -> str:
        r = subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True)
        assert r.returncode == 0, f"git {args}: {r.stderr}"
        return r.stdout.strip()

    def run(cwd: Path, *args: str) -> subprocess.CompletedProcess:
        return subprocess.run([sys.executable, str(me), *args], cwd=cwd,
                              capture_output=True, text=True,
                              env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"})

    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        git(root, "init", "-q", ".")
        git(root, "config", "user.email", "t@t.t")
        git(root, "config", "user.name", "t")
        (root / "vteam.config.yaml").write_text(
            "version: 1\nproject:\n  key: PROJ\n"
            "paths:\n  specs: docs\n  evidence: evd\n"
            "git:\n  code_paths: [src/]\n"
            "tracker:\n  provider: markdown\n", encoding="utf-8")
        (root / "src").mkdir()
        (root / "src" / "alpha.py").write_text(
            "import os\n"
            "from beta import charge_wallet\n"
            "\n"
            "def render_topup():\n"
            f"    return \"{SENTINEL}\"\n"
            "\n"
            "def other():\n"
            "    return 1\n"
            "\n"
            "class TopupForm:\n"
            "    def submit(self):\n"
            "        return charge_wallet()\n", encoding="utf-8")
        (root / "src" / "beta.py").write_text(
            "def charge_wallet():\n    return 2\n", encoding="utf-8")
        (root / "src" / "widget.mjs").write_text(
            'import { helper } from "./util.mjs";\n'
            "export function renderWidget() { return helper(); }\n"
            "export const WIDGET_LIMIT = 3;\n", encoding="utf-8")
        (root / "src" / "util.mjs").write_text(
            "export function helper() { return 4; }\n", encoding="utf-8")
        (root / "src" / "broken.py").write_text("def oops(:\n  pass\n", encoding="utf-8")
        (root / "docs").mkdir()
        (root / "docs" / "guide.md").write_text(
            "# Wallet topup flow\n\nPROJ-42 covers this. Code lives in "
            "`src/alpha.py`.\n\n## Refund rules\n\nSee FR-WAL-01.\n", encoding="utf-8")
        git(root, "add", "-A")
        git(root, "commit", "-qm", "fixture")

        # ── build ────────────────────────────────────────────────────────────
        r = run(root, "build")
        assert r.returncode == 0, f"build failed:\n{r.stdout}{r.stderr}"
        assert "parse_error" in r.stdout and "broken.py" in r.stdout, \
            f"the syntax-error file must be reported LOUDLY:\n{r.stdout}"
        m = json.loads((root / ".vteam" / "map.json").read_text(encoding="utf-8"))
        f = m["files"]
        assert m["generated_at_commit"] == git(root, "rev-parse", "HEAD")
        assert m["roots"] == ["docs", "src"], m["roots"]

        # python: real parse — defs, class, method, imports
        a = f["src/alpha.py"]
        names = {s["name"]: s for s in a["symbols"]}
        assert a["lang"] == "py"
        assert {"render_topup", "other", "TopupForm", "TopupForm.submit"} <= set(names), names
        assert names["TopupForm"]["kind"] == "class"
        assert names["render_topup"]["line"] == 4 and names["render_topup"]["end_line"] == 5
        assert "beta" in a["imports"] and "os" in a["imports"], a["imports"]
        assert a["edges"] == ["src/beta.py"], a["edges"]

        # js: lexical scan — function + top-level const + resolved relative import
        w = f["src/widget.mjs"]
        assert {"renderWidget", "WIDGET_LIMIT"} <= {s["name"] for s in w["symbols"]}
        assert w["imports"] == ["./util.mjs"] and w["edges"] == ["src/util.mjs"]

        # markdown: headings + keys + backticked path becomes a doc→code edge
        d = f["docs/guide.md"]
        assert [h["text"] for h in d["headings"]] == ["Wallet topup flow", "Refund rules"]
        assert d["keys"] == ["FR-WAL-01", "PROJ-42"], d["keys"]
        assert d["edges"] == ["src/alpha.py"], d["edges"]

        # a python file that does not parse is RECORDED, never dropped
        assert f["src/broken.py"] == {"lang": "py", "parse_error": True}, f["src/broken.py"]

        # reverse index
        idx = m["index"]
        # the index carries DEFINITIONS (python records module targets, not the
        # names pulled from them) — the caller is reached by the one-hop below
        assert idx["charge_wallet"] == ["src/beta.py"], idx["charge_wallet"]
        assert idx["proj-42"] == ["docs/guide.md"]
        assert "src/alpha.py" in idx["topup"] and "docs/guide.md" in idx["topup"]
        assert list(idx) == sorted(idx), "index must be sorted (clean diffs)"
        assert list(f) == sorted(f), "files must be sorted (clean diffs)"
        raw = (root / ".vteam" / "map.json").read_text(encoding="utf-8")
        assert SENTINEL not in raw, "the map must index names, never file bodies"

        # rebuild is byte-identical — a no-op build diffs to nothing
        assert run(root, "build").returncode == 0
        assert (root / ".vteam" / "map.json").read_text(encoding="utf-8") == raw

        # ── query: ranking + one-hop expansion + paths-only ─────────────────
        r = run(root, "query", "renderWidget")
        assert r.returncode == 0, r.stdout + r.stderr
        rows = [ln for ln in r.stdout.split("\n") if ln.startswith("  src/")]
        assert rows and rows[0].strip().startswith("src/widget.mjs"), \
            f"the symbol hit must rank first:\n{r.stdout}"
        assert any("src/util.mjs" in ln and "1-hop" in ln for ln in rows), \
            f"one-hop expansion must pull the imported file:\n{r.stdout}"
        assert "read THESE, not the tree" in r.stdout
        assert SENTINEL not in r.stdout, "query must print PATHS, never content"

        # one hop the other way: the definition's CALLER must come along
        r = run(root, "query", "charge_wallet")
        rows = [ln for ln in r.stdout.split("\n") if ln.startswith("  src/")]
        assert rows[0].strip().startswith("src/beta.py"), f"definition first:\n{r.stdout}"
        assert any("src/alpha.py" in ln and "1-hop" in ln for ln in rows), \
            f"the importer must arrive by one-hop expansion:\n{r.stdout}"

        # multi-term coverage beats a single strong hit
        r = run(root, "query", "PROJ-42", "topup", "wallet")
        first = [ln for ln in r.stdout.split("\n")
                 if ln.startswith("  docs/") or ln.startswith("  src/")][0]
        assert "docs/guide.md" in first, f"the doc covering all 3 terms must lead:\n{r.stdout}"
        assert "src/alpha.py" in r.stdout, "the doc's backticked path must be reachable"

        # truncation is LOUD and the total candidate count is always printed
        r = run(root, "query", "wallet", "topup", "--max", "1")
        assert "TRUNCATED" in r.stdout and " of " in r.stdout, r.stdout
        assert len([ln for ln in r.stdout.split("\n")
                    if ln.startswith(("  src/", "  docs/"))]) == 1, r.stdout

        # ── staleness: commit a change under code_paths ──────────────────────
        r = run(root, "query", "wallet", "--strict")
        assert r.returncode == 0, f"fresh map must not red under --strict:\n{r.stdout}"
        (root / "src" / "beta.py").write_text(
            "def charge_wallet():\n    return 3\n", encoding="utf-8")
        r = run(root, "query", "wallet")
        assert "uncommitted" in r.stdout, f"dirty tree should be noted:\n{r.stdout}"
        assert r.returncode == 0, "uncommitted edits are advisory, never a red"
        git(root, "add", "-A")
        git(root, "commit", "-qm", "move the code")
        r = run(root, "query", "wallet")
        assert "STALE" in r.stdout and "rebuild" in r.stdout, \
            f"a moved code path must warn LOUDLY:\n{r.stdout}"
        assert r.returncode == 0, "stale is advisory without --strict (results still shown)"
        assert any(ln.startswith("  src/") for ln in r.stdout.split("\n")), \
            "stale must still return results"
        r = run(root, "query", "wallet", "--strict")
        assert r.returncode == 1, f"--strict must RED on a stale map:\n{r.stdout}"
        assert run(root, "build").returncode == 0
        assert run(root, "query", "wallet", "--strict").returncode == 0, \
            "rebuild must clear the staleness red"

        # a commit OUTSIDE the scan roots must NOT make the map stale
        (root / "README.md").write_text("docs only\n", encoding="utf-8")
        git(root, "add", "README.md")
        git(root, "commit", "-qm", "readme")
        r = run(root, "query", "wallet", "--strict")
        assert r.returncode == 0 and "STALE" not in r.stdout, \
            f"a commit outside git.code_paths must not flag staleness:\n{r.stdout}"

        # absent map: loud, advisory (0) — but --strict reds
        (root / ".vteam" / "map.json").unlink()
        r = run(root, "query", "wallet")
        assert r.returncode == 0 and "NO CODE MAP" in r.stdout, r.stdout
        assert run(root, "query", "wallet", "--strict").returncode == 1

    # ── a repo with NO commits: `rev-parse HEAD` echoes the word "HEAD", so an
    # unverified pin would record a fake sha. The map must say "unknown", stay
    # advisory while there is nothing to compare, then red once a commit exists.
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        git(root, "init", "-q", ".")
        git(root, "config", "user.email", "t@t.t")
        git(root, "config", "user.name", "t")
        (root / "vteam.config.yaml").write_text(
            "version: 1\nproject:\n  key: PROJ\ngit:\n  code_paths: [src/]\n",
            encoding="utf-8")
        (root / "src").mkdir()
        (root / "src" / "a.py").write_text("def widget_total():\n    return 1\n",
                                           encoding="utf-8")
        r = run(root, "build")
        assert r.returncode == 0, r.stdout + r.stderr
        assert "paths.specs is not configured" in r.stdout, \
            f"an unconfigured docs root must be said out loud:\n{r.stdout}"
        m = json.loads((root / ".vteam" / "map.json").read_text(encoding="utf-8"))
        assert m["generated_at_commit"] == "unknown", m["generated_at_commit"]
        r = run(root, "query", "widget_total", "--strict")
        assert r.returncode == 0 and "no commits yet" in r.stdout, \
            f"nothing to compare is not a red:\n{r.stdout}"
        git(root, "add", "-A")
        git(root, "commit", "-qm", "first")
        r = run(root, "query", "widget_total", "--strict")
        assert r.returncode == 1 and "before this repo had any commit" in r.stdout, \
            f"an uncomparable pin must red once commits exist:\n{r.stdout}"

    # ── mutation: no git.code_paths → the build must die LOUDLY ─────────────
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        git(root, "init", "-q", ".")
        (root / "vteam.config.yaml").write_text(
            "version: 1\nproject:\n  key: PROJ\npaths:\n  specs: docs\n"
            "git:\n  protected_branch: main\n", encoding="utf-8")
        r = run(root, "build")
        assert r.returncode != 0, "a map with no scan roots must not pretend to work"
        assert "needs git.code_paths" in (r.stdout + r.stderr), r.stdout + r.stderr

    print("code_map selftest: OK (python ast + js lexical + md headings/keys/refs "
          "· reverse index sorted · symbol hit ranks above its 1-hop neighbor "
          "· multi-term coverage wins · truncation loud · paths-only (no bodies) "
          "· stale warns / --strict reds / out-of-root commit ignored "
          "· syntax error recorded · unborn HEAD pinned 'unknown' "
          "· missing code_paths red)")


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        _selftest()
        sys.exit(0)
    sys.exit(main())
