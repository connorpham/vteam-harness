#!/usr/bin/env python3
"""evdpack.py — the vocabulary of an evidence pack, and a reader for one.

Two things live here so that nothing has to guess them twice:

1. **The vocabulary.** The verdicts, the case results, the case kinds, the
   severity ladder and the origins. `evd_check.py` enforces them and
   `xlsx_export.py` prints them; when they were separate lists the gate and the
   report disagreed about what a legal value was.

2. **The reader.** One pass over `evd/<TICKET>/` that turns a folder of
   markdown into rows: cases, defects, requirement citations, evidence files.

The reader has one rule, and it is the same rule the whole tool runs on:
**it never invents a value.** A field the pack does not declare comes back as
`""`, is listed in `pack.gaps`, and prints as NOT DECLARED. A spreadsheet cell
that quietly says "Major" because Major is the usual answer would be the single
most damaging thing this file could do.

Python 3.9 compatible.
"""
import os
import re

# ---------------------------------------------------------------------------
# the vocabulary
# ---------------------------------------------------------------------------
VERDICTS = ("PASS", "FAIL", "PARTIAL", "NEW-BUG", "BLOCKED", "UNCLEAR")
CASE_RESULTS = ("PASS", "FAIL", "BLOCKED")
KINDS = ("acceptance", "boundary", "whole-screen", "write-readback", "exploratory", "security")

# Ordered worst-first: the report ranks by this, so the order IS the ladder.
SEVERITIES = ("Blocker", "Critical", "Major", "Minor")
ORIGINS = ("DEV", "SPEC")

# Verdicts that assert something is wrong. One of these with no FAIL case, or a
# PASS with one, means the pack contradicts itself — worth saying out loud.
FAILING_VERDICTS = ("FAIL", "PARTIAL", "NEW-BUG")

# Fields every case manifest must carry. The names are the discipline: a field
# you have to fill in is a question you cannot skip.
REQUIRED_FIELDS = ("RESULT", "AS", "PRECONDITION", "ENTRY", "STEPS", "EXPECTED", "ACTUAL")
UI_ONLY_FIELDS = ("AFTER", "BACK")

# Mirrors evd_check.py — conformance keeps the two tuples identical. A value made
# only of one of these is a judgement, not something the screen showed, and the
# sheet has nothing to print for "what was it supposed to read?"
_VAGUE_PHRASES = (
    "works", "work", "worked", "working", "not working", "not work", "works fine",
    "works correctly", "works properly", "works as expected", "works ok", "work fine",
    "work correctly", "work properly", "work as expected", "did not work", "does not work",
    "doesn't work", "passes", "passed", "pass", "ok", "okay", "fine", "good", "success",
    "successful", "successfully", "as expected", "correct", "correctly", "proper", "properly",
    "no error", "no errors", "no issue", "no issues", "no problem", "no problems",
    "behaves correctly", "behaves properly", "behaves as expected", "failed", "fail", "fails",
    "failure", "error", "broken", "wrong", "incorrect", "n/a", "tbd", "todo",
)
VAGUE_VALUE = re.compile(
    r"^\W*(?:it\s+|this\s+|the\s+(?:feature|page|screen|form|button)\s+)?(?:should\s+|must\s+)?"
    r"(?:be\s+|is\s+|was\s+)?(?:"
    + "|".join(re.escape(x).replace(r"\ ", r"\s+")
               for x in sorted(_VAGUE_PHRASES, key=len, reverse=True))
    + r")\W*$", re.I)
# Required on a case that FAILED: a defect with no severity cannot be
# prioritised, and one with no origin gets routed to the wrong person.
FAIL_FIELDS = ("SEVERITY", "ORIGIN")

SEVERITY_MEANING = {
    "Blocker": ("Testing or use cannot continue · the system is unreachable · data is lost",
                "Everything else stops. Next session."),
    "Critical": ("A core function is broken with no workaround — money and irreversible state first",
                 "Before any new work in the same cycle"),
    "Major": ("Behaviour contradicts the spec, but a workaround exists",
              "Within the cycle"),
    "Minor": ("Small deviation, no business impact — visual drift, wording",
              "May roll to the next cycle; recorded in the backlog"),
}

