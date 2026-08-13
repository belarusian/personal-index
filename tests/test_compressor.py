"""Tests for compression utilities."""

from personal_index.content_archive.compressor import (
    Compressor,
    CompressionFormat,
)


class TestCompressor:
    def test_compress_gzip(self):
        c = Compressor()
        data = b"hello world this is test data" * 10
        compressed = c.compress(data, CompressionFormat.GZIP)
        assert len(compressed) < len(data)

    def test_compress_zlib(self):
        c = Compressor()
        data = b"hello world this is test data" * 10
        compressed = c.compress(data, CompressionFormat.ZLIB)
        assert len(compressed) < len(data)

    def test_decompress_gzip(self):
        c = Compressor()
        original = b"hello world"
        compressed = c.compress(original, CompressionFormat.GZIP)
        assert c.decompress(compressed, CompressionFormat.GZIP) == original

    def test_decompress_zlib(self):
        c = Compressor()
        original = b"hello world"
        compressed = c.compress(original, CompressionFormat.ZLIB)
        assert c.decompress(compressed, CompressionFormat.ZLIB) == original

    def test_compress_text(self):
        c = Compressor()
        result = c.compress_text("hello world")
        assert isinstance(result, bytes)

    def test_decompress_text(self):
        c = Compressor()
        compressed = c.compress_text("hello world")
        assert c.decompress_text(compressed) == "hello world"

    def test_roundtrip_zlib(self):
        c = Compressor()
        text = "testing roundtrip compression"
        compressed = c.compress_text(text, CompressionFormat.ZLIB)
        assert c.decompress_text(compressed, CompressionFormat.ZLIB) == text

    def test_compression_ratio(self):
        c = Compressor()
        original = b"a" * 1000
        compressed = c.compress(original)
        ratio = c.compression_ratio(original, compressed)
        assert 0.0 < ratio < 1.0

    def test_compression_ratio_empty(self):
        c = Compressor()
        assert c.compression_ratio(b"", b"") == 0.0

    def test_get_stats(self):
        c = Compressor()
        original = b"a" * 1000
        compressed = c.compress(original)
        stats = c.get_stats(original, compressed)
        assert stats["original_size"] == 1000
        assert stats["compressed_size"] < 1000
        assert "savings_percent" in stats

    def test_get_stats_uncompressible(self):
        c = Compressor()
        import os
        original = os.urandom(100)
        compressed = c.compress(original)
        stats = c.get_stats(original, compressed)
        assert stats["ratio"] >= 0.9
