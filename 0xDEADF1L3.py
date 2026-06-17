#!/usr/bin/env python3
"""0xDEADF1L3 — Corrupted File Generator"""

import os
import sys
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

# ── File types with magic bytes ───────────────────────────────────────────────
FILE_TYPES = [
    ("pdf",  b"%PDF-1.7\n%\xe2\xe3\xcf\xd3\n"),
    ("md",   b""),
    ("txt",  b"\xef\xbb\xbf"),                          # UTF-8 BOM
    ("pptx", b"PK\x03\x04\x14\x00\x00\x00"),
    ("docx", b"PK\x03\x04\x14\x00\x00\x00"),
    ("xlsx", b"PK\x03\x04\x14\x00\x00\x00"),
    ("png",  b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR"),
    ("mp3",  b"ID3\x03\x00\x00\x00\x00\x00#"),
    ("mp4",  b"\x00\x00\x00\x1cftypisom\x00\x00\x02\x00isomiso2avc1"),
]

# ── Size specs: prompt text, default, unit label, bytes converter ─────────────
#   converter receives the raw string the user typed
SIZE_SPECS = {
    "pdf":  ("Number of pages",            "5",         "pages",  lambda v: int(v) * 100 * 1024),
    "md":   ("Number of lines",            "100",       "lines",  lambda v: max(1, int(v)) * 80),
    "txt":  ("Number of lines",            "200",       "lines",  lambda v: max(1, int(v)) * 80),
    "pptx": ("Number of slides",           "10",        "slides", lambda v: int(v) * 250 * 1024),
    "docx": ("Number of pages",            "5",         "pages",  lambda v: int(v) * 20 * 1024),
    "xlsx": ("Number of rows",             "500",       "rows",   lambda v: 8 * 1024 + int(v) * 50),
    "png":  ("Resolution (e.g. 1920x1080)","1920x1080", "px",     lambda v: _png_bytes(v)),
    "mp3":  ("Duration (minutes)",         "3",         "min",    lambda v: int(float(v) * 60 * 16_000)),
    "mp4":  ("Duration (minutes)",         "5",         "min",    lambda v: int(float(v) * 60 * 187_500)),
}


def _png_bytes(res: str) -> int:
    try:
        w, h = res.lower().split("x")
        return int(w) * int(h) * 3  # uncompressed RGB estimate
    except Exception:
        raise ValueError(f"Expected WxH format, got: {res!r}")


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
    # Binary formats: embed readable tag after magic header
    parts = []
    if title:  parts.append(f"Title={title}")
    if author: parts.append(f"Author={author}")
    if date:   parts.append(f"Date={date}")
    if desc:   parts.append(f"Desc={desc}")
    return ("; ".join(parts) + "\x00").encode("utf-8")


# ── File generation ───────────────────────────────────────────────────────────

def generate(path: str, header: bytes, meta: bytes, target: int) -> None:
    chunk = 65536
    with open(path, "wb") as f:
        f.write(header)
        f.write(meta)
        remaining = target - f.tell()
        written   = f.tell()
        while remaining > 0:
            n = min(chunk, remaining)
            f.write(os.urandom(n))
            remaining -= n
            written   += n
            pct = written / target * 100
            filled = int(pct / 5)
            bar = f"{C}{'█' * filled}{GR}{'░' * (20 - filled)}"
            print(f"\r  {GR}[{bar}{GR}]{X} {Y}{pct:5.1f}%{X}", end="", flush=True)
    bar = f"{G}{'█' * 20}"
    print(f"\r  {GR}[{bar}{GR}]{X} {G}100.0%  done{X}   ")


# ── Prompt helper ─────────────────────────────────────────────────────────────

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
        ext, header = FILE_TYPES[idx]
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

    # Build and write
    meta   = build_meta(ext, title, author, desc, date)
    target = max(target_bytes, len(header) + len(meta) + 1)
    out    = f"{name}.{ext}"

    print()
    generate(out, header, meta, target)

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
