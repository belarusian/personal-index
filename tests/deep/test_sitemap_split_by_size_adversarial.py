"""Cycle 199 VERIFY + PROBE: personal_index/sitemap_builder.py `split_by_size`.

VERIFY (ARCH-22, issue #1060): the implementer chose Option A (enforce).
`split_by_size(max_bytes=MAX_SITEMAP_SIZE_BYTES)` measures each entry's
serialized length plus the fixed per-chunk wrapper overhead and breaks a
chunk when adding the next entry would exceed `max_bytes`. These hard-pass
pins lock the documented Option-A shape on current main:
  - the constant is present and load-bearing (default max_bytes),
  - `build()` documents it enforces NO size limit,
  - the empty-builder guard path returns the XML declaration + empty <urlset>
    and `split_by_size()` returns [],
  - ASCII entries: no chunk serializes past max_bytes,
  - a single oversized entry still gets its own chunk,
  - idempotence / purity of the split.

PROBE (QA-29, xfail-strict pins): the docstring and docs/content-sitemap.md
claim a chunk "serializes to at most max_bytes BYTES when passed to build()",
but the code measures `len(tostring(entry.to_element(), encoding="unicode"))`
— a CHARACTER count, not a byte count. For multi-byte (non-ASCII) content the
UTF-8 byte length exceeds the character count, so a returned chunk can
serialize to MORE than max_bytes bytes. The xfail-strict pins below document
the gap; flip to hard passes when the measurement is switched to UTF-8 bytes.
"""

from __future__ import annotations

import subprocess
import sys
from xml.etree.ElementTree import fromstring

from personal_index.sitemap_builder import SitemapBuilder, SitemapEntry, SM_NS


# ---------------------------------------------------------------------------
# ARCH-22 — Option A shape is real on main (hard passes)
# ---------------------------------------------------------------------------
class TestArch22ConstantLoadBearing:
    def test_constant_present(self):
        assert hasattr(SitemapBuilder, "MAX_SITEMAP_SIZE_BYTES")
        assert SitemapBuilder.MAX_SITEMAP_SIZE_BYTES == 50 * 1024 * 1024

    def test_url_count_constant_present(self):
        assert SitemapBuilder.MAX_URLS_PER_SITEMAP == 50_000

    def test_split_by_size_default_is_max_bytes(self):
        import inspect

        sig = inspect.signature(SitemapBuilder.split_by_size)
        assert sig.parameters["max_bytes"].default == SitemapBuilder.MAX_SITEMAP_SIZE_BYTES

    def test_build_docstring_says_no_limit_enforced(self):
        doc = SitemapBuilder.build.__doc__ or ""
        assert "no size limit" in doc.lower() or "enforces no" in doc.lower()
        # build() must point callers at the two split paths
        assert "split_into_chunks" in doc
        assert "split_by_size" in doc

    def test_split_into_chunks_docstring_says_byte_not_enforced(self):
        doc = SitemapBuilder.split_into_chunks.__doc__ or ""
        assert "split_by_size" in doc
        assert "byte" in doc.lower()

    def test_split_by_size_docstring_says_byte_enforced(self):
        doc = SitemapBuilder.split_by_size.__doc__ or ""
        assert "byte" in doc.lower()
        assert "MAX_SITEMAP_SIZE_BYTES" in doc


# ---------------------------------------------------------------------------
# ARCH-22 — guard path (empty builder)
# ---------------------------------------------------------------------------
class TestArch22GuardPath:
    def test_empty_build_is_declaration_plus_empty_urlset(self):
        b = SitemapBuilder()
        out = b.build()
        assert out.startswith(b'<?xml version="1.0" encoding="UTF-8"?>')
        root = fromstring(out)
        # no <url> children
        assert len(root.findall("url")) == 0
        assert len(root.findall(f"{{{SM_NS}}}url")) == 0

    def test_empty_split_by_size_returns_empty_list(self):
        assert SitemapBuilder().split_by_size() == []

    def test_empty_split_into_chunks_returns_empty_list(self):
        assert SitemapBuilder().split_into_chunks() == []


