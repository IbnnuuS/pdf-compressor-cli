"""
Compression Result
==================
Data class representing the outcome of a single PDF compression operation.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


@dataclass
class CompressionResult:
    """
    Complete record of a single PDF compression run.

    Attributes:
        input_path: Path to the source PDF.
        output_path: Path to the compressed output PDF (may be None on failure).
        original_size: File size before compression (bytes).
        compressed_size: File size after compression (bytes).
        elapsed_seconds: Wall-clock time taken (seconds).
        preset_name: Name of the compression preset used.
        success: True if compression completed without fatal error.
        error_message: Human-readable error description (only when success=False).
        stages_used: List of pipeline stages that were applied.
    """

    input_path: Path
    output_path: Optional[Path]
    original_size: int
    compressed_size: int
    elapsed_seconds: float
    preset_name: str
    success: bool
    error_message: str = ""
    stages_used: list[str] = field(default_factory=list)

    @property
    def reduction_percent(self) -> float:
        """Percentage reduction in file size (positive = smaller)."""
        if self.original_size == 0:
            return 0.0
        return ((self.original_size - self.compressed_size) / self.original_size) * 100

    @property
    def size_delta_bytes(self) -> int:
        """Absolute byte difference (positive = saved space)."""
        return self.original_size - self.compressed_size

    def to_dict(self) -> dict:
        """Serialize result to a JSON-friendly dictionary."""
        return {
            "input": str(self.input_path),
            "output": str(self.output_path) if self.output_path else None,
            "original_size": self.original_size,
            "compressed_size": self.compressed_size,
            "reduction_percent": round(self.reduction_percent, 2),
            "elapsed_seconds": round(self.elapsed_seconds, 2),
            "preset": self.preset_name,
            "success": self.success,
            "error": self.error_message,
            "stages": self.stages_used,
        }
