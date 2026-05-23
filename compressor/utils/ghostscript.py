"""
Ghostscript Wrapper
===================
Locates the Ghostscript executable and runs it as a subprocess with
compression-oriented arguments derived from a CompressionPreset.
"""

import shutil
import subprocess
import sys
from pathlib import Path
from typing import Optional

from compressor.presets import CompressionPreset
from compressor.utils.logger import get_logger

logger = get_logger("ghostscript")

# Common Windows installation paths for Ghostscript
_WIN_GS_SEARCH_PATHS = [
    r"C:\Program Files\gs",
    r"C:\Program Files (x86)\gs",
]

# Track whether we've already shown the install guide this session
_guide_shown: bool = False


def find_ghostscript() -> Optional[str]:
    """
    Locate the Ghostscript executable on the current system.

    Search order:
    1. PATH (via shutil.which)
    2. Common Windows installation directories

    Returns:
        Absolute path to the Ghostscript executable, or None if not found.
    """
    # Try PATH first (works on all platforms)
    for name in ("gswin64c", "gswin32c", "gs"):
        found = shutil.which(name)
        if found:
            logger.debug(f"Found Ghostscript via PATH: {found}")
            return found

    # Windows-specific deep search
    if sys.platform == "win32":
        for base in _WIN_GS_SEARCH_PATHS:
            base_path = Path(base)
            if not base_path.exists():
                continue
            # Enumerate versioned subdirectories (e.g. gs10.02.1)
            for version_dir in sorted(base_path.iterdir(), reverse=True):
                for exe_name in ("gswin64c.exe", "gswin32c.exe"):
                    candidate = version_dir / "bin" / exe_name
                    if candidate.is_file():
                        logger.debug(f"Found Ghostscript at: {candidate}")
                        return str(candidate)

    return None


def ghostscript_install_guide() -> str:
    """Return a formatted installation guide for Ghostscript on Windows."""
    return (
        "\n"
        "+-------------------------------------------------------------+\n"
        "|         GHOSTSCRIPT NOT FOUND -- INSTALL GUIDE              |\n"
        "+-------------------------------------------------------------+\n"
        "|                                                             |\n"
        "|  1. Download from: https://www.ghostscript.com/download/    |\n"
        "|     -> Choose: Ghostscript AGPL Release (Windows 64-bit)    |\n"
        "|                                                             |\n"
        "|  2. Run the installer and follow default prompts.           |\n"
        "|                                                             |\n"
        "|  3. Add to PATH (optional but recommended):                 |\n"
        r"|     C:\Program Files\gs\gs<version>\bin                     |" + "\n"
        "|                                                             |\n"
        "|  4. Restart your terminal / command prompt.                 |\n"
        "|                                                             |\n"
        "|  5. Verify: gswin64c --version                              |\n"
        "|                                                             |\n"
        "|  Alternatively use winget:                                  |\n"
        "|     winget install ArtifexSoftware.GhostScript              |\n"
        "|                                                             |\n"
        "+-------------------------------------------------------------+\n"
    )


