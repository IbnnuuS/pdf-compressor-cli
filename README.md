---
title: Mursal PDF Compressor
emoji: 📄
colorFrom: indigo
colorTo: blue
sdk: docker
app_port: 7860
pinned: false
---

# PDF Compressor CLI — Professional Edition

> **Reduce PDF file sizes dramatically** — compress scanned PDFs, image-heavy PDFs,
> and text documents using a highly optimized pipeline powered by Ghostscript, pikepdf,
> and Pillow.

---

## Features

| Feature | Details |
|---|---|
| **Optimized Pipeline** | Native Ghostscript downsampling + pikepdf chained for maximum safe reduction |
| **5 Compression Presets** | `low` / `medium` / `high` / `extreme` / `ultra` |
| **Batch Compression** | Compress entire folders recursively |
| **Scan/Image PDF Support** | True Bicubic DPI downsampling + JPEG recompression |
| **Pristine Quality** | Perfect handling of alpha transparency, masks, vector overlays, and color spaces |
| **Robust File Locking** | Gracefully handles files currently open in PDF viewers on Windows (no crashes) |
| **Custom DPI/Quality** | Override preset DPI and JPEG quality per-run |
| **Progress Display** | Realtime step-by-step CLI progress |
| **Statistics Output** | Before/after size, reduction %, processing time |
| **Auto Output Folder** | Output always goes to `output/` automatically |
| **Recursive Scan** | Discovers PDFs in nested subdirectories |
| **Overwrite Control** | `--overwrite` flag to replace existing outputs |
| **Error Handling** | Encrypted, corrupted, and missing files handled gracefully |
| **Logging** | Rotating file log at `compressor/logs/app.log` |
| **Buildable to EXE** | `build.bat` → single `pdf_compressor.exe` |

---

## Requirements

| Requirement | Version | Notes |
|---|---|---|
| Python | 3.11+ | Required |
| Ghostscript | Latest | **External tool** — essential for quality downsampling |
| pikepdf | 8.0+ | pip |
| PyMuPDF (fitz) | 1.24+ | pip (fallback engine) |
| Pillow | 10.0+ | pip |
| PyInstaller | 6.0+ | pip (build only) |

---

## Installation

### 1. Install Python

