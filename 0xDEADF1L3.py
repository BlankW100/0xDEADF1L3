#!/usr/bin/env python3
"""0xDEADF1L3 — Corrupted File Generator"""

import io, os, struct, sys, zipfile, zlib
from datetime import datetime

if sys.platform == "win32":
    os.system("color")
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]

# ── ANSI ──────────────────────────────────────────────────────────────────────
R  = "\033[91m"; G  = "\033[92m"; Y  = "\033[93m"; C  = "\033[96m"
GR = "\033[90m"; BD = "\033[1m";  X  = "\033[0m"

# ── Banner ────────────────────────────────────────────────────────────────────
_BANNER = [
    r" ________     ___    ___ ________  _______   ________  ________  ________  _____  ___      ________     ",
    r"|\   __  \   |\  \  /  /|\   ___ \|\  ___ \ |\   __  \|\   ___ \|\  _____\/ __  \|\  \    |\_____  \    ",
    r"\ \  \|\  \  \ \  \/  / | \  \_|\ \ \   __/|\ \  \|\  \ \  \_|\ \ \  \__/|\/_|\  \ \  \   \|____|\ /_   ",
    r" \ \  \\\  \  \ \    / / \ \  \ \\ \ \  \_|/_\ \   __  \ \  \ \\ \ \   __\|/ \ \  \ \  \        \|\  \  ",
    r"  \ \  \\\  \  /     \/   \ \  \_\\ \ \  \_|\ \ \  \ \  \ \  \_\\ \ \  \_|    \ \  \ \  \____  __\_\  \ ",
    r"   \ \_______\/  /\   \    \ \_______\ \_______\ \__\ \__\ \_______\ \__\      \ \__\ \_______\\_______\ ",
    r"    \|_______/__/ /\ __\    \|_______|\|_______|\|__|\|__|\|_______|\|__|       \|__|\|_______\|_______| ",
    r"             |__|/ \|__|                                                                                  ",
]
_COLORS = [R, R, Y, Y, G, G, C, C]

# ── Format list ───────────────────────────────────────────────────────────────
FILE_TYPES = [
    ("pdf",  b"%PDF-1.7\n"),
    ("md",   b""),
    ("txt",  b"\xef\xbb\xbf"),
    ("pptx", b"PK\x03\x04"),
    ("docx", b"PK\x03\x04"),
    ("xlsx", b"PK\x03\x04"),
    ("png",  b"\x89PNG\r\n\x1a\n"),
    ("mp3",  b"ID3"),
    ("mp4",  b"\x00\x00\x00\x1cftypisom"),
]

SIZE_SPECS: dict = {
    "pdf":  ("Number of pages",             "5",         "pages",  lambda v: int(v) * 100 * 1024),
    "md":   ("Number of lines",             "100",       "lines",  lambda v: max(1, int(v)) * 80),
    "txt":  ("Number of lines",             "200",       "lines",  lambda v: max(1, int(v)) * 80),
    "pptx": ("Number of slides",            "10",        "slides", lambda v: int(v) * 250 * 1024),
    "docx": ("Number of pages",             "5",         "pages",  lambda v: int(v) * 20 * 1024),
    "xlsx": ("Number of rows",              "500",       "rows",   lambda v: 8 * 1024 + int(v) * 50),
    "png":  ("Resolution (e.g. 1920x1080)", "1920x1080", "px",     lambda v: _png_size_bytes(v)),
    "mp3":  ("Duration (minutes)",          "3",         "min",    lambda v: int(float(v) * 60 * 16_000)),
    "mp4":  ("Duration (minutes)",          "5",         "min",    lambda v: int(float(v) * 60 * 187_500)),
}


def _png_size_bytes(res: str) -> int:
    try:
        w, h = res.lower().split("x")
        return int(w) * int(h) * 3
    except Exception:
        raise ValueError(f"Expected WxH format, got: {res!r}")


def _sanitize_name(name: str) -> str:
    name = os.path.basename(name)
    bad = set('<>:"/\\|?*') | {chr(i) for i in range(32)}
    cleaned = "".join("_" if c in bad else c for c in name)
    return cleaned.strip(". ") or "output"


# ── Office XML helpers ────────────────────────────────────────────────────────

