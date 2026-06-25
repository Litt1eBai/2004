#!/usr/bin/env python3
"""Minimal, dependency-free .xlsx I/O for the content pipeline (step 5).

No openpyxl. Reader handles the two ways a cell can hold text — Excel's shared
strings (t="s") and inline strings (t="inlineStr") — plus numbers/bools, so a
file authored here AND a file re-saved by Excel both load. Writer emits inline
strings only (simplest valid OOXML), with xml:space="preserve" so leading/trailing
spaces in values like " Slab" survive the round-trip.

Public API:
  write_xlsx(path, sheets)            sheets = [(name, rows)], rows = list[list[cell]]
  read_xlsx(path) -> {name: rows}     rows = list[list[cell]] (str/int/float/bool/None)
  sheet_to_dicts(rows) -> list[dict]  row 0 is the header
  dicts_to_sheet(headers, dicts)      -> rows (header + one row per dict)
"""
from __future__ import annotations

import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path


# ---- column letters <-> 0-based index ------------------------------------
def col_letter(index: int) -> str:
    s = ""
    index += 1
    while index:
        index, rem = divmod(index - 1, 26)
        s = chr(65 + rem) + s
    return s


def col_index(letter: str) -> int:
    n = 0
    for ch in letter:
        if ch.isalpha():
            n = n * 26 + (ord(ch.upper()) - 64)
    return n - 1


def _xml_escape(s: str) -> str:
    return (s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


def _local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


# ---- writer (inline strings) ---------------------------------------------
_CONTENT_TYPES = (
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
    '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
    '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
    '<Default Extension="xml" ContentType="application/xml"/>'
    '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
    "{sheet_overrides}"
    '<Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>'
    "</Types>"
)
_ROOT_RELS = (
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
    '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
    '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>'
    "</Relationships>"
)
_STYLES = (
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
    '<styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
    '<fonts count="1"><font><sz val="11"/><name val="Calibri"/></font></fonts>'
    '<fills count="1"><fill><patternFill patternType="none"/></fill></fills>'
    '<borders count="1"><border/></borders>'
    '<cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs>'
    '<cellXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0"/></cellXfs>'
    "</styleSheet>"
)
_NS_MAIN = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
_NS_R = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"


def _cell_xml(ref: str, value) -> str:
    if value is None or value == "":
        return f'<c r="{ref}"/>'
    if isinstance(value, bool):
        return f'<c r="{ref}" t="b"><v>{1 if value else 0}</v></c>'
    if isinstance(value, (int, float)):
        # int floats stay int-looking so the reader recovers them cleanly
        v = int(value) if isinstance(value, float) and value.is_integer() else value
        return f'<c r="{ref}"><v>{v}</v></c>'
    text = _xml_escape(str(value))
    space = ' xml:space="preserve"' if str(value) != str(value).strip() else ""
    return f'<c r="{ref}" t="inlineStr"><is><t{space}>{text}</t></is></c>'


def _sheet_xml(rows: list) -> str:
    out = [
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>',
        f'<worksheet xmlns="{_NS_MAIN}"><sheetData>',
    ]
    for r, row in enumerate(rows, start=1):
        out.append(f'<row r="{r}">')
        for c, value in enumerate(row):
            out.append(_cell_xml(f"{col_letter(c)}{r}", value))
        out.append("</row>")
    out.append("</sheetData></worksheet>")
    return "".join(out)


def write_xlsx(path, sheets: list) -> None:
    path = Path(path)
    sheet_overrides = "".join(
        f'<Override PartName="/xl/worksheets/sheet{i}.xml" '
        'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
        for i in range(1, len(sheets) + 1)
    )
    wb_sheets = "".join(
        f'<sheet name="{_xml_escape(name)}" sheetId="{i}" r:id="rId{i}"/>'
        for i, (name, _rows) in enumerate(sheets, start=1)
    )
    workbook = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        f'<workbook xmlns="{_NS_MAIN}" xmlns:r="{_NS_R}"><sheets>{wb_sheets}</sheets></workbook>'
    )
    wb_rels_items = "".join(
        f'<Relationship Id="rId{i}" '
        'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" '
        f'Target="worksheets/sheet{i}.xml"/>'
        for i in range(1, len(sheets) + 1)
    )
    style_rel_id = len(sheets) + 1
    wb_rels = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        f"{wb_rels_items}"
        f'<Relationship Id="rId{style_rel_id}" '
        'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" '
        'Target="styles.xml"/>'
        "</Relationships>"
    )
    def _put(z, name, data):
        # fixed timestamp -> byte-stable output (re-seeding yields an identical file,
        # so a binary source-of-truth doesn't churn its git blob on every run)
        zi = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
        zi.compress_type = zipfile.ZIP_DEFLATED
        zi.external_attr = 0o644 << 16
        z.writestr(zi, data)

    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        _put(z, "[Content_Types].xml", _CONTENT_TYPES.format(sheet_overrides=sheet_overrides))
        _put(z, "_rels/.rels", _ROOT_RELS)
        _put(z, "xl/workbook.xml", workbook)
        _put(z, "xl/_rels/workbook.xml.rels", wb_rels)
        _put(z, "xl/styles.xml", _STYLES)
        for i, (_name, rows) in enumerate(sheets, start=1):
            _put(z, f"xl/worksheets/sheet{i}.xml", _sheet_xml(rows))


