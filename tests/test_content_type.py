"""Tests for content type detection module."""

from __future__ import annotations

import inspect

from personal_index.content_type import (
    ContentTypeDetector,
    ContentTypeInfo,
)


class TestContentTypeInfo:
    def test_text_info(self):
        info = ContentTypeInfo(
            mime_type="text/plain",
            category="text",
            extension=".txt",
            is_text=True,
            is_media=False,
            is_document=False,
        )
        assert info.is_downloadable is True

    def test_document_info(self):
        info = ContentTypeInfo(
            mime_type="application/pdf",
            category="document",
            extension=".pdf",
            is_text=False,
            is_media=False,
            is_document=True,
        )
        assert info.is_downloadable is True

    def test_media_info_not_downloadable(self):
        info = ContentTypeInfo(
            mime_type="image/png",
            category="image",
            extension=".png",
            is_text=False,
            is_media=True,
            is_document=False,
        )
        assert info.is_downloadable is False


    def test_media_category_is_documented(self):
        """The category field comment must document the "media" value the detector emits."""
        src = inspect.getsource(ContentTypeInfo)
        cat_line = next(line for line in src.splitlines() if line.strip().startswith("category:"))
        assert 'media' in cat_line


class TestContentTypeDetector:
    def setup_method(self):
        self.detector = ContentTypeDetector()

    # --- detect_from_url ---

    def test_detect_html_url(self):
        info = self.detector.detect_from_url("https://example.com/page.html")
        assert info.category == "text"
        assert info.is_text is True

    def test_detect_pdf_url(self):
        info = self.detector.detect_from_url("https://example.com/doc.pdf")
        assert info.category == "document"
        assert info.is_document is True

    def test_detect_unknown_url(self):
        info = self.detector.detect_from_url("https://example.com/noext")
        assert info.category == "unknown"

    def test_detect_url_with_query(self):
        info = self.detector.detect_from_url("https://example.com/file.txt?q=1")
        assert info.extension == ".txt"

    # --- detect_from_filename ---

    def test_detect_md_file(self):
        info = self.detector.detect_from_filename("notes.md")
        assert info.category == "text"
        assert info.is_text is True

    def test_detect_docx_file(self):
        info = self.detector.detect_from_filename("report.docx")
        assert info.category == "document"
        assert info.is_document is True

    def test_detect_png_file(self):
        info = self.detector.detect_from_filename("photo.png")
        assert info.is_media is True

    def test_detect_zip_file(self):
        info = self.detector.detect_from_filename("archive.zip")
        assert info.category == "archive"

    # --- detect_from_extension ---

    def test_detect_py_extension(self):
        info = self.detector.detect_from_extension(".py")
        assert info.category == "text"

    def test_detect_json_extension(self):
        info = self.detector.detect_from_extension(".json")
        assert info.category == "text"

    def test_detect_mp3_extension(self):
        info = self.detector.detect_from_extension(".mp3")
        assert info.is_media is True

    def test_detect_unknown_extension(self):
        info = self.detector.detect_from_extension(".xyz")
        assert info.category in ("unknown", "text", "image", "video", "audio", "document", "archive")

    def test_extension_without_dot(self):
        info = self.detector.detect_from_extension("txt")
        assert info.extension == ".txt"

    # --- detect_from_bytes ---

    def test_detect_pdf_bytes(self):
        info = self.detector.detect_from_bytes(b"%PDF-1.4 test content")
        assert info.mime_type == "application/pdf"
        assert info.category == "document"

    def test_detect_gzip_bytes(self):
        info = self.detector.detect_from_bytes(b"\x1f\x8b\x08\x00test")
        assert info.mime_type == "application/gzip"

    def test_detect_zip_bytes(self):
        info = self.detector.detect_from_bytes(b"PK\x03\x04test")
        assert info.mime_type == "application/zip"

    def test_detect_png_bytes(self):
        info = self.detector.detect_from_bytes(b"\x89PNG\r\n\x1a\n")
        assert info.mime_type == "image/png"

    def test_detect_jpeg_bytes(self):
        info = self.detector.detect_from_bytes(b"\xff\xd8\xff\xe0test")
        assert info.mime_type == "image/jpeg"

    def test_detect_gif_bytes(self):
        info = self.detector.detect_from_bytes(b"GIF89atest")
        assert info.mime_type == "image/gif"

    def test_detect_webp_bytes(self):
        info = self.detector.detect_from_bytes(b"RIFF\x00\x00\x00\x00WEBP")
        assert info.mime_type == "image/webp"

    def test_detect_text_bytes(self):
        info = self.detector.detect_from_bytes(b"Hello world, this is text content")
        assert info.mime_type == "text/plain"
        assert info.is_text is True

    def test_detect_binary_bytes(self):
        info = self.detector.detect_from_bytes(b"\x00\x01\x02\x03\x04\x05")
        assert info.category == "unknown"

    def test_detect_empty_bytes(self):
        info = self.detector.detect_from_bytes(b"")
        assert info.category == "unknown"

    # --- classify ---

    def test_classify_text_plain(self):
        assert self.detector.classify("text/plain") == "text"

    def test_classify_text_html(self):
        assert self.detector.classify("text/html") == "text"

    def test_classify_image_png(self):
        assert self.detector.classify("image/png") == "image"

    def test_classify_video_mp4(self):
        assert self.detector.classify("video/mp4") == "video"

    def test_classify_audio_mp3(self):
        assert self.detector.classify("audio/mpeg") == "audio"

    def test_classify_pdf(self):
        assert self.detector.classify("application/pdf") == "document"

    def test_classify_json(self):
        assert self.detector.classify("application/json") == "text"

    def test_classify_unknown(self):
        assert self.detector.classify("application/octet-stream") == "unknown"

    def test_classify_empty(self):
        assert self.detector.classify("") == "unknown"

    def test_classify_no_slash(self):
        assert self.detector.classify("weirdtype") == "unknown"

    # --- should_index ---

    def test_should_index_text(self):
        assert self.detector.should_index("https://example.com/page.html") is True

    def test_should_index_pdf(self):
        assert self.detector.should_index("https://example.com/doc.pdf") is True

    def test_should_not_index_image(self):
        assert self.detector.should_index("https://example.com/photo.png") is False

    def test_should_not_index_video(self):
        assert self.detector.should_index("https://example.com/video.mp4") is False

    def test_should_not_index_archive(self):
        assert self.detector.should_index("https://example.com/file.zip") is False

    def test_should_index_with_content_type(self):
        assert self.detector.should_index("https://example.com/x", "text/html") is True

    def test_should_not_index_with_content_type(self):
        assert self.detector.should_index("https://example.com/x", "image/png") is False

    # --- caching ---

    def test_extension_caching(self):
        info1 = self.detector.detect_from_extension(".txt")
        info2 = self.detector.detect_from_extension(".txt")
        assert info1 is info2


