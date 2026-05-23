"""
Core Package
============
Exports the public API for the compression core.
"""

from compressor.core.engine import CompressionEngine
from compressor.core.result import CompressionResult

__all__ = ["CompressionEngine", "CompressionResult"]
