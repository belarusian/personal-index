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

    HTML_PATTERN = re.compile(
        r"<\s*(html|head|body|div|p|span|a|table|script|style)\b",
        re.IGNORECASE,
    )
    JSON_PATTERN = re.compile(r"^\s*[\{\[]", re.MULTILINE)
    XML_PATTERN = re.compile(r"<\?xml\b|<\s*\w+\s+[^>]*>")
    CSV_PATTERN = re.compile(r"^[^,]+(,[^,]+)+$", re.MULTILINE)
    MARKDOWN_PATTERN = re.compile(
        r"^(#{1,6}\s|[-*]\s|\d+\.\s|>\s)",
        re.MULTILINE,
    )
    CODE_PATTERNS = [
        re.compile(
            r"(def |class |function |import |from |return |if |else |for |while )",
            re.MULTILINE,
        ),
        re.compile(
            r"(let |const |var |=>|\.map\(|\.filter\(|\.reduce\()",
            re.MULTILINE,
        ),
        # SQL patterns
        re.compile(
            r"(SELECT |INSERT |UPDATE |DELETE |CREATE TABLE|FROM |WHERE )",
            re.IGNORECASE | re.MULTILINE,
        ),
    ]

    LANGUAGE_INDICATORS: Dict[str, List[re.Pattern]] = {
        "python": [
            re.compile(r"(def |class |import |from |self\.|print\(|@property)", re.MULTILINE),
        ],
        "javascript": [
            re.compile(r"(let |const |var |=>|\.map\(|console\.|document\.)", re.MULTILINE),
        ],
        "typescript": [
            re.compile(r": (string|number|boolean|void|any)\b|interface |type ", re.MULTILINE),
        ],
        "rust": [
            re.compile(r"(fn |let mut |pub struct |impl |use std::|Option<)", re.MULTILINE),
        ],
        "go": [
            re.compile(r"(func |package |import \(|var |chan |goroutine)", re.MULTILINE),
        ],
        "java": [
            re.compile(r"(public class |private |static void |System\.out|@Override)", re.MULTILINE),
        ],
        "c": [
            re.compile(r"(#include|int main\(|printf\(|malloc\(|struct )", re.MULTILINE),
        ],
        "sql": [
            re.compile(r"(SELECT |INSERT |UPDATE |DELETE |CREATE TABLE|FROM |WHERE )", re.IGNORECASE | re.MULTILINE),
        ],
    }

    def detect(self, content: str) -> ContentAnalysis:
        """Detect the content type of the given text."""
        if not content or not content.strip():
            return ContentAnalysis(
                content_type=ContentType.UNKNOWN,
                confidence=0.0,
                char_count=len(content) if content else 0,
            )

        scores: Dict[ContentType, float] = {}
        lines = content.strip().split("\n")

        html_matches = len(self.HTML_PATTERN.findall(content[:2000]))
        if html_matches > 0:
            scores[ContentType.HTML] = min(html_matches * 0.2, 1.0)

        if self.JSON_PATTERN.search(content[:500]):
            scores[ContentType.JSON] = 0.8

        xml_matches = len(self.XML_PATTERN.findall(content[:1000]))
        if xml_matches > 0:
            scores[ContentType.XML] = min(xml_matches * 0.3, 1.0)

        if len(lines) > 1:
            csv_lines = sum(1 for line in lines[:10] if self.CSV_PATTERN.match(line.strip()))
            if csv_lines > len(lines[:10]) * 0.5:
                scores[ContentType.CSV] = csv_lines / len(lines[:10])

        md_matches = len(self.MARKDOWN_PATTERN.findall(content[:2000]))
        if md_matches > 0:
            scores[ContentType.MARKDOWN] = min(md_matches * 0.15, 1.0)

        code_score = 0.0
        for pattern in self.CODE_PATTERNS:
            code_score += len(pattern.findall(content[:2000])) * 0.1
        if code_score > 0:
            scores[ContentType.CODE] = min(code_score, 1.0)

        if not scores:
            return ContentAnalysis(
                content_type=ContentType.TEXT,
                confidence=0.5,
                word_count=self._count_words(content),
                char_count=len(content),
                line_count=len(lines),
            )

        best_type = max(scores, key=scores.get)
        confidence = scores[best_type]

        language = "unknown"
        if best_type == ContentType.CODE:
            language = self._detect_language(content)

        return ContentAnalysis(
            content_type=best_type,
            confidence=confidence,
            language=language,
            word_count=self._count_words(content),
            char_count=len(content),
            line_count=len(lines),
        )

    def _detect_language(self, content: str) -> str:
        """Detect programming language from content."""
        best_lang = "unknown"
        best_score = 0
        for lang, patterns in self.LANGUAGE_INDICATORS.items():
            score = sum(len(p.findall(content[:3000])) for p in patterns)
            if score > best_score:
                best_score = score
                best_lang = lang
        return best_lang

    @staticmethod
    def _count_words(text: str) -> int:
        """Count words in text."""
        return len(text.split())

    def detect_from_headers(self, content_type_header: str, content: str) -> ContentAnalysis:
        """Detect content type using HTTP headers and content analysis."""
        if not content_type_header:
            return self.detect(content)

        header_type = content_type_header.lower().split(";")[0].strip()
        type_map = {
            "text/html": ContentType.HTML,
            "application/json": ContentType.JSON,
            "application/xml": ContentType.XML,
            "text/csv": ContentType.CSV,
            "text/plain": ContentType.TEXT,
            "text/markdown": ContentType.MARKDOWN,
            "application/javascript": ContentType.CODE,
        }

        if header_type in type_map:
            return ContentAnalysis(
                content_type=type_map[header_type],
                confidence=0.9,
                word_count=self._count_words(content) if content else 0,
                char_count=len(content) if content else 0,
                line_count=content.count("\n") + 1 if content else 0,
                metadata={"content_type_header": content_type_header},
            )

        # Unknown content type header - return UNKNOWN
        return ContentAnalysis(
            content_type=ContentType.UNKNOWN,
            confidence=0.1,
            word_count=self._count_words(content) if content else 0,
            char_count=len(content) if content else 0,
            line_count=content.count("\n") + 1 if content else 0,
            metadata={"content_type_header": content_type_header},
        )
