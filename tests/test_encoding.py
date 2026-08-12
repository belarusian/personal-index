"""Tests for text encoding utilities."""

from personal_index.encoding import EncodingDetector, EncodingResult


class TestEncodingResult:
    def test_creation(self):
        r = EncodingResult(encoding="utf-8", confidence=0.9)
        assert r.encoding == "utf-8"
        assert r.confidence == 0.9


class TestEncodingDetector:
    def test_detect_utf8_bom(self):
        d = EncodingDetector()
        data = b"\xef\xbb\xbfhello"
        result = d.detect(data)
        assert result.encoding == "utf-8"
        assert result.confidence == 1.0

    def test_detect_utf16_bom(self):
        d = EncodingDetector()
        data = b"\xff\xfehello"
        result = d.detect(data)
        assert result.encoding == "utf-16"
        assert result.confidence == 1.0

    def test_detect_ascii(self):
        d = EncodingDetector()
        data = b"hello world"
        result = d.detect(data)
        assert result.encoding == "ascii"

    def test_detect_utf8(self):
        d = EncodingDetector()
        data = "héllo wörld".encode()
        result = d.detect(data)
        assert result.encoding == "utf-8"

    def test_detect_fallback(self):
        d = EncodingDetector()
        data = bytes(range(128, 256))
        result = d.detect(data)
        assert result.encoding == "iso-8859-1"

    def test_decode_auto(self):
        d = EncodingDetector()
        text = d.decode(b"hello world")
        assert text == "hello world"

    def test_decode_explicit(self):
        d = EncodingDetector()
        text = d.decode("café".encode(), "utf-8")
        assert text == "café"

    def test_decode_fallback(self):
        d = EncodingDetector()
        text = d.decode(b"\xff\xfe", "utf-8")
        assert len(text) > 0

    def test_encode(self):
        d = EncodingDetector()
        data = d.encode("hello")
        assert data == b"hello"

    def test_convert(self):
        d = EncodingDetector()
        original = "hello".encode("ascii")
        converted = d.convert(original, "ascii", "utf-8")
        assert converted == b"hello"

    def test_normalize_whitespace(self):
        d = EncodingDetector()
        result = d.normalize_whitespace("  hello   world  ")
        assert result == "hello world"

    def test_remove_control_chars(self):
        d = EncodingDetector()
        result = d.remove_control_chars("hello\x00world\x01test")
        assert "\x00" not in result
        assert "\x01" not in result

    def test_sanitize(self):
        d = EncodingDetector()
        result = d.sanitize("  hello\x00world  ")
        assert result == "helloworld"
