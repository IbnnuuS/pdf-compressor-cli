"""
PDF Compression Engine
======================
Orchestrates the multi-stage compression pipeline:

    Stage 1 — Validation
        Verify the PDF is readable, not encrypted, and structurally valid.

    Stage 2 — Image Recompression  (PyMuPDF + Pillow)
        Extract all raster images, downscale to target DPI, re-encode as JPEG
        at target quality, and replace them in the document.

    Stage 3 — Ghostscript Compression
        Run Ghostscript with PDFSETTINGS and downsampling flags for aggressive
        content-stream and font optimization.

    Stage 4 — Structural Optimization  (pikepdf)
        Strip metadata, remove thumbnails, garbage-collect unused objects,
        recompress streams, and linearize.

    Stage 5 — Output Validation
        Confirm the output is a valid PDF and is actually smaller.
        If the compressed file is larger (shouldn't happen in practice for
        typical PDFs), fall back to copying the smallest intermediate.

Each stage is optional and gracefully degraded if the required library is
not installed. At minimum, Ghostscript alone provides solid compression.
"""

import shutil
import tempfile
from pathlib import Path
from typing import Callable, Optional

from compressor.core.image_compressor import recompress_pdf_images
from compressor.core.optimizer import optimize_with_pikepdf
from compressor.core.result import CompressionResult
from compressor.presets import CompressionPreset, get_preset
from compressor.utils.display import (
    print_error,
    print_info,
    print_step,
    print_success,
    print_warning,
)
from compressor.utils.file_utils import Timer, get_file_size, get_output_path
from compressor.utils.ghostscript import run_ghostscript
from compressor.utils.logger import get_logger
from compressor.utils.validator import (
    CorruptedPDFError,
    EncryptedPDFError,
    validate_pdf,
)

logger = get_logger("engine")

# Total number of pipeline stages (used for [n/N] display)
_TOTAL_STAGES = 5


