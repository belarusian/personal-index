"""Tests for personal_index.content_dedup module."""

from __future__ import annotations

from personal_index.content_dedup import (
    ContentDeduplicator,
    DedupResult,
    DocumentHash,
    DuplicateGroup,
    content_hash,
    normalize_url,
    text_similarity,
    url_hash,
)

# ── normalize_url ──────────────────────────────────────────────────

class TestNormalizeUrl:
    """Tests for content_dedup.normalize_url."""

    def test_trailing_slash_removal(self) -> None:
        assert normalize_url("https://example.com/") == "https://example.com"

    def test_fragment_removal(self) -> None:
        assert (
            normalize_url("https://example.com/page#section")
            == "https://example.com/page"
        )

    def test_case_normalization(self) -> None:
        assert (
            normalize_url("HTTPS://EXAMPLE.COM/page")
            == "https://example.com/page"
        )

    def test_empty_url(self) -> None:
        assert normalize_url("") == ""

    def test_no_change_needed(self) -> None:
        assert (
            normalize_url("https://example.com/page")
            == "https://example.com/page"
        )

    def test_trailing_slash_and_fragment(self) -> None:
        assert (
            normalize_url("https://example.com/path/#frag")
            == "https://example.com/path"
        )


    def test_path_case_preserved(self) -> None:
        """Uppercase path segments are NOT lowercased (only scheme+host are)."""
        assert (
            normalize_url("https://example.com/MyPage/Section")
            == "https://example.com/MyPage/Section"
        )

# ── content_hash ───────────────────────────────────────────────────

class TestContentHash:
    """Tests for content_hash."""

    def test_deterministic(self) -> None:
        h1 = content_hash("Hello world")
        h2 = content_hash("Hello world")
        assert h1 == h2

    def test_different_content_different_hash(self) -> None:
        h1 = content_hash("Hello world")
        h2 = content_hash("Goodbye world")
        assert h1 != h2

    def test_empty_input(self) -> None:
        assert content_hash("") == ""

    def test_whitespace_normalized(self) -> None:
        h1 = content_hash("Hello  world")
        h2 = content_hash("Hello world")
        assert h1 == h2

    def test_case_insensitive(self) -> None:
        h1 = content_hash("Hello World")
        h2 = content_hash("hello world")
        assert h1 == h2


# ── url_hash ───────────────────────────────────────────────────────

class TestUrlHash:
    """Tests for url_hash."""

    def test_deterministic(self) -> None:
        h1 = url_hash("https://example.com/page")
        h2 = url_hash("https://example.com/page")
        assert h1 == h2

    def test_normalized_urls_same_hash(self) -> None:
        h1 = url_hash("https://example.com/")
        h2 = url_hash("https://example.com")
        assert h1 == h2

    def test_empty_input(self) -> None:
        h = url_hash("")
        assert isinstance(h, str)
        assert len(h) == 64  # SHA-256 hex length


# ── text_similarity ────────────────────────────────────────────────

class TestTextSimilarity:
    """Tests for text_similarity."""

    def test_identical_texts(self) -> None:
        assert text_similarity("hello world", "hello world") == 1.0

    def test_disjoint_texts(self) -> None:
        assert text_similarity("hello world", "foo bar baz") == 0.0

    def test_partial_overlap(self) -> None:
        sim = text_similarity("hello world foo", "hello world bar")
        assert 0.0 < sim < 1.0

    def test_empty_first_string(self) -> None:
        assert text_similarity("", "hello") == 0.0

    def test_empty_second_string(self) -> None:
        assert text_similarity("hello", "") == 0.0

    def test_both_empty(self) -> None:
        assert text_similarity("", "") == 0.0


# ── DuplicateGroup ─────────────────────────────────────────────────

