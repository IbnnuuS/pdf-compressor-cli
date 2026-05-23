"""
CLI Progress Display
====================
Provides rich, colored CLI progress output for each compression stage
without external dependencies.
"""

import io
import sys
import time
from dataclasses import dataclass, field
from typing import Optional

# ── Fix Windows console encoding to UTF-8 so Unicode chars print correctly
if sys.platform == "win32":
    try:
        sys.stdout = io.TextIOWrapper(
            sys.stdout.buffer,
            encoding="utf-8",
            errors="replace",
            line_buffering=True,
        )
        sys.stderr = io.TextIOWrapper(
            sys.stderr.buffer,
            encoding="utf-8",
            errors="replace",
            line_buffering=True,
        )
    except (AttributeError, io.UnsupportedOperation):
        pass  # Already wrapped or no buffer (e.g., in PyInstaller bundle)

# ANSI codes
RESET = "\033[0m"
BOLD = "\033[1m"
DIM = "\033[2m"
RED = "\033[91m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
MAGENTA = "\033[95m"
CYAN = "\033[96m"
WHITE = "\033[97m"
GRAY = "\033[90m"

# Box drawing — ASCII safe versions
BOX_H = "-"
BOX_V = "|"
BOX_TL = "+"
BOX_TR = "+"
BOX_BL = "+"
BOX_BR = "+"
BOX_ML = "+"
BOX_MR = "+"

WIDTH = 60


def _line(char: str = BOX_H, left: str = BOX_ML, right: str = BOX_MR) -> str:
    return f"{left}{char * (WIDTH - 2)}{right}"


def _banner() -> None:
    """Print the application banner using ASCII art (safe on all terminals)."""
    print(f"\n{CYAN}{BOLD}")
    print(r"  ____  ____  _____")
    print(r"  |  _ \|  _ \|  ___|")
    print(r"  | |_) | | | | |_  ")
    print(r"  |  __/| |_| |  _| ")
    print(r"  |_|   |____/|_|   ")
    print(f"{RESET}{GRAY}  PDF Compressor v1.0 -- Professional Edition{RESET}")
    print(f"{GRAY}  ==========================================={RESET}\n")


def print_banner() -> None:
    """Display the application banner."""
    _banner()


def print_separator(title: str = "") -> None:
    """Print a section separator with optional title."""
    if title:
        pad = WIDTH - len(title) - 4
        left = pad // 2
        right = pad - left
        print(f"{GRAY}{BOX_H * left} {CYAN}{title}{GRAY} {BOX_H * right}{RESET}")
    else:
        print(f"{GRAY}{BOX_H * WIDTH}{RESET}")


def print_step(current: int, total: int, message: str) -> None:
    """
    Print a numbered progress step.

    Args:
        current: Current step number (1-based).
        total: Total number of steps.
        message: Step description.
    """
    step_str = f"{GRAY}[{CYAN}{current}{GRAY}/{CYAN}{total}{GRAY}]{RESET}"
    print(f"  {step_str} {WHITE}{message}{RESET}")


def print_success(message: str) -> None:
    """Print a success message."""
    print(f"  {GREEN}[OK]{RESET} {message}")


def print_warning(message: str) -> None:
    """Print a warning message."""
    print(f"  {YELLOW}[WARN]{RESET} {message}")


def print_error(message: str) -> None:
    """Print an error message."""
    print(f"  {RED}[ERR]{RESET} {RED}{message}{RESET}")


def print_info(message: str) -> None:
    """Print an info message."""
    print(f"  {CYAN}[i]{RESET} {message}")


