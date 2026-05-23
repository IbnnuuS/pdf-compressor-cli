"""
PDF Validator
=============
Checks PDF files for encryption, corruption, and read permission
before attempting compression.
"""

from pathlib import Path
from typing import Optional

from compressor.utils.logger import get_logger

logger = get_logger("validator")

# PDF magic bytes header
_PDF_MAGIC = b"%PDF-"


class PDFValidationError(Exception):
    """Raised when a PDF fails validation."""

    pass


class EncryptedPDFError(PDFValidationError):
    """Raised when a PDF is password-protected."""

    pass


class CorruptedPDFError(PDFValidationError):
    """Raised when a PDF appears to be corrupted."""

    pass


def check_file_readable(path: Path) -> None:
    """
    Verify the file exists and is readable.

    Args:
        path: Path to the PDF file.

    Raises:
        FileNotFoundError: If the file does not exist.
        PermissionError: If the process lacks read permission.
    """
    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")
    if not path.is_file():
        raise FileNotFoundError(f"Path is not a file: {path}")
    try:
        path.open("rb").close()
    except PermissionError as exc:
        raise PermissionError(f"Cannot read file (permission denied): {path}") from exc


def check_pdf_magic(path: Path) -> None:
    """
    Verify the PDF magic bytes at the start of the file.

    Args:
        path: Path to the file.

    Raises:
        CorruptedPDFError: If the file does not begin with '%PDF-'.
    """
    with path.open("rb") as fh:
        header = fh.read(5)
    if header != _PDF_MAGIC:
        raise CorruptedPDFError(
            f"File does not appear to be a valid PDF (bad magic bytes): {path}"
        )


def check_pdf_encryption(path: Path) -> None:
    """
    Detect if a PDF is encrypted / password-protected using pikepdf.

    Args:
        path: Path to the PDF file.

    Raises:
        EncryptedPDFError: If the PDF requires a password.
        CorruptedPDFError: If the PDF is structurally invalid.
    """
    try:
        import pikepdf  # type: ignore

        try:
            pdf = pikepdf.open(path)
            pdf.close()
        except pikepdf.PasswordError as exc:
            raise EncryptedPDFError(
                f"PDF is password-protected and cannot be compressed: {path}"
            ) from exc
        except pikepdf.PdfError as exc:
            raise CorruptedPDFError(
                f"PDF appears to be corrupted: {path}\nDetails: {exc}"
            ) from exc
    except ImportError:
        # pikepdf not available — fall back to basic structural check
        logger.warning("pikepdf not installed; skipping encryption check.")


def validate_pdf(path: Path) -> None:
    """
    Run all validation checks on a PDF file.

    Args:
        path: Path to the PDF file.

    Raises:
        FileNotFoundError: File does not exist.
        PermissionError: Cannot read the file.
        CorruptedPDFError: File is not a valid PDF.
        EncryptedPDFError: PDF is password-protected.
    """
    logger.debug(f"Validating: {path}")
    check_file_readable(path)
    check_pdf_magic(path)
    check_pdf_encryption(path)
    logger.debug(f"Validation passed: {path}")
