"""URL and content validation utilities."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import ClassVar
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


@dataclass
class ValidationResult:
    """Result of a validation check."""

    valid: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def add_error(self, message: str) -> None:
        """Mark the result invalid and append message to errors.

        Args:
        message.
        """
        self.valid = False
        self.errors.append(message)

    def add_warning(self, message: str) -> None:
        """Append message to warnings; does not change valid.

        Args:
        message.
        """
        self.warnings.append(message)


class URLValidator:
    """Validates URLs for crawling."""

    SCHEMES: ClassVar[set[str]] = {"http", "https", "ftp", "ftps"}
    MAX_URL_LENGTH = 2048
    MAX_DOMAIN_LENGTH = 253

    def __init__(
        self,
        allowed_schemes: set[str] | None = None,
        blocked_domains: set[str] | None = None,
        blocked_paths: list[str] | None = None,
        max_url_length: int = MAX_URL_LENGTH,
    ):
        self.allowed_schemes = allowed_schemes or self.SCHEMES
        self.blocked_domains = blocked_domains or set()
        self.blocked_paths = blocked_paths or []
        self.max_url_length = max_url_length

    def validate(self, url: str) -> ValidationResult:
        """Run length, scheme, domain, path and fragment checks; return a
        ValidationResult that is valid iff no errors were added."""
        result = ValidationResult(valid=True)
        if not url or not url.strip():
            result.add_error("URL is empty")
            return result
        url = url.strip()
        self._check_length(url, result)
        parsed = urlparse(url)
        self._check_scheme(parsed, result)
        self._check_domain(parsed, result)
        self._check_path(parsed, result)
        self._check_fragment(parsed, result)
        if not result.errors:
            result.valid = True
        return result

    def _check_length(self, url: str, result: ValidationResult) -> None:
        """Check URL length."""
        if len(url) > self.max_url_length:
            result.add_error(f"URL exceeds max length of {self.max_url_length}")

    def _check_scheme(self, parsed, result: ValidationResult) -> None:
        """Check URL scheme."""
        if not parsed.scheme:
            result.add_error("URL missing scheme")
        elif parsed.scheme.lower() not in self.allowed_schemes:
            result.add_error(f"Scheme '{parsed.scheme}' not allowed")

    def _check_domain(self, parsed, result: ValidationResult) -> None:
        """Check URL domain."""
        if not parsed.netloc:
            result.add_error("URL missing domain")
        else:
            if len(parsed.netloc) > self.MAX_DOMAIN_LENGTH:
                result.add_error("Domain name too long")
            if self._is_blocked_domain(parsed.netloc):
                result.add_error(f"Domain '{parsed.netloc}' is blocked")

    def _check_path(self, parsed, result: ValidationResult) -> None:
        """Check URL path."""
        if self._is_blocked_path(parsed.path):
            result.add_error(f"Path '{parsed.path}' is blocked")

    def _check_fragment(self, parsed, result: ValidationResult) -> None:
        """Check URL fragment."""
        if parsed.fragment:
            result.add_warning("URL contains fragment identifier")

    def _is_blocked_domain(self, domain: str) -> bool:
        domain = domain.lower().rstrip(".")
        for blocked in self.blocked_domains:
            if domain == blocked or domain.endswith(f".{blocked}"):
                return True
        return False

    def _is_blocked_path(self, path: str) -> bool:
        path = path.lower()
        return any(path.startswith(blocked.lower()) for blocked in self.blocked_paths)

    def validate_batch(self, urls: list[str]) -> list[tuple[str, ValidationResult]]:
        """Validate multiple URLs."""
        return [(url, self.validate(url)) for url in urls]


class ContentValidator:
    """Validates extracted content quality."""

    MIN_CONTENT_LENGTH = 50
    MAX_CONTENT_LENGTH = 10_000_000
    MIN_WORD_COUNT = 10

    def __init__(
        self,
        min_length: int = MIN_CONTENT_LENGTH,
        max_length: int = MAX_CONTENT_LENGTH,
        min_words: int = MIN_WORD_COUNT,
    ):
        self.min_length = min_length
        self.max_length = max_length
        self.min_words = min_words

    def validate(self, content: str) -> ValidationResult:
        """Check length, word count, link ratio and whitespace; return a
        ValidationResult with warnings for soft limits and errors for empty
        or mostly-whitespace content."""
        result = ValidationResult(valid=True)

        if not content:
            result.add_error("Content is empty")
            return result

        if len(content) < self.min_length:
            result.add_warning(f"Content too short: {len(content)} chars")

        if len(content) > self.max_length:
            result.add_warning(f"Content very long: {len(content)} chars")

        word_count = len(content.split())
        if word_count < self.min_words:
            result.add_warning(f"Too few words: {word_count}")

        if self._has_too_many_links(content):
            result.add_warning("Content has too many links relative to text")

        if self._is_mostly_whitespace(content):
            result.add_error("Content is mostly whitespace")

        return result

    def _has_too_many_links(self, content: str) -> bool:
        link_count = content.count("http")
        word_count = len(content.split())
        return word_count > 0 and (link_count / word_count) > 0.5

    def _is_mostly_whitespace(self, content: str) -> bool:
        if not content.strip():
            return True
        whitespace_ratio = content.count(" ") / len(content) if content else 0
        return whitespace_ratio > 0.95
