#!/usr/bin/env python3
"""
PDF Compressor CLI — Professional Edition
==========================================
Entry point for the PDF Compressor command-line interface.

Supported commands:
  compress   Compress a single PDF file
  batch      Compress all PDFs in a folder
  presets    List all available compression presets

Usage examples:
  python main.py compress input.pdf
  python main.py compress input.pdf --preset ultra
  python main.py compress input.pdf --dpi 96 --quality 30
  python main.py compress input.pdf --preset high --output-name report_v2
  python main.py batch ./pdfs --preset extreme
  python main.py batch ./pdfs --recursive --overwrite
  python main.py presets

Run `python main.py --help` or `python main.py <command> --help` for details.
"""

import argparse
import os
import sys
from pathlib import Path

# ── Ensure the project root is on sys.path when run directly ─────────────
_PROJECT_ROOT = Path(__file__).resolve().parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from compressor.cli.commands import cmd_batch, cmd_compress, cmd_presets
from compressor.utils.display import print_banner
from compressor.utils.logger import setup_logging

# ── Paths ────────────────────────────────────────────────────────────────
DEFAULT_OUTPUT_DIR = str(_PROJECT_ROOT / "output")
DEFAULT_LOG_DIR = _PROJECT_ROOT / "compressor" / "logs"


# ══════════════════════════════════════════════════════════════════════════
# Argument Parser
# ══════════════════════════════════════════════════════════════════════════