ORIGIN_MEANING = {
    "DEV": "The code diverges from a correctly written specification — goes to the developer, with the citation",
    "SPEC": "The specification itself is wrong, missing or contradictory — goes to whoever owns the requirement, NOT the developer",
}

KIND_MEANING = {
    "acceptance": "The exact path the ticket asked for, as specified",
    "boundary": "The adjacent input that must behave the OTHER way — the equal case, the empty value, the day before the cutoff",
    "whole-screen": "The neighbourhood still works; a fix that breaks a neighbour is a defect too",
    "write-readback": "The record was read back after the write — the interface saying 'Saved' is a claim about the interface",
    "exploratory": "Shapes and edges nobody planned for, usually added after a challenger pass",
    "security": "The input an attacker sends on purpose — lockout, enumeration, session, authorization, injection (OWASP WSTG)",
}

RESULT_MEANING = {
    "PASS": "Ran, and the product matched the cited expected value",
    "FAIL": "Ran, and the product contradicted the cited expected value",
    "BLOCKED": "Could not run. Nothing was verified, so nothing is claimed — the reason and the unblock path are in the row",
}

NOT_DECLARED = "NOT DECLARED"

# One key regex, two reading policies. `fields()` is the gate's strict,
# line-at-a-time reading; `fields_multiline()` folds wrapped prose in for the
# report. Sharing the pattern is what stops them drifting apart.
_FIELD = re.compile(r"^\s*(?:[-*]\s*)?([A-Z][A-Z_-]{1,20}):\s*(.*)$")
_HEADER = re.compile(r"^\s*([A-Z][A-Z 0-9._-]{1,30}?):\s*(.*)$")
_BULLET = re.compile(r"^\s*[-*]\s+(.*)$")
_BACKTICKED = re.compile(r"`([^`]+)`")
_STEP_SPLIT = re.compile(r"\s+(?=\d{1,2}[.)]\s)")

IMAGE_EXT = (".png", ".jpg", ".jpeg", ".gif", ".webp")


def fields(text):
    """Parse 'KEY: value' lines out of a case manifest, one entry per key.

    Strict and line-at-a-time on purpose — this is what the evidence gate reads,
    and a rule like "ENTRY is only a URL" only works on the line as written.
    """
    out = {}
    for line in text.splitlines():
        m = _FIELD.match(line)
        if m:
            key = m.group(1).upper()
            if key not in out:
                out[key] = m.group(2).strip()
    return out


def fields_multiline(text):
    """The same fields, with wrapped continuation lines folded in.

    A hand-wrapped EXPECTED is normal in an editor and unreadable in a
    spreadsheet cell that stops at the wrap. Continuation is anything that is
    not a new KEY:, a heading, a bullet, a table row or a blank line.
    """
    out = {}
    order = []
    current = None
    for raw in text.splitlines():
        m = _FIELD.match(raw)
        if m:
            key = m.group(1).upper()
            if key in out:
                current = None
                continue
            out[key] = m.group(2).strip()
            order.append(key)
            current = key
            continue
        line = raw.strip()
        if current is None:
            continue
        if not line or line.startswith(("#", "-", "*", "|", ">", "```")):
            current = None
            continue
        out[current] = (out[current] + " " + line).strip()
    return out


def header_fields(text):
    """'KEY: value' out of a root manifest, where keys may contain spaces
    ('STATUS WHEN VERIFIED:') and a value may wrap over several lines."""
    out = {}
    current = None
    for raw in text.splitlines():
        m = _HEADER.match(raw)
        if m and not raw.lstrip().startswith(("|", ">")):
            key = re.sub(r"\s+", " ", m.group(1).strip().upper())
            if key in out:
                current = None
                continue
            out[key] = m.group(2).strip()
            current = key
            continue
        line = raw.strip()
        if current is None:
            continue
        if not line or line.startswith(("#", "-", "*", "|", ">", "```")):
            current = None
            continue
        out[current] = (out[current] + " " + line).strip()
    return out


