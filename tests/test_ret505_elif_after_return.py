"""Tests for TICKET-72: RET505 - unnecessary elif/else after return."""

from personal_index.bookmark_export import BookmarkExporter
from personal_index.content_archive.compressor import CompressionFormat, Compressor
from personal_index.content_priority import PriorityLevel


class TestBookmarkExporter:
    def test_export_format_json(self):
        exporter = BookmarkExporter(bookmarks=[])
        result = exporter.export(fmt="json")
        assert result is not None

    def test_export_format_html(self):
        exporter = BookmarkExporter(bookmarks=[])
        result = exporter.export(fmt="html")
        assert result is not None

    def test_export_format_none(self):
        exporter = BookmarkExporter(bookmarks=[])
        result = exporter.export(fmt="xml")
        assert result is None


class TestCompressor:
    def test_compress_gzip(self):
        compressor = Compressor()
        data = b"hello world"
        compressed = compressor.compress(data, CompressionFormat.GZIP)
        assert compressed != data

    def test_compress_zlib(self):
        compressor = Compressor()
        data = b"hello world"
        compressed = compressor.compress(data, CompressionFormat.ZLIB)
        assert compressed != data

    def test_decompress_gzip(self):
        compressor = Compressor()
        data = b"hello world"
        compressed = compressor.compress(data, CompressionFormat.GZIP)
        decompressed = compressor.decompress(compressed, CompressionFormat.GZIP)
        assert decompressed == data

    def test_decompress_zlib(self):
        compressor = Compressor()
        data = b"hello world"
        compressed = compressor.compress(data, CompressionFormat.ZLIB)
        decompressed = compressor.decompress(compressed, CompressionFormat.ZLIB)
        assert decompressed == data


class TestPriorityLevel:
    def test_from_score_critical(self):
        level = PriorityLevel.from_score(0.9)
        assert level == PriorityLevel.CRITICAL

    def test_from_score_high(self):
        level = PriorityLevel.from_score(0.7)
        assert level == PriorityLevel.HIGH

    def test_from_score_medium(self):
        level = PriorityLevel.from_score(0.5)
        assert level == PriorityLevel.MEDIUM

    def test_from_score_low(self):
        level = PriorityLevel.from_score(0.1)
        assert level == PriorityLevel.LOW