def build_gs_command(
    gs_exe: str,
    input_path: Path,
    output_path: Path,
    preset: CompressionPreset,
    custom_dpi: Optional[int] = None,
    custom_quality: Optional[int] = None,
) -> list[str]:
    """
    Build the Ghostscript command-line arguments list.

    Args:
        gs_exe: Path to the Ghostscript executable.
        input_path: Source PDF file path.
        output_path: Destination PDF file path.
        preset: Compression preset containing all quality parameters.
        custom_dpi: Override the preset DPI if provided.
        custom_quality: Override the preset JPEG quality if provided.

    Returns:
        List of command-line tokens ready to pass to subprocess.
    """
    dpi = custom_dpi if custom_dpi is not None else preset.dpi
    quality = custom_quality if custom_quality is not None else preset.jpeg_quality

    cmd = [
        gs_exe,
        "-q",                          # Quiet mode — suppress banner
        "-dBATCH",                     # Exit after processing
        "-dNOPAUSE",                   # No prompt between pages
        "-dNOSAFER",                   # Allow file I/O
        "-dCompatibilityLevel=1.4",    # PDF 1.4 compatibility for broad support
        f"-sDEVICE=pdfwrite",
        f"-dPDFSETTINGS=/{preset.gs_quality}",

        # Image downsampling — Color
        f"-dColorImageDownsampleType=/Bicubic",
        f"-dColorImageResolution={dpi}",
        f"-dDownsampleColorImages={'true' if preset.gs_color_downsampling else 'false'}",
        f"-dColorImageDownsampleThreshold=1.0",

        # Image downsampling — Grayscale
        f"-dGrayImageDownsampleType=/Bicubic",
        f"-dGrayImageResolution={dpi}",
        f"-dDownsampleGrayImages={'true' if preset.gs_gray_downsampling else 'false'}",
        f"-dGrayImageDownsampleThreshold=1.0",

        # Image downsampling — Monochrome
        f"-dMonoImageDownsampleType=/Bicubic",
        f"-dMonoImageResolution={dpi}",
        f"-dDownsampleMonoImages={'true' if preset.gs_mono_downsampling else 'false'}",

        # JPEG encoding quality
        f"-dJPEGQ={quality}",

        # Font optimization
        "-dEmbedAllFonts=true",
        "-dSubsetFonts=true",
        "-dCompressFonts=true",

        # Object / stream compression
        "-dCompressPages=true",
        "-dOptimize=true",
        "-dFastWebView=true",  # Linearize for fast web view

        # Remove thumbnails and metadata
        "-dNoThumbs=true",
    ]

    # Grayscale conversion
    if preset.grayscale:
        cmd += [
            "-sColorConversionStrategy=Gray",
            "-dProcessColorModel=/DeviceGray",
        ]
    else:
        cmd += [
            "-sColorConversionStrategy=sRGB",
        ]

    # Remove all metadata
    if preset.remove_metadata:
        cmd += [
            "-dFastWebView=true",
        ]

    # Aggressive cleanup
    if preset.aggressive_cleanup:
        cmd += [
            "-dDetectDuplicateImages=true",
            "-dAutoFilterColorImages=false",
            "-sColorImageFilter=DCTEncode",
            "-dAutoFilterGrayImages=false",
            "-sGrayImageFilter=DCTEncode",
        ]

    # Output / input
    cmd += [
        f"-sOutputFile={output_path}",
        str(input_path),
    ]

    return cmd


def run_ghostscript(
    input_path: Path,
    output_path: Path,
    preset: CompressionPreset,
    custom_dpi: Optional[int] = None,
    custom_quality: Optional[int] = None,
) -> bool:
    """
    Execute Ghostscript compression.

    Args:
        input_path: Source PDF.
        output_path: Destination PDF.
        preset: Compression preset.
        custom_dpi: Optional DPI override.
        custom_quality: Optional JPEG quality override.

    Returns:
        True if Ghostscript completed successfully, False otherwise.

    Raises:
        FileNotFoundError: If Ghostscript is not installed on the system.
        RuntimeError: If Ghostscript returns a non-zero exit code.
    """
    gs_exe = find_ghostscript()
    if not gs_exe:
        global _guide_shown
        if not _guide_shown:
            print(ghostscript_install_guide())
            _guide_shown = True
        raise FileNotFoundError(
            "Ghostscript not found. Please install it and try again."
        )

    cmd = build_gs_command(gs_exe, input_path, output_path, preset, custom_dpi, custom_quality)
    logger.debug(f"Ghostscript command: {' '.join(cmd)}")

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=600,  # 10-minute timeout for large files
        )

        if result.returncode != 0:
            logger.error(f"Ghostscript stderr: {result.stderr}")
            raise RuntimeError(
                f"Ghostscript failed with exit code {result.returncode}:\n{result.stderr}"
            )

        logger.debug("Ghostscript completed successfully.")
        return True

    except subprocess.TimeoutExpired as exc:
        raise RuntimeError("Ghostscript timed out (> 10 minutes). File may be too large.") from exc
    except FileNotFoundError as exc:
        raise FileNotFoundError(f"Could not execute Ghostscript: {gs_exe}") from exc
