"""
Compression Presets
===================
Defines all compression quality presets with their associated parameters.
Each preset controls image quality, DPI, optimization flags, and Ghostscript settings.
"""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class CompressionPreset:
    """
    Represents a complete compression configuration preset.

    Attributes:
        name: Preset identifier
        description: Human-readable description of the preset
        gs_quality: Ghostscript quality setting (screen/ebook/printer/prepress/default)
        jpeg_quality: JPEG image quality (1-95)
        dpi: Target resolution in dots per inch
        grayscale: Convert color images to grayscale
        remove_metadata: Strip all PDF metadata
        remove_thumbnails: Remove embedded thumbnail images
        optimize_fonts: Subset and optimize embedded fonts
        linearize: Linearize PDF for fast web view
        aggressive_cleanup: Perform aggressive object/stream cleanup
        image_resampling: Resample images to target DPI
        compress_streams: Recompress all content streams
    """
    name: str
    description: str
    gs_quality: str
    jpeg_quality: int
    dpi: int
    grayscale: bool = False
    remove_metadata: bool = True
    remove_thumbnails: bool = True
    optimize_fonts: bool = True
    linearize: bool = True
    aggressive_cleanup: bool = False
    image_resampling: bool = True
    compress_streams: bool = True
    gs_color_downsampling: bool = True
    gs_gray_downsampling: bool = True
    gs_mono_downsampling: bool = True
    color_conversion: Optional[str] = None  # e.g. "sRGB", "Gray"

    def to_dict(self) -> dict:
        """Convert preset to dictionary for logging/display."""
        return {
            "name": self.name,
            "description": self.description,
            "gs_quality": self.gs_quality,
            "jpeg_quality": self.jpeg_quality,
            "dpi": self.dpi,
            "grayscale": self.grayscale,
            "remove_metadata": self.remove_metadata,
            "optimize_fonts": self.optimize_fonts,
            "linearize": self.linearize,
            "aggressive_cleanup": self.aggressive_cleanup,
        }


# ---------------------------------------------------------------------------
# Built-in Presets
# ---------------------------------------------------------------------------

PRESETS: dict[str, CompressionPreset] = {
    "low": CompressionPreset(
        name="low",
        description="Minimal compression — nearly identical quality, small size reduction",
        gs_quality="prepress",
        jpeg_quality=85,
        dpi=200,
        grayscale=False,
        remove_metadata=True,
        remove_thumbnails=True,
        optimize_fonts=True,
        linearize=True,
        aggressive_cleanup=False,
        image_resampling=True,
        compress_streams=True,
        gs_color_downsampling=True,
        gs_gray_downsampling=True,
        gs_mono_downsampling=False,
    ),
    "medium": CompressionPreset(
        name="medium",
        description="Balanced compression — good quality with noticeable size reduction",
        gs_quality="printer",
        jpeg_quality=72,
        dpi=150,
        grayscale=False,
        remove_metadata=True,
        remove_thumbnails=True,
        optimize_fonts=True,
        linearize=True,
        aggressive_cleanup=False,
        image_resampling=True,
        compress_streams=True,
        gs_color_downsampling=True,
        gs_gray_downsampling=True,
        gs_mono_downsampling=True,
    ),
    "high": CompressionPreset(
        name="high",
        description="High compression — acceptable quality, significant size reduction",
        gs_quality="ebook",
        jpeg_quality=55,
        dpi=120,
        grayscale=False,
        remove_metadata=True,
        remove_thumbnails=True,
        optimize_fonts=True,
        linearize=True,
        aggressive_cleanup=True,
        image_resampling=True,
        compress_streams=True,
        gs_color_downsampling=True,
        gs_gray_downsampling=True,
        gs_mono_downsampling=True,
    ),
    "extreme": CompressionPreset(
        name="extreme",
        description="Aggressive compression — lower quality, maximum practical size reduction",
        gs_quality="screen",
        jpeg_quality=40,
        dpi=96,
        grayscale=False,
        remove_metadata=True,
        remove_thumbnails=True,
        optimize_fonts=True,
        linearize=True,
        aggressive_cleanup=True,
        image_resampling=True,
        compress_streams=True,
        gs_color_downsampling=True,
        gs_gray_downsampling=True,
        gs_mono_downsampling=True,
    ),
    "ultra": CompressionPreset(
        name="ultra",
        description="Brutal compression — small file size above all else; grayscale, minimal quality",
        gs_quality="screen",
        jpeg_quality=28,
        dpi=72,
        grayscale=True,
        remove_metadata=True,
        remove_thumbnails=True,
        optimize_fonts=True,
        linearize=True,
        aggressive_cleanup=True,
        image_resampling=True,
        compress_streams=True,
        gs_color_downsampling=True,
        gs_gray_downsampling=True,
        gs_mono_downsampling=True,
        color_conversion="Gray",
    ),
}


def get_preset(name: str) -> CompressionPreset:
    """
    Retrieve a compression preset by name.

    Args:
        name: Preset name (low/medium/high/extreme/ultra)

    Returns:
        CompressionPreset instance

    Raises:
        ValueError: If the preset name is not recognized
    """
    if name not in PRESETS:
        valid = ", ".join(PRESETS.keys())
        raise ValueError(f"Unknown preset '{name}'. Valid presets: {valid}")
    return PRESETS[name]


def list_presets() -> list[CompressionPreset]:
    """Return all available presets in order."""
    return list(PRESETS.values())
