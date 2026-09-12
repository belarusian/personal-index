"""Adversarial deep tests for personal_index.versioning.

Contract sources: personal_index/versioning.py docstrings (ContentVersion.to_dict
exact contract; VersionTracker dedup/max-versions/clear semantics).

Attacks guard inputs (None/empty/whitespace/unicode/duplicate/out-of-range),
round-trips, idempotence, and property checks. No CLI exposure exists for this
module (not registered in cli.py), so end-to-end coverage is via the public
VersionTracker API directly.
"""

from __future__ import annotations

from typing import Any

from datetime import datetime

from personal_index.versioning import ContentVersion, VersionTracker


# ---------------------------------------------------------------------------
# ContentVersion.to_dict contract
# ---------------------------------------------------------------------------

def _cv(**kw: Any) -> ContentVersion:
    base: dict[str, Any] = dict(url="http://example.com", version_id="v1", content_hash="abc")
    base.update(kw)
    return ContentVersion(**base)


def test_to_dict_seven_keys_in_declaration_order():
    d = _cv().to_dict()
    assert list(d.keys()) == [
        "url", "version_id", "content_hash", "title",
        "content_length", "captured_at", "metadata",
    ]


def test_to_dict_returns_fresh_dict_each_call():
    v = _cv()
    a = v.to_dict()
    b = v.to_dict()
    assert a is not b


def test_to_dict_captured_at_is_isoformat_string():
    d = _cv().to_dict()
    assert isinstance(d["captured_at"], str)
    # round-trips back to a datetime
    datetime.fromisoformat(d["captured_at"])


def test_to_dict_metadata_same_reference_not_copied():
    meta = {"k": "v"}
    v = _cv(metadata=meta)
    d = v.to_dict()
    assert d["metadata"] is meta


def test_to_dict_is_pure_does_not_mutate_scalar_fields():
    # Docstring: to_dict is pure for scalar fields; metadata is the SAME
    # reference (documented, not a copy), so we only assert the scalars are
    # untouched by mutating the returned dict's scalar keys.
    v = _cv(title="orig", content_length=5)
    d = v.to_dict()
    d["title"] = "mutated"
    d["content_length"] = 999
    assert v.title == "orig"
    assert v.content_length == 5


def test_to_dict_unicode_fields_roundtrip():
    v = _cv(url="http://ex.com/é/日本語", title="Ünïcödé 标题", metadata={"x": "✓"})
    d = v.to_dict()
    assert d["url"] == "http://ex.com/é/日本語"
    assert d["title"] == "Ünïcödé 标题"
    assert d["metadata"]["x"] == "✓"


def test_to_dict_empty_string_fields():
    v = _cv(url="", title="", content_hash="")
    d = v.to_dict()
    assert d["url"] == ""
    assert d["title"] == ""
    assert d["content_hash"] == ""


# ---------------------------------------------------------------------------
# compute_hash / generate_version_id
# ---------------------------------------------------------------------------

def test_compute_hash_is_sha256_hexdigest():
    import hashlib
    assert VersionTracker.compute_hash("hello") == hashlib.sha256(b"hello").hexdigest()


def test_compute_hash_empty_string():
    import hashlib
    assert VersionTracker.compute_hash("") == hashlib.sha256(b"").hexdigest()


def test_compute_hash_unicode_deterministic():
    assert VersionTracker.compute_hash("café ☕") == VersionTracker.compute_hash("café ☕")
    assert VersionTracker.compute_hash("café ☕") != VersionTracker.compute_hash("café ☕ ")


def test_generate_version_id_is_12_chars():
    vid = VersionTracker.generate_version_id("http://x.com", "deadbeef")
    assert len(vid) == 12
    assert vid == VersionTracker.generate_version_id("http://x.com", "deadbeef")


def test_generate_version_id_differs_by_url_and_hash():
    a = VersionTracker.generate_version_id("http://a.com", "h")
    b = VersionTracker.generate_version_id("http://b.com", "h")
    c = VersionTracker.generate_version_id("http://a.com", "h2")
    assert len({a, b, c}) == 3


def test_generate_version_id_empty_inputs():
    # empty url + empty hash still yields a 12-char id (no crash)
    vid = VersionTracker.generate_version_id("", "")
    assert len(vid) == 12


# ---------------------------------------------------------------------------
# record_version: dedup, max_versions, metadata
# ---------------------------------------------------------------------------

def test_record_version_first_call_records():
    t = VersionTracker()
    v = t.record_version("http://x.com", "content1")
    assert t.get_change_count("http://x.com") == 1
    assert v.content_length == len("content1")


def test_record_version_consecutive_duplicate_is_noop():
    t = VersionTracker()
    v1 = t.record_version("http://x.com", "same")
    v2 = t.record_version("http://x.com", "same")
    assert v1 is v2
    assert t.get_change_count("http://x.com") == 1


def test_record_version_nonconsecutive_duplicate_is_recorded():
    t = VersionTracker()
    t.record_version("http://x.com", "A")
    t.record_version("http://x.com", "B")
    v3 = t.record_version("http://x.com", "A")  # A again, not consecutive
    assert t.get_change_count("http://x.com") == 3
    assert v3.content_hash == t.get_versions("http://x.com")[0].content_hash