def build_parser() -> argparse.ArgumentParser:
    """
    Build and return the argument parser for the CLI.

    Returns:
        Configured ArgumentParser with compress, batch, and presets sub-commands.
    """
    parser = argparse.ArgumentParser(
        prog="pdf-compressor",
        description=(
            "Professional PDF Compressor — Reduce PDF file sizes using\n"
            "Ghostscript, PyMuPDF, pikepdf, and Pillow.\n\n"
            "Examples:\n"
            "  python main.py compress report.pdf --preset ultra\n"
            "  python main.py batch ./documents --preset high\n"
            "  python main.py presets"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        default=False,
        help="Enable verbose / debug output",
    )
    parser.add_argument(
        "--log-dir",
        default=str(DEFAULT_LOG_DIR),
        metavar="DIR",
        help=f"Directory for log files (default: {DEFAULT_LOG_DIR})",
    )
    parser.add_argument(
        "--no-banner",
        action="store_true",
        default=False,
        help="Suppress the startup banner",
    )

    subparsers = parser.add_subparsers(
        dest="command",
        metavar="COMMAND",
        help="Available commands",
    )

    # ── compress ──────────────────────────────────────────────────────────
    compress_parser = subparsers.add_parser(
        "compress",
        help="Compress a single PDF file",
        description=(
            "Compress a single PDF using the selected preset.\n"
            "The output is automatically placed in the output/ directory."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    compress_parser.add_argument(
        "input",
        metavar="FILE",
        help="Path to the PDF file to compress",
    )
    compress_parser.add_argument(
        "--preset", "-p",
        default="medium",
        choices=["low", "medium", "high", "extreme", "ultra"],
        metavar="PRESET",
        help="Compression preset: low | medium | high | extreme | ultra (default: medium)",
    )
    compress_parser.add_argument(
        "--output-dir", "-o",
        default=DEFAULT_OUTPUT_DIR,
        metavar="DIR",
        help=f"Output directory (default: {DEFAULT_OUTPUT_DIR})",
    )
    compress_parser.add_argument(
        "--output-name", "-n",
        default=None,
        metavar="NAME",
        help="Custom output filename stem (without .pdf extension)",
    )
    compress_parser.add_argument(
        "--dpi",
        type=int,
        default=None,
        metavar="N",
        help="Override preset DPI (e.g. 96, 120, 150)",
    )
    compress_parser.add_argument(
        "--quality",
        type=int,
        default=None,
        metavar="N",
        help="Override JPEG quality (1–95; lower = smaller file)",
    )
    compress_parser.add_argument(
        "--overwrite",
        action="store_true",
        default=False,
        help="Overwrite output file if it already exists",
    )

    # ── batch ─────────────────────────────────────────────────────────────
    batch_parser = subparsers.add_parser(
        "batch",
        help="Compress all PDFs in a directory",
        description=(
            "Compress all PDF files found in a directory.\n"
            "Subdirectory structure is preserved in the output directory."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    batch_parser.add_argument(
        "input_dir",
        metavar="DIR",
        help="Directory containing PDF files",
    )
    batch_parser.add_argument(
        "--preset", "-p",
        default="medium",
        choices=["low", "medium", "high", "extreme", "ultra"],
        metavar="PRESET",
        help="Compression preset: low | medium | high | extreme | ultra (default: medium)",
    )
    batch_parser.add_argument(
        "--output-dir", "-o",
        default=DEFAULT_OUTPUT_DIR,
        metavar="DIR",
        help=f"Output directory (default: {DEFAULT_OUTPUT_DIR})",
    )
    batch_parser.add_argument(
        "--dpi",
        type=int,
        default=None,
        metavar="N",
        help="Override preset DPI",
    )
    batch_parser.add_argument(
        "--quality",
        type=int,
        default=None,
        metavar="N",
        help="Override JPEG quality (1–95)",
    )
    batch_parser.add_argument(
        "--overwrite",
        action="store_true",
        default=False,
        help="Overwrite existing output files",
    )
    batch_parser.add_argument(
        "--no-recursive",
        action="store_true",
        default=False,
        help="Do not scan subdirectories",
    )

    # ── presets ───────────────────────────────────────────────────────────
    subparsers.add_parser(
        "presets",
        help="List all available compression presets",
        description="Display all available presets with their settings.",
    )

    return parser


# ══════════════════════════════════════════════════════════════════════════
# Entry Point
# ══════════════════════════════════════════════════════════════════════════


def main() -> int:
    """
    Parse CLI arguments and dispatch to the appropriate command.

    Returns:
        Shell exit code (0 = success, non-zero = failure).
    """
    # Enable ANSI escape codes on Windows
    if sys.platform == "win32":
        os.system("")  # Trick to enable VT100 sequences on older Windows terminals

    parser = build_parser()
    args = parser.parse_args()

    # Setup logging
    log_dir = Path(args.log_dir)
    setup_logging(log_dir=log_dir, verbose=args.verbose)

    # Banner
    if not args.no_banner:
        print_banner()

    # Dispatch
    if args.command == "compress":
        # Validate DPI and quality ranges
        if args.dpi is not None and not (36 <= args.dpi <= 600):
            print(f"Error: --dpi must be between 36 and 600 (got {args.dpi})", file=sys.stderr)
            return 1
        if args.quality is not None and not (1 <= args.quality <= 95):
            print(f"Error: --quality must be between 1 and 95 (got {args.quality})", file=sys.stderr)
            return 1

        return cmd_compress(
            input_file=args.input,
            preset=args.preset,
            output_dir=args.output_dir,
            output_name=args.output_name,
            dpi=args.dpi,
            quality=args.quality,
            overwrite=args.overwrite,
            verbose=args.verbose,
        )

    elif args.command == "batch":
        if args.dpi is not None and not (36 <= args.dpi <= 600):
            print(f"Error: --dpi must be between 36 and 600 (got {args.dpi})", file=sys.stderr)
            return 1
        if args.quality is not None and not (1 <= args.quality <= 95):
            print(f"Error: --quality must be between 1 and 95 (got {args.quality})", file=sys.stderr)
            return 1

        return cmd_batch(
            input_dir=args.input_dir,
            preset=args.preset,
            output_dir=args.output_dir,
            dpi=args.dpi,
            quality=args.quality,
            overwrite=args.overwrite,
            recursive=not args.no_recursive,
            verbose=args.verbose,
        )

    elif args.command == "presets":
        return cmd_presets()

    else:
        parser.print_help()
        return 0


if __name__ == "__main__":
    sys.exit(main())