class CompressionEngine:
    """
    Orchestrates the full PDF compression pipeline.

    Usage::

        engine = CompressionEngine(output_dir=Path("output"))
        result = engine.compress(
            input_path=Path("document.pdf"),
            preset_name="high",
            custom_dpi=120,
            custom_quality=55,
        )
        if result.success:
            print(f"Saved {result.reduction_percent:.1f}%")
    """

    def __init__(
        self,
        output_dir: Path,
        overwrite: bool = False,
        verbose: bool = False,
    ) -> None:
        """
        Initialize the compression engine.

        Args:
            output_dir: Directory where compressed PDFs will be written.
            overwrite: If True, overwrite existing output files.
            verbose: If True, show debug-level stage details.
        """
        self.output_dir = output_dir
        self.overwrite = overwrite
        self.verbose = verbose
        self.output_dir.mkdir(parents=True, exist_ok=True)

    # ──────────────────────────────────────────────────────────────────────
    # Public API
    # ──────────────────────────────────────────────────────────────────────

    def compress(
        self,
        input_path: Path,
        preset_name: str = "medium",
        custom_dpi: Optional[int] = None,
        custom_quality: Optional[int] = None,
        output_name: Optional[str] = None,
    ) -> CompressionResult:
        """
        Compress a single PDF file through the full pipeline.

        Args:
            input_path: Source PDF to compress.
            preset_name: Name of the compression preset to apply.
            custom_dpi: Override the preset's target DPI.
            custom_quality: Override the preset's JPEG quality.
            output_name: Custom output filename stem (without extension).

        Returns:
            A :class:`CompressionResult` describing the outcome.
        """
        timer = Timer()
        timer.start()

        stages_used: list[str] = []
        original_size = get_file_size(input_path)

        # Resolve preset
        try:
            preset = get_preset(preset_name)
        except ValueError as exc:
            return self._failure_result(
                input_path, original_size, timer, str(exc), stages_used
            )

        # Determine output path
        output_path = get_output_path(
            input_path, self.output_dir, custom_name=output_name
        )

        # Guard against overwriting without permission
        if output_path.exists() and not self.overwrite:
            print_warning(
                f"Output already exists: {output_path.name} (use --overwrite to replace)"
            )
            return self._failure_result(
                input_path,
                original_size,
                timer,
                f"Output file already exists: {output_path}",
                stages_used,
            )

        logger.info(f"Starting compression: {input_path.name} → {output_path.name}")
        logger.info(f"Preset: {preset_name} | DPI: {custom_dpi or preset.dpi} | Quality: {custom_quality or preset.jpeg_quality}")

        with tempfile.TemporaryDirectory(prefix="pdfcomp_") as tmp_dir:
            tmp = Path(tmp_dir)

            # ── Stage 1: Validate ─────────────────────────────────────────
            print_step(1, _TOTAL_STAGES, "Validating PDF...")
            try:
                validate_pdf(input_path)
                stages_used.append("validate")
            except EncryptedPDFError as exc:
                print_error(str(exc))
                return self._failure_result(
                    input_path, original_size, timer, str(exc), stages_used
                )
            except CorruptedPDFError as exc:
                print_error(str(exc))
                return self._failure_result(
                    input_path, original_size, timer, str(exc), stages_used
                )
            except (FileNotFoundError, PermissionError) as exc:
                print_error(str(exc))
                return self._failure_result(
                    input_path, original_size, timer, str(exc), stages_used
                )

            # ── Stage 2: Image recompression (PyMuPDF + Pillow) ──────────
            print_step(2, _TOTAL_STAGES, "Recompressing images (PyMuPDF + Pillow)...")
            stage2_input = input_path
            stage2_output = tmp / "stage2_images.pdf"

            try:
                ok = recompress_pdf_images(
                    input_path=stage2_input,
                    output_path=stage2_output,
                    preset=preset,
                    custom_dpi=custom_dpi,
                    custom_quality=custom_quality,
                )
                if ok and stage2_output.exists():
                    stages_used.append("image_recompress")
                    logger.debug(f"Stage 2 output: {get_file_size(stage2_output):,} bytes")
                else:
                    # Fall through to Ghostscript with original
                    stage2_output = stage2_input
                    print_info("  Image recompression skipped (PyMuPDF/Pillow unavailable)")
            except Exception as exc:
                logger.warning(f"Stage 2 failed, continuing: {exc}")
                stage2_output = stage2_input

            # ── Stage 3: Ghostscript compression ─────────────────────────
            print_step(3, _TOTAL_STAGES, "Running Ghostscript compression...")
            stage3_output = tmp / "stage3_gs.pdf"

            try:
                run_ghostscript(
                    input_path=stage2_output,
                    output_path=stage3_output,
                    preset=preset,
                    custom_dpi=custom_dpi,
                    custom_quality=custom_quality,
                )
                stages_used.append("ghostscript")
                logger.debug(f"Stage 3 output: {get_file_size(stage3_output):,} bytes")
            except FileNotFoundError as exc:
                # Ghostscript not installed
                print_warning("Ghostscript not found — continuing without it.")
                print_warning("Install GS for best results: https://www.ghostscript.com/")
                logger.info(f"Ghostscript not installed: {exc}")
                stage3_output = stage2_output  # Fall back to stage 2
            except RuntimeError as exc:
                print_warning(f"Ghostscript error: {exc}")
                logger.warning(f"Ghostscript failed: {exc}")
                stage3_output = stage2_output  # Fall back

            # ── Stage 4: Structural optimization (pikepdf) ────────────────
            print_step(4, _TOTAL_STAGES, "Optimizing PDF structure (pikepdf)...")
            stage4_output = tmp / "stage4_pikepdf.pdf"

            try:
                # Only run if we have a valid stage3 output
                source_for_pikepdf = stage3_output if stage3_output.exists() else stage2_output
                ok = optimize_with_pikepdf(
                    input_path=source_for_pikepdf,
                    output_path=stage4_output,
                    preset=preset,
                )
                if ok and stage4_output.exists():
                    stages_used.append("pikepdf")
                    logger.debug(f"Stage 4 output: {get_file_size(stage4_output):,} bytes")
                else:
                    stage4_output = source_for_pikepdf
                    print_info("  Structural optimization skipped (pikepdf unavailable)")
            except Exception as exc:
                logger.warning(f"Stage 4 failed, continuing: {exc}")
                source_for_pikepdf = stage3_output if stage3_output.exists() else stage2_output
                stage4_output = source_for_pikepdf

            # ── Stage 5: Save output ──────────────────────────────────────
            print_step(5, _TOTAL_STAGES, "Saving compressed PDF...")

            # Pick the smallest valid intermediate
            best_path = self._pick_best_output(
                original=input_path,
                candidates=[stage4_output, stage3_output, stage2_output],
            )

            compressed_size = get_file_size(best_path)

            try:
                if compressed_size == 0:
                    # All stages failed — copy original
                    shutil.copy2(input_path, output_path)
                    compressed_size = original_size
                    print_warning("All compression stages failed; original file copied.")
                else:
                    shutil.copy2(best_path, output_path)
            except PermissionError:
                # File is locked! Save to a timestamped backup name instead
                import time
                timestamp = int(time.time())
                backup_path = output_path.with_name(f"{output_path.stem}_{timestamp}{output_path.suffix}")
                print_warning(
                    f"\n[!] Warning: The destination file is locked by another process (e.g., opened in a PDF viewer).\n"
                    f"    Saving the output to a new file instead:\n"
                    f"    -> {backup_path.name}"
                )
                try:
                    if compressed_size == 0:
                        shutil.copy2(input_path, backup_path)
                    else:
                        shutil.copy2(best_path, backup_path)
                    output_path = backup_path
                except Exception as inner_exc:
                    return self._failure_result(
                        input_path, original_size, timer,
                        f"Permission denied on destination and backup path creation failed: {inner_exc}", stages_used
                    )

        elapsed = timer.stop()

        if compressed_size < original_size:
            reduction = ((original_size - compressed_size) / original_size) * 100
            print_success(f"Compression complete — {reduction:.1f}% smaller")
        elif compressed_size == original_size:
            print_warning("File size unchanged.")
        else:
            print_warning("Compressed file is larger than original (original copied).")
            # In this edge case, copy the original instead
            try:
                shutil.copy2(input_path, output_path)
            except PermissionError:
                import time
                timestamp = int(time.time())
                backup_path = output_path.with_name(f"{output_path.stem}_original_{timestamp}{output_path.suffix}")
                print_warning(
                    f"\n[!] Warning: Destination locked. Saving fallback original to:\n"
                    f"    -> {backup_path.name}"
                )
                try:
                    shutil.copy2(input_path, backup_path)
                    output_path = backup_path
                except Exception:
                    pass
            compressed_size = original_size

        logger.info(
            f"Result: {input_path.name} | "
            f"Original={original_size:,}B | "
            f"Compressed={compressed_size:,}B | "
            f"Reduction={((original_size - compressed_size)/max(original_size,1)*100):.1f}% | "
            f"Time={elapsed:.1f}s | "
            f"Stages={stages_used}"
        )

        return CompressionResult(
            input_path=input_path,
            output_path=output_path,
            original_size=original_size,
            compressed_size=compressed_size,
            elapsed_seconds=elapsed,
            preset_name=preset_name,
            success=True,
            stages_used=stages_used,
        )

    # ──────────────────────────────────────────────────────────────────────
    # Private helpers
    # ──────────────────────────────────────────────────────────────────────

    @staticmethod
    def _pick_best_output(original: Path, candidates: list[Path]) -> Path:
        """
        Return the path with the smallest valid (non-zero) file size among
        the candidates, falling back to the original if none are valid.

        Args:
            original: Original input path (used as fallback).
            candidates: List of output paths from each pipeline stage.

        Returns:
            Path to the best (smallest) valid output.
        """
        best: Optional[Path] = None
        best_size: int = get_file_size(original)  # Start with original as baseline

        for candidate in candidates:
            if not candidate.exists():
                continue
            size = get_file_size(candidate)
            if size > 0 and size <= best_size:
                best = candidate
                best_size = size

        return best if best is not None else original

    @staticmethod
    def _failure_result(
        input_path: Path,
        original_size: int,
        timer: Timer,
        error_msg: str,
        stages_used: list[str],
    ) -> CompressionResult:
        """Construct a failed CompressionResult."""
        return CompressionResult(
            input_path=input_path,
            output_path=None,
            original_size=original_size,
            compressed_size=0,
            elapsed_seconds=timer.elapsed,
            preset_name="unknown",
            success=False,
            error_message=error_msg,
            stages_used=stages_used,
        )
