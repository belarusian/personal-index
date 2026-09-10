"""Adversarial deep tests for personal_index/content_type.py (cycle 200).

content_type is a never-probed subsystem: it has no dedicated docs page and
no prior tests/deep coverage. This file pins the documented/observed
classification semantics with guard inputs (None/empty/whitespace/unicode/
duplicate/out-of-range), round-trips, idempotence, and property checks, plus
one end-to-end CLI run.

No defect was found: every adversarial input behaved consistently with the
module's own docstrings and the CATEGORY_MAP / *_EXTENSIONS tables. These
tests are regression armor.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from personal_index.content_type import (
    ARCHIVE_EXTENSIONS,
    DOCUMENT_EXTENSIONS,
    MEDIA_EXTENSIONS,
    TEXT_EXTENSIONS,
    ContentTypeDetector,
)


@pytest.fixture
def det() -> ContentTypeDetector:
    return ContentTypeDetector()


# ===========================================================================
# detect_from_extension
# ===========================================================================
class TestDetectFromExtension:
    def test_text_extension(self, det):
        info = det.detect_from_extension(".txt")
        assert info.category == "text"
        assert info.is_text is True
        assert info.is_media is False
        assert info.is_document is False

    def test_document_extension(self, det):
        info = det.detect_from_extension(".pdf")
        assert info.category == "document"
        assert info.is_document is True
        assert info.is_text is False

    def test_image_extension(self, det):
        info = det.detect_from_extension(".png")
        assert info.category == "image"
        assert info.is_media is True
        assert info.is_text is False

    def test_media_video_extension(self, det):
        info = det.detect_from_extension(".mp4")
        assert info.category == "media"
        assert info.is_media is True

    def test_archive_extension(self, det):
        info = det.detect_from_extension(".zip")
        assert info.category == "archive"
        assert info.is_media is False
        assert info.is_document is False

    def test_no_leading_dot_normalized(self, det):
        info = det.detect_from_extension("pdf")
        assert info.extension == ".pdf"
        assert info.category == "document"

    def test_uppercase_normalized(self, det):
        info = det.detect_from_extension("PDF")
        assert info.extension == ".pdf"
        assert info.category == "document"

    def test_unknown_extension(self, det):
        info = det.detect_from_extension(".xyzzy")
        assert info.category == "unknown"
        assert info.is_text is False
        assert info.is_media is False
        assert info.is_document is False

    def test_empty_extension(self, det):
        # Empty ext -> Path("").suffix is "" -> normalized to "." -> unknown.
        info = det.detect_from_extension("")
        assert info.category == "unknown"

    def test_svg_dual_membership_resolves_to_text(self, det):
        # .svg appears in BOTH TEXT_EXTENSIONS and MEDIA_EXTENSIONS; the
        # classifier checks TEXT_EXTENSIONS first, so it resolves to "text".
        assert ".svg" in TEXT_EXTENSIONS
        assert ".svg" in MEDIA_EXTENSIONS
        info = det.detect_from_extension(".svg")
        assert info.category == "text"
        assert info.is_text is True
        assert info.is_media is False

    def test_cache_idempotence_same_object(self, det):
        a = det.detect_from_extension(".pdf")
        b = det.detect_from_extension(".pdf")
        assert a is b  # cached, identical object returned

    def test_cache_keyed_by_normalized_ext(self, det):
        a = det.detect_from_extension("PDF")
        b = det.detect_from_extension(".pdf")
        assert a is b  # both normalize to ".pdf" -> same cache entry


# ===========================================================================
# detect_from_url
# ===========================================================================
class TestDetectFromUrl:
    def test_url_with_extension(self, det):
        info = det.detect_from_url("https://example.com/a.pdf")
        assert info.category == "document"

    def test_url_query_string_stripped(self, det):
        info = det.detect_from_url("https://example.com/a.pdf?download=1")
        assert info.category == "document"

    def test_url_fragment_stripped(self, det):
        info = det.detect_from_url("https://example.com/a.pdf#frag")
        assert info.category == "document"

    def test_url_no_extension_mime_fallback(self, det):
        info = det.detect_from_url("https://example.com/file.html")
        assert info.category == "text"

    def test_url_no_extension_unknown(self, det):
        info = det.detect_from_url("https://example.com/file")
        assert info.category == "unknown"

    def test_url_double_extension_uses_last(self, det):
        # Path("a.tar.gz").suffix == ".gz" -> archive.
        info = det.detect_from_url("https://example.com/a.tar.gz")
        assert info.extension == ".gz"
        assert info.category == "archive"

    def test_url_empty(self, det):
        info = det.detect_from_url("")
        assert info.category == "unknown"

    def test_url_whitespace(self, det):
        info = det.detect_from_url("   ")
        assert info.category == "unknown"


# ===========================================================================
# detect_from_filename
# ===========================================================================
class TestDetectFromFilename:
    def test_filename_with_extension(self, det):
        info = det.detect_from_filename("report.pdf")
        assert info.category == "document"

    def test_filename_no_extension(self, det):
        info = det.detect_from_filename("README")
        assert info.category == "unknown"

    def test_filename_unicode(self, det):
        info = det.detect_from_filename("файл.txt")
        assert info.category == "text"

    def test_filename_empty(self, det):
        info = det.detect_from_filename("")
        assert info.category == "unknown"

    def test_filename_hidden_dotfile(self, det):
        # ".gitignore" -> Path.suffix is "" (no extension) -> unknown.
        info = det.detect_from_filename(".gitignore")
        assert info.category == "unknown"


# ===========================================================================
# detect_from_bytes
# ===========================================================================
class TestDetectFromBytes:
    def test_empty_bytes_unknown(self, det):
        info = det.detect_from_bytes(b"")
        assert info.category == "unknown"

    def test_null_byte_only_unknown(self, det):
        # A lone null byte decodes to "\x00" which contains a null -> not text.
        info = det.detect_from_bytes(b"\x00")
        assert info.category == "unknown"

    def test_valid_utf8_text(self, det):
        info = det.detect_from_bytes("hello world".encode("utf-8"))
        assert info.category == "text"

    def test_invalid_utf8_unknown(self, det):
        info = det.detect_from_bytes(b"\xff\xfe\x00\x01")
        assert info.category == "unknown"

    def test_magic_pdf(self, det):
        info = det.detect_from_bytes(b"%PDF-1.4 rest")
        assert info.category == "document"

    def test_magic_gzip(self, det):
        info = det.detect_from_bytes(b"\x1f\x8b" + b"x" * 10)
        assert info.category == "archive"

    def test_magic_zip(self, det):
        info = det.detect_from_bytes(b"PK\x03\x04" + b"x" * 10)
        assert info.category == "archive"

    def test_magic_png(self, det):
        info = det.detect_from_bytes(b"\x89PNG\r\n\x1a\n" + b"x" * 10)
        assert info.category == "image"

    def test_magic_jpeg(self, det):
        info = det.detect_from_bytes(b"\xff\xd8\xff" + b"x" * 10)
        assert info.category == "image"

    def test_magic_gif(self, det):
        info = det.detect_from_bytes(b"GIF89a" + b"x" * 10)
        assert info.category == "image"

    def test_magic_webp(self, det):
        info = det.detect_from_bytes(b"RIFF\x00\x00\x00\x00WEBP")
        assert info.category == "image"


# ===========================================================================
# classify
# ===========================================================================
class TestClassify:
    def test_empty_unknown(self, det):
        assert det.classify("") == "unknown"

    def test_direct_match_text(self, det):
        assert det.classify("text/html") == "text"

    def test_direct_match_image(self, det):
        assert det.classify("image/svg+xml") == "image"

    def test_direct_match_video(self, det):
        assert det.classify("video/mp4") == "video"

    def test_direct_match_archive(self, det):
        assert det.classify("application/zip") == "archive"

    def test_prefix_match(self, det):
        # "application/vnd.openxmlformats-officedocument..." starts with the
        # CATEGORY_MAP prefix "application/vnd.openxmlformats-officedocument".
        assert (
            det.classify(
                "application/vnd.openxmlformats-officedocument."
                "wordprocessingml.document"
            )
            == "document"
        )

    def test_major_type_fallback_text(self, det):
        assert det.classify("text/csv") == "text"

    def test_major_type_fallback_audio(self, det):
        assert det.classify("audio/mpeg") == "audio"

    def test_no_slash_unknown(self, det):
        assert det.classify("octetstream") == "unknown"

    def test_unrecognized_application(self, det):
        assert det.classify("application/vnd.rar") == "unknown"

    def test_charset_param_still_classifies(self, det):
        # Prefix match on "text/plain" still works with a charset param.
        assert det.classify("text/plain; charset=utf-8") == "text"


# ===========================================================================
# should_index
# ===========================================================================
class TestShouldIndex:
    def test_text_indexed(self, det):
        assert det.should_index("https://x/a.txt") is True

    def test_document_indexed(self, det):
        assert det.should_index("https://x/a.pdf") is True

    def test_media_not_indexed(self, det):
        assert det.should_index("https://x/a.mp4") is False

    def test_image_not_indexed(self, det):
        assert det.should_index("https://x/a.png") is False

    def test_unknown_not_indexed(self, det):
        assert det.should_index("https://x/a.bin") is False

    def test_explicit_content_type_overrides_url(self, det):
        # A URL with no extension but an explicit image MIME type is not indexed.
        assert det.should_index("https://x/whatever", "image/png") is False

    def test_explicit_document_content_type(self, det):
        assert det.should_index("https://x/whatever", "application/pdf") is True


# ===========================================================================
# is_downloadable property
# ===========================================================================
class TestIsDownloadable:
    def test_document_downloadable(self, det):
        assert det.detect_from_extension(".pdf").is_downloadable is True

    def test_text_downloadable(self, det):
        assert det.detect_from_extension(".txt").is_downloadable is True

    def test_image_not_downloadable(self, det):
        assert det.detect_from_extension(".png").is_downloadable is False

    def test_media_not_downloadable(self, det):
        assert det.detect_from_extension(".mp4").is_downloadable is False

    def test_archive_not_downloadable(self, det):
        assert det.detect_from_extension(".zip").is_downloadable is False


# ===========================================================================
# Extension-table invariants (property checks)
# ===========================================================================
class TestExtensionTableInvariants:
    def test_document_and_text_disjoint(self):
        assert DOCUMENT_EXTENSIONS.isdisjoint(TEXT_EXTENSIONS)

    def test_archive_and_document_disjoint(self):
        assert ARCHIVE_EXTENSIONS.isdisjoint(DOCUMENT_EXTENSIONS)

    def test_every_text_ext_classifies_text(self, det):
        for ext in TEXT_EXTENSIONS:
            assert det.detect_from_extension(ext).category == "text", ext

    def test_every_document_ext_classifies_document(self, det):
        for ext in DOCUMENT_EXTENSIONS:
            assert det.detect_from_extension(ext).category == "document", ext

    def test_every_archive_ext_classifies_archive(self, det):
        for ext in ARCHIVE_EXTENSIONS:
            assert det.detect_from_extension(ext).category == "archive", ext


# ===========================================================================
# End-to-end CLI run
# ===========================================================================
class TestCLIEndToEnd:
    """End-to-end CLI run (content_type is not directly wired to a
    subcommand; use `status` as the CLI smoke test, same pattern as
    cycle 162 / test_content_categorizer_adversarial.py)."""

    def test_cli_status_runs(self):
        result = subprocess.run(
            [sys.executable, "-m", "personal_index", "status"],
            capture_output=True,
            text=True,
            timeout=30,
            cwd=str(Path(__file__).resolve().parents[2]),
        )
        assert result.returncode == 0, f"CLI status failed: {result.stderr}"
