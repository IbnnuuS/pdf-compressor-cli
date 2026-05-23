"""
PDF Optimizer (pikepdf)
=======================
Post-processing step that uses pikepdf to perform structural PDF optimizations
after Ghostscript has already compressed the content:

- Remove metadata (XMP, DocInfo)
- Remove embedded thumbnails
- Remove unused objects
- Linearize (fast web view)
- Recompress content streams
"""

from pathlib import Path
from typing import Optional

from compressor.presets import CompressionPreset
from compressor.utils.logger import get_logger

logger = get_logger("optimizer")


def optimize_with_pikepdf(
    input_path: Path,
    output_path: Path,
    preset: CompressionPreset,
) -> bool:
    """
    Apply structural optimizations to a PDF using pikepdf.

    Operations performed (based on preset flags):
    - Strip XMP metadata and document info dictionary
    - Remove embedded thumbnail images (/Thumb entries)
    - Remove unused/orphaned objects (garbage collection)
    - Recompress streams with zlib
    - Linearize for fast web viewing

    Args:
        input_path: Source PDF (typically Ghostscript output).
        output_path: Optimized output PDF.
        preset: Compression preset controlling which optimizations to apply.

    Returns:
        True if optimization succeeded, False if pikepdf is not available
        or an error occurred.
    """
    try:
        import pikepdf  # type: ignore
    except ImportError:
        logger.warning("pikepdf not installed; skipping structural optimization stage.")
        return False

    logger.debug(f"Opening PDF for structural optimization: {input_path}")

    try:
        pdf = pikepdf.open(input_path, allow_overwriting_input=False)
    except pikepdf.PasswordError as exc:
        logger.error(f"Cannot open encrypted PDF: {exc}")
        return False
    except pikepdf.PdfError as exc:
        logger.error(f"Cannot open PDF (possibly corrupted): {exc}")
        return False

    # ── Remove metadata ────────────────────────────────────────────────────
    if preset.remove_metadata:
        try:
            with pdf.open_metadata(set_pikepdf_as_editor=False) as meta:
                # Clear all XMP namespaces
                for key in list(meta.keys()):
                    del meta[key]
        except Exception as exc:
            logger.debug(f"Could not clear XMP metadata: {exc}")

        # Clear the traditional DocInfo dictionary
        try:
            if "/Info" in pdf.trailer:
                info = pdf.trailer["/Info"]
                # Remove all entries from the info dict
                for key in list(info.keys()):
                    del info[key]
        except Exception as exc:
            logger.debug(f"Could not clear DocInfo: {exc}")

    # ── Remove embedded thumbnails ─────────────────────────────────────────
    if preset.remove_thumbnails:
        for page in pdf.pages:
            try:
                if "/Thumb" in page:
                    del page["/Thumb"]
            except Exception:
                pass

    # ── Remove Article Beads and other non-essential structures ───────────
    if preset.aggressive_cleanup:
        try:
            if "/Threads" in pdf.root:
                del pdf.root["/Threads"]
        except Exception:
            pass
        try:
            if "/AcroForm" not in pdf.root:  # Don't remove if there's a form
                if "/Names" in pdf.root:
                    # Keep names but remove JavaScript
                    names = pdf.root["/Names"]
                    if "/JavaScript" in names:
                        del names["/JavaScript"]
        except Exception:
            pass

    # ── Save with optimization flags ───────────────────────────────────────
    try:
        save_kwargs = {
            "object_stream_mode": pikepdf.ObjectStreamMode.generate,
            "compress_streams": True,
            "recompress_flate": True,
            "linearize": preset.linearize,
        }
        pdf.save(str(output_path), **save_kwargs)
        pdf.close()
        logger.debug(f"pikepdf optimization saved to: {output_path}")
        return True

    except Exception as exc:
        logger.error(f"pikepdf save failed: {exc}")
        pdf.close()
        return False
