"""
Logging Configuration
=====================
Sets up structured, rotating file + colored console logging for the application.
"""

import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

# ANSI color codes for terminal output
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


class ColoredFormatter(logging.Formatter):
    """Console formatter that adds ANSI color codes based on log level."""

    LEVEL_COLORS = {
        logging.DEBUG: GRAY,
        logging.INFO: CYAN,
        logging.WARNING: YELLOW,
        logging.ERROR: RED,
        logging.CRITICAL: f"{BOLD}{RED}",
    }

    def format(self, record: logging.LogRecord) -> str:  # noqa: A003
        color = self.LEVEL_COLORS.get(record.levelno, RESET)
        # Only colorize the level name prefix
        level_str = f"{color}[{record.levelname[:4]}]{RESET}"
        message = super().format(record)
        # Replace the plain level name with the colored one
        return f"{GRAY}{self.formatTime(record, '%H:%M:%S')}{RESET} {level_str} {record.getMessage()}"


def setup_logging(log_dir: Path, verbose: bool = False) -> logging.Logger:
    """
    Configure and return the application logger.

    Creates:
    - A rotating file handler that writes to logs/app.log (max 5 MB × 3 backups)
    - A colored console handler (INFO level by default, DEBUG if verbose)

    Args:
        log_dir: Directory where log files will be stored.
        verbose: If True, set console handler to DEBUG level.

    Returns:
        The configured root application logger.
    """
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / "app.log"

    logger = logging.getLogger("pdf_compressor")
    logger.setLevel(logging.DEBUG)

    # ── File handler ────────────────────────────────────────────────────────
    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=5 * 1024 * 1024,  # 5 MB
        backupCount=3,
        encoding="utf-8",
    )
    file_handler.setLevel(logging.DEBUG)
    file_formatter = logging.Formatter(
        fmt="%(asctime)s [%(levelname)-8s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    file_handler.setFormatter(file_formatter)
    logger.addHandler(file_handler)

    # ── Console handler ──────────────────────────────────────────────────────
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.DEBUG if verbose else logging.WARNING)
    console_handler.setFormatter(ColoredFormatter())
    logger.addHandler(console_handler)

    return logger


def get_logger(name: str) -> logging.Logger:
    """Get a child logger under the application namespace."""
    return logging.getLogger(f"pdf_compressor.{name}")