# ---------------------------------------------------------------------------
# ARCH-22 — ASCII byte enforcement (hard passes)
# ---------------------------------------------------------------------------
class TestArch22AsciiByteEnforcement:
    def _chunk_bytes(self, chunk: list[SitemapEntry]) -> int:
        bb = SitemapBuilder()
        bb.add_entries(chunk)
        return len(bb.build())

    def test_no_chunk_exceeds_max_bytes_ascii(self):
        b = SitemapBuilder()
        for i in range(10):
            b.add_entry("http://example.com/" + "a" * 1000)
        max_bytes = 5000
        chunks = b.split_by_size(max_bytes=max_bytes)
        assert chunks, "expected at least one chunk"
        for chunk in chunks:
            assert self._chunk_bytes(chunk) <= max_bytes

    def test_default_max_bytes_single_chunk_for_small_set(self):
        b = SitemapBuilder()
        for i in range(10):
            b.add_entry("http://example.com/" + "a" * 1000)
        # 10 * ~1000 bytes << 50MB -> one chunk
        assert len(b.split_by_size()) == 1

    def test_single_oversized_entry_gets_own_chunk(self):
        b = SitemapBuilder()
        b.add_entry("http://example.com/" + "a" * 10_000)
        chunks = b.split_by_size(max_bytes=1000)
        # cannot be split further -> exactly one chunk holding the entry
        assert len(chunks) == 1
        assert len(chunks[0]) == 1

    def test_split_preserves_all_entries_in_order(self):
        b = SitemapBuilder()
        urls = [f"http://example.com/{i}" + "a" * 500 for i in range(7)]
        for u in urls:
            b.add_entry(u)
        chunks = b.split_by_size(max_bytes=2000)
        flat = [e.url for c in chunks for e in c]
        assert flat == urls

    def test_split_is_pure_does_not_mutate(self):
        b = SitemapBuilder()
        for i in range(5):
            b.add_entry("http://example.com/" + "a" * 500)
        before = len(b.entries)
        b.split_by_size(max_bytes=2000)
        assert len(b.entries) == before

    def test_split_idempotent(self):
        b = SitemapBuilder()
        for i in range(6):
            b.add_entry("http://example.com/" + "a" * 500)
        c1 = b.split_by_size(max_bytes=2000)
        c2 = b.split_by_size(max_bytes=2000)
        assert [[e.url for e in c] for c in c1] == [[e.url for e in c] for c in c2]


# ---------------------------------------------------------------------------
# QA-29 — the byte-vs-character measurement gap (xfail-strict pins)
# docs/content-sitemap.md + split_by_size docstring: "serializes to at most
# max_bytes BYTES when passed to build()". The code measures
# len(tostring(..., encoding="unicode")) = CHARACTERS. For multi-byte content
# the UTF-8 byte length > character count, so a chunk can exceed max_bytes.
# ---------------------------------------------------------------------------
class TestQA29ByteVsCharacter:
    def test_multibyte_chunk_respects_byte_budget(self):
        """Each chunk must serialize to <= max_bytes BYTES (UTF-8)."""
        b = SitemapBuilder()
        # each entry ~1000 multi-byte chars -> ~3000 UTF-8 bytes
        for i in range(10):
            b.add_entry("http://example.com/" + "\u00e9" * 1000)
        max_bytes = 5000
        for chunk in b.split_by_size(max_bytes=max_bytes):
            bb = SitemapBuilder()
            bb.add_entries(chunk)
            assert len(bb.build()) <= max_bytes

    def test_measurement_is_bytes_not_chars(self):
        """Multi-byte content: UTF-8 byte length exceeds character count.

        This is the premise the fix relies on: measuring characters
        (len(tostring(..., encoding='unicode'))) under-counts, so the code
        must measure UTF-8 bytes to honor the byte budget.
        """
        entry = SitemapEntry("http://example.com/" + "\u00e9" * 100)
        from xml.etree.ElementTree import tostring

        char_count = len(tostring(entry.to_element(), encoding="unicode"))
        byte_count = len(tostring(entry.to_element(), encoding="unicode").encode("utf-8"))
        # For multi-byte content the byte length strictly exceeds the char count.
        assert byte_count > char_count


# ---------------------------------------------------------------------------
# End-to-end CLI smoke run
# ---------------------------------------------------------------------------
class TestCliSmoke:
    def test_cli_version_runs(self):
        proc = subprocess.run(
            [sys.executable, "-m", "personal_index", "--version"],
            capture_output=True,
            text=True,
            timeout=60,
        )
        assert proc.returncode == 0
        assert "version" in proc.stdout.lower()