Download Python 3.11+ from [python.org](https://www.python.org/downloads/).

**During installation:**
- ✅ Check **"Add Python to PATH"**
- ✅ Check **"Install pip"**

Verify:
```cmd
python --version
```

---

### 2. Install Ghostscript

Ghostscript is the most important compression engine. **Without it, Stage 3 compression will be skipped.**

#### Option A: Direct Installer (Recommended)

1. Go to [https://www.ghostscript.com/download/](https://www.ghostscript.com/download/)
2. Download **Ghostscript AGPL Release (Windows 64-bit)**
3. Run the installer and follow the default prompts.
4. *Note: The application will automatically detect Ghostscript if installed to standard paths (`C:\Program Files\gs`)*.

#### Option B: Silent Command-line Install (Windows PowerShell Admin)

You can download and install it silently with a single command:
```powershell
$url = "https://github.com/ArtifexSoftware/ghostpdl-downloads/releases/download/gs10051/gs10051w64.exe"
Invoke-WebRequest -Uri $url -OutFile "$env:TEMP\gs_installer.exe" -UseBasicParsing
Start-Process -FilePath "$env:TEMP\gs_installer.exe" -ArgumentList "/S" -Wait
```

#### Verify:
```cmd
gswin64c --version
```

---

### 3. Install Python Dependencies

```cmd
pip install -r requirements.txt
```

Or install manually:
```cmd
pip install pikepdf PyMuPDF Pillow pyinstaller
```

Verify all libraries:
```cmd
python -c "import pikepdf, fitz, PIL; print('All libraries OK')"
```

---

## Quick Start

```cmd
# Compress a single PDF (medium preset)
python main.py compress document.pdf

# Compress with ultra preset (smallest file, grayscale)
python main.py compress document.pdf --preset ultra

# Compress with high preset and force overwrite
python main.py compress document.pdf --preset high --overwrite

# Compress an entire folder of PDFs
python main.py batch ./pdfs --preset extreme

# List available presets
python main.py presets
```

---

## Commands

### `compress`

Compress a single PDF file.

```
python main.py compress FILE [OPTIONS]
```

**Arguments:**

| Argument | Description |
|---|---|
| `FILE` | Path to the PDF file to compress |

**Options:**

| Option | Default | Description |
|---|---|---|
| `--preset PRESET` | `medium` | Compression preset: `low`, `medium`, `high`, `extreme`, `ultra` |
| `--output-dir DIR` | `./output` | Directory for the compressed output |
| `--output-name NAME` | auto | Custom output filename (without `.pdf`) |
| `--dpi N` | preset | Override target DPI (36–600) |
| `--quality N` | preset | Override JPEG quality (1–95) |
| `--overwrite` | off | Replace existing output file |
| `--verbose` / `-v` | off | Show debug-level details |

**Examples:**

```cmd
# Basic compression
python main.py compress report.pdf

# Ultra compression for upload
python main.py compress scan_100mb.pdf --preset ultra

# Custom DPI and quality
python main.py compress document.pdf --dpi 96 --quality 30

# Custom output filename
python main.py compress input.pdf --output-name compressed_v2

# Force overwrite
python main.py compress input.pdf --preset high --overwrite
```

**Output:**

```
  ____  ____  _____
  |  _ \|  _ \|  ___|
  | |_) | | | | |_  
  |  __/| |_| |  _| 
  |_|   |____/|_|   
  PDF Compressor v1.0 -- Professional Edition
  ===========================================

------ COMPRESSING: scan.pdf -------
  [i] Input  : C:\...\scan.pdf
  [i] Output : C:\...\output\scan_compressed.pdf
  [i] Preset : high
  [i] Size   : 221.63 MB

  [1/5] Validating PDF...
  [2/5] Recompressing images (PyMuPDF + Pillow)...
  [i]   Image recompression skipped (Using robust Ghostscript downsampling)
  [3/5] Running Ghostscript compression...
  [4/5] Optimizing PDF structure (pikepdf)...
  [5/5] Saving compressed PDF...
  [OK] Compression complete — 96.4% smaller

------------------------ RESULTS -------------------------
  File      : scan.pdf
  Original  :    221.63 MB
  Compressed:      7.94 MB
  Reduction :       96.42%
  Time      :     71.0 sec
------------------------------------------------------------
```

---

### `batch`

Compress all PDF files in a directory.

```
python main.py batch DIR [OPTIONS]
```

**Arguments:**

| Argument | Description |
|---|---|
| `DIR` | Directory containing PDF files to compress |

**Options:**

| Option | Default | Description |
|---|---|---|
| `--preset PRESET` | `medium` | Compression preset |
| `--output-dir DIR` | `./output` | Output directory |
| `--dpi N` | preset | Override DPI |
| `--quality N` | preset | Override JPEG quality |
| `--overwrite` | off | Overwrite existing outputs |
| `--no-recursive` | off | Do not scan subdirectories |

**Examples:**

```cmd
# Compress all PDFs in a folder
python main.py batch ./documents

# Extreme preset, flat scan (no subdirs)
python main.py batch ./uploads --preset extreme --no-recursive
```

---

### `presets`

List all available compression presets.

```
python main.py presets
```

---

## Compression Presets

| Preset | DPI | Quality | GS Setting | Grayscale | Use Case |
|---|---|---|---|---|---|
| `low` | 200 | 85 | prepress | No | Archive / quality-first (High fidelity) |
| `medium` | 150 | 72 | printer | No | General purpose (default) |
| `high` | 120 | 55 | ebook | No | Significant reduction (Standard Web upload) |
| `extreme` | 96 | 40 | screen | No | Strict upload size limits |
| `ultra` | 72 | 28 | screen | **Yes** | Smallest possible file (Grayscale) |

---

## How It Works

The application applies a **5-stage pipeline** to each PDF:

```
Input PDF
    │
    ▼
[Stage 1] Validation
    │  • Check file exists and is readable
    │  • Verify PDF magic bytes (%PDF-)
    │  • Detect encryption (pikepdf)
    │
    ▼
[Stage 2] Image Recompression (PyMuPDF + Pillow)
    │  • *Optional fallback stage*
    │  • Bypassed by default to prevent visual rendering artifacts/loss on complex slides.
    │
    ▼
[Stage 3] Ghostscript Compression
    │  • Apply PDFSETTINGS (screen/ebook/printer/prepress)
    │  • Downsample color, gray, mono images (Bicubic Resampling)
    │  • Optimize fonts (subset, compress)
    │  • Recompress content streams
    │  • Linearize for fast web view
    │  • Fully preserves image transparency, masks, and alpha overlays.
    │
    ▼
[Stage 4] Structural Optimization (pikepdf)
    │  • Strip XMP metadata and DocInfo
    │  • Remove embedded thumbnails
    │  • Garbage-collect unused objects
    │  • Recompress flate streams
    │  • Re-linearize output
    │
    ▼
[Stage 5] Output Validation & Save
       • Catch and resolve destination file-locking issues (saves as unique timestamped file)
       • Pick smallest valid intermediate from all stages
       • Verify output is smaller than input
       • Save to output/ directory
```

---


## Project Structure

```
pdfCompress/
│
├── compressor/                 # Main application package
│   ├── core/
│   │   ├── engine.py           # 5-stage compression pipeline orchestrator
│   │   ├── image_compressor.py # PyMuPDF + Pillow image recompression (Bypassed by default)
│   │   ├── optimizer.py        # pikepdf structural optimizer
│   │   └── result.py           # CompressionResult data class
│   │
│   ├── cli/
│   │   └── commands.py         # compress / batch / presets command handlers
│   │
│   ├── presets/
│   │   └── __init__.py         # Preset definitions (low/medium/high/extreme/ultra)
│   │
│   ├── utils/
│   │   ├── display.py          # CLI progress, stats, banner output
│   │   ├── file_utils.py       # Size formatting, path helpers, timer
│   │   ├── ghostscript.py      # GS auto-detection and subprocess wrapper
│   │   ├── logger.py           # Rotating file + colored console logging
│   │   └── validator.py        # PDF validation (encryption, corruption)
│   │
│   └── logs/
│       └── app.log             # Application log (auto-created, rotating 5MB×3)
│
├── output/                     # Compressed PDF output (auto-created)
│
├── main.py                     # CLI entry point (argparse)
├── requirements.txt            # Python dependencies
├── build.bat                   # Windows build script (PyInstaller)
├── .gitignore                  # Git ignore rules for uploading to GitHub
└── README.md                   # This file
```

---

## Troubleshooting

### ❌ `Ghostscript not found`

The tool will display an automatic installation guide. In short:
1. Download from [ghostscript.com](https://www.ghostscript.com/download/)
2. Install with default options
3. Optionally add `C:\Program Files\gs\gs<version>\bin` to PATH
4. Restart your terminal

Test: `gswin64c --version`

---

### ❌ File is locked / Permission denied (`PermissionError`)

**No crash occurs!** If you have the output PDF open in a PDF viewer (like Acrobat, Chrome, or Edge) while compressing again, the tool will gracefully intercept the write-lock and save your optimized file with a unique suffix (e.g., `_compressed_1779493850.pdf`) inside the `output/` directory so no progress is lost.

---

### ❌ Compressed file is same size or larger

This can happen with:
- PDFs that are already compressed (e.g., already run through Ghostscript)
- PDFs containing only text with embedded fonts that compress well already
- Very small PDFs (< 100 KB)

Try using `--preset ultra` for maximum reduction.

---

## Tips for Maximum Compression

1. **Use `--preset high`** for the best balance of visual clarity and maximum web upload savings (ideal for slide decks and resumes).
2. **Use `--preset ultra`** for the absolute smallest file (converts to grayscale).
3. **Scanned PDFs** compress the most — often 80%+ reduction.
4. **Use --dpi 72** for screen-only documents: `--preset extreme --dpi 72`
5. For **batch processing**, use `--overwrite` to replace previous outputs automatically.

---
