# 0xDEADF1L3 — Corrupted File Generator

Terminal-based tool that generates structurally convincing corrupted files for CTF challenges, bug testing, and social engineering awareness training.

Zero external dependencies — pure Python stdlib.

## Features

- **9 file formats**: PDF, Markdown, TXT, PPTX, DOCX, XLSX, PNG, MP3, MP4
- **Format-specific size inputs**: pages, slides, rows, resolution, duration — not raw MB
- **Structurally valid skeletons**: files pass basic web-based format validators
- **Embedded metadata**: title, author, description, date written into format-native fields
- **File timestamp spoofing**: OS modified-date matches the metadata date via `os.utime()`
- **Generate-again loop**: batch multiple files without restarting
- **Progress bar**: live progress during generation
- **Windows UTF-8 / ANSI support**: works in Windows Terminal and CMD

## Usage

```bash
python 0xDEADF1L3.py
```

Interactive prompts walk through filename → format → size → metadata → generate.
After each file, choose to generate another or exit.

## Format internals

Each format includes a realistic internal structure designed to pass basic web validators:

| Format | Structure |
|--------|-----------|
| **PDF** | Catalog/Pages/Page/Content objects • Info dict (title/author/date) • Font resource • xref table • `%%EOF` marker |
| **DOCX** | Real ZIP with: `[Content_Types].xml` • `_rels/.rels` • `word/document.xml` • `docProps/core.xml` (W3CDTF date) • `docProps/app.xml` (word/page/line/paragraph counts) |
| **PPTX** | Real ZIP with: `[Content_Types].xml` • `ppt/presentation.xml` (with slide ID list) • Individual `ppt/slides/slide1..N.xml` • `docProps/core.xml` and `docProps/app.xml` (slide count) |
| **XLSX** | Real ZIP with: `[Content_Types].xml` • `xl/workbook.xml` • `xl/worksheets/sheet1.xml` (with row dimension) • `docProps/core.xml` and `docProps/app.xml` |
| **PNG** | PNG signature • IHDR chunk (correct CRC32 for dimensions) • IDAT (random data) • IEND terminator |
| **MP3** | ID3v2.3 header (syncsafe-encoded file size) • MPEG1 Layer3 frame headers (`0xFF 0xFB`) at 128 kbps |
| **MP4** | Valid `ftyp` box (codec identifiers) • Sized `mdat` box header |
| **TXT** | UTF-8 BOM • Metadata as plain text |
| **MD** | YAML front-matter (title/author/date/description) • Markdown separator |

## Size inputs

| Format | Prompt           | Default   |
|--------|------------------|-----------|
| PDF    | Number of pages  | 5         |
| MD     | Number of lines  | 100       |
| TXT    | Number of lines  | 200       |
| PPTX   | Number of slides | 10        |
| DOCX   | Number of pages  | 5         |
| XLSX   | Number of rows   | 500       |
| PNG    | Resolution (WxH) | 1920x1080 |
| MP3    | Duration (min)   | 3         |
| MP4    | Duration (min)   | 5         |

## Size estimation

Sizes are converted from format-specific units to bytes using realistic per-unit estimates:

```
PDF page      →  100 KB   (text + layout objects)
DOCX page     →  20 KB    (compressed XML)
PPTX slide    →  250 KB   (compressed slide + media stub)
XLSX row      →  50 bytes (cell data)
PNG pixel     →  3 bytes  (RGB, 8-bit)
MP3 minute    →  16 KB    (128 kbps @ 8000 Hz)
MP4 minute    →  187.5 KB (1080p @ 24fps stub)
MD/TXT line   →  80 bytes (avg line length)
```

## Date and metadata

**Date workflow:**
```
> Date (optional, e.g. 2026-06-17):          ← type a date, or leave empty
  Date is empty. Choose an option:
  [1]  Use today's date (2026-06-17)
  [2]  No date
> Select option [2]:
```

When set, the date is written to:
- **Format-native fields**: PDF Info dictionary, Office `docProps/core.xml` (W3CDTF format), Markdown YAML, TXT header
- **OS metadata**: File modified-time via `os.utime()` — visible in file properties / `ls -la`

**Metadata embedding:**
- Title, author, description are stored in each format's native structure
- Office files get realistic word/page/line/character/slide/row counts based on your size input
- PDF Info dictionary lists creator as "Microsoft Word" for extra authenticity

## Filename handling

- Illegal characters (`<>:"/\|?*` and control chars) are stripped and replaced with `_`
- Path separators are removed (prevents directory traversal)
- Names are trimmed of trailing dots/spaces

## Large file safeguard

If you request a file larger than **512 MB**, you'll be prompted to confirm before generation begins.

## Example session

```
> Filename (without extension): report_q2
> Choose file type [1]: 4          ← PPTX
> Number of slides [10]: 15
> Date (optional): 2026-05-30
> Title: Q2 Results
> Author: J. Smith
> Description: Internal review deck
  ────────────────────────────────────────────────
  File generated successfully!

  Path        C:\Users\...\report_q2.pptx
  Type        .pptx
  Slides      15 slides
  Size        3,932,160 bytes  (3.750 MB)
  Date        2026-05-30
  Title       Q2 Results
  Author      J. Smith

> Generate another file? [y/N]: y

> Filename (without extension): meeting_notes
> Choose file type [1]: 2          ← Markdown
> Number of lines [100]: 250
> Date (optional):                ← empty
  Date is empty. Choose an option:
  [1]  Use today's date (2026-06-17)
  [2]  No date
> Select option [2]: 1
  [generating...]
  ────────────────────────────────────────────────
  File generated successfully!

  Path        C:\Users\...\meeting_notes.md
  Type        .md
  Lines       250 lines
  Size        20,002 bytes  (0.019 MB)
  Date        2026-06-17
  Title       meeting_notes

> Generate another file? [y/N]: n

  Goodbye.
```

## Disclaimer

For CTF challenges, bug testing, and security awareness training only.
