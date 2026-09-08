"""Adversarial deep tests for personal_index.encoding.EncodingDetector.

Contract source: personal_index/encoding.py docstrings. These tests pin the
documented 5-rule priority cascade in detect(), the error-fallback behavior
in decode/encode/convert, and the whitespace/control-char helpers against
adversarial inputs: empty bytes, BOM-only payloads, invalid UTF-8, unicode
round-trips, idempotence, and one end-to-end CLI run.

Functions armored:
  EncodingDetector.detect, .decode, .encode, .convert,
  .normalize_whitespace, .remove_control_chars, .sanitize.
"""

from __future__ import annotations

from personal_index.encoding import EncodingDetector, EncodingResult


DET = EncodingDetector()


# --- detect: 5-rule priority cascade ----------------------------------------

def test_detect_empty_bytes_is_ascii():
    """Rule 3: empty bytes are vacuously pure ASCII."""
    r = DET.detect(b"")
    assert r.encoding == "ascii"
    assert r.confidence == 0.9
    assert r.language is None


def test_detect_utf8_bom():
    """Rule 1: UTF-8 BOM takes priority over everything."""
    r = DET.detect(b"\xef\xbb\xbf")
    assert r.encoding == "utf-8"
    assert r.confidence == 1.0


def test_detect_utf8_bom_with_payload():
    """UTF-8 BOM + non-ASCII payload still reports utf-8/1.0."""
    r = DET.detect(b"\xef\xbb\xbf" + "héllo".encode("utf-8"))
    assert r.encoding == "utf-8"
    assert r.confidence == 1.0


def test_detect_utf16_le_bom():
    """Rule 2: UTF-16 LE BOM."""
    r = DET.detect(b"\xff\xfe" + "hi".encode("utf-16-le"))
    assert r.encoding == "utf-16"
    assert r.confidence == 1.0


def test_detect_utf16_be_bom():
    """Rule 2: UTF-16 BE BOM."""
    r = DET.detect(b"\xfe\xff" + "hi".encode("utf-16-be"))
    assert r.encoding == "utf-16"
    assert r.confidence == 1.0


def test_detect_pure_ascii():
    """Rule 3: every byte < 0x80 → ascii/0.9."""
    r = DET.detect(b"hello world 123")
    assert r.encoding == "ascii"
    assert r.confidence == 0.9


def test_detect_ascii_takes_priority_over_utf8():
    """Docstring: 'This takes priority over valid UTF-8'."""
    # "abc" is valid UTF-8 but also pure ASCII → must report ascii.
    r = DET.detect(b"abc")
    assert r.encoding == "ascii"
    assert r.confidence == 0.9


def test_detect_valid_utf8_non_ascii():
    """Rule 4: valid UTF-8 with non-ASCII bytes → utf-8/0.8."""
    r = DET.detect("café".encode("utf-8"))
    assert r.encoding == "utf-8"
    assert r.confidence == 0.8


def test_detect_invalid_utf8_fallback():
    """Rule 5: not valid UTF-8 → iso-8859-1/0.5."""
    # 0x80-0xFF single bytes are not valid UTF-8 multi-byte sequences.
    r = DET.detect(b"\x80\x81\x82")
    assert r.encoding == "iso-8859-1"
    assert r.confidence == 0.5


def test_detect_bom_priority_over_ascii():
    """UTF-8 BOM (rule 1) beats ASCII (rule 3) even if payload is ASCII."""
    r = DET.detect(b"\xef\xbb\xbf" + b"plain ascii")
    assert r.encoding == "utf-8"
    assert r.confidence == 1.0


def test_detect_property_encoding_in_known_set():
    """Property: detect always returns one of the 5 documented encodings."""
    valid = {"utf-8", "ascii", "iso-8859-1", "utf-16"}
    samples = [b"", b"a", b"\xff\xfe", b"\xef\xbb\xbf", b"\x80", "é".encode("utf-8")]
    for s in samples:
        r = DET.detect(s)
        assert r.encoding in valid, f"unexpected encoding {r.encoding!r} for {s!r}"


def test_detect_property_confidence_range():
    """Property: confidence is always in [0, 1]."""
    import random
    random.seed(42)
    for _ in range(50):
        data = bytes(random.randrange(256) for _ in range(random.randrange(0, 20)))
        r = DET.detect(data)
        assert 0.0 <= r.confidence <= 1.0


# --- decode -----------------------------------------------------------------

def test_decode_auto_detect_ascii():
    assert DET.decode(b"hello") == "hello"


def test_decode_auto_detect_utf8():
    assert DET.decode("café".encode("utf-8")) == "café"


def test_decode_explicit_encoding():
    assert DET.decode("café".encode("iso-8859-1"), "iso-8859-1") == "café"


def test_decode_invalid_encoding_falls_back_to_utf8_replace():
    """Docstring: on UnicodeDecodeError/LookupError → utf-8 with errors='replace'."""
    # 0x80 is invalid UTF-8; decode should not raise.
    result = DET.decode(b"\x80\x81", "utf-8")
    # Should contain replacement characters, not raise.
    assert isinstance(result, str)
    assert "\ufffd" in result


def test_decode_unknown_encoding_name_falls_back():
    """LookupError path: unknown encoding name → utf-8 replace."""
    result = DET.decode(b"hello", "not-a-real-encoding")
    assert result == "hello"  # utf-8 decode of ascii works fine


def test_decode_empty_bytes():
    assert DET.decode(b"") == ""


# --- encode -----------------------------------------------------------------

def test_encode_default_utf8():
    assert DET.encode("café") == "café".encode("utf-8")


