"""
CLI Commands
============
Implements the `compress` and `batch` sub-commands with full argument parsing,
progress display, error handling, and result reporting.
"""

import sys
import time
from pathlib import Path
from typing import Optional

from compressor.core.engine import CompressionEngine
from compressor.core.result import CompressionResult
from compressor.presets import list_presets
from compressor.utils.display import (
    ProgressBar,
    print_batch_summary,
    print_error,
    print_info,
    print_separator,
    print_stats,
    print_success,
    print_warning,
)
from compressor.utils.file_utils import (
    Timer,
    find_pdf_files,
    format_size,
    get_file_size,
)
from compressor.utils.logger import get_logger

# ANSI
RESET = "\033[0m"
BOLD = "\033[1m"
CYAN = "\033[96m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
GRAY = "\033[90m"
WHITE = "\033[97m"

logger = get_logger("commands")


# ═══════════════════════════════════════════════════════════════════════════
# compress command
# ═══════════════════════════════════════════════════════════════════════════


def cmd_compress(
    input_file: str,
    preset: str = "medium",
    output_dir: str = "output",
    output_name: Optional[str] = None,
    dpi: Optional[int] = None,
    quality: Optional[int] = None,
    overwrite: bool = False,
    verbose: bool = False,
) -> int:
    """
    Compress a single PDF file.

    Args:
        input_file: Path to the source PDF.
        preset: Compression preset name.
        output_dir: Directory for the output file.
        output_name: Optional custom stem for the output filename.
        dpi: Override DPI.
        quality: Override JPEG quality.
        overwrite: Overwrite existing output files.
        verbose: Enable verbose output.

    Returns:
        Exit code (0 = success, 1 = failure).
    """
    input_path = Path(input_file).resolve()

    # Pre-flight checks
    if not input_path.exists():
        print_error(f"File not found: {input_path}")
        return 1
    if not input_path.suffix.lower() == ".pdf":
        print_warning(f"File may not be a PDF: {input_path.name}")

    out_dir = Path(output_dir)

    # Display pre-compression info
    file_size = get_file_size(input_path)
    print_separator(f"COMPRESSING: {input_path.name}")
    print_info(f"Input  : {input_path}")
    print_info(f"Output : {out_dir / (output_name or input_path.stem + '_compressed')}.pdf")
    print_info(f"Preset : {CYAN}{preset}{RESET}")
    print_info(f"Size   : {format_size(file_size)}")
    if dpi:
        print_info(f"DPI    : {dpi}")
    if quality:
        print_info(f"Quality: {quality}")
    print()

    engine = CompressionEngine(
        output_dir=out_dir,
        overwrite=overwrite,
        verbose=verbose,
    )

    result = engine.compress(
        input_path=input_path,
        preset_name=preset,
        custom_dpi=dpi,
        custom_quality=quality,
        output_name=output_name,
    )

    # Show statistics
    if result.success and result.output_path:
        print_stats(
            original_bytes=result.original_size,
            compressed_bytes=result.compressed_size,
            elapsed_seconds=result.elapsed_seconds,
            filename=input_path.name,
        )
        print_info(f"Output saved to: {result.output_path}")
        logger.info(
            f"compress OK | {input_path.name} | "
            f"{format_size(result.original_size)} → {format_size(result.compressed_size)} | "
            f"{result.reduction_percent:.1f}% saved"
        )
        return 0
    else:
        print_error(f"Compression failed: {result.error_message}")
        logger.error(f"compress FAILED | {input_path.name} | {result.error_message}")
        return 1


# ═══════════════════════════════════════════════════════════════════════════
# batch command
# ═══════════════════════════════════════════════════════════════════════════


