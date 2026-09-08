#!/usr/bin/env python3
"""xlsx.py — write a real .xlsx with nothing but the standard library.

ai-qa ships no dependencies on purpose. A QA tool that needs a `pip install`
before it can hand a manager a spreadsheet is a tool that gets skipped, so this
is a small, honest SpreadsheetML writer: enough for a report someone reads,
filters and prints, and deliberately nothing more.

Supported: several sheets, inline strings, numbers, a fixed palette of named
styles, column widths, merged cells, frozen panes, autofilter, external
hyperlinks, landscape print setup.
Not supported: formulas, charts, images, conditional formatting, shared strings.

Output is BYTE-DETERMINISTIC for identical input — every zip entry carries the
same fixed timestamp — so one evidence pack always produces one file, and a
workbook whose bytes changed is telling you the evidence changed.

Python 3.9 compatible.
"""
import re
import zipfile

# Excel refuses a cell longer than this, and truncates silently in some
# readers. We truncate loudly instead: a reader must be able to tell.
CELL_LIMIT = 32767
TRUNCATED = " …[truncated — the full text is in the evidence file]"

# A fixed DOS timestamp, so the same input produces the same bytes.
_ZIP_DATE = (1980, 1, 1, 0, 0, 0)

# A drawing anchor is measured in EMU (English Metric Units); at the 96 DPI Excel
# assumes, one screen pixel is 9525 of them. This is the only unit conversion an
# embedded image needs, and getting it wrong stretches every picture.
EMU_PER_PX = 9525


def png_size(data):
    """(width, height) in pixels from a PNG's IHDR, with no image library — just
    the bytes every PNG starts with. Returns None for anything that is not a PNG,
    so the caller can fall back to a default box rather than crash on a JPEG."""
    if len(data) >= 24 and data[:8] == b"\x89PNG\r\n\x1a\n" and data[12:16] == b"IHDR":
        return (int.from_bytes(data[16:20], "big"), int.from_bytes(data[20:24], "big"))
    return None

_ILLEGAL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f￾￿]")
_SHEETNAME_BAD = re.compile(r"[\[\]:*?/\\]")


# ---------------------------------------------------------------------------
# the style palette
#
# A fixed table, not a style engine. Naming the styles is what keeps every
# sheet in the workbook looking like the same document — and it means a caller
# says `style="fail"`, never a colour.
# ---------------------------------------------------------------------------
INK = "FF1F2937"      # body text
INK_DARK = "FF0F172A"  # headings
MUTED = "FF6B7280"
LINE = "FFD1D5DB"

_FONTS = [
    dict(sz=11, color=INK),                                  # 0 body
    dict(sz=11, color=INK, b=True),                          # 1 body bold
    dict(sz=18, color=INK_DARK, b=True),                     # 2 title
    dict(sz=9, color=MUTED),                                 # 3 muted
    dict(sz=11, color="FFFFFFFF", b=True),                   # 4 on dark
    dict(sz=11, color="FF991B1B", b=True),                   # 5 fail
    dict(sz=11, color="FF166534", b=True),                   # 6 pass
    dict(sz=11, color="FF374151"),                           # 7 blocked
    dict(sz=11, color="FF422006", b=True),                   # 8 major
    dict(sz=11, color="FF78350F", b=True),                   # 9 minor
    dict(sz=10, color=INK, name="Consolas"),                 # 10 mono
    dict(sz=11, color="FF1D4ED8", u=True),                   # 11 link
    dict(sz=13, color=INK_DARK, b=True),                     # 12 section
    dict(sz=10, color=MUTED, i=True),                        # 13 note
    dict(sz=20, color=INK_DARK, b=True),                     # 14 kpi
    dict(sz=11, color=MUTED),                                # 15 dash
    dict(sz=20, color="FF166534", b=True),                   # 16 kpi pass
    dict(sz=20, color="FF991B1B", b=True),                   # 17 kpi fail
    dict(sz=20, color="FF374151", b=True),                   # 18 kpi blocked
    dict(sz=11, color=INK, name="Consolas"),                 # 19 bar
]