class TestDuplicateGroup:
    """Tests for DuplicateGroup dataclass."""

    def test_total_count(self) -> None:
        group = DuplicateGroup(
            representative="https://a.com",
            duplicates=["https://b.com", "https://c.com"],
        )
        assert group.total_count == 3

    def test_total_count_no_duplicates(self) -> None:
        group = DuplicateGroup(representative="https://a.com")
        assert group.total_count == 1

    def test_to_dict(self) -> None:
        group = DuplicateGroup(
            representative="https://a.com",
            duplicates=["https://b.com"],
            similarity_score=0.95,
            dedup_method="hash",
        )
        d = group.to_dict()
        assert d["representative"] == "https://a.com"
        assert d["duplicates"] == ["https://b.com"]
        assert d["similarity_score"] == 0.95
        assert d["dedup_method"] == "hash"
        assert d["total_count"] == 2


# ── DedupResult ────────────────────────────────────────────────────

class TestDedupResult:
    """Tests for DedupResult dataclass."""

    def test_dedup_ratio(self) -> None:
        result = DedupResult(
            total_items=10,
            unique_items=7,
            removed_count=3,
        )
        assert result.dedup_ratio == 0.3

    def test_dedup_ratio_empty(self) -> None:
        result = DedupResult()
        assert result.dedup_ratio == 0.0

    def test_summary(self) -> None:
        result = DedupResult(
            total_items=10,
            unique_items=7,
            removed_count=3,
            duplicate_groups=[DuplicateGroup(representative="a")],
            method="hash",
        )
        summary = result.summary()
        assert "Total items: 10" in summary
        assert "Unique items: 7" in summary
        assert "Duplicates found: 3" in summary
        assert "Method: hash" in summary


# ── DocumentHash ───────────────────────────────────────────────────

class TestDocumentHash:
    """Tests for DocumentHash class."""

    def test_compute_fingerprint(self) -> None:
        fp = DocumentHash.compute_fingerprint("Hello world")
        assert isinstance(fp, str)
        assert len(fp) == 16

    def test_compute_fingerprint_deterministic(self) -> None:
        fp1 = DocumentHash.compute_fingerprint("Hello world")
        fp2 = DocumentHash.compute_fingerprint("Hello world")
        assert fp1 == fp2

    def test_compute_fingerprint_different_content(self) -> None:
        fp1 = DocumentHash.compute_fingerprint("Hello")
        fp2 = DocumentHash.compute_fingerprint("World")
        assert fp1 != fp2


# ── ContentDeduplicator ────────────────────────────────────────────

