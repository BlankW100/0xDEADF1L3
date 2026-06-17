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

| Format | What's valid inside |
|--------|---------------------|
| PDF    | xref table, Catalog/Pages/Page/Font objects, Info dictionary, `%%EOF` |
| DOCX   | Real ZIP: `[Content_Types].xml`, `_rels/.rels`, `word/document.xml`, `docProps/core.xml`, `docProps/app.xml` with word/page/line counts |
| PPTX   | Real ZIP: per-slide XML files, `ppt/presentation.xml` with slide IDs, app properties with slide count |
| XLSX   | Real ZIP: `xl/workbook.xml`, `xl/worksheets/sheet1.xml` with row dimension, app properties |
| PNG    | Valid `IHDR` chunk with correct CRC32 for specified dimensions, `IEND` at EOF |
| MP3    | ID3v2.3 header + MPEG1 Layer3 frame sync bytes (`0xFF 0xFB`) at 128 kbps |
| MP4    | Valid `ftyp` box + sized `mdat` box header |
| TXT/MD | UTF-8 BOM / YAML front-matter with metadata |

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

## Date workflow

```
> Date (optional, e.g. 2026-06-17):          ← type a date, or leave empty
  Date is empty. Choose an option:
  [1]  Use today's date (2026-06-17)
  [2]  No date
> Select option [2]:
```

When a date is set it is written into the format's native metadata field **and** applied to the file's OS modified-time (`os.utime`).

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

  Path        C:\...\report_q2.pptx
  Type        .pptx
  Slides      15 slides
  Size        3,932,160 bytes  (3.750 MB)
  Date        2026-05-30
  Title       Q2 Results
  Author      J. Smith

> Generate another file? [y/N]: n
```

## Disclaimer

For CTF challenges, bug testing, and security awareness training only.