def _core_xml(title: str, author: str, date: str, desc: str) -> str:
    dt = (date or datetime.now().strftime("%Y-%m-%d")) + "T00:00:00Z"
    body = []
    if title:  body.append(f"  <dc:title>{title}</dc:title>")
    if author: body.append(f"  <dc:creator>{author}</dc:creator>")
    if author: body.append(f"  <cp:lastModifiedBy>{author}</cp:lastModifiedBy>")
    body += [
        f'  <dcterms:created xsi:type="dcterms:W3CDTF">{dt}</dcterms:created>',
        f'  <dcterms:modified xsi:type="dcterms:W3CDTF">{dt}</dcterms:modified>',
    ]
    if desc: body.append(f"  <dc:description>{desc}</dc:description>")
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\r\n'
        '<cp:coreProperties'
        ' xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties"'
        ' xmlns:dc="http://purl.org/dc/elements/1.1/"'
        ' xmlns:dcterms="http://purl.org/dc/terms/"'
        ' xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">\r\n'
        + "\r\n".join(body) + "\r\n"
        + "</cp:coreProperties>"
    )


def _make_docx(title: str, author: str, date: str, desc: str, n_pages: int, target: int) -> bytes:
    words = n_pages * 275
    ct = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\r\n'
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
        '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
        '<Default Extension="xml" ContentType="application/xml"/>'
        '<Override PartName="/word/document.xml"'
        ' ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>'
        '<Override PartName="/docProps/core.xml"'
        ' ContentType="application/vnd.openxmlformats-package.core-properties+xml"/>'
        '<Override PartName="/docProps/app.xml"'
        ' ContentType="application/vnd.openxmlformats-officedocument.extended-properties+xml"/>'
        '</Types>'
    )
    rels = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\r\n'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1"'
        ' Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument"'
        ' Target="word/document.xml"/>'
        '<Relationship Id="rId2"'
        ' Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties"'
        ' Target="docProps/core.xml"/>'
        '<Relationship Id="rId3"'
        ' Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/extended-properties"'
        ' Target="docProps/app.xml"/>'
        '</Relationships>'
    )
    doc = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
        '<w:body><w:p><w:r><w:t> </w:t></w:r></w:p></w:body>'
        '</w:document>'
    )
    doc_rels = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"/>'
    )
    app = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/extended-properties">'
        '<Application>Microsoft Office Word</Application>'
        f'<Pages>{n_pages}</Pages><Words>{words}</Words>'
        f'<Characters>{words * 5}</Characters><Lines>{n_pages * 42}</Lines>'
        f'<Paragraphs>{n_pages * 9}</Paragraphs>'
        '</Properties>'
    )
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("[Content_Types].xml", ct)
        zf.writestr("_rels/.rels", rels)
        zf.writestr("word/document.xml", doc)
        zf.writestr("word/_rels/document.xml.rels", doc_rels)
        zf.writestr("docProps/core.xml", _core_xml(title, author, date, desc))
        zf.writestr("docProps/app.xml", app)
        payload = max(0, target - 12 * 1024)
        zf.writestr(zipfile.ZipInfo("word/document.bin"), os.urandom(payload), compress_type=zipfile.ZIP_STORED)
    return buf.getvalue()


