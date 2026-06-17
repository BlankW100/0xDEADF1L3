#!/usr/bin/env python3
"""0xDEADF1L3 — Corrupted File Generator"""

import os, sys
from datetime import datetime

from formats import FILE_TYPES, SIZE_SPECS, generate_bytes

if sys.platform == "win32":
    os.system("color")
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]

# ── ANSI colors ───────────────────────────────────────────────────────────────
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


def _sanitize_name(name: str) -> str:
    name = os.path.basename(name)
    bad = set('<>:"/\\|?*') | {chr(i) for i in range(32)}
    cleaned = "".join("_" if c in bad else c for c in name)
    return cleaned.strip(". ") or "output"


# ── Progress helpers ──────────────────────────────────────────────────────────

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


def _set_mtime(path: str, date: str) -> None:
    try:
        ts = datetime.strptime(date, "%Y-%m-%d").timestamp()
        os.utime(path, (ts, ts))
    except Exception:
        pass


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

        # Generate file
        data = generate_bytes(ext, title, author, date, desc, target_bytes, size_raw)
        _write_bytes(out, data)
        if date:
            _set_mtime(out, date)

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