class TestCheckMagicNumbers:
    """Tests for _check_magic_numbers helper."""

    def setup_method(self):
        self.detector = ContentTypeDetector()

    def test_pdf_magic(self):
        result = self.detector._check_magic_numbers(b"%PDF-1.4 test")
        assert result is not None
        assert result.mime_type == "application/pdf"

    def test_gzip_magic(self):
        result = self.detector._check_magic_numbers(b"\x1f\x8b\x08\x00test")
        assert result is not None
        assert result.mime_type == "application/gzip"

    def test_zip_magic(self):
        result = self.detector._check_magic_numbers(b"PK\x03\x04test")
        assert result is not None
        assert result.mime_type == "application/zip"

    def test_png_magic(self):
        result = self.detector._check_magic_numbers(b"\x89PNG\r\n\x1a\n")
        assert result is not None
        assert result.mime_type == "image/png"

    def test_jpeg_magic(self):
        result = self.detector._check_magic_numbers(b"\xff\xd8\xff\xe0test")
        assert result is not None
        assert result.mime_type == "image/jpeg"

    def test_gif87a_magic(self):
        result = self.detector._check_magic_numbers(b"GIF87atest")
        assert result is not None
        assert result.mime_type == "image/gif"

    def test_gif89a_magic(self):
        result = self.detector._check_magic_numbers(b"GIF89atest")
        assert result is not None
        assert result.mime_type == "image/gif"

    def test_webp_magic(self):
        result = self.detector._check_magic_numbers(b"RIFF\x00\x00\x00\x00WEBP")
        assert result is not None
        assert result.mime_type == "image/webp"

    def test_no_magic_match(self):
        result = self.detector._check_magic_numbers(b"Hello world text")
        assert result is None

    def test_binary_no_magic(self):
        result = self.detector._check_magic_numbers(b"\x00\x01\x02\x03")
        assert result is None
