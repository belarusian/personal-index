"""Tests for TICKET-106: Fix BeautifulSoup AttributeValueList type mismatches."""

from __future__ import annotations

import subprocess
import sys

import pytest


def _check_mypy_union_attr(paths: list[str]) -> list[str]:
    """Run mypy on given files and return union-attr errors."""
    result = subprocess.run(
        [sys.executable, "-m", "mypy"] + paths + ["--no-error-summary"],
        capture_output=True,
        text=True,
    )
    errors = [line for line in result.stdout.split("\n") if "union-attr" in line]
    return errors


class TestTicket106AttributeValueList:
    """Verify AttributeValueList type mismatches are fixed."""

    def test_content_extractor_no_union_attr(self):
        """content_extractor.py should have no union-attr errors."""
        errors = _check_mypy_union_attr(["personal_index/content_extractor.py"])
        assert not errors, f"content_extractor.py has union-attr errors:\n" + "\n".join(errors)

    def test_content_no_union_attr(self):
        """content.py should have no union-attr errors."""
        errors = _check_mypy_union_attr(["personal_index/content.py"])
        assert not errors, f"content.py has union-attr errors:\n" + "\n".join(errors)

    def test_utils_no_union_attr(self):
        """utils/__init__.py should have no union-attr errors."""
        errors = _check_mypy_union_attr(["personal_index/utils/__init__.py"])
        assert not errors, f"utils/__init__.py has union-attr errors:\n" + "\n".join(errors)

    def test_crawler_init_no_union_attr(self):
        """crawler/__init__.py should have no union-attr errors."""
        errors = _check_mypy_union_attr(["personal_index/crawler/__init__.py"])
        assert not errors, f"crawler/__init__.py has union-attr errors:\n" + "\n".join(errors)

    def test_url_utils_no_union_attr(self):
        """url_utils.py should have no union-attr errors."""
        errors = _check_mypy_union_attr(["personal_index/url_utils.py"])
        assert not errors, f"url_utils.py has union-attr errors:\n" + "\n".join(errors)

    def test_content_extractor_strips_attributes(self):
        """ContentExtractor should properly strip attribute values."""
        from personal_index.content_extractor import ContentExtractor
        extractor = ContentExtractor()
        html = '<html><head><title> Test </title></head><body><a href=" /link ">link</a></body></html>'
        content = extractor.extract(html)
        assert content.title == "Test"
        assert ("link", "/link") in content.links

    def test_content_extractor_handles_attribute_value_list(self):
        """ContentExtractor should handle multi-valued attributes (AttributeValueList)."""
        from personal_index.content_extractor import ContentExtractor
        extractor = ContentExtractor()
        # rel attribute can have multiple values (e.g., "canonical noopener")
        html = '<html><head><link rel="canonical noopener" href="http://example.com/canonical" /></head></html>'
        content = extractor.extract(html)
        assert content.canonical_url == "http://example.com/canonical"

    def test_utils_extract_links_handles_attribute_value_list(self):
        """utils.extract_links should handle AttributeValueList."""
        from personal_index.utils import extract_links
        html = '<html><body><a href="http://example.com/link">link</a></body></html>'
        links = extract_links(html, "http://example.com")
        assert "http://example.com/link" in links