def test_encode_explicit_encoding():
    assert DET.encode("café", "iso-8859-1") == "café".encode("iso-8859-1")


def test_encode_unencodable_char_falls_back_to_utf8():
    """Docstring: on UnicodeEncodeError → utf-8."""
    # '€' cannot be encoded in ascii; should fall back to utf-8.
    result = DET.encode("€", "ascii")
    assert result == "€".encode("utf-8")


def test_encode_unknown_encoding_falls_back():
    """LookupError path: unknown encoding → utf-8."""
    result = DET.encode("hello", "not-a-real-encoding")
    assert result == b"hello"


def test_encode_empty_string():
    assert DET.encode("") == b""


# --- convert ----------------------------------------------------------------

def test_convert_round_trip():
    """encode → convert back → original bytes."""
    original = "héllo wörld".encode("utf-8")
    as_latin = DET.convert(original, "utf-8", "iso-8859-1")
    back = DET.convert(as_latin, "iso-8859-1", "utf-8")
    assert back == original


def test_convert_ascii_to_utf8():
    assert DET.convert(b"hello", "ascii", "utf-8") == b"hello"


def test_convert_empty():
    assert DET.convert(b"", "utf-8", "utf-8") == b""


# --- normalize_whitespace ---------------------------------------------------

def test_normalize_whitespace_basic():
    assert DET.normalize_whitespace("  hello   world  ") == "hello world"


def test_normalize_whitespace_empty():
    assert DET.normalize_whitespace("") == ""


def test_normalize_whitespace_only_whitespace():
    assert DET.normalize_whitespace("   \t\n  ") == ""


def test_normalize_whitespace_tabs_and_newlines():
    assert DET.normalize_whitespace("a\tb\nc") == "a b c"


def test_normalize_whitespace_idempotent():
    """Property: normalize(normalize(x)) == normalize(x)."""
    samples = ["  a  b  ", "a\tb\nc", "", "   ", "x"]
    for s in samples:
        once = DET.normalize_whitespace(s)
        twice = DET.normalize_whitespace(once)
        assert once == twice, f"idempotence violated for {s!r}"


def test_normalize_whitespace_unicode_spaces():
    """Unicode whitespace (NBSP, etc.) is matched by \\s in Python 3."""
    # \xa0 is NBSP; Python re \\s matches it in unicode mode.
    result = DET.normalize_whitespace("a\xa0b")
    assert result == "a b"


# --- remove_control_chars ---------------------------------------------------

def test_remove_control_chars_basic():
    assert DET.remove_control_chars("hello\x00world") == "helloworld"


def test_remove_control_chars_preserves_tab_newline():
    """\\x09 (tab) and \\x0a (newline) are NOT in the removal set."""
    assert DET.remove_control_chars("a\tb\nc") == "a\tb\nc"


def test_remove_control_chars_empty():
    assert DET.remove_control_chars("") == ""


def test_remove_control_chars_all_control():
    """All chars in the removal set are stripped."""
    s = "\x00\x01\x02\x03\x04\x05\x06\x07\x08\x0b\x0c\x0e\x0f\x10\x11\x12\x13\x14\x15\x16\x17\x18\x19\x1a\x1b\x1c\x1d\x1e\x1f\x7f"
    assert DET.remove_control_chars(s) == ""


def test_remove_control_chars_preserves_printable():
    assert DET.remove_control_chars("hello world 123") == "hello world 123"


# --- sanitize (composition) -------------------------------------------------

def test_sanitize_combines_remove_and_normalize():
    assert DET.sanitize("  hello\x00  world  ") == "hello world"


def test_sanitize_empty():
    assert DET.sanitize("") == ""


def test_sanitize_only_control_chars():
    assert DET.sanitize("\x00\x01\x02") == ""


def test_sanitize_idempotent():
    """Property: sanitize(sanitize(x)) == sanitize(x)."""
    samples = ["  a\x00b  ", "x", "", "\x00\x01"]
    for s in samples:
        once = DET.sanitize(s)
        twice = DET.sanitize(once)
        assert once == twice, f"idempotence violated for {s!r}"


# --- round-trip property: encode → decode -----------------------------------

def test_round_trip_encode_decode_utf8():
    """Property: encode(s, 'utf-8') → decode → s for arbitrary unicode."""
    samples = ["hello", "café", "日本語", "€£¥", "", "a b  c"]
    for s in samples:
        encoded = DET.encode(s, "utf-8")
        decoded = DET.decode(encoded, "utf-8")
        assert decoded == s, f"round-trip failed for {s!r}"


def test_round_trip_encode_decode_ascii():
    """Property: encode(s, 'ascii') → decode → s for ASCII-only strings."""
    samples = ["hello", "12345", "a b c", ""]
    for s in samples:
        encoded = DET.encode(s, "ascii")
        decoded = DET.decode(encoded, "ascii")
        assert decoded == s


# --- end-to-end CLI run -----------------------------------------------------

def test_end_to_end_cli_init_and_search(tmp_path):
    """End-to-end: init + search on an empty index (exit 0, no crash)."""
    from click.testing import CliRunner
    from personal_index.cli import main

    runner = CliRunner()
    dd = str(tmp_path / "data")
    r = runner.invoke(main, ["init", "--data-dir", dd])
    assert r.exit_code == 0, r.output
    assert "Initialized" in r.output

    r = runner.invoke(main, ["search", "python", "--data-dir", dd, "--format", "json"])
    assert r.exit_code == 0, r.output
    assert "No indexed content found" in r.output