_FILLS = [
    None, "gray125",                                         # 0,1 mandatory
    "FF1F2937",                                              # 2 header band
    "FFDCFCE7",                                              # 3 pass
    "FFFEE2E2",                                              # 4 fail
    "FFE5E7EB",                                              # 5 blocked
    "FF7F1D1D",                                              # 6 blocker
    "FFDC2626",                                              # 7 critical
    "FFFBBF24",                                              # 8 major
    "FFFEF3C7",                                              # 9 minor
    "FFF3F4F6",                                              # 10 label
    "FFEFF6FF",                                              # 11 info
]

_BORDERS = ["none", "thin", "top"]

# name -> (font, fill, border, align)   align = (horizontal, vertical, wrap)
_XFS = [
    ("default",      0, 0, 0, (None, None, False)),
    ("title",        2, 0, 0, (None, "center", False)),
    ("subtitle",     0, 0, 0, (None, "center", False)),
    ("note",        13, 0, 0, ("left", "top", True)),
    ("section",     12, 0, 2, ("left", "bottom", False)),
    ("header",       4, 2, 1, ("center", "center", True)),
    ("header_left",  4, 2, 1, ("left", "center", True)),
    ("cell",         0, 0, 1, ("left", "top", True)),
    ("cell_center",  0, 0, 1, ("center", "top", True)),
    ("bold",         1, 0, 1, ("left", "top", True)),
    ("label",        1, 10, 1, ("left", "top", True)),
    ("info",         0, 11, 1, ("left", "top", True)),
    ("muted",       15, 0, 1, ("left", "top", True)),
    ("dash",        15, 0, 1, ("center", "center", False)),
    ("mono",        10, 0, 1, ("left", "top", True)),
    ("link",        11, 0, 1, ("left", "top", True)),
    ("num",          1, 0, 1, ("center", "center", False)),
    ("kpi",         14, 0, 1, ("center", "center", False)),
    ("pass",         6, 3, 1, ("center", "center", True)),
    ("fail",         5, 4, 1, ("center", "center", True)),
    ("blocked",      7, 5, 1, ("center", "center", True)),
    ("blocker",      4, 6, 1, ("center", "center", True)),
    ("critical",     4, 7, 1, ("center", "center", True)),
    ("major",        8, 8, 1, ("center", "center", True)),
    ("minor",        9, 9, 1, ("center", "center", True)),
    ("kpi_pass",    16, 3, 1, ("center", "center", False)),
    ("kpi_fail",    17, 4, 1, ("center", "center", False)),
    ("kpi_blocked", 18, 5, 1, ("center", "center", False)),
    ("bar",         19, 11, 1, ("left", "center", False)),
    ("plain",        0, 0, 0, ("left", "top", True)),
    ("plain_bold",   1, 0, 0, ("left", "top", False)),
]

STYLES = {name: i for i, (name, _f, _fl, _b, _a) in enumerate(_XFS)}


def style_id(name):
    """Style index for `name`; unknown names fall back to the body style rather
    than raising — a report that renders plainly beats a report that fails."""
    return STYLES.get(name, 0)


# ---------------------------------------------------------------------------
# escaping and references
# ---------------------------------------------------------------------------
def esc(text):
    """XML-escape, and drop the control characters XML 1.0 cannot carry.

    Evidence text comes out of terminals and HTTP responses, so it really does
    contain escape sequences. One of them in a cell makes the whole workbook
    unopenable, which reads to the user as "ai-qa produced a corrupt file".
    """
    s = _ILLEGAL.sub("", str(text))
    return (s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
             .replace('"', "&quot;"))


def clamp(text):
    s = str(text)
    if len(s) <= CELL_LIMIT:
        return s
    return s[: CELL_LIMIT - len(TRUNCATED)] + TRUNCATED


def col_letter(n):
    """1 -> A, 27 -> AA."""
    out = ""
    while n > 0:
        n, rem = divmod(n - 1, 26)
        out = chr(65 + rem) + out
    return out


