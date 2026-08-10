"""Text encoding detection and conversion utilities."""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import ClassVar

logger = logging.getLogger(__name__)

@dataclass
class EncodingResult:
    """Result of encoding detection."""

    encoding: str
    confidence: float
    language: str | None = None

class EncodingDetector:
    """Detects text encoding and performs conversions."""

    COMMON_ENCODINGS: ClassVar[list[str]] = ["utf-8", "ascii", "iso-8859-1", "windows-1252", "utf-16", "utf-16-le", "utf-16-be"]

    def detect(self, data: bytes) -> EncodingResult:
        """Detect the encoding of byte data."""
        if self._is_utf8_bom(data):
            return EncodingResult(encoding="utf-8", confidence=1.0)

        if self._is_utf16_bom(data):
            return EncodingResult(encoding="utf-16", confidence=1.0)

        if self._is_ascii(data):
            return EncodingResult(encoding="ascii", confidence=0.9)

        if self._looks_like_utf8(data):
            return EncodingResult(encoding="utf-8", confidence=0.8)

        return EncodingResult(encoding="iso-8859-1", confidence=0.5)

    def decode(self, data: bytes, encoding: str | None = None) -> str:
        """Decode bytes to string, auto-detecting if needed."""
        if encoding is None:
            result = self.detect(data)
            encoding = result.encoding
        try:
            return data.decode(encoding)
        except (UnicodeDecodeError, LookupError):
            return data.decode("utf-8", errors="replace")

    def encode(self, text: str, encoding: str = "utf-8") -> bytes:
        """Encode string to bytes."""
        try:
            return text.encode(encoding)
        except (UnicodeEncodeError, LookupError):
            return text.encode("utf-8")

    def convert(self, data: bytes, from_encoding: str, to_encoding: str = "utf-8") -> bytes:
        """Convert between encodings."""
        text = self.decode(data, from_encoding)
        return self.encode(text, to_encoding)

    def _is_utf8_bom(self, data: bytes) -> bool:
        return data[:3] == b"\xef\xbb\xbf"

    def _is_utf16_bom(self, data: bytes) -> bool:
        return data[:2] in (b"\xff\xfe", b"\xfe\xff")

    def _is_ascii(self, data: bytes) -> bool:
        try:
            data.decode("ascii")
            return True
        except UnicodeDecodeError:
            return False

    def _looks_like_utf8(self, data: bytes) -> bool:
        try:
            data.decode("utf-8")
            return True
        except UnicodeDecodeError:
            return False

    def normalize_whitespace(self, text: str) -> str:
        """Normalize whitespace in text."""
        return re.sub(r"\s+", " ", text).strip()

    def remove_control_chars(self, text: str) -> str:
        """Remove control characters from text."""
        return re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", text)

    def sanitize(self, text: str) -> str:
        """Sanitize text by removing control chars and normalizing whitespace."""
        text = self.remove_control_chars(text)
        return self.normalize_whitespace(text)