def _make_pptx(title: str, author: str, date: str, desc: str, n_slides: int, target: int) -> bytes:
    slide_ids  = "".join(f'<p:sldId id="{256+i}" r:id="rId{i+1}"/>' for i in range(n_slides))
    slide_rels = "".join(
        f'<Relationship Id="rId{i+1}"'
        f' Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slide"'
        f' Target="slides/slide{i+1}.xml"/>' for i in range(n_slides)
    )
    slide_ct = "".join(
        f'<Override PartName="/ppt/slides/slide{i+1}.xml"'
        f' ContentType="application/vnd.openxmlformats-officedocument.presentationml.slide+xml"/>'
        for i in range(n_slides)
    )
    ct = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\r\n'
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
        '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
        '<Default Extension="xml" ContentType="application/xml"/>'
        '<Override PartName="/ppt/presentation.xml"'
        ' ContentType="application/vnd.openxmlformats-officedocument.presentationml.presentation.main+xml"/>'
        f'{slide_ct}'
        '<Override PartName="/docProps/core.xml"'
        ' ContentType="application/vnd.openxmlformats-package.core-properties+xml"/>'
        '<Override PartName="/docProps/app.xml"'
        ' ContentType="application/vnd.openxmlformats-officedocument.extended-properties+xml"/>'
        '</Types>'
    )
    rels = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\r\n'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1"'
        ' Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument"'
        ' Target="ppt/presentation.xml"/>'
        '<Relationship Id="rId2"'
        ' Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties"'
        ' Target="docProps/core.xml"/>'
        '<Relationship Id="rId3"'
        ' Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/extended-properties"'
        ' Target="docProps/app.xml"/>'
        '</Relationships>'
    )
    prs = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<p:presentation xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main"'
        ' xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
        '<p:sldMasterIdLst/>'
        '<p:sldSz cx="9144000" cy="6858000" type="screen4x3"/>'
        '<p:notesSz cx="6858000" cy="9144000"/>'
        f'<p:sldIdLst>{slide_ids}</p:sldIdLst>'
        '</p:presentation>'
    )
    prs_rels = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        f'{slide_rels}'
        '</Relationships>'
    )
    slide_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<p:sld xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main">'
        '<p:cSld><p:spTree/></p:cSld>'
        '</p:sld>'
    )
    empty_rels = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"/>'
    )
    app = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/extended-properties">'
        '<Application>Microsoft Office PowerPoint</Application>'
        f'<Slides>{n_slides}</Slides><Notes>0</Notes><HiddenSlides>0</HiddenSlides>'
        f'<Words>{n_slides * 50}</Words><Paragraphs>{n_slides * 5}</Paragraphs>'
        '</Properties>'
    )
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("[Content_Types].xml", ct)
        zf.writestr("_rels/.rels", rels)
        zf.writestr("ppt/presentation.xml", prs)
        zf.writestr("ppt/_rels/presentation.xml.rels", prs_rels)
        for i in range(n_slides):
            zf.writestr(f"ppt/slides/slide{i+1}.xml", slide_xml)
            zf.writestr(f"ppt/slides/_rels/slide{i+1}.xml.rels", empty_rels)
        zf.writestr("docProps/core.xml", _core_xml(title, author, date, desc))
        zf.writestr("docProps/app.xml", app)
        payload = max(0, target - 12 * 1024 - n_slides * 600)
        zf.writestr(zipfile.ZipInfo("ppt/media/data.bin"), os.urandom(payload), compress_type=zipfile.ZIP_STORED)
    return buf.getvalue()


def _make_xlsx(title: str, author: str, date: str, desc: str, n_rows: int, target: int) -> bytes:
    ct = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\r\n'
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
        '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
        '<Default Extension="xml" ContentType="application/xml"/>'
        '<Override PartName="/xl/workbook.xml"'
        ' ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
        '<Override PartName="/xl/worksheets/sheet1.xml"'
        ' ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
        '<Override PartName="/docProps/core.xml"'
        ' ContentType="application/vnd.openxmlformats-package.core-properties+xml"/>'
        '<Override PartName="/docProps/app.xml"'
        ' ContentType="application/vnd.openxmlformats-officedocument.extended-properties+xml"/>'
        '</Types>'
    )
    rels = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\r\n'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1"'
        ' Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument"'
        ' Target="xl/workbook.xml"/>'
        '<Relationship Id="rId2"'
        ' Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties"'
        ' Target="docProps/core.xml"/>'
        '<Relationship Id="rId3"'
        ' Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/extended-properties"'
        ' Target="docProps/app.xml"/>'
        '</Relationships>'
    )
    wb = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"'
        ' xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
        '<sheets><sheet name="Sheet1" sheetId="1" r:id="rId1"/></sheets>'
        '</workbook>'
    )
    wb_rels = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1"'
        ' Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet"'
        ' Target="worksheets/sheet1.xml"/>'
        '</Relationships>'
    )
    ws = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        f'<dimension ref="A1:Z{n_rows}"/>'
        '<sheetData>'
        f'<row r="1"><c r="A1" t="inlineStr"><is><t>Data</t></is></c>'
        f'<c r="B1" t="inlineStr"><is><t>{n_rows} rows</t></is></c></row>'
        '</sheetData>'
        '</worksheet>'
    )
    app = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/extended-properties">'
        '<Application>Microsoft Office Excel</Application>'
        '<Worksheets>1</Worksheets><SharedDoc>false</SharedDoc>'
        '</Properties>'
    )
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("[Content_Types].xml", ct)
        zf.writestr("_rels/.rels", rels)
        zf.writestr("xl/workbook.xml", wb)
        zf.writestr("xl/_rels/workbook.xml.rels", wb_rels)
        zf.writestr("xl/worksheets/sheet1.xml", ws)
        zf.writestr("docProps/core.xml", _core_xml(title, author, date, desc))
        zf.writestr("docProps/app.xml", app)
        payload = max(0, target - 12 * 1024)
        zf.writestr(zipfile.ZipInfo("xl/worksheets/sheet1.bin"), os.urandom(payload), compress_type=zipfile.ZIP_STORED)
    return buf.getvalue()