def cmd_batch(
    input_dir: str,
    preset: str = "medium",
    output_dir: str = "output",
    dpi: Optional[int] = None,
    quality: Optional[int] = None,
    overwrite: bool = False,
    recursive: bool = True,
    verbose: bool = False,
) -> int:
    """
    Compress all PDF files in a directory (optionally recursive).

    Args:
        input_dir: Directory containing PDF files to process.
        preset: Compression preset name.
        output_dir: Directory for compressed output files.
        dpi: Override DPI.
        quality: Override JPEG quality.
        overwrite: Overwrite existing output files.
        recursive: Search subdirectories recursively.
        verbose: Enable verbose output.

    Returns:
        Exit code (0 = all succeeded, 1 = some/all failed).
    """
    source_dir = Path(input_dir).resolve()
    if not source_dir.exists():
        print_error(f"Directory not found: {source_dir}")
        return 1
    if not source_dir.is_dir():
        print_error(f"Not a directory: {source_dir}")
        return 1

    # Collect all PDF files
    pdf_files = list(find_pdf_files(source_dir, recursive=recursive))
    total = len(pdf_files)

    if total == 0:
        print_warning(f"No PDF files found in: {source_dir}")
        return 0

    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    print_separator(f"BATCH COMPRESSION")
    print_info(f"Source   : {source_dir}")
    print_info(f"Output   : {out_dir}")
    print_info(f"Preset   : {CYAN}{preset}{RESET}")
    print_info(f"Files    : {total}")
    print_info(f"Recursive: {'Yes' if recursive else 'No'}")
    print()

    engine = CompressionEngine(
        output_dir=out_dir,
        overwrite=overwrite,
        verbose=verbose,
    )

    results: list[CompressionResult] = []
    progress = ProgressBar(total=total, label="Batch")
    batch_timer = Timer()
    batch_timer.start()

    for idx, pdf_path in enumerate(pdf_files, start=1):
        progress.update(idx, pdf_path.name)

        # For batch, preserve relative folder structure in output
        try:
            rel = pdf_path.relative_to(source_dir)
            item_out_dir = out_dir / rel.parent
        except ValueError:
            item_out_dir = out_dir

        item_engine = CompressionEngine(
            output_dir=item_out_dir,
            overwrite=overwrite,
            verbose=verbose,
        )

        try:
            result = item_engine.compress(
                input_path=pdf_path,
                preset_name=preset,
                custom_dpi=dpi,
                custom_quality=quality,
            )
        except Exception as exc:
            logger.error(f"Unhandled exception on {pdf_path.name}: {exc}")
            result = CompressionResult(
                input_path=pdf_path,
                output_path=None,
                original_size=get_file_size(pdf_path),
                compressed_size=0,
                elapsed_seconds=0,
                preset_name=preset,
                success=False,
                error_message=str(exc),
            )

        results.append(result)

    progress.done()
    batch_elapsed = batch_timer.stop()

    # ── Batch results summary ──────────────────────────────────────────────
    succeeded = [r for r in results if r.success]
    failed = [r for r in results if not r.success]
    skipped: list[CompressionResult] = []  # Future: skip logic

    total_original = sum(r.original_size for r in results)
    total_compressed = sum(r.compressed_size for r in succeeded)
    # For failed files, add original size as-is (no compression)
    total_compressed += sum(r.original_size for r in failed)

    print_batch_summary(
        total=total,
        succeeded=len(succeeded),
        failed=len(failed),
        skipped=len(skipped),
        total_original=total_original,
        total_compressed=total_compressed,
        elapsed=batch_elapsed,
    )

    # ── Per-file detail table ──────────────────────────────────────────────
    if len(results) <= 20:
        _print_batch_table(results)

    # ── Failed files list ─────────────────────────────────────────────────
    if failed:
        print_separator("FAILED FILES")
        for r in failed:
            print_error(f"{r.input_path.name}: {r.error_message}")
        print()

    logger.info(
        f"Batch complete | {total} files | "
        f"{len(succeeded)} OK | {len(failed)} failed | "
        f"{format_size(total_original)} → {format_size(total_compressed)} | "
        f"{batch_elapsed:.1f}s"
    )

    return 0 if len(failed) == 0 else 1


def _print_batch_table(results: list[CompressionResult]) -> None:
    """Print a compact table showing each file's compression results."""
    print_separator("PER-FILE RESULTS")
    header = (
        f"  {'FILE':<35} {'ORIG':>10} {'COMP':>10} {'SAVED':>8}  STATUS"
    )
    print(f"{GRAY}{header}{RESET}")
    print(f"  {GRAY}{'':->35} {'':->10} {'':->10} {'':->8}  {'':->8}{RESET}")

    for r in results:
        name = r.input_path.name[:34]
        orig = format_size(r.original_size)
        if r.success and r.compressed_size > 0:
            comp = format_size(r.compressed_size)
            saved = f"{r.reduction_percent:+.1f}%"
            color = GREEN if r.reduction_percent > 0 else YELLOW
            status = f"{GREEN}OK{RESET}"
        else:
            comp = "-"
            saved = "-"
            color = RED
            status = f"{RED}FAIL{RESET}"

        print(
            f"  {WHITE}{name:<35}{RESET} "
            f"{GRAY}{orig:>10}{RESET} "
            f"{GRAY}{comp:>10}{RESET} "
            f"{color}{saved:>8}{RESET}  {status}"
        )
    print()


# ═══════════════════════════════════════════════════════════════════════════
# presets command
# ═══════════════════════════════════════════════════════════════════════════


def cmd_presets() -> int:
    """Display all available compression presets and their settings."""
    presets = list_presets()

    print_separator("AVAILABLE PRESETS")
    for p in presets:
        star = f"{CYAN}*{RESET}" if p.name == "medium" else " "
        print(
            f"  {star} {BOLD}{CYAN}{p.name:<10}{RESET}"
            f"  {GRAY}DPI:{RESET}{WHITE}{p.dpi:<5}{RESET}"
            f"  {GRAY}Quality:{RESET}{WHITE}{p.jpeg_quality:<5}{RESET}"
            f"  {GRAY}GS:{RESET}{WHITE}{p.gs_quality:<10}{RESET}"
            f"  {GRAY}{p.description}{RESET}"
        )
    print()
    print_info("Usage:  python main.py compress file.pdf --preset <name>")
    print()
    return 0