def read(path):
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as fh:
            return fh.read()
    except Exception:
        return ""


def canon(value, allowed):
    """Match a declared value against the vocabulary, case-insensitively.
    Anything else comes back "" — an unrecognised severity is not a severity."""
    v = str(value or "").strip().strip(".").strip()
    for a in allowed:
        if v.lower() == a.lower():
            return a
    return ""


def split_steps(value):
    """'1. do this  2. do that' -> ['1. do this', '2. do that'].

    Numbered steps on one line are what the case manifests actually contain, and
    a reader cannot follow ten of them run together in a single cell."""
    v = str(value or "").strip()
    if not v:
        return []
    parts = [p.strip() for p in _STEP_SPLIT.split(v) if p.strip()]
    return parts if len(parts) > 1 else [v]


# ---------------------------------------------------------------------------
# requirement citations
# ---------------------------------------------------------------------------
# The severity a report states in prose. Read, never inferred — and reported as
# a statement in the report, never promoted into a defect row: one sentence
# cannot say which of three failed cases it grades.
_SEV_IN_PROSE = re.compile(r"(?i)\bseverity\b\s*[:\-\u2013\u2014]?\s*\*{0,2}\s*"
                           r"(Blocker|Critical|Major|Minor)\b")
_ORIGIN_IN_PROSE = re.compile(r"(?i)\borigin\b\s*[:\-\u2013\u2014]?\s*\*{0,2}\s*(DEV|SPEC)\b")

_CITE_FILE = re.compile(r"\b((?:docs?|spec|specs)[\w./-]*\.(?:md|yaml|yml|json|pdf)"
                        r"(?:\s+(?:§\s*)?\d+(?:\.\d+)*(?:\s*R\d+)?)?)", re.I)
_CITE_SPEC = re.compile(r"\bspec(?:ification)?\s+(\d+(?:\.\d+)*(?:\s*R\d+(?:\s*\+\s*R\d+)*)?)", re.I)
# "3.2 R1" is a rule id and can never be a quantity, so it is taken on sight.
# A bare "3.2" could be either, so it is only read as a citation when the text
# around it is talking about a document.
_CITE_RULE = re.compile(r"(?<![\d,.])(\d{1,2}(?:\.\d{1,2}){0,2}\s*R\d+"
                        r"(?:\s*\+\s*R\d+)*)(?!\d|,\d)")
_CITE_SECTION = re.compile(r"(?<![\d,.])(\d{1,2}\.\d{1,2}(?:\.\d{1,2})?)(?!\d|,\d)")
_CITE_PARA = re.compile(r"§\s*(\d+(?:\.\d+)*)")
_CITE_MODEL = re.compile(r"\b([a-z][a-z0-9_]*:[a-z][a-z0-9_]*)\b")
_CITE_HINT = re.compile(r"spec|section|§|\.md\b|contract|paragraph|clause|rule|\bR\d", re.I)
_CITE_SCHEMA_HINT = re.compile(r"schema|model|field|column|table", re.I)


# "spec 3.2 R1", "section 3.2 R1" and a bare "3.2 R1" are one requirement. They
# have to collapse to one row, or the traceability matrix counts the same rule
# three times and its coverage means nothing.
_CITE_LEAD = re.compile(r"(?i)^(?:specification|specs|spec|sections?|§)\s+(?=[\d§])")


def normalise_citation(value):
    v = re.sub(r"\s+", " ", str(value).strip().strip(",;.()")).strip()
    v = _CITE_LEAD.sub("", v).strip()
    return re.sub(r"\s*\+\s*", "+", v)


