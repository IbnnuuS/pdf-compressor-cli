"""
Image Compressor (PyMuPDF + Pillow)
====================================
Re-compresses all raster images embedded in a PDF using PyMuPDF to extract
them and Pillow to re-encode them at the target quality and DPI.

This module is used as a *pre-processing* step before Ghostscript, producing
an intermediate PDF with already-compressed images that Ghostscript can then
further optimize structurally.
"""

import io
import tempfile
from pathlib import Path
from typing import Optional

from compressor.presets import CompressionPreset
from compressor.utils.logger import get_logger

logger = get_logger("image_compressor")

# Minimum image area (pixels) worth reprocessing
_MIN_IMAGE_AREA = 100 * 100  # 10000 px²


def _recompress_image(
    image_bytes: bytes,
    ext: str,
    jpeg_quality: int,
    dpi: int,
    grayscale: bool,
    target_dpi: int,
) -> Optional[bytes]:
    """
    Recompress a single image with Pillow at the given quality and DPI.

    Args:
        image_bytes: Raw image data (as stored in the PDF).
        ext: Source image format hint (e.g. 'png', 'jpeg', 'jp2').
        jpeg_quality: JPEG compression quality (1–95).
        dpi: Target resolution (used for resampling size calculation).
        grayscale: Convert image to grayscale before saving.
        target_dpi: Target DPI to resample to.

    Returns:
        Compressed JPEG bytes, or None if the image should be skipped.
    """
    try:
        from PIL import Image, ImageFilter  # type: ignore

        img = Image.open(io.BytesIO(image_bytes))

        # Skip tiny images — not worth recompressing
        if img.width * img.height < _MIN_IMAGE_AREA:
            return None

        # Convert to RGB/L for JPEG compatibility
        if grayscale:
            img = img.convert("L")
        elif img.mode in ("RGBA", "P", "CMYK", "LA"):
            img = img.convert("RGB")
        elif img.mode not in ("RGB", "L"):
            img = img.convert("RGB")

        # Resample if current DPI is known and higher than target
        current_dpi = img.info.get("dpi", (72, 72))
        if isinstance(current_dpi, (tuple, list)):
            src_dpi = max(current_dpi[0], 1)
        else:
            src_dpi = max(current_dpi, 1)

        if src_dpi > target_dpi:
            scale = target_dpi / src_dpi
            new_w = max(1, int(img.width * scale))
            new_h = max(1, int(img.height * scale))
            img = img.resize((new_w, new_h), Image.LANCZOS)

        # Save as JPEG
        buf = io.BytesIO()
        save_kwargs: dict = {
            "format": "JPEG",
            "quality": jpeg_quality,
            "optimize": True,
            "progressive": True,
        }
        if not grayscale:
            save_kwargs["subsampling"] = 2  # 4:2:0 chroma subsampling
        img.save(buf, **save_kwargs)
        return buf.getvalue()

    except Exception as exc:
        logger.debug(f"Could not recompress image ({ext}): {exc}")
        return None


def recompress_pdf_images(
    input_path: Path,
    output_path: Path,
    preset: CompressionPreset,
    custom_dpi: Optional[int] = None,
    custom_quality: Optional[int] = None,
    on_page_done: Optional[callable] = None,
) -> bool:
    """
    Extract and recompress all images in a PDF using PyMuPDF + Pillow.

    Iterates over each page and each image XObject, recompresses the image
    data, and replaces it in-place. The result is saved to output_path.

    Args:
        input_path: Source PDF.
        output_path: Destination PDF (intermediate, before Ghostscript).
        preset: Compression preset.
        custom_dpi: Override preset DPI.
        custom_quality: Override preset JPEG quality.
        on_page_done: Optional callback(page_num, total_pages) for progress.

    Returns:
        True if successful, False if PyMuPDF or Pillow are unavailable.
    """
    # Bypass PyMuPDF image recompression because manual update_stream on xrefs
    # changes the stream bytes to JPEG without updating the object's /Filter key
    # to /DCTDecode, which corrupts the images and causes rendering failures.
    # Ghostscript is far safer, faster, and perfectly handles transparency and colors.
    return False