def print_stats(
    original_bytes: int,
    compressed_bytes: int,
    elapsed_seconds: float,
    filename: str = "",
) -> None:
    """
    Print a formatted statistics block comparing original vs compressed sizes.

    Args:
        original_bytes: Size of the original file in bytes.
        compressed_bytes: Size of the compressed file in bytes.
        elapsed_seconds: Processing time in seconds.
        filename: Optional filename to display in the header.
    """
    from compressor.utils.file_utils import format_size, format_duration, reduction_percent

    reduction = reduction_percent(original_bytes, compressed_bytes)
    orig_str = format_size(original_bytes)
    comp_str = format_size(compressed_bytes)
    time_str = format_duration(elapsed_seconds)

    # Color reduction based on how much we saved
    if reduction >= 60:
        red_color = GREEN + BOLD
    elif reduction >= 30:
        red_color = CYAN
    elif reduction >= 10:
        red_color = YELLOW
    elif reduction < 0:
        red_color = RED  # File got bigger
    else:
        red_color = GRAY

    print()
    print_separator("RESULTS")
    if filename:
        print(f"  {GRAY}File      :{RESET} {WHITE}{filename}{RESET}")
    print(f"  {GRAY}Original  :{RESET} {WHITE}{orig_str:>12}{RESET}")
    print(f"  {GRAY}Compressed:{RESET} {WHITE}{comp_str:>12}{RESET}")
    print(f"  {GRAY}Reduction :{RESET} {red_color}{reduction:>11.2f}%{RESET}")
    print(f"  {GRAY}Time      :{RESET} {WHITE}{time_str:>12}{RESET}")
    print_separator()
    print()


def print_batch_summary(
    total: int,
    succeeded: int,
    failed: int,
    skipped: int,
    total_original: int,
    total_compressed: int,
    elapsed: float,
) -> None:
    """
    Print a summary table for batch compression results.

    Args:
        total: Total number of files attempted.
        succeeded: Number of files compressed successfully.
        failed: Number of files that encountered errors.
        skipped: Number of files skipped.
        total_original: Sum of original sizes in bytes.
        total_compressed: Sum of compressed sizes in bytes.
        elapsed: Total elapsed time in seconds.
    """
    from compressor.utils.file_utils import format_size, format_duration, reduction_percent

    reduction = reduction_percent(total_original, total_compressed)

    print()
    print_separator("BATCH SUMMARY")
    print(f"  {GRAY}Total files:{RESET}   {WHITE}{total}{RESET}")
    print(f"  {GREEN}[v] Success:{RESET}   {GREEN}{succeeded}{RESET}")
    if failed:
        print(f"  {RED}[x] Failed :{RESET}   {RED}{failed}{RESET}")
    if skipped:
        print(f"  {YELLOW}[-] Skipped:{RESET}   {YELLOW}{skipped}{RESET}")
    print(f"  {GRAY}---------------------------------{RESET}")
    print(f"  {GRAY}Original   :{RESET}   {WHITE}{format_size(total_original):>12}{RESET}")
    print(f"  {GRAY}Compressed :{RESET}   {WHITE}{format_size(total_compressed):>12}{RESET}")
    if reduction >= 0:
        print(f"  {GRAY}Saved      :{RESET}   {GREEN}{reduction:.2f}%{RESET}")
    else:
        print(f"  {GRAY}Change     :{RESET}   {RED}{reduction:.2f}%{RESET}")
    print(f"  {GRAY}Total Time :{RESET}   {WHITE}{format_duration(elapsed):>12}{RESET}")
    print_separator()
    print()


class ProgressBar:
    """
    Simple ASCII progress bar for batch operations.

    Example output:
        Processing [████████░░░░░░░░░░░░] 40% (2/5)
    """

    FILL = "#"
    EMPTY = "."
    BAR_WIDTH = 20

    def __init__(self, total: int, label: str = "Processing") -> None:
        self.total = total
        self.label = label
        self.current = 0

    def update(self, current: int, filename: str = "") -> None:
        """
        Render and print the current progress bar state.

        Args:
            current: Current item index (1-based).
            filename: Filename being processed.
        """
        self.current = current
        filled = int(self.BAR_WIDTH * current / max(self.total, 1))
        empty = self.BAR_WIDTH - filled
        bar = f"{CYAN}{self.FILL * filled}{GRAY}{self.EMPTY * empty}{RESET}"
        pct = int(100 * current / max(self.total, 1))
        name = f" {GRAY}- {filename[:30]}...{RESET}" if filename else ""
        line = f"\r  {GRAY}{self.label}{RESET} [{bar}] {CYAN}{pct:3d}%{RESET} ({current}/{self.total}){name}"
        sys.stdout.write(line)
        sys.stdout.flush()

    def done(self) -> None:
        """Finalize and move to the next line."""
        sys.stdout.write("\n")
        sys.stdout.flush()