def citations(text):
    """Requirement references inside an EXPECTED value, in the order written.

    This is extraction, not interpretation: the sheet says so, because a
    citation the tool guessed at is exactly as useless as no citation at all.
    """
    s = str(text or "")
    if not s.strip():
        return []
    seen = {}

    def add(match, value=None):
        v = normalise_citation(value if value is not None else match.group(1))
        if v and v not in seen:
            seen[v] = match.start()

    for m in _CITE_FILE.finditer(s):
        add(m)
    for m in _CITE_SPEC.finditer(s):
        add(m, "spec " + m.group(1))
    for m in _CITE_PARA.finditer(s):
        add(m, "§ " + m.group(1))
    for m in _CITE_RULE.finditer(s):
        add(m)
    if _CITE_HINT.search(s):
        for m in _CITE_SECTION.finditer(s):
            add(m)
    if _CITE_SCHEMA_HINT.search(s):
        for m in _CITE_MODEL.finditer(s):
            if not m.group(1).startswith(("http", "https")):
                add(m)

    # "in the order written" has to be true of the output, not of the order the
    # patterns happen to run in — a reader compares the cell against the sentence.
    found = sorted(seen, key=lambda v: seen[v])
    # "spec 3.2 R1" already covers a bare "3.2 R1" found later in the same text,
    # and "3.2 R1" already covers a bare "3.2".
    return [c for c in found
            if not any(other != c and (other.endswith(" " + c) or other.startswith(c + " "))
                       for other in found)]


# ---------------------------------------------------------------------------
# the pack
# ---------------------------------------------------------------------------
class Evidence(object):
    __slots__ = ("rel", "abs", "case", "note", "size", "kind")

    def __init__(self, rel, abspath, case, note, size, kind):
        self.rel = rel
        self.abs = abspath
        self.case = case
        self.note = note
        self.size = size
        self.kind = kind


def _classify(name):
    low = name.lower()
    if low.endswith(IMAGE_EXT):
        return "annotated screenshot" if "_boxed." in low else "screenshot"
    if low == "request.http":
        return "request as sent"
    if low == "response.json":
        return "response as received"
    if low.startswith("db_verify"):
        return "read-only database check"
    if low.endswith(".sql"):
        return "the SELECT that was run"
    if low.endswith(".mjs"):
        return "re-runnable journey script"
    if low == "cmd_verify.md":
        return "command and its real output"
    if low == "manifest.md":
        return "case record"
    if low.endswith(".json"):
        return "recorded data"
    if low.endswith(".md"):
        return "written record"
    return "file"


class Case(object):
    def __init__(self, name, path):
        self.name = name          # TC_<n> — what the report and the sheet cite
        self.dirname = name       # the folder on disk: TC_<n>_<what_it_proves>
        self.path = path
        self.f = {}
        self.result = ""
        self.kind = ""
        self.non_ui = False
        self.title = ""
        self.title_source = ""
        self.severity = ""
        self.origin = ""
        self.priority = ""
        self.requirements = []
        self.req_source = ""
        self.steps = []
        self.evidence = []
        self.reason = ""
        self.unblock = ""
        self.finding = ""

    def get(self, key, default=""):
        return self.f.get(key, default) or default

    @property
    def executed(self):
        return self.result in ("PASS", "FAIL")

    @property
    def surface(self):
        return "NON-UI" if self.non_ui else "UI"


class Defect(object):
    def __init__(self, ident, case):
        self.id = ident
        self.case = case
        self.summary = ""
        self.severity = ""
        self.origin = ""
        self.priority = ""
        self.status = "Open"
        self.requirements = []
        self.steps = []
        self.expected = ""
        self.actual = ""
        self.evidence = []
        self.recommendation = ""
        # True when the recommendation came from the report and addresses the
        # ticket, not this defect. The sheet has to say which, or a reader acts
        # on advice that was written about something else.
        self.recommendation_is_ticket_wide = False


