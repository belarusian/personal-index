"""Tests for TICKET-73: RET504 - unnecessary assignment before return."""

from personal_index.encoding import EncodingDetector
from personal_index.utils import extract_text_content
from personal_index.text_utils import tokenize


class TestEncodingDetector:
    def test_sanitize(self):
        detector = EncodingDetector()
        result = detector.sanitize("hello\x00world")
        assert "\x00" not in result

    def test_sanitize_whitespace(self):
        detector = EncodingDetector()
        result = detector.sanitize("hello   world")
        assert "  " not in result


class TestExtractTextContent:
    def test_extract_text(self):
        html = "<html><body><p>Hello World</p></body></html>"
        result = extract_text_content(html)
        assert "Hello World" in result


class TestTokenize:
    def test_tokenize(self):
        result = tokenize("hello world test")
        assert "hello" in result
        assert "world" in result
        assert "test" in result
