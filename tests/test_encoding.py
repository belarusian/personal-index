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


class TestDetectContract:
    """Pinning tests for EncodingDetector.detect's exact contract (TICKET-503)."""

    def test_returns_encoding_result(self):
        d = EncodingDetector()
        result = d.detect(b"hello")
        assert isinstance(result, EncodingResult)

    def test_utf8_bom_confidence(self):
        d = EncodingDetector()
        result = d.detect(b"\xef\xbb\xbfhello")
        assert result.encoding == "utf-8"
        assert result.confidence == 1.0

    def test_utf16_le_bom_confidence(self):
        d = EncodingDetector()
        result = d.detect(b"\xff\xfe\x00h")
        assert result.encoding == "utf-16"
        assert result.confidence == 1.0

    def test_utf16_be_bom_confidence(self):
        d = EncodingDetector()
        result = d.detect(b"\xfe\xffh\x00")
        assert result.encoding == "utf-16"
        assert result.confidence == 1.0

    def test_ascii_confidence(self):
        d = EncodingDetector()
        result = d.detect(b"hello world")
        assert result.encoding == "ascii"
        assert result.confidence == 0.9

    def test_ascii_takes_priority_over_valid_utf8(self):
        # ASCII-only bytes are valid UTF-8, but the cascade reports ascii first.
        d = EncodingDetector()
        result = d.detect(b"plain ascii text")
        assert result.encoding == "ascii"
        assert result.confidence == 0.9

    def test_valid_utf8_non_ascii_confidence(self):
        d = EncodingDetector()
        result = d.detect("h\u00e9llo".encode("utf-8"))
        assert result.encoding == "utf-8"
        assert result.confidence == 0.8

    def test_fallback_iso8859_1_confidence(self):
        d = EncodingDetector()
        # Bytes that are not valid UTF-8 fall back to iso-8859-1.
        result = d.detect(b"caf\xe9")
        assert result.encoding == "iso-8859-1"
        assert result.confidence == 0.5

    def test_empty_bytes_reported_as_ascii(self):
        d = EncodingDetector()
        result = d.detect(b"")
        assert result.encoding == "ascii"
        assert result.confidence == 0.9

    def test_language_always_none(self):
        d = EncodingDetector()
        for data in (b"\xef\xbb\xbf", b"\xff\xfe", b"abc", "h\u00e9".encode("utf-8"), b"caf\xe9"):
            assert d.detect(data).language is None
