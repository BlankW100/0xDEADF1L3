#!/usr/bin/env python3
"""0xDEADF1L3 — Corrupted File Generator"""

import io
import os
import struct
import sys
import zipfile
import zlib
from datetime import datetime

# Enable ANSI colours and UTF-8 output on Windows
if sys.platform == "win32":
    os.system("color")
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]

# ── ANSI ──────────────────────────────────────────────────────────────────────
R  = "\033[91m"
G  = "\033[92m"
Y  = "\033[93m"
C  = "\033[96m"
GR = "\033[90m"
BD = "\033[1m"
X  = "\033[0m"

# ── Banner (ASCII art) ────────────────────────────────────────────────────────
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

# ── File types ────────────────────────────────────────────────────────────────
FILE_TYPES = [
    ("pdf",  b"%PDF-1.7\n%\xe2\xe3\xcf\xd3\n"),
    ("md",   b""),
    ("txt",  b"\xef\xbb\xbf"),
    ("pptx", b"PK\x03\x04\x14\x00\x00\x00"),
    ("docx", b"PK\x03\x04\x14\x00\x00\x00"),
    ("xlsx", b"PK\x03\x04\x14\x00\x00\x00"),
    ("png",  b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR"),
    ("mp3",  b"ID3\x03\x00\x00\x00\x00\x00#"),
    ("mp4",  b"\x00\x00\x00\x1cftypisom\x00\x00\x02\x00isomiso2avc1"),
]

# ── Size specs ────────────────────────────────────────────────────────────────
SIZE_SPECS = {
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


# ── Format builders ───────────────────────────────────────────────────────────

def _make_pdf(meta: bytes, n_pages: int, target: int) -> bytes:
    """Build a valid PDF skeleton with proper xref table and %%EOF.
    Each page gets a content stream object filled with random bytes."""
    overhead = 600 + n_pages * 300
    stream_per_page = max(512, (target - overhead) // max(1, n_pages))

    parts = []

    def tell() -> int:
        return sum(len(p) for p in parts)

    parts.append(b"%PDF-1.7\n%\xe2\xe3\xcf\xd3\n")
    if meta:
        parts.append(meta)

    offsets: dict[int, int] = {}

    # Obj 1 — Catalog
    offsets[1] = tell()
    parts.append(b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n")

    # Obj 2 — Pages tree
    offsets[2] = tell()
    kids = " ".join(f"{3 + i} 0 R" for i in range(n_pages))
    parts.append(f"2 0 obj\n<< /Type /Pages /Kids [{kids}] /Count {n_pages} >>\nendobj\n".encode())

    # Page objects (obj 3 … 2+n_pages)
    for i in range(n_pages):
        obj_n     = 3 + i
        c_obj     = 3 + n_pages + i
        offsets[obj_n] = tell()
        parts.append(
            f"{obj_n} 0 obj\n<< /Type /Page /Parent 2 0 R "
            f"/MediaBox [0 0 612 792] /Contents {c_obj} 0 R >>\nendobj\n".encode()
        )

    # Content stream objects (obj 3+n_pages … 2+2*n_pages)
    for i in range(n_pages):
        obj_n = 3 + n_pages + i
        data  = os.urandom(stream_per_page)
        offsets[obj_n] = tell()
        parts.append(
            f"{obj_n} 0 obj\n<< /Length {len(data)} >>\nstream\n".encode()
            + data
            + b"\nendstream\nendobj\n"
        )

    # xref table
    xref_pos  = tell()
    total_obj = 2 + 2 * n_pages
    parts.append(f"xref\n0 {total_obj + 1}\n".encode())
    parts.append(b"0000000000 65535 f \r\n")
    for idx in range(1, total_obj + 1):
        parts.append(f"{offsets[idx]:010d} 00000 n \r\n".encode())

    parts.append(
        f"trailer\n<< /Size {total_obj + 1} /Root 1 0 R >>\n"
        f"startxref\n{xref_pos}\n%%EOF\n".encode()
    )
    return b"".join(parts)


def _make_office_zip(meta: bytes, target: int) -> bytes:
    """Build a real ZIP file with valid central directory.
    Includes Content_Types and _rels stubs so the Office MIME type validates."""
    ct_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\r\n'
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
        '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
        '<Default Extension="xml" ContentType="application/xml"/>'
        '</Types>'
    )
    rels_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\r\n'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '</Relationships>'
    )

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("[Content_Types].xml", ct_xml)
        zf.writestr("_rels/.rels", rels_xml)
        if meta:
            zf.writestr("docProps/core.xml", meta.decode("utf-8", errors="replace"))
        payload_size = max(0, target - 4096)
        zf.writestr(
            zipfile.ZipInfo("word/document.bin"),
            os.urandom(payload_size),
            compress_type=zipfile.ZIP_STORED,
        )
    return buf.getvalue()


def _png_chunk(ctype: bytes, data: bytes) -> bytes:
    crc = zlib.crc32(ctype + data) & 0xFFFFFFFF
    return struct.pack(">I", len(data)) + ctype + data + struct.pack(">I", crc)


def _make_png(width: int, height: int, target: int) -> bytes:
    """PNG with valid IHDR (correct CRC32 for dimensions) and IEND at EOF."""
    sig  = b"\x89PNG\r\n\x1a\n"
    ihdr = _png_chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
    iend = _png_chunk(b"IEND", b"")
    idat_size = max(0, target - len(sig) - len(ihdr) - len(iend) - 12)
    idat = _png_chunk(b"IDAT", os.urandom(idat_size))
    return sig + ihdr + idat + iend


def _syncsafe4(n: int) -> bytes:
    return bytes([(n >> (7 * (3 - i))) & 0x7F for i in range(4)])


def _make_mp3_prefix(target: int) -> bytes:
    """ID3v2.3 header with syncsafe-encoded size covering the whole file."""
    id3_payload = max(0, target - 10)
    return b"ID3\x03\x00\x00" + _syncsafe4(id3_payload)


def _make_mp4_prefix(target: int) -> bytes:
    """Valid ftyp box followed by mdat box header sized to fill the file."""
    ftyp_data = b"isom\x00\x00\x02\x00isomiso2avc1mp41"
    ftyp      = struct.pack(">I", 8 + len(ftyp_data)) + b"ftyp" + ftyp_data
    mdat_size = max(8, target - len(ftyp))
    mdat_hdr  = struct.pack(">I", mdat_size) + b"mdat"
    return ftyp + mdat_hdr


# ── Metadata injection ────────────────────────────────────────────────────────

def build_meta(ext: str, title: str, author: str, desc: str, date: str = "") -> bytes:
    if not (title or author or desc or date):
        return b""
    if ext == "pdf":
        lines = ["% --- Metadata ---"]
        if title:  lines.append(f"% Title: {title}")
        if author: lines.append(f"% Author: {author}")
        if date:   lines.append(f"% Date: {date}")
        if desc:   lines.append(f"% Description: {desc}")
        return ("\n".join(lines) + "\n").encode("utf-8")
    if ext == "md":
        front = ["---"]
        if title:  front.append(f"title: \"{title}\"")
        if author: front.append(f"author: \"{author}\"")
        if date:   front.append(f"date: \"{date}\"")
        if desc:   front.append(f"description: \"{desc}\"")
        front.append("---\n")
        return "\n".join(front).encode("utf-8")
    parts = []
    if title:  parts.append(f"Title={title}")
    if author: parts.append(f"Author={author}")
    if date:   parts.append(f"Date={date}")
    if desc:   parts.append(f"Desc={desc}")
    return ("; ".join(parts) + "\x00").encode("utf-8")


# ── Progress helpers ──────────────────────────────────────────────────────────

def _progress(pct: float) -> None:
    filled = int(pct / 5)
    bar = f"{C}{'█' * filled}{GR}{'░' * (20 - filled)}"
    print(f"\r  {GR}[{bar}{GR}]{X} {Y}{pct:5.1f}%{X}", end="", flush=True)


def _progress_done() -> None:
    print(f"\r  {GR}[{G}{'█' * 20}{GR}]{X} {G}100.0%  done{X}   ")


def _write_bytes(path: str, data: bytes) -> None:
    chunk   = 65536
    total   = len(data)
    written = 0
    with open(path, "wb") as f:
        while written < total:
            n = min(chunk, total - written)
            f.write(data[written : written + n])
            written += n
            _progress(written / total * 100)
    _progress_done()


def _stream_random(path: str, prefix: bytes, target: int) -> None:
    chunk     = 65536
    written   = 0
    with open(path, "wb") as f:
        f.write(prefix)
        written   = len(prefix)
        remaining = target - written
        while remaining > 0:
            n = min(chunk, remaining)
            f.write(os.urandom(n))
            written   += n
            remaining -= n
            _progress(written / target * 100)
    _progress_done()


# ── Main generate dispatcher ──────────────────────────────────────────────────

def generate(path: str, ext: str, meta: bytes, target: int, size_raw: str) -> None:
    if ext == "pdf":
        _write_bytes(path, _make_pdf(meta, int(size_raw), target))
    elif ext in ("docx", "pptx", "xlsx"):
        _write_bytes(path, _make_office_zip(meta, target))
    elif ext == "png":
        w, h = (int(v) for v in size_raw.lower().split("x"))
        _write_bytes(path, _make_png(w, h, target))
    elif ext == "mp3":
        _stream_random(path, _make_mp3_prefix(target), target)
    elif ext == "mp4":
        _stream_random(path, _make_mp4_prefix(target), target)
    else:
        # txt / md — stream with plain header + metadata prefix
        header = dict(FILE_TYPES)[ext]
        _stream_random(path, header + meta, target)


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
    date_input = ask("Date (optional, e.g. 2026-06-17)")
    if date_input:
        return date_input
    print(f"  {GR}Date is empty. Choose an option:{X}")
    print(f"  {GR}[{Y}1{GR}]{X}  Use today's date ({datetime.now().strftime('%Y-%m-%d')})")
    print(f"  {GR}[{Y}2{GR}]{X}  No date")
    choice = ask("Select option", "2")
    if choice == "1":
        return datetime.now().strftime("%Y-%m-%d")
    return ""


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    print()
    for line, color in zip(_BANNER, _COLORS):
        print(f"{color}{BD}{line}{X}")
    print(f"  {GR}Corrupted File Generator{X}")
    print()

    # Step 1 – filename
    name = ask("Filename (without extension)")
    if not name:
        print(f"  {R}Error: filename cannot be empty.{X}")
        sys.exit(1)

    # Step 2 – file type
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

    # Step 3 – size (type-specific unit)
    spec_prompt, spec_default, spec_unit, spec_convert = SIZE_SPECS[ext]
    size_raw = ask(spec_prompt, spec_default)
    try:
        target_bytes = spec_convert(size_raw)
        if target_bytes <= 0:
            raise ValueError
    except ValueError as e:
        print(f"  {R}Error: {e or 'invalid value.'}{X}")
        sys.exit(1)

    # Step 4 – metadata (optional)
    print()
    print(f"  {GR}Metadata (optional — press Enter to skip each){X}")
    date   = ask_date()
    title  = ask("Title")
    author = ask("Author")
    desc   = ask("Description")

    meta   = build_meta(ext, title, author, desc, date)
    out    = f"{name}.{ext}"

    print()
    generate(out, ext, meta, target_bytes, size_raw)

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


if __name__ == "__main__":
    main()
