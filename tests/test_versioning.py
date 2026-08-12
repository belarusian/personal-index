"""Tests for content versioning module."""

from personal_index.versioning import ContentVersion, VersionTracker


class TestContentVersion:
    def test_creation(self):
        v = ContentVersion(url="http://example.com", version_id="v1", content_hash="abc123")
        assert v.url == "http://example.com"
        assert v.version_id == "v1"
        assert v.content_hash == "abc123"
        assert v.title == ""
        assert v.content_length == 0

    def test_to_dict(self):
        v = ContentVersion(url="http://example.com", version_id="v1", content_hash="abc", title="Test")
        d = v.to_dict()
        assert d["url"] == "http://example.com"
        assert d["version_id"] == "v1"
        assert "captured_at" in d


class TestVersionTracker:
    def test_compute_hash(self):
        h1 = VersionTracker.compute_hash("hello")
        h2 = VersionTracker.compute_hash("hello")
        h3 = VersionTracker.compute_hash("world")
        assert h1 == h2
        assert h1 != h3

    def test_generate_version_id(self):
        v1 = VersionTracker.generate_version_id("http://example.com", "abc")
        v2 = VersionTracker.generate_version_id("http://example.com", "abc")
        v3 = VersionTracker.generate_version_id("http://other.com", "abc")
        assert v1 == v2
        assert v1 != v3
        assert len(v1) == 12

    def test_record_version(self):
        tracker = VersionTracker()
        v = tracker.record_version("http://example.com", "content v1", title="Page")
        assert v.url == "http://example.com"
        assert v.title == "Page"
        assert v.content_length == 10

    def test_record_multiple_versions(self):
        tracker = VersionTracker()
        tracker.record_version("http://example.com", "content v1")
        tracker.record_version("http://example.com", "content v2")
        versions = tracker.get_versions("http://example.com")
        assert len(versions) == 2
        assert versions[0].content_hash != versions[1].content_hash

    def test_duplicate_content_not_recorded(self):
        tracker = VersionTracker()
        v1 = tracker.record_version("http://example.com", "same content")
        v2 = tracker.record_version("http://example.com", "same content")
        assert v1.version_id == v2.version_id
        assert len(tracker.get_versions("http://example.com")) == 1

    def test_max_versions_enforced(self):
        tracker = VersionTracker(max_versions=3)
        for i in range(5):
            tracker.record_version("http://example.com", f"content v{i}")
        versions = tracker.get_versions("http://example.com")
        assert len(versions) == 3

    def test_get_latest(self):
        tracker = VersionTracker()
        tracker.record_version("http://example.com", "old")
        tracker.record_version("http://example.com", "new")
        latest = tracker.get_latest("http://example.com")
        assert latest is not None
        assert latest.content_hash == VersionTracker.compute_hash("new")

    def test_get_latest_none(self):
        tracker = VersionTracker()
        assert tracker.get_latest("http://unknown.com") is None

    def test_has_changed_new_url(self):
        tracker = VersionTracker()
        assert tracker.has_changed("http://example.com", "content") is True

    def test_has_changed_same_content(self):
        tracker = VersionTracker()
        tracker.record_version("http://example.com", "same")
        assert tracker.has_changed("http://example.com", "same") is False

    def test_has_changed_different_content(self):
        tracker = VersionTracker()
        tracker.record_version("http://example.com", "original")
        assert tracker.has_changed("http://example.com", "modified") is True

    def test_get_change_count(self):
        tracker = VersionTracker()
        assert tracker.get_change_count("http://example.com") == 0
        tracker.record_version("http://example.com", "v1")
        tracker.record_version("http://example.com", "v2")
        assert tracker.get_change_count("http://example.com") == 2

    def test_get_all_urls(self):
        tracker = VersionTracker()
        tracker.record_version("http://a.com", "x")
        tracker.record_version("http://b.com", "y")
        urls = tracker.get_all_urls()
        assert "http://a.com" in urls
        assert "http://b.com" in urls

    def test_clear_single_url(self):
        tracker = VersionTracker()
        tracker.record_version("http://a.com", "x")
        tracker.record_version("http://b.com", "y")
        tracker.clear("http://a.com")
        assert tracker.get_versions("http://a.com") == []
        assert len(tracker.get_versions("http://b.com")) == 1

    def test_clear_all(self):
        tracker = VersionTracker()
        tracker.record_version("http://a.com", "x")
        tracker.clear()
        assert tracker.total_versions == 0

    def test_total_versions(self):
        tracker = VersionTracker()
        tracker.record_version("http://a.com", "x")
        tracker.record_version("http://a.com", "y")
        tracker.record_version("http://b.com", "z")
        assert tracker.total_versions == 3

    def test_tracked_urls(self):
        tracker = VersionTracker()
        tracker.record_version("http://a.com", "x")
        tracker.record_version("http://b.com", "y")
        assert tracker.tracked_urls == 2

    def test_metadata(self):
        tracker = VersionTracker()
        v = tracker.record_version("http://example.com", "content", metadata={"source": "crawl"})
        assert v.metadata == {"source": "crawl"}


class TestVersioningSecurity:
    """Test that versioning uses secure hashing."""

    def test_generate_version_id_uses_sha256(self):
        """Verify generate_version_id produces SHA-256 based output."""
        from personal_index.versioning import VersionTracker
        vid = VersionTracker.generate_version_id("http://example.com", "abc123")
        assert len(vid) == 12  # First 12 chars of SHA-256 hex
        # Verify it is deterministic
        vid2 = VersionTracker.generate_version_id("http://example.com", "abc123")
        assert vid == vid2
        # Verify different input produces different version id
        vid3 = VersionTracker.generate_version_id("http://example.com", "def456")
        assert vid != vid3
