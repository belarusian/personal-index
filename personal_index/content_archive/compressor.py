"""Compression utilities for content archiving."""

from __future__ import annotations

import gzip
import zlib
from enum import Enum
from typing import Any


class CompressionFormat(Enum):
    """Supported compression formats."""

    GZIP = "gzip"
    ZLIB = "zlib"


class Compressor:
    """Handles compression and decompression of content."""

    def compress(self, data: bytes, fmt: CompressionFormat = CompressionFormat.GZIP) -> bytes:
        """Compress raw bytes data."""
        if fmt == CompressionFormat.GZIP:
            return gzip.compress(data)
        if fmt == CompressionFormat.ZLIB:
            return zlib.compress(data)
        raise ValueError(f"Unsupported format: {fmt}")

    def decompress(self, data: bytes, fmt: CompressionFormat = CompressionFormat.GZIP) -> bytes:
        """Decompress raw bytes data."""
        if fmt == CompressionFormat.GZIP:
            return gzip.decompress(data)
        if fmt == CompressionFormat.ZLIB:
            return zlib.decompress(data)
        raise ValueError(f"Unsupported format: {fmt}")

    def compress_text(self, text: str, fmt: CompressionFormat = CompressionFormat.GZIP) -> bytes:
        """Compress a text string."""
        return self.compress(text.encode("utf-8"), fmt)

    def decompress_text(self, data: bytes, fmt: CompressionFormat = CompressionFormat.GZIP) -> str:
        """Decompress bytes back to text string."""
        return self.decompress(data, fmt).decode("utf-8")

    def compression_ratio(self, original: bytes, compressed: bytes) -> float:
        """Calculate compression ratio (1.0 = no compression, 0.0 = perfect)."""
        if not original:
            return 0.0
        return len(compressed) / len(original)

    def get_stats(self, original: bytes, compressed: bytes) -> dict[str, Any]:
        """Get compression statistics."""
        return {
            "original_size": len(original),
            "compressed_size": len(compressed),
            "ratio": round(self.compression_ratio(original, compressed), 4),
            "savings_bytes": len(original) - len(compressed),
            "savings_percent": round((1 - self.compression_ratio(original, compressed)) * 100, 2),
        }
