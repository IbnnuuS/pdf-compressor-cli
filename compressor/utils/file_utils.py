"""
File Utilities
==============
Helper functions for file size formatting, path handling, and I/O validation.
"""

import os
import shutil
import time
from pathlib import Path
from typing import Generator


def format_size(size_bytes: int) -> str:
    """
    Convert raw byte count to human-readable string (KB / MB / GB).

    Args:
        size_bytes: File size in bytes.

    Returns:
        Formatted string such as '12.34 MB'.
    """
    if size_bytes < 0:
        return "0 B"
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if size_bytes < 1024.0:
            return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.2f} PB"


def format_duration(seconds: float) -> str:
    """
    Format a duration in seconds to a human-readable string.

    Args:
        seconds: Elapsed time in seconds.

    Returns:
        String like '3.45 sec' or '1 min 23.4 sec'.
    """
    if seconds < 60:
        return f"{seconds:.1f} sec"
    minutes = int(seconds // 60)
    remaining = seconds % 60
    return f"{minutes} min {remaining:.1f} sec"


def reduction_percent(original: int, compressed: int) -> float:
    """
    Calculate percentage reduction between two sizes.

    Args:
        original: Original file size in bytes.
        compressed: Compressed file size in bytes.

    Returns:
        Reduction percentage (positive = smaller).
    """
    if original == 0:
        return 0.0
    return ((original - compressed) / original) * 100


def get_output_path(
    input_path: Path,
    output_dir: Path,
    suffix: str = "_compressed",
    custom_name: str | None = None,
) -> Path:
    """
    Derive the output file path from the input path.

    Args:
        input_path: Source PDF path.
        output_dir: Directory where the output file will be written.
        suffix: Suffix to append before the extension (default: '_compressed').
        custom_name: Optional override for the output filename (without extension).

    Returns:
        Full output Path object.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    if custom_name:
        return output_dir / f"{custom_name}.pdf"
    stem = input_path.stem + suffix
    return output_dir / f"{stem}.pdf"


def find_pdf_files(directory: Path, recursive: bool = True) -> Generator[Path, None, None]:
    """
    Yield all PDF files within a directory.

    Args:
        directory: Root directory to search.
        recursive: If True, search subdirectories as well.

    Yields:
        Path objects pointing to each discovered PDF file.
    """
    pattern = "**/*.pdf" if recursive else "*.pdf"
    for path in sorted(directory.glob(pattern)):
        if path.is_file():
            yield path


def safe_remove(path: Path) -> None:
    """
    Remove a file, suppressing errors if it does not exist.

    Args:
        path: File to delete.
    """
    try:
        path.unlink(missing_ok=True)
    except OSError:
        pass


def copy_file(src: Path, dst: Path) -> None:
    """
    Copy a file, creating parent directories as needed.

    Args:
        src: Source path.
        dst: Destination path.
    """
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)


def get_file_size(path: Path) -> int:
    """
    Return file size in bytes, or 0 if the file does not exist.

    Args:
        path: Path to the file.

    Returns:
        Size in bytes.
    """
    try:
        return path.stat().st_size
    except OSError:
        return 0


class Timer:
    """Simple context manager / manual timer."""

    def __init__(self) -> None:
        self._start: float = 0.0
        self._end: float = 0.0

    def start(self) -> "Timer":
        self._start = time.perf_counter()
        return self

    def stop(self) -> float:
        self._end = time.perf_counter()
        return self.elapsed

    @property
    def elapsed(self) -> float:
        """Elapsed time in seconds."""
        end = self._end if self._end else time.perf_counter()
        return end - self._start

    def __enter__(self) -> "Timer":
        return self.start()

    def __exit__(self, *_: object) -> None:
        self.stop()