# ── PDF builder ───────────────────────────────────────────────────────────────

def _make_pdf(title: str, author: str, date: str, desc: str, n_pages: int, target: int) -> bytes:
    overhead = 900 + n_pages * 350
    stream_per_page = max(512, (target - overhead) // max(1, n_pages))

    parts: list[bytes] = []
    offsets: dict[int, int] = {}

    def tell() -> int:
        return sum(len(p) for p in parts)

    parts.append(b"%PDF-1.7\n%\xe2\xe3\xcf\xd3\n")

    # Object layout:
    # 1=Catalog  2=Pages  3=Info  4=Font
    # 5..4+n_pages        = Page objects
    # 5+n_pages..4+2*n   = Content streams
    info_obj   = 3
    font_obj   = 4
    page_start = 5
    cont_start = 5 + n_pages
    total_objs = 4 + 2 * n_pages

    offsets[1] = tell()
    parts.append(b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n")

    offsets[2] = tell()
    kids = " ".join(f"{page_start + i} 0 R" for i in range(n_pages))
    parts.append(f"2 0 obj\n<< /Type /Pages /Kids [{kids}] /Count {n_pages} >>\nendobj\n".encode())

    offsets[info_obj] = tell()
    info_str = ""
    if title:  info_str += f"/Title ({title})\n"
    if author: info_str += f"/Author ({author})\n"
    if date:   info_str += f"/CreationDate (D:{date.replace('-', '')}120000)\n"
    if desc:   info_str += f"/Subject ({desc})\n"
    info_str += "/Creator (Microsoft Word)\n/Producer (Microsoft Word)\n"
    parts.append(f"{info_obj} 0 obj\n<< {info_str}>>\nendobj\n".encode())

    offsets[font_obj] = tell()
    parts.append(
        f"{font_obj} 0 obj\n<< /Type /Font /Subtype /Type1 "
        f"/BaseFont /Helvetica /Encoding /WinAnsiEncoding >>\nendobj\n".encode()
    )

    for i in range(n_pages):
        pobj = page_start + i
        cobj = cont_start + i
        offsets[pobj] = tell()
        parts.append(
            f"{pobj} 0 obj\n<< /Type /Page /Parent 2 0 R "
            f"/MediaBox [0 0 612 792] /Contents {cobj} 0 R "
            f"/Resources << /Font << /F1 {font_obj} 0 R >> >> >>\nendobj\n".encode()
        )

    for i in range(n_pages):
        cobj = cont_start + i
        data = os.urandom(stream_per_page)
        offsets[cobj] = tell()
        parts.append(
            f"{cobj} 0 obj\n<< /Length {len(data)} >>\nstream\n".encode()
            + data + b"\nendstream\nendobj\n"
        )

    xref_pos = tell()
    parts.append(f"xref\n0 {total_objs + 1}\n".encode())
    parts.append(b"0000000000 65535 f \r\n")
    for idx in range(1, total_objs + 1):
        parts.append(f"{offsets[idx]:010d} 00000 n \r\n".encode())
    parts.append(
        f"trailer\n<< /Size {total_objs + 1} /Root 1 0 R /Info {info_obj} 0 R >>\n"
        f"startxref\n{xref_pos}\n%%EOF\n".encode()
    )
    return b"".join(parts)


# ── PNG builder ───────────────────────────────────────────────────────────────

def _png_chunk(ctype: bytes, data: bytes) -> bytes:
    crc = zlib.crc32(ctype + data) & 0xFFFFFFFF
    return struct.pack(">I", len(data)) + ctype + data + struct.pack(">I", crc)


def _make_png(width: int, height: int, target: int) -> bytes:
    sig  = b"\x89PNG\r\n\x1a\n"
    ihdr = _png_chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
    iend = _png_chunk(b"IEND", b"")
    idat_size = max(0, target - len(sig) - len(ihdr) - len(iend) - 12)
    idat = _png_chunk(b"IDAT", os.urandom(idat_size))
    return sig + ihdr + idat + iend


# ── MP3 / MP4 builders ────────────────────────────────────────────────────────

def _syncsafe4(n: int) -> bytes:
    return bytes([(n >> (7 * (3 - i))) & 0x7F for i in range(4)])


_MP3_FRAME_HDR  = b"\xFF\xFB\x90\x64"  # MPEG1 Layer3 128kbps 44100Hz Joint Stereo
_MP3_FRAME_SIZE = 417                   # bytes per frame


def _make_mp3_prefix(target: int) -> bytes:
    id3 = b"ID3\x03\x00\x00" + _syncsafe4(0)
    n_frames = min(20, max(1, target // _MP3_FRAME_SIZE))
    frames = (_MP3_FRAME_HDR + b"\x00" * (_MP3_FRAME_SIZE - 4)) * n_frames
    return id3 + frames


def _make_mp4_prefix(target: int) -> bytes:
    ftyp_data = b"isom\x00\x00\x02\x00isomiso2avc1mp41"
    ftyp      = struct.pack(">I", 8 + len(ftyp_data)) + b"ftyp" + ftyp_data
    mdat_size = max(8, target - len(ftyp))
    return ftyp + struct.pack(">I", mdat_size) + b"mdat"


# ── Metadata for text formats ─────────────────────────────────────────────────

def _text_meta(ext: str, title: str, author: str, desc: str, date: str) -> bytes:
    if not (title or author or desc or date):
        return b""
    if ext == "md":
        front = ["---"]
        if title:  front.append(f'title: "{title}"')
        if author: front.append(f'author: "{author}"')
        if date:   front.append(f'date: "{date}"')
        if desc:   front.append(f'description: "{desc}"')
        front.append("---\n")
        return "\n".join(front).encode()
    lines = []
    if title:  lines.append(f"Title: {title}")
    if author: lines.append(f"Author: {author}")
    if date:   lines.append(f"Date: {date}")
    if desc:   lines.append(f"Description: {desc}")
    return ("\n".join(lines) + "\n\n").encode()


# ── Progress & write helpers ──────────────────────────────────────────────────

def _progress(pct: float) -> None:
    filled = int(pct / 5)
    bar = f"{C}{'█' * filled}{GR}{'░' * (20 - filled)}"
    print(f"\r  {GR}[{bar}{GR}]{X} {Y}{pct:5.1f}%{X}", end="", flush=True)


def _progress_done() -> None:
    print(f"\r  {GR}[{G}{'█' * 20}{GR}]{X} {G}100.0%  done{X}   ")


def _write_bytes(path: str, data: bytes) -> None:
    chunk, total, written = 65536, len(data), 0
    with open(path, "wb") as f:
        while written < total:
            n = min(chunk, total - written)
            f.write(data[written:written + n])
            written += n
            _progress(written / total * 100)
    _progress_done()


def _stream_random(path: str, prefix: bytes, target: int) -> None:
    chunk = 65536
    with open(path, "wb") as f:
        f.write(prefix)
        written   = len(prefix)
        remaining = max(0, target - written)
        while remaining > 0:
            n = min(chunk, remaining)
            f.write(os.urandom(n))
            written   += n
            remaining -= n
            _progress(written / target * 100)
    _progress_done()


def _set_mtime(path: str, date: str) -> None:
    try:
        ts = datetime.strptime(date, "%Y-%m-%d").timestamp()
        os.utime(path, (ts, ts))
    except Exception:
        pass


# ── Generate dispatcher ───────────────────────────────────────────────────────

def generate(
    path: str, ext: str,
    title: str, author: str, date: str, desc: str,
    target: int, size_raw: str,
) -> None:
    n = int(size_raw) if size_raw.isdigit() else 0
    if ext == "pdf":
        _write_bytes(path, _make_pdf(title, author, date, desc, max(1, n), target))
    elif ext == "docx":
        _write_bytes(path, _make_docx(title, author, date, desc, max(1, n), target))
    elif ext == "pptx":
        _write_bytes(path, _make_pptx(title, author, date, desc, max(1, n), target))
    elif ext == "xlsx":
        _write_bytes(path, _make_xlsx(title, author, date, desc, n or 500, target))
    elif ext == "png":
        w, h = (int(v) for v in size_raw.lower().split("x"))
        _write_bytes(path, _make_png(w, h, target))
    elif ext == "mp3":
        _stream_random(path, _make_mp3_prefix(target), target)
    elif ext == "mp4":
        _stream_random(path, _make_mp4_prefix(target), target)
    else:
        bom  = b"\xef\xbb\xbf" if ext == "txt" else b""
        meta = _text_meta(ext, title, author, desc, date)
        _stream_random(path, bom + meta, target)
    if date:
        _set_mtime(path, date)


# ── Prompt helpers ────────────────────────────────────────────────────────────

def ask(prompt: str, default: str = "") -> str:
    hint = f" {GR}[{default}]{X}" if default else ""
    try:
        val = input(f"  {G}>{X} {prompt}{hint}: ").strip()
        return val if val else default
    except (EOFError, KeyboardInterrupt):
        print(f"\n{R}Aborted.{X}")
        sys.exit(0)


def ask_date() -> str:
    val = ask("Date (optional, e.g. 2026-06-17)")
    if val:
        return val
    print(f"  {GR}Date is empty. Choose an option:{X}")
    print(f"  {GR}[{Y}1{GR}]{X}  Use today's date ({datetime.now().strftime('%Y-%m-%d')})")
    print(f"  {GR}[{Y}2{GR}]{X}  No date")
    return datetime.now().strftime("%Y-%m-%d") if ask("Select option", "2") == "1" else ""


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    print()
    for line, color in zip(_BANNER, _COLORS):
        print(f"{color}{BD}{line}{X}")
    print(f"  {GR}Corrupted File Generator  —  CTF / Bug Testing / Awareness Training{X}")
    print()

    while True:
        # Step 1 — filename
        name = ask("Filename (without extension)")
        if not name:
            print(f"  {R}Error: filename cannot be empty.{X}")
            sys.exit(1)
        name = _sanitize_name(name)

        # Step 2 — file type
        print()
        print(f"  {C}Available file types:{X}")
        for i, (ext, _) in enumerate(FILE_TYPES, 1):
            print(f"  {GR}[{Y}{i}{GR}]{X}  .{ext}")
        print()
        choice = ask("Choose file type", "1")
        try:
            idx = int(choice) - 1
            if not (0 <= idx < len(FILE_TYPES)):
                raise ValueError
            ext, _ = FILE_TYPES[idx]
        except ValueError:
            print(f"  {R}Error: invalid choice.{X}")
            sys.exit(1)

        # Step 3 — size
        spec_prompt, spec_default, spec_unit, spec_convert = SIZE_SPECS[ext]
        size_raw = ask(spec_prompt, spec_default)
        try:
            target_bytes = spec_convert(size_raw)
            if target_bytes <= 0:
                raise ValueError("size must be positive")
        except ValueError as e:
            print(f"  {R}Error: {e or 'invalid value.'}{X}")
            sys.exit(1)

        if target_bytes > 512 * 1024 * 1024:
            mb = target_bytes / 1_048_576
            if ask(f"Target size is {mb:.0f} MB — continue? [y/N]", "N").lower() != "y":
                sys.exit(0)

        # Step 4 — metadata
        print()
        print(f"  {GR}Metadata (optional — press Enter to skip each){X}")
        date   = ask_date()
        title  = ask("Title")
        author = ask("Author")
        desc   = ask("Description")

        out = f"{name}.{ext}"
        print()
        generate(out, ext, title, author, date, desc, target_bytes, size_raw)

        actual = os.path.getsize(out)
        print()
        print(f"  {GR}{'─' * 48}{X}")
        print(f"  {G}{BD}File generated successfully!{X}")
        print()
        print(f"  {GR}Path       {X}  {os.path.abspath(out)}")
        print(f"  {GR}Type       {X}  .{ext}")
        print(f"  {GR}{spec_unit.capitalize():<10}{X}  {size_raw} {spec_unit}")
        print(f"  {GR}Size       {X}  {actual:,} bytes  ({actual / 1_048_576:.3f} MB)")
        if date:   print(f"  {GR}Date       {X}  {date}")
        if title:  print(f"  {GR}Title      {X}  {title}")
        if author: print(f"  {GR}Author     {X}  {author}")
        print()

        if ask("Generate another file? [y/N]", "N").lower() != "y":
            break

    print(f"\n  {GR}Goodbye.{X}\n")


if __name__ == "__main__":
    main()