def test_record_version_metadata_none_becomes_empty_dict():
    t = VersionTracker()
    v = t.record_version("http://x.com", "c", metadata=None)
    assert v.metadata == {}


def test_record_version_empty_content():
    t = VersionTracker()
    v = t.record_version("http://x.com", "")
    assert v.content_length == 0
    assert t.get_change_count("http://x.com") == 1


def test_record_version_whitespace_content_distinct():
    t = VersionTracker()
    t.record_version("http://x.com", "  ")
    t.record_version("http://x.com", "   ")
    assert t.get_change_count("http://x.com") == 2


def test_record_version_max_versions_enforced():
    t = VersionTracker(max_versions=3)
    for i in range(10):
        t.record_version("http://x.com", f"c{i}")
    versions = t.get_versions("http://x.com")
    assert len(versions) == 3
    # keeps the most recent three
    assert [v.content_length for v in versions] == [len("c7"), len("c8"), len("c9")]


def test_record_version_max_versions_zero_keeps_none():
    t = VersionTracker(max_versions=0)
    t.record_version("http://x.com", "c1")
    assert t.get_versions("http://x.com") == []


def test_record_version_per_url_isolation():
    t = VersionTracker()
    t.record_version("http://a.com", "x")
    t.record_version("http://b.com", "x")
    assert t.get_change_count("http://a.com") == 1
    assert t.get_change_count("http://b.com") == 1
    assert t.tracked_urls == 2


def test_record_version_idempotent_for_same_content():
    t = VersionTracker()
    for _ in range(5):
        t.record_version("http://x.com", "stable")
    assert t.get_change_count("http://x.com") == 1


# ---------------------------------------------------------------------------
# query methods
# ---------------------------------------------------------------------------

def test_get_versions_unknown_url_empty():
    t = VersionTracker()
    assert t.get_versions("http://nope.com") == []


def test_get_latest_unknown_url_none():
    t = VersionTracker()
    assert t.get_latest("http://nope.com") is None


def test_get_latest_returns_last():
    t = VersionTracker()
    t.record_version("http://x.com", "A")
    t.record_version("http://x.com", "B")
    assert t.get_latest("http://x.com").content_length == len("B")


def test_has_changed_no_versions_true():
    t = VersionTracker()
    assert t.has_changed("http://x.com", "anything") is True


def test_has_changed_same_content_false():
    t = VersionTracker()
    t.record_version("http://x.com", "same")
    assert t.has_changed("http://x.com", "same") is False


def test_has_changed_different_content_true():
    t = VersionTracker()
    t.record_version("http://x.com", "old")
    assert t.has_changed("http://x.com", "new") is True


def test_get_all_urls_reflects_tracked():
    t = VersionTracker()
    t.record_version("http://a.com", "x")
    t.record_version("http://b.com", "y")
    assert set(t.get_all_urls()) == {"http://a.com", "http://b.com"}


def test_get_all_urls_empty_tracker():
    assert VersionTracker().get_all_urls() == []


# ---------------------------------------------------------------------------
# clear / totals
# ---------------------------------------------------------------------------

def test_clear_single_url():
    t = VersionTracker()
    t.record_version("http://a.com", "x")
    t.record_version("http://b.com", "y")
    t.clear("http://a.com")
    assert t.get_all_urls() == ["http://b.com"]
    assert t.tracked_urls == 1


def test_clear_unknown_url_noop():
    t = VersionTracker()
    t.record_version("http://a.com", "x")
    t.clear("http://nope.com")
    assert t.tracked_urls == 1


def test_clear_all():
    t = VersionTracker()
    t.record_version("http://a.com", "x")
    t.record_version("http://b.com", "y")
    t.clear()
    assert t.get_all_urls() == []
    assert t.tracked_urls == 0
    assert t.total_versions == 0


def test_clear_none_clears_all():
    t = VersionTracker()
    t.record_version("http://a.com", "x")
    t.clear(None)
    assert t.tracked_urls == 0


def test_total_versions_sums_across_urls():
    t = VersionTracker()
    t.record_version("http://a.com", "1")
    t.record_version("http://a.com", "2")
    t.record_version("http://b.com", "3")
    assert t.total_versions == 3


def test_total_versions_empty():
    assert VersionTracker().total_versions == 0


# ---------------------------------------------------------------------------
# property / round-trip checks
# ---------------------------------------------------------------------------

def test_version_id_stable_across_trackers():
    t1 = VersionTracker()
    t2 = VersionTracker()
    v1 = t1.record_version("http://x.com", "content")
    v2 = t2.record_version("http://x.com", "content")
    assert v1.version_id == v2.version_id
    assert v1.content_hash == v2.content_hash


def test_to_dict_roundtrip_reconstructs_version():
    v = _cv(title="T", content_length=42, metadata={"m": 1})
    d = v.to_dict()
    rebuilt = ContentVersion(
        url=d["url"],
        version_id=d["version_id"],
        content_hash=d["content_hash"],
        title=d["title"],
        content_length=d["content_length"],
        captured_at=datetime.fromisoformat(d["captured_at"]),
        metadata=d["metadata"],
    )
    assert rebuilt.to_dict() == d
