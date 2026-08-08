"""Content type detection and classification."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Tuple


class ContentType(Enum):
    """Types of content that can be detected."""
    TEXT = "text"
    HTML = "html"
    JSON = "json"
    XML = "xml"
    CSV = "csv"
    MARKDOWN = "markdown"
    CODE = "code"
    UNKNOWN = "unknown"


@dataclass
class ContentAnalysis:
    """Result of content type analysis."""
    content_type: ContentType
    confidence: float
    language: str = "unknown"
    word_count: int = 0
    char_count: int = 0
    line_count: int = 0
    metadata: Dict[str, str] = field(default_factory=dict)


class ContentTypeDetector:
    """Detect and classify content types."""

    # Patterns for content type detection
    HTML_PATTERN = re.compile(r"<\s*(html|head|body|div|p|span|a|table|script|style)\b", re.IGNORECASE)
    JSON_PATTERN = re.compile(r"^\s*[\{\[]", re.MULTILINE)
    XML_PATTERN = re.compile(r"<\?xml\b|<\s*\w+\s+[^>]*>")
    CSV_PATTERN = re.compile(r"^[^,]+(,[^,]+)+$", re.MULTILINE)
    MARKDOWN_PATTERN = re.compile(r"^(#{1,6}\s|[-*]\s|\d+\.\s|>\s|