def ref(row, col):
    return "{}{}".format(col_letter(col), row)


def safe_sheet_name(name, taken):
    """Excel: 31 characters, none of []:*?/\\, and unique in the workbook."""
    base = _SHEETNAME_BAD.sub(" ", str(name)).strip() or "Sheet"
    base = base[:31]
    out = base
    n = 2
    while out.lower() in taken:
        suffix = " {}".format(n)
        out = base[: 31 - len(suffix)] + suffix
        n += 1
    taken.add(out.lower())
    return out


def est_height(text, width_chars, min_pt=15.0, line_pt=13.5, pad=4.0):
    """Row height for a MERGED cell.

    Excel auto-fits a wrapped cell only while it is not merged, so a merged
    block with no explicit height clips its own text — and clipped text in a
    report is worse than no report, because the reader cannot tell.
    """
    s = str(text)
    if not s:
        return min_pt
    lines = 0
    for para in s.split("\n"):
        lines += max(1, -(-len(para) // max(8, int(width_chars))))
    return max(min_pt, lines * line_pt + pad)


class Cell:
    __slots__ = ("value", "style", "kind", "link", "tooltip")

    def __init__(self, value="", style="cell", kind="s", link=None, tooltip=None):
        self.value = value
        self.style = style
        self.kind = kind          # "s" inline string · "n" number · "b" blank
        self.link = link          # external target, relative to the workbook
        self.tooltip = tooltip


def S(value, style="cell", link=None, tooltip=None):
    return Cell(value, style, "s", link, tooltip)


def N(value, style="num"):
    return Cell(value, style, "n")


def B(style="default"):
    return Cell("", style, "b")


class Sheet:
    def __init__(self, name, widths=None, freeze=None, gridlines=False,
                 landscape=True, fit_width=True):
        self.name = name
        self.widths = list(widths or [])
        self.freeze = freeze              # (rows, cols) frozen from the top-left
        self.gridlines = gridlines
        self.landscape = landscape
        self.fit_width = fit_width
        self.rows = []                    # list of (cells, height or None)
        self.merges = []                  # "A1:F1"
        self.autofilter = None            # "A4:R20"
        self._links = []                  # (cellref, target, display, tooltip)
        self.pics = []                    # {data, row, col, w, h, name, descr}
        self._index = None                # 1-based position, set by Workbook.sheet()

    # -- writing --------------------------------------------------------------
    def row(self, cells=None, height=None):
        """Append a row. Returns its 1-based index, so callers can merge or
        filter against a row they just wrote instead of counting."""
        self.rows.append((list(cells or []), height))
        r = len(self.rows)
        for i, cell in enumerate(self.rows[-1][0], start=1):
            if isinstance(cell, Cell) and cell.link:
                self._links.append((ref(r, i), cell.link, str(cell.value), cell.tooltip))
        return r

    def blank(self, height=6.0):
        return self.row([], height)

    def image(self, data, row, col, w_px, h_px, name="", descr=""):
        """Anchor a picture's top-left to a cell (1-based row/col) at a fixed
        pixel size, so it does not stretch when a column is widened. `data` is
        the raw image bytes; they are written verbatim into the workbook."""
        self.pics.append({"data": data, "row": row, "col": col,
                          "w": int(w_px), "h": int(h_px),
                          "name": name or "image", "descr": descr})

    def merge(self, r1, c1, r2, c2):
        self.merges.append("{}:{}".format(ref(r1, c1), ref(r2, c2)))

    def span(self, cells, height=None, merge_from=1, merge_to=None):
        """A row whose first cell spans to `merge_to` — the banner/paragraph
        shape used all over the summary sheet."""
        r = self.row(cells, height)
        if merge_to and merge_to > merge_from:
            self.merge(r, merge_from, r, merge_to)
        return r

    @property
    def width(self):
        return max([len(c) for c, _h in self.rows] + [len(self.widths), 1])

    # -- rendering ------------------------------------------------------------
    def xml(self):
        n_rows = max(1, len(self.rows))
        n_cols = max(1, self.width)
        out = ['<?xml version="1.0" encoding="UTF-8" standalone="yes"?>',
               '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"'
               ' xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">']
        # fitToPage is only kind to a sheet that is nearly a page wide. On an
        # 18-column test-case sheet it shrinks the text to a quarter size and
        # calls that printed, so a wide sheet paginates at full size instead.
        if self.fit_width:
            out.append('<sheetPr><pageSetUpPr fitToPage="1"/></sheetPr>')
        out.append('<dimension ref="A1:{}"/>'.format(ref(n_rows, n_cols)))

        view = '<sheetView workbookViewId="0"{}>'.format(
            "" if self.gridlines else ' showGridLines="0"')
        pane = ""
        if self.freeze:
            fr, fc = self.freeze
            attrs = []
            if fc:
                attrs.append('xSplit="{}"'.format(fc))
            if fr:
                attrs.append('ySplit="{}"'.format(fr))
            attrs.append('topLeftCell="{}"'.format(ref(fr + 1, fc + 1)))
            attrs.append('activePane="{}"'.format(
                "bottomRight" if (fr and fc) else ("bottomLeft" if fr else "topRight")))
            attrs.append('state="frozen"')
            pane = "<pane {}/>".format(" ".join(attrs))
        out.append("<sheetViews>{}{}</sheetView></sheetViews>".format(view, pane))
        out.append('<sheetFormatPr defaultRowHeight="15"/>')

        if self.widths:
            cols = ["<cols>"]
            for i, w in enumerate(self.widths, start=1):
                cols.append('<col min="{0}" max="{0}" width="{1}" customWidth="1"/>'.format(i, w))
            cols.append("</cols>")
            out.append("".join(cols))

        out.append("<sheetData>")
        for r, (cells, height) in enumerate(self.rows, start=1):
            attrs = ' r="{}"'.format(r)
            if height:
                attrs += ' ht="{:.1f}" customHeight="1"'.format(height)
            if not cells:
                out.append("<row{}/>".format(attrs))
                continue
            out.append("<row{}>".format(attrs))
            for i, cell in enumerate(cells, start=1):
                if cell is None:
                    continue
                s = style_id(cell.style)
                loc = ref(r, i)
                if cell.kind == "b" or cell.value == "":
                    out.append('<c r="{}" s="{}"/>'.format(loc, s))
                elif cell.kind == "n":
                    out.append('<c r="{}" s="{}"><v>{}</v></c>'.format(loc, s, cell.value))
                else:
                    out.append('<c r="{}" s="{}" t="inlineStr"><is><t xml:space="preserve">'
                               "{}</t></is></c>".format(loc, s, esc(clamp(cell.value))))
            out.append("</row>")
        out.append("</sheetData>")

        # Schema order is strict here: autoFilter, then mergeCells, then
        # hyperlinks, then the print parts. Out of order, Excel repairs the
        # file — which loses the sheet, silently.
        if self.autofilter:
            out.append('<autoFilter ref="{}"/>'.format(self.autofilter))
        if self.merges:
            out.append('<mergeCells count="{}">'.format(len(self.merges)))
            for m in self.merges:
                out.append('<mergeCell ref="{}"/>'.format(m))
            out.append("</mergeCells>")
        if self._links:
            out.append("<hyperlinks>")
            for i, (loc, _t, display, tooltip) in enumerate(self._links, start=1):
                tip = ' tooltip="{}"'.format(esc(tooltip)) if tooltip else ""
                out.append('<hyperlink ref="{}" r:id="rId{}" display="{}"{}/>'.format(
                    loc, i, esc(clamp(display)), tip))
            out.append("</hyperlinks>")
        out.append('<pageMargins left="0.4" right="0.4" top="0.5" bottom="0.5"'
                   ' header="0.3" footer="0.3"/>')
        fit = ' fitToWidth="1" fitToHeight="0"' if self.fit_width else ""
        out.append('<pageSetup orientation="{}"{} paperSize="9"/>'.format(
            "landscape" if self.landscape else "portrait", fit))
        # The drawing reference comes AFTER pageSetup in the schema; out of order,
        # Excel silently drops the sheet. Its rId follows the hyperlink rIds.
        if self.pics:
            out.append('<drawing r:id="rId{}"/>'.format(len(self._links) + 1))
        out.append("</worksheet>")
        return "".join(out)

    def rels_xml(self):
        if not self._links and not self.pics:
            return None
        out = ['<?xml version="1.0" encoding="UTF-8" standalone="yes"?>',
               '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">']
        for i, (_loc, target, _d, _tip) in enumerate(self._links, start=1):
            out.append('<Relationship Id="rId{}" Type="http://schemas.openxmlformats.org/'
                       'officeDocument/2006/relationships/hyperlink" Target="{}"'
                       ' TargetMode="External"/>'.format(i, esc(target)))
        if self.pics:
            out.append('<Relationship Id="rId{}" Type="http://schemas.openxmlformats.org/'
                       'officeDocument/2006/relationships/drawing"'
                       ' Target="../drawings/drawing{}.xml"/>'.format(
                           len(self._links) + 1, self._index))
        out.append("</Relationships>")
        return "".join(out)

    def drawing_xml(self):
        """One floating picture per image, sized in EMU so it keeps its shape
        whatever the columns do. Media ids are local to this drawing's rels
        (rId1, rId2, …), assigned in the same order as self.pics."""
        if not self.pics:
            return None
        out = ['<?xml version="1.0" encoding="UTF-8" standalone="yes"?>',
               '<xdr:wsDr xmlns:xdr="http://schemas.openxmlformats.org/drawingml/2006/'
               'spreadsheetDrawing" xmlns:a="http://schemas.openxmlformats.org/'
               'drawingml/2006/main">']
        for i, p in enumerate(self.pics, start=1):
            cx, cy = p["w"] * EMU_PER_PX, p["h"] * EMU_PER_PX
            out.append(
                '<xdr:oneCellAnchor>'
                '<xdr:from><xdr:col>{col}</xdr:col><xdr:colOff>0</xdr:colOff>'
                '<xdr:row>{row}</xdr:row><xdr:rowOff>0</xdr:rowOff></xdr:from>'
                '<xdr:ext cx="{cx}" cy="{cy}"/>'
                '<xdr:pic>'
                '<xdr:nvPicPr>'
                '<xdr:cNvPr id="{id}" name="{name}" descr="{descr}"/>'
                '<xdr:cNvPicPr><a:picLocks noChangeAspect="1"/></xdr:cNvPicPr>'
                '</xdr:nvPicPr>'
                '<xdr:blipFill>'
                '<a:blip xmlns:r="http://schemas.openxmlformats.org/officeDocument/'
                '2006/relationships" r:embed="rId{id}"/>'
                '<a:stretch><a:fillRect/></a:stretch>'
                '</xdr:blipFill>'
                '<xdr:spPr>'
                '<a:xfrm><a:off x="0" y="0"/><a:ext cx="{cx}" cy="{cy}"/></a:xfrm>'
                '<a:prstGeom prst="rect"><a:avLst/></a:prstGeom>'
                '</xdr:spPr>'
                '</xdr:pic>'
                '<xdr:clientData/>'
                '</xdr:oneCellAnchor>'.format(
                    col=max(0, p["col"] - 1), row=max(0, p["row"] - 1),
                    cx=cx, cy=cy, id=i, name=esc(p["name"]), descr=esc(p["descr"])))
        out.append("</xdr:wsDr>")
        return "".join(out)


class Workbook:
    def __init__(self, title="", creator="ai-qa"):
        self.sheets = []
        self._names = set()
        self.title = title
        self.creator = creator

    def sheet(self, name, **kw):
        sh = Sheet(safe_sheet_name(name, self._names), **kw)
        self.sheets.append(sh)
        sh._index = len(self.sheets)   # 1-based, so its drawing part can be named
        return sh

    # -- parts ----------------------------------------------------------------
    def _content_types(self):
        out = ['<?xml version="1.0" encoding="UTF-8" standalone="yes"?>',
               '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">',
               '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package'
               '.relationships+xml"/>',
               '<Default Extension="xml" ContentType="application/xml"/>']
        if any(sh.pics for sh in self.sheets):
            out.append('<Default Extension="png" ContentType="image/png"/>')
        out += [
               '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats'
               '-officedocument.spreadsheetml.sheet.main+xml"/>',
               '<Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats'
               '-officedocument.spreadsheetml.styles+xml"/>',
               '<Override PartName="/docProps/core.xml" ContentType="application/vnd'
               '.openxmlformats-package.core-properties+xml"/>']
        for i in range(1, len(self.sheets) + 1):
            out.append('<Override PartName="/xl/worksheets/sheet{}.xml" ContentType="application/'
                       'vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'.format(i))
        out.append("</Types>")
        return "".join(out)

    def _root_rels(self):
        return ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/'
                '2006/relationships/officeDocument" Target="xl/workbook.xml"/>'
                '<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/package/2006/'
                'relationships/metadata/core-properties" Target="docProps/core.xml"/>'
                "</Relationships>")

    def _core(self):
        return ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                '<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/'
                'metadata/core-properties" xmlns:dc="http://purl.org/dc/elements/1.1/">'
                "<dc:title>{}</dc:title><dc:creator>{}</dc:creator>"
                "<cp:lastModifiedBy>{}</cp:lastModifiedBy>"
                "</cp:coreProperties>".format(esc(self.title), esc(self.creator),
                                              esc(self.creator)))

    def _workbook(self):
        out = ['<?xml version="1.0" encoding="UTF-8" standalone="yes"?>',
               '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"'
               ' xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">',
               "<sheets>"]
        for i, sh in enumerate(self.sheets, start=1):
            out.append('<sheet name="{}" sheetId="{}" r:id="rId{}"/>'.format(esc(sh.name), i, i))
        out.append("</sheets></workbook>")
        return "".join(out)

    def _workbook_rels(self):
        out = ['<?xml version="1.0" encoding="UTF-8" standalone="yes"?>',
               '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">']
        for i in range(1, len(self.sheets) + 1):
            out.append('<Relationship Id="rId{0}" Type="http://schemas.openxmlformats.org/'
                       'officeDocument/2006/relationships/worksheet"'
                       ' Target="worksheets/sheet{0}.xml"/>'.format(i))
        out.append('<Relationship Id="rId{}" Type="http://schemas.openxmlformats.org/'
                   'officeDocument/2006/relationships/styles" Target="styles.xml"/>'
                   .format(len(self.sheets) + 1))
        out.append("</Relationships>")
        return "".join(out)

    def _styles(self):
        out = ['<?xml version="1.0" encoding="UTF-8" standalone="yes"?>',
               '<styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">']

        out.append('<fonts count="{}">'.format(len(_FONTS)))
        for f in _FONTS:
            bits = ['<sz val="{}"/>'.format(f.get("sz", 11)),
                    '<color rgb="{}"/>'.format(f.get("color", INK)),
                    '<name val="{}"/>'.format(f.get("name", "Calibri"))]
            if f.get("b"):
                bits.insert(0, "<b/>")
            if f.get("i"):
                bits.insert(0, "<i/>")
            if f.get("u"):
                bits.insert(0, "<u/>")
            out.append("<font>{}</font>".format("".join(bits)))
        out.append("</fonts>")

        out.append('<fills count="{}">'.format(len(_FILLS)))
        for fill in _FILLS:
            if fill is None:
                out.append('<fill><patternFill patternType="none"/></fill>')
            elif fill == "gray125":
                out.append('<fill><patternFill patternType="gray125"/></fill>')
            else:
                out.append('<fill><patternFill patternType="solid"><fgColor rgb="{}"/>'
                           '<bgColor indexed="64"/></patternFill></fill>'.format(fill))
        out.append("</fills>")

        out.append('<borders count="{}">'.format(len(_BORDERS)))
        for b in _BORDERS:
            if b == "thin":
                edge = '<{0} style="thin"><color rgb="{1}"/></{0}>'
                out.append("<border>{}{}{}{}<diagonal/></border>".format(
                    edge.format("left", LINE), edge.format("right", LINE),
                    edge.format("top", LINE), edge.format("bottom", LINE)))
            elif b == "top":
                out.append('<border><left/><right/><top/><bottom style="medium">'
                           '<color rgb="{}"/></bottom><diagonal/></border>'.format(INK_DARK))
            else:
                out.append("<border><left/><right/><top/><bottom/><diagonal/></border>")
        out.append("</borders>")

        out.append('<cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0"'
                   ' borderId="0"/></cellStyleXfs>')

        out.append('<cellXfs count="{}">'.format(len(_XFS)))
        for _name, font, fill, border, align in _XFS:
            h, v, wrap = align
            bits = []
            if h:
                bits.append('horizontal="{}"'.format(h))
            if v:
                bits.append('vertical="{}"'.format(v))
            if wrap:
                bits.append('wrapText="1"')
            inner = "<alignment {}/>".format(" ".join(bits)) if bits else ""
            out.append('<xf numFmtId="0" fontId="{}" fillId="{}" borderId="{}" xfId="0"'
                       ' applyFont="1" applyFill="1" applyBorder="1"{}>{}</xf>'.format(
                           font, fill, border,
                           ' applyAlignment="1"' if inner else "", inner))
        out.append("</cellXfs>")
        out.append('<cellStyles count="1"><cellStyle name="Normal" xfId="0" builtinId="0"/>'
                   "</cellStyles>")
        out.append('<dxfs count="0"/><tableStyles count="0"/>')
        out.append("</styleSheet>")
        return "".join(out)

    # -- output ---------------------------------------------------------------
    def parts(self):
        """Every zip entry, in write order. Text parts are str; embedded image
        media are bytes. Exposed so a test can assert on the parts without
        unzipping a temporary file."""
        items = [("[Content_Types].xml", self._content_types()),
                 ("_rels/.rels", self._root_rels()),
                 ("docProps/core.xml", self._core()),
                 ("xl/workbook.xml", self._workbook()),
                 ("xl/_rels/workbook.xml.rels", self._workbook_rels()),
                 ("xl/styles.xml", self._styles())]
        media = []            # (arcname, bytes), appended after the sheets
        media_seq = 0
        for i, sh in enumerate(self.sheets, start=1):
            items.append(("xl/worksheets/sheet{}.xml".format(i), sh.xml()))
            rels = sh.rels_xml()
            if rels:
                items.append(("xl/worksheets/_rels/sheet{}.xml.rels".format(i), rels))
            if sh.pics:
                drels = ['<?xml version="1.0" encoding="UTF-8" standalone="yes"?>',
                         '<Relationships xmlns="http://schemas.openxmlformats.org/'
                         'package/2006/relationships">']
                for k, p in enumerate(sh.pics, start=1):
                    media_seq += 1
                    arc = "image{}.png".format(media_seq)
                    media.append(("xl/media/" + arc, p["data"]))
                    drels.append('<Relationship Id="rId{}" Type="http://schemas.'
                                 'openxmlformats.org/officeDocument/2006/relationships/image"'
                                 ' Target="../media/{}"/>'.format(k, arc))
                drels.append("</Relationships>")
                items.append(("xl/drawings/drawing{}.xml".format(i), sh.drawing_xml()))
                items.append(("xl/drawings/_rels/drawing{}.xml.rels".format(i), "".join(drels)))
        items.extend(media)
        return items

    def save(self, path):
        if not self.sheets:
            raise ValueError("a workbook with no sheets is not a workbook")
        with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
            for name, payload in self.parts():
                info = zipfile.ZipInfo(name, date_time=_ZIP_DATE)
                info.compress_type = zipfile.ZIP_DEFLATED
                info.external_attr = 0o644 << 16
                z.writestr(info, payload if isinstance(payload, bytes)
                           else payload.encode("utf-8"))
        return path