class Pack(object):
    def __init__(self, evd):
        self.dir = os.path.abspath(evd)
        self.key = os.path.basename(self.dir.rstrip(os.sep))
        self.title = ""
        self.verdict = ""
        self.commit = ""
        self.verified_at = ""
        self.environment = ""
        self.oracle = ""
        self.surfaces = ""
        self.status = ""
        self.verdict_note = ""
        self.conclusion = ""
        self.recommendation = ""
        self.report_severities = []
        self.report_origins = []
        self.cases = []
        self.defects = []
        self.pack_files = []
        self.gaps = []
        self.project = {}

    # -- derived counts -------------------------------------------------------
    @property
    def counts(self):
        c = {"cases": len(self.cases), "pass": 0, "fail": 0, "blocked": 0, "other": 0}
        for case in self.cases:
            key = case.result.lower() if case.result.lower() in ("pass", "fail", "blocked") else "other"
            c[key] += 1
        c["executed"] = c["pass"] + c["fail"]
        c["rate"] = int(round(100.0 * c["pass"] / c["executed"])) if c["executed"] else 0
        return c

    @property
    def severity_counts(self):
        out = dict((s, 0) for s in SEVERITIES)
        out[NOT_DECLARED] = 0
        for d in self.defects:
            out[d.severity if d.severity in out else NOT_DECLARED] += 1
        return out

    @property
    def worst_severity(self):
        for s in SEVERITIES:
            if self.severity_counts.get(s):
                return s
        return ""

    def gap(self, where, what):
        self.gaps.append((where, what))


def _case_titles_from_manifest(text):
    """The root manifest's case table is where a human already wrote a one-line
    title per case. Reuse it rather than asking for the same sentence twice."""
    out = {}
    for line in text.splitlines():
        m = re.match(r"^\s*\|\s*\**\s*(TC_\d+)\s*\**\s*\|\s*(.+?)\s*\|", line)
        if m:
            out[m.group(1)] = re.sub(r"\*\*", "", m.group(2)).strip()
    return out


def _file_notes(text):
    """Map a filename to the sentence the manifest wrote about it, from the
    '## What the files show' bullets."""
    notes = {}
    for line in text.splitlines():
        m = _BULLET.match(line)
        if not m:
            continue
        body = m.group(1)
        names = _BACKTICKED.findall(body)
        if not names:
            continue
        note = _BACKTICKED.sub("", body)
        note = re.sub(r"^[\s,·—–-]+", "", note).strip().rstrip(".")
        note = re.sub(r"\s+", " ", note)
        if not note:
            continue
        for name in names:
            notes[name.strip().rstrip("/")] = note
    return notes


def _walk_case_files(case_dir, depth=2):
    out = []
    base = case_dir

    def rec(d, level):
        try:
            entries = sorted(os.listdir(d))
        except OSError:
            return
        for name in entries:
            if name in ("__pycache__", ".DS_Store"):
                continue
            p = os.path.join(d, name)
            if os.path.isdir(p):
                if level < depth:
                    rec(p, level + 1)
            elif os.path.isfile(p):
                out.append((os.path.relpath(p, base).replace(os.sep, "/"), p))

    rec(case_dir, 1)
    return out


