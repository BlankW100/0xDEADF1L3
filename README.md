# 0xDEADF1L3 — Corrupted File Generator

Generate dummy/corrupted files of various formats for testing, security challenges, or educational purposes.

## Features

- **Multiple file formats**: PDF, Markdown, TXT, PPTX, DOCX, XLSX, PNG, MP3, MP4
- **Customizable size**: Specify size in format-specific units (pages, lines, slides, rows, resolution, duration)
- **Optional metadata**: Add title, author, and description to generated files
- **Random payload**: Files contain proper format headers followed by random data
- **Progress tracking**: Visual progress bar during file generation
- **Windows UTF-8 support**: ANSI colors and UTF-8 output on Windows terminals

## Usage

```bash
python 0xDEADF1L3.py
```

The program will interactively prompt you for:
1. **Filename** (without extension)
2. **File type** (1-9 for available formats)
3. **Size** (in format-specific units)
4. **Metadata** (optional: title, author, description)

## Supported File Types

| Format | Size Unit | Default |
|--------|-----------|---------|
| PDF    | Pages     | 5       |
| Markdown | Lines   | 100     |
| TXT    | Lines     | 200     |
| PPTX   | Slides    | 10      |
| DOCX   | Pages     | 5       |
| XLSX   | Rows      | 500     |
| PNG    | Resolution| 1920x1080 |
| MP3    | Minutes   | 3       |
| MP4    | Minutes   | 5       |

## Example

```
> Filename (without extension): test
> Choose file type [1]: 1
> Number of pages [5]: 10
> Title: My PDF
> Author: Developer
> Description: Test file
```

This creates `test.pdf` with 10 pages of random data.