class TestContentDeduplicator:
    """Tests for ContentDeduplicator class."""

    def setup_method(self) -> None:
        self.dedup = ContentDeduplicator(similarity_threshold=0.8)

    # ── dedup_by_hash ────────────────────────────────────────────

    def test_dedup_by_hash_exact_duplicates(self) -> None:
        items = [
            {"url": "https://a.com", "content": "Hello world"},
            {"url": "https://b.com", "content": "Hello world"},
            {"url": "https://c.com", "content": "Different content"},
        ]
        result = self.dedup.dedup_by_hash(items)
        assert result.removed_count == 1
        assert len(result.duplicate_groups) == 1

    def test_dedup_by_hash_no_duplicates(self) -> None:
        items = [
            {"url": "https://a.com", "content": "Content A"},
            {"url": "https://b.com", "content": "Content B"},
        ]
        result = self.dedup.dedup_by_hash(items)
        assert result.removed_count == 0
        assert len(result.duplicate_groups) == 0

    def test_dedup_by_hash_custom_hash_field(self) -> None:
        items = [
            {"url": "https://a.com", "title": "Same Title"},
            {"url": "https://b.com", "title": "Same Title"},
            {"url": "https://c.com", "title": "Different Title"},
        ]
        result = self.dedup.dedup_by_hash(items, hash_field="title")
        assert result.removed_count == 1

    def test_dedup_by_hash_empty_items(self) -> None:
        result = self.dedup.dedup_by_hash([])
        assert result.total_items == 0
        assert result.removed_count == 0

    # ── dedup_by_url ─────────────────────────────────────────────

    def test_dedup_by_url_normalized(self) -> None:
        items = [
            {"url": "https://example.com/"},
            {"url": "https://example.com"},
            {"url": "https://other.com"},
        ]
        result = self.dedup.dedup_by_url(items)
        assert result.removed_count == 1

    def test_dedup_by_url_no_duplicates(self) -> None:
        items = [
            {"url": "https://a.com"},
            {"url": "https://b.com"},
        ]
        result = self.dedup.dedup_by_url(items)
        assert result.removed_count == 0

    def test_dedup_by_url_empty_urls_not_duplicates(self) -> None:
        """Items with no URL cannot be deduplicated by URL.

        An empty URL must not be grouped with other empty-URL items (mirrors
        the `if h:` guard in _group_by_hash for empty content).
        """
        items = [
            {"url": "", "content": "a"},
            {"url": "", "content": "b"},
            {"url": "", "content": "c"},
        ]
        result = self.dedup.dedup_by_url(items)
        assert result.removed_count == 0
        assert result.unique_items == 3
        assert result.duplicate_groups == []

    def test_dedup_by_url_mixed_empty_and_real(self) -> None:
        """Empty-URL items are kept; real URL duplicates are still removed."""
        items = [
            {"url": "", "content": "a"},
            {"url": "https://x.com/"},
            {"url": "https://x.com"},
        ]
        result = self.dedup.dedup_by_url(items)
        assert result.removed_count == 1
        assert result.unique_items == 2
        assert len(result.duplicate_groups) == 1
        assert result.duplicate_groups[0].representative == "https://x.com/"

    # ── dedup_by_similarity ──────────────────────────────────────

    def test_dedup_by_similarity_above_threshold(self) -> None:
        items = [
            {"url": "https://a.com", "content": "Python is a great programming language"},
            {"url": "https://b.com", "content": "Python is a great programming language"},
            {"url": "https://c.com", "content": "Completely different topic here"},
        ]
        result = self.dedup.dedup_by_similarity(items)
        assert result.removed_count >= 1

    def test_dedup_by_similarity_below_threshold(self) -> None:
        dedup = ContentDeduplicator(similarity_threshold=0.99)
        items = [
            {"url": "https://a.com", "content": "Python programming tutorial"},
            {"url": "https://b.com", "content": "Python programming guide"},
        ]
        result = dedup.dedup_by_similarity(items)
        assert result.removed_count == 0

    # ── dedup_all ────────────────────────────────────────────────

    def test_dedup_all_combined(self) -> None:
        items = [
            {"url": "https://a.com/", "content": "Hello world"},
            {"url": "https://a.com", "content": "Hello world"},
            {"url": "https://b.com", "content": "Hello world"},
            {"url": "https://c.com", "content": "Different"},
        ]
        result = self.dedup.dedup_all(items)
        assert result.removed_count >= 2
        assert result.method == "combined"

    # ── _check_single_item ───────────────────────────────────────

    def test_check_single_item_not_duplicate(self) -> None:
        dedup = ContentDeduplicator()
        result = dedup._check_single_item(
            url="https://a.com",
            _title="Test",
            content="Hello world",
        )
        assert result.is_duplicate is False
        assert result.unique_items == 1

    def test_check_single_item_is_duplicate(self) -> None:
        dedup = ContentDeduplicator()
        dedup._check_single_item(
            url="https://a.com",
            _title="Test",
            content="Hello world",
        )
        result = dedup._check_single_item(
            url="https://b.com",
            _title="Test",
            content="Hello world",
        )
        assert result.is_duplicate is True
        assert result.removed_count == 1


# ── docstring contract (TICKET-333) ────────────────────────────────

class TestContentDedupDocstring:
    def test_dedup_all_docstring_does_not_promise_all_strategies(self) -> None:
        """Regression: dedup_all docstring must not over-promise 'all strategies'.

        ContentDeduplicator defines three strategies (dedup_by_hash,
        dedup_by_url, dedup_by_similarity), but dedup_all invokes only the
        URL and content-hash strategies (it never calls dedup_by_similarity).
        The docstring must therefore not claim it runs 'all deduplication
        strategies' (TICKET-333).
        """
        doc = (ContentDeduplicator.dedup_all.__doc__ or "").lower()
        assert "all deduplication strategies" not in doc
        # The corrected contract names the two strategies actually run.
        assert "url" in doc
        assert "hash" in doc