def _read_case(pack, dirname, titles):
    # The folder says what the case proves; the report cites the number. Keep
    # both: TC_1 is what a reader writes down, TC_1_<what> is what they open.
    m = re.match(r"^TC_(\d+)", dirname)
    name = "TC_{}".format(int(m.group(1))) if m else dirname
    case_dir = os.path.join(pack.dir, dirname)
    case = Case(name, case_dir)
    case.dirname = dirname
    man = os.path.join(case_dir, "manifest.md")
    text = read(man)
    if not text:
        pack.gap(name, "no manifest.md — a folder of files is not a test case, and nothing "
                       "about this case can be reported")
        return case

    case.f = fields_multiline(text)
    case.result = canon(case.get("RESULT"), CASE_RESULTS)
    if case.get("RESULT") and not case.result:
        pack.gap(name, "RESULT is {!r}, which is not one of {}".format(
            case.get("RESULT"), "/".join(CASE_RESULTS)))
    case.kind = canon(case.get("KIND"), KINDS)
    case.non_ui = case.get("TYPE").upper() == "NON-UI"
    case.reason = case.get("REASON") or case.get("BLOCKED_BY")
    case.unblock = case.get("UNBLOCK")
    case.finding = case.get("FINDING")
    case.priority = case.get("PRIORITY")
    case.steps = split_steps(case.get("STEPS"))

    # title: declared, else the sentence the root manifest already wrote, else
    # the opening clause of EXPECTED — and the sheet says which.
    if case.get("TITLE"):
        case.title, case.title_source = case.get("TITLE"), "declared in the case record"
    elif titles.get(name):
        case.title, case.title_source = titles[name], "from the pack manifest's case table"
    elif dirname != name:
        case.title = re.sub(r"[_-]+", " ", dirname[len(name) + 1:]).strip()
        case.title_source = "the case folder name"
    elif case.get("EXPECTED"):
        first = re.split(r"\s+—\s+|\s+·\s+|\.\s", case.get("EXPECTED"))[0].strip()
        case.title = (first[:150] + "…") if len(first) > 150 else first
        case.title_source = "first clause of EXPECTED — no title was declared"
        pack.gap(name, "no TITLE: — the sheet is showing the opening of EXPECTED instead")
    else:
        case.title_source = "none"
        pack.gap(name, "no TITLE: and no EXPECTED: — this case cannot be named")

    if case.get("REQUIREMENT"):
        case.requirements = [p.strip() for p in re.split(r"[;,]\s*|\s+·\s+",
                                                         case.get("REQUIREMENT")) if p.strip()]
        case.req_source = "declared"
    else:
        case.requirements = citations(case.get("EXPECTED"))
        case.req_source = "extracted from EXPECTED" if case.requirements else "none"

    if case.result == "FAIL":
        case.severity = canon(case.get("SEVERITY"), SEVERITIES)
        case.origin = canon(case.get("ORIGIN"), ORIGINS)
        if not case.severity:
            if case.get("SEVERITY"):
                why = "{!r} is not one of {}".format(case.get("SEVERITY"), "/".join(SEVERITIES))
            elif pack.report_severities:
                why = ("the report names {} in prose, but a defect row cannot be graded, "
                       "filtered or counted from a sentence in another file — and a report "
                       "naming one severity cannot say which failed case it grades"
                       .format("/".join(pack.report_severities)))
            else:
                why = ("a defect nobody graded cannot be prioritised, and the reader cannot "
                       "tell a wrong colour from a wrong balance")
            pack.gap(name, "FAILED with no SEVERITY: — {}".format(why))
        if not case.origin:
            pack.gap(name, "FAILED with no ORIGIN: — a spec-origin finding sent to a developer "
                           "produces a fix that is still wrong")

    if case.result != "BLOCKED" and not case.requirements:
        pack.gap(name, "EXPECTED carries no citation — an expected value with no source is the "
                       "verifier's opinion, and this row cannot be traced to a requirement")
    for key in ("EXPECTED", "ACTUAL"):
        value = case.get(key)
        if value and VAGUE_VALUE.match(value):
            pack.gap(name, "{} is {!r} — a judgement, not a value; the sheet cannot say what the "
                           "screen was supposed to read".format(key, value))

    if case.result == "BLOCKED" and not (case.reason and case.unblock):
        pack.gap(name, "BLOCKED with no REASON:/UNBLOCK: — a blocker with no way out is a shrug")

    notes = _file_notes(text)
    for rel, abspath in _walk_case_files(case_dir):
        leaf = rel.split("/")[-1]
        folder = rel.split("/")[0] if "/" in rel else ""
        note = notes.get(rel) or notes.get(leaf) or (notes.get(folder) if folder else "") or ""
        try:
            size = os.path.getsize(abspath)
        except OSError:
            size = 0
        case.evidence.append(Evidence("{}/{}".format(dirname, rel), abspath, name,
                                      note, size, _classify(leaf)))
    return case


def _report_section(text, heading):
    m = re.search(r"(?im)^\s*#{2,3}\s*\d*\.?\s*" + heading + r"\b.*$", text)
    if not m:
        return ""
    rest = text[m.end():]
    nxt = re.search(r"(?m)^\s*#{2,3}\s+", rest)
    body = rest[: nxt.start()] if nxt else rest
    return re.sub(r"\n{3,}", "\n\n", body).strip()


def _bold_paragraph(text, label):
    m = re.search(r"(?im)^\s*\*\*" + label + r"[^*]*\*\*:?\s*(.*)$", text)
    if not m:
        return ""
    lines = [m.group(1).strip()]
    # `$` in MULTILINE stops BEFORE the newline, so the remainder starts with an
    # empty fragment. Dropping it is what lets a wrapped paragraph be read whole.
    rest = text[m.end():].splitlines()
    if rest and not rest[0].strip():
        rest = rest[1:]
    for line in rest:
        if not line.strip() or line.lstrip().startswith(("#", "**", "|")):
            break
        lines.append(line.strip())
    return re.sub(r"\s+", " ", " ".join(lines)).strip()