# ---- reader (shared strings + inline strings + numbers/bools) -------------
def _parse_xml(z: zipfile.ZipFile, name: str):
    with z.open(name) as f:
        return ET.parse(f).getroot()


def _si_text(si) -> str:
    """Text of one <si>/<is>: the direct <t>, plus <t> inside each formatting run <r>.
    Crucially SKIPS <rPh> (phonetic guide runs Excel adds in CJK/JP/KR locales) and
    <phoneticPr> — a plain iter() over <t> would concatenate phonetic text into the
    value and silently corrupt every CJK cell after an Excel round-trip."""
    parts = []
    for child in si:
        lt = _local(child.tag)
        if lt == "t":
            parts.append(child.text or "")
        elif lt == "r":  # rich run: take its <t>, ignore <rPr>
            for rc in child:
                if _local(rc.tag) == "t":
                    parts.append(rc.text or "")
        # rPh / phoneticPr / anything else: not part of the cell value
    return "".join(parts)


def _shared_strings(z: zipfile.ZipFile) -> list:
    if "xl/sharedStrings.xml" not in z.namelist():
        return []
    root = _parse_xml(z, "xl/sharedStrings.xml")
    return [_si_text(si) for si in root]


def _cell_value(c, shared: list):
    t = c.get("t")
    if t == "s":
        v = c.find("{*}v")
        return shared[int(v.text)] if v is not None and v.text is not None else ""
    if t == "inlineStr":
        is_el = c.find("{*}is")
        return _si_text(is_el) if is_el is not None else ""
    if t == "str":
        v = c.find("{*}v")
        return v.text if v is not None else ""
    if t == "b":
        v = c.find("{*}v")
        return (v is not None and v.text == "1")
    # default: number (or empty)
    v = c.find("{*}v")
    if v is None or v.text is None:
        return ""
    text = v.text
    try:
        f = float(text)
        return int(f) if f.is_integer() else f
    except ValueError:
        return text


def read_xlsx(path) -> dict:
    path = Path(path)
    with zipfile.ZipFile(path) as z:
        shared = _shared_strings(z)
        wb = _parse_xml(z, "xl/workbook.xml")
        rels = _parse_xml(z, "xl/_rels/workbook.xml.rels")
        rid_to_target = {}
        for rel in rels:
            rid_to_target[rel.get("Id")] = rel.get("Target")
        result = {}
        for sheet in wb.iter():
            if _local(sheet.tag) != "sheet":
                continue
            name = sheet.get("name")
            rid = sheet.get(f"{{{_NS_R}}}id")
            target = rid_to_target.get(rid, "")
            part = "xl/" + target.lstrip("/")
            ws = _parse_xml(z, part)
            rows = []
            for row in ws.iter():
                if _local(row.tag) != "row":
                    continue
                cells = {}
                maxc = -1
                for c in row:
                    if _local(c.tag) != "c":
                        continue
                    ref = c.get("r", "")
                    letters = "".join(ch for ch in ref if ch.isalpha())
                    ci = col_index(letters) if letters else (maxc + 1)
                    cells[ci] = _cell_value(c, shared)
                    maxc = max(maxc, ci)
                rows.append([cells.get(i, "") for i in range(maxc + 1)])
            result[name] = rows
    return result


def sheet_to_dicts(rows: list) -> list:
    if not rows:
        return []
    header = [str(h) for h in rows[0]]
    if any(h == "" for h in header) or len(set(header)) != len(header):
        raise SystemExit(f"xlsx sheet has a blank or duplicate header (would drop columns): {header}")
    out = []
    for row in rows[1:]:
        if all(v == "" for v in row):
            continue
        if len(row) > len(header):
            raise SystemExit(
                f"xlsx data row has more cells ({len(row)}) than headers ({len(header)}); "
                f"extra cells would be lost: {row}")
        out.append({header[i]: (row[i] if i < len(row) else "") for i in range(len(header))})
    return out


def dicts_to_sheet(headers: list, dicts: list) -> list:
    rows = [list(headers)]
    for d in dicts:
        rows.append([d.get(h, "") for h in headers])
    return rows