def _flatten(text, limit=None):
    s = re.sub(r"\s+", " ", re.sub(r"\*\*|`", "", str(text or ""))).strip()
    if limit and len(s) > limit:
        s = s[:limit].rstrip() + "…"
    return s


def read_pack(evd, project=None):
    """Read `evd/<TICKET>/` into a Pack. Never raises on a malformed pack: an
    incomplete pack has to be reportable, or the report can only ever describe
    work that already went well."""
    pack = Pack(evd)
    pack.project = dict(project or {})
    if not os.path.isdir(pack.dir):
        pack.gap(pack.key, "no such evidence folder")
        return pack

    root_man = read(os.path.join(pack.dir, "manifest.md"))
    if not root_man:
        pack.gap("manifest.md", "missing at the evidence root — the plain-language index of "
                                "what was checked")
    head = header_fields(root_man)
    titles = _case_titles_from_manifest(root_man)

    m = re.search(r"(?m)^#\s+(.+)$", root_man)
    if m:
        heading = m.group(1).strip()
        heading = re.sub(r"^{}\s*[—:-]\s*".format(re.escape(pack.key)), "", heading).strip()
        pack.title = heading
    if head.get("TICKET"):
        ticket = head["TICKET"]
        ticket = re.sub(r"^{}\s*[—:-]\s*".format(re.escape(pack.key)), "", ticket).strip()
        if ticket and (not pack.title or len(ticket) > len(pack.title)):
            pack.title = ticket
    if not pack.title:
        tm = re.search(r"(?m)^#\s+(.+)$", read(os.path.join(pack.dir, "ticket.md")))
        if tm:
            pack.title = re.sub(r"^{}\s*[—:-]\s*".format(re.escape(pack.key)), "",
                                tm.group(1).strip()).strip()

    pack.status = head.get("STATUS WHEN VERIFIED", "")
    pack.surfaces = head.get("SURFACES", "")
    pack.verdict_note = _flatten(head.get("VERDICT", ""))

    report = read(os.path.join(pack.dir, "REPORT.md"))
    if not report:
        pack.gap("REPORT.md", "missing — the report is the deliverable; everything else is "
                              "preparation, and this workbook has no verdict to print")
    else:
        first = report.splitlines()[0] if report.splitlines() else ""
        pack.verdict = next((v for v in VERDICTS if v in first.upper()), "")
        if not pack.verdict:
            pack.gap("REPORT.md", "the first line carries no verdict; one of {}".format(
                "/".join(VERDICTS)))
        rf = header_fields(report)
        pack.commit = rf.get("COMMIT", "") or head.get("COMMIT", "")
        pack.verified_at = rf.get("VERIFIED-AT", "") or head.get("VERIFIED-AT", "")
        pack.environment = rf.get("ENVIRONMENT", "") or head.get("ENVIRONMENT", "")
        pack.oracle = rf.get("ORACLE", "") or head.get("ORACLE", "")
        for key, value, why in (("COMMIT", pack.commit, "the verdict binds to the code it ran against"),
                                ("VERIFIED-AT", pack.verified_at, "the fallback anchor when the "
                                 "branch and its commit are squashed away"),
                                ("ENVIRONMENT", pack.environment, "which environment produced this "
                                 "verdict — a bug found on staging is not evidence about production"),
                                ("ORACLE", pack.oracle, "what 'correct' was compared against")):
            if not value:
                pack.gap("REPORT.md", "no {}: line, in the report or the pack manifest — {}"
                         .format(key, why))
        if re.match(r"(?i)^\s*none\b", pack.oracle or ""):
            pack.gap("REPORT.md", "ORACLE is NONE — every verdict in this workbook compares the "
                                  "product against nothing written, and is an opinion, not a fact")
        conclusion = _report_section(report, "Conclusion")
        # The findings and the recommendation have sheets of their own; keeping
        # them here too would put the same sentence in three places.
        cut = re.search(r"(?m)^\s*\*\*(?:Finding|Severity|Origin|Recommendation)", conclusion)
        pack.conclusion = _flatten(conclusion[: cut.start()] if cut else conclusion, 4000)
        pack.recommendation = _bold_paragraph(report, "Recommendation")
        for m in _SEV_IN_PROSE.finditer(report):
            v = canon(m.group(1), SEVERITIES)
            if v and v not in pack.report_severities:
                pack.report_severities.append(v)
        for m in _ORIGIN_IN_PROSE.finditer(report):
            v = canon(m.group(1), ORIGINS)
            if v and v not in pack.report_origins:
                pack.report_origins.append(v)

    if not pack.verdict and pack.verdict_note:
        pack.verdict = next((v for v in VERDICTS if pack.verdict_note.upper().startswith(v)), "")

    names = sorted((d for d in os.listdir(pack.dir)
                    if re.match(r"^TC_\d+(?:_.+)?$", d) and os.path.isdir(os.path.join(pack.dir, d))),
                   key=lambda n: int(n.split("_")[1]))
    if not names:
        pack.gap(pack.key, "no TC_<n>_<what_it_proves> folders — nothing was verified")
    for name in names:
        pack.cases.append(_read_case(pack, name, titles))

    # -- defects: one per failed case, in severity order ----------------------
    failed = [c for c in pack.cases if c.result == "FAIL"]
    failed.sort(key=lambda c: (SEVERITIES.index(c.severity) if c.severity in SEVERITIES
                               else len(SEVERITIES), c.name))
    for i, case in enumerate(failed, start=1):
        d = Defect("{}-D{}".format(pack.key, i), case.name)
        d.summary = case.finding or case.title
        d.severity = case.severity
        d.origin = case.origin
        d.priority = case.priority
        d.status = canon(case.get("DEFECT_STATUS"), ("Open", "Fixed", "Rejected", "Deferred")) or "Open"
        d.requirements = case.requirements
        d.steps = case.steps
        d.expected = case.get("EXPECTED")
        d.actual = case.get("ACTUAL")
        d.evidence = case.evidence
        if case.get("RECOMMENDATION"):
            d.recommendation = case.get("RECOMMENDATION")
        else:
            d.recommendation = pack.recommendation
            d.recommendation_is_ticket_wide = len(failed) > 1
        pack.defects.append(d)

    # -- does the pack agree with itself? -------------------------------------
    if pack.verdict in FAILING_VERDICTS and not pack.defects:
        pack.gap("REPORT.md", "the verdict is {} but no case is marked RESULT: FAIL — the "
                              "workbook can show no defect for a verdict that asserts one"
                 .format(pack.verdict))
    if pack.verdict == "PASS" and pack.defects:
        pack.gap("REPORT.md", "the verdict is PASS but {} case(s) FAILED — one of the two is "
                              "wrong".format(len(pack.defects)))

    # -- pack-level files ----------------------------------------------------
    for name, note in (("REPORT.md", "the report a non-programmer reads in two minutes"),
                       ("verifysheet.md", "every expected value, with the sentence of the spec it came from"),
                       ("manifest.md", "the plain-language index of what was checked"),
                       ("debate.md", "the challenger's attempt to break this verdict, and how it ended"),
                       ("ticket.md", "the ticket as fetched — data, not the oracle")):
        p = os.path.join(pack.dir, name)
        if os.path.isfile(p):
            pack.pack_files.append(Evidence(name, p, "", note, os.path.getsize(p), "written record"))
        elif name in ("verifysheet.md", "debate.md"):
            pack.gap(name, "missing — {}".format(note))

    prep = os.path.join(pack.dir, "data_prep")
    if os.path.isdir(prep):
        for rel, abspath in _walk_case_files(prep):
            pack.pack_files.append(Evidence("data_prep/" + rel, abspath, "", "test data created "
                                           "through the product's own flow", os.path.getsize(abspath),
                                           _classify(rel.split("/")[-1])))
    return pack
