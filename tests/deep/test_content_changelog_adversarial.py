"""Adversarial deep tests for personal_index.content_changelog.

Cycle 181 — VALIDATOR probe.

Covers: None/empty/whitespace/unicode/duplicate/out-of-range inputs,
round-trips, idempotence, ordering/stability, boundary lengths,
defensive loads, and CLI-level contracts.

The module's contract (from docstrings):
- ChangeEntry: dataclass with url, change_type, timestamp, details
- ContentChangelog.add_entry: appends to internal list
- ContentChangelog.get_entries(url=None): returns a NEW list (copy),
  filtered by exact URL match when url is truthy, all entries when falsy
- ContentChangelog.clear: clears all entries
"""

from __future__ import annotations

from typing import Any

from personal_index.content_changelog import ChangeEntry, ContentChangelog


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _entry(
    url: str = "http://example.com",
    change_type: str = "modified",
    timestamp: str = "2026-01-01T00:00:00+00:00",
    details: dict[str, Any] | None = None,
) -> ChangeEntry:
    """Create a ChangeEntry with sensible defaults."""
    if details is None:
        details = {}
    return ChangeEntry(url=url, change_type=change_type, timestamp=timestamp, details=details)


# ---------------------------------------------------------------------------
# 1. ChangeEntry — construction and edge cases
# ---------------------------------------------------------------------------

class TestChangeEntry:
    """ChangeEntry dataclass construction edge cases."""

    def test_basic_construction(self) -> None:
        e = _entry()
        assert e.url == "http://example.com"
        assert e.change_type == "modified"
        assert e.timestamp == "2026-01-01T00:00:00+00:00"
        assert e.details == {}

    def test_empty_string_fields(self) -> None:
        e = ChangeEntry(url="", change_type="", timestamp="", details={})
        assert e.url == ""
        assert e.change_type == ""
        assert e.timestamp == ""
        assert e.details == {}

    def test_unicode_fields(self) -> None:
        e = ChangeEntry(
            url="http://пример.рф/путь",
            change_type="変更",
            timestamp="2026-01-01T00:00:00+00:00",
            details={"key": "値"},
        )
        assert e.url == "http://пример.рф/путь"
        assert e.change_type == "変更"
        assert e.details == {"key": "値"}

    def test_very_long_fields(self) -> None:
        e = ChangeEntry(
            url="http://example.com/" + "a" * 10_000,
            change_type="t" * 1_000,
            timestamp="z" * 100,
            details={"k": "v" * 10_000},
        )
        assert len(e.url) == 10_000 + len("http://example.com/")
        assert len(e.change_type) == 1_000
        assert len(e.details["k"]) == 10_000

    def test_details_default_factory_isolation(self) -> None:
        """Each entry must get its own details dict (not shared)."""
        e1 = ChangeEntry(url="a", change_type="t", timestamp="ts")
        e2 = ChangeEntry(url="b", change_type="t", timestamp="ts")
        e1.details["x"] = 1
        assert e2.details == {}

    def test_details_with_nested_structures(self) -> None:
        nested: dict[str, Any] = {"a": [1, 2, 3], "b": {"c": "d"}}
        e = ChangeEntry(url="u", change_type="t", timestamp="ts", details=nested)
        assert e.details == nested

    def test_details_with_none_values(self) -> None:
        e = ChangeEntry(url="u", change_type="t", timestamp="ts", details={"k": None})
        assert e.details == {"k": None}

    def test_none_url_accepted_no_runtime_type_check(self) -> None:
        """Plain @dataclass does not runtime-enforce str annotations.

        Passing None where a str is annotated is accepted (stored as None);
        the annotation is for static checkers (mypy), not runtime validation.
        This pins the actual behavior so a future __post_init__ guard is
        noticed if added.
        """
        e = ChangeEntry(url=None, change_type="t", timestamp="ts")  # type: ignore[arg-type]
        assert e.url is None

    def test_none_change_type_accepted(self) -> None:
        e = ChangeEntry(url="u", change_type=None, timestamp="ts")  # type: ignore[arg-type]
        assert e.change_type is None

    def test_none_timestamp_accepted(self) -> None:
        e = ChangeEntry(url="u", change_type="t", timestamp=None)  # type: ignore[arg-type]
        assert e.timestamp is None


# ---------------------------------------------------------------------------
# 2. ContentChangelog.__init__ and basic state
# ---------------------------------------------------------------------------

class TestContentChangelogInit:
    """ContentChangelog starts empty and independent."""

    def test_starts_empty(self) -> None:
        cl = ContentChangelog()
        assert cl.get_entries() == []

    def test_independent_instances(self) -> None:
        cl1 = ContentChangelog()
        cl2 = ContentChangelog()
        cl1.add_entry(_entry(url="http://a.com"))
        assert cl2.get_entries() == []

    def test_multiple_instances_no_shared_state(self) -> None:
        cl1 = ContentChangelog()
        cl2 = ContentChangelog()
        cl1.add_entry(_entry(url="http://a.com"))
        cl2.add_entry(_entry(url="http://b.com"))
        assert len(cl1.get_entries()) == 1
        assert len(cl2.get_entries()) == 1


# ---------------------------------------------------------------------------
# 3. add_entry — mutation, ordering, duplicates
# ---------------------------------------------------------------------------

class TestAddEntry:
    """add_entry must append correctly and handle edge cases."""

    def test_add_to_empty(self) -> None:
        cl = ContentChangelog()
        e = _entry(url="http://a.com")
        cl.add_entry(e)
        entries = cl.get_entries()
        assert len(entries) == 1
        assert entries[0].url == "http://a.com"

    def test_add_preserves_order(self) -> None:
        cl = ContentChangelog()
        cl.add_entry(_entry(url="http://1.com"))
        cl.add_entry(_entry(url="http://2.com"))
        cl.add_entry(_entry(url="http://3.com"))
        entries = cl.get_entries()
        assert [e.url for e in entries] == ["http://1.com", "http://2.com", "http://3.com"]

    def test_add_duplicate_url_is_allowed(self) -> None:
        """Multiple entries with the same URL are allowed (no uniqueness)."""
        cl = ContentChangelog()
        cl.add_entry(_entry(url="http://same.com", change_type="v1"))
        cl.add_entry(_entry(url="http://same.com", change_type="v2"))
        entries = cl.get_entries()
        assert len(entries) == 2
        assert entries[0].change_type == "v1"
        assert entries[1].change_type == "v2"

    def test_add_same_entry_object_twice(self) -> None:
        """Adding the same object reference twice stores two references."""
        cl = ContentChangelog()
        e = _entry(url="http://ref.com")
        cl.add_entry(e)
        cl.add_entry(e)
        entries = cl.get_entries()
        assert len(entries) == 2
        assert entries[0] is e
        assert entries[1] is e

    def test_add_none_appended_no_runtime_type_check(self) -> None:
        """add_entry does not runtime-validate its ChangeEntry annotation.

        Appending None to the internal list succeeds (list.append accepts
        any object). Pins actual behavior; a future guard would be noticed.
        """
        cl = ContentChangelog()
        cl.add_entry(None)  # type: ignore[arg-type]
        assert len(cl.get_entries()) == 1
        assert cl.get_entries()[0] is None

    def test_add_many_entries_stability(self) -> None:
        """Adding 100 entries must preserve insertion order."""
        cl = ContentChangelog()
        for i in range(100):
            cl.add_entry(_entry(url=f"http://{i}.com"))
        entries = cl.get_entries()
        assert len(entries) == 100
        assert entries[0].url == "http://0.com"
        assert entries[99].url == "http://99.com"

    def test_add_entry_with_unicode_url(self) -> None:
        cl = ContentChangelog()
        cl.add_entry(_entry(url="http://пример.рф/путь"))
        entries = cl.get_entries()
        assert entries[0].url == "http://пример.рф/путь"

    def test_add_entry_empty_url(self) -> None:
        cl = ContentChangelog()
        cl.add_entry(_entry(url=""))
        entries = cl.get_entries()
        assert len(entries) == 1
        assert entries[0].url == ""

    def test_add_entry_whitespace_url(self) -> None:
        cl = ContentChangelog()
        cl.add_entry(_entry(url="   "))
        entries = cl.get_entries()
        assert len(entries) == 1
        assert entries[0].url == "   "


# ---------------------------------------------------------------------------
# 4. get_entries — filtering, copy semantics, edge cases
# ---------------------------------------------------------------------------

class TestGetEntries:
    """get_entries must return a copy, filter by exact URL, handle edge cases."""

    def test_get_all_from_empty(self) -> None:
        cl = ContentChangelog()
        assert cl.get_entries() == []

    def test_get_all_returns_all(self) -> None:
        cl = ContentChangelog()
        cl.add_entry(_entry(url="http://a.com"))
        cl.add_entry(_entry(url="http://b.com"))
        cl.add_entry(_entry(url="http://c.com"))
        entries = cl.get_entries()
        assert len(entries) == 3

    def test_get_filtered_exact_match(self) -> None:
        cl = ContentChangelog()
        cl.add_entry(_entry(url="http://a.com"))
        cl.add_entry(_entry(url="http://b.com"))
        entries = cl.get_entries("http://a.com")
        assert len(entries) == 1
        assert entries[0].url == "http://a.com"

    def test_get_filtered_no_match(self) -> None:
        cl = ContentChangelog()
        cl.add_entry(_entry(url="http://a.com"))
        entries = cl.get_entries("http://nonexistent.com")
        assert entries == []

    def test_get_filtered_is_exact_not_substring(self) -> None:
        """Filtering must be exact match, not substring or prefix."""
        cl = ContentChangelog()
        cl.add_entry(_entry(url="http://a.com/page"))
        cl.add_entry(_entry(url="http://a.com"))
        # Substring match would return both; exact match returns only the second
        entries = cl.get_entries("http://a.com")
        assert len(entries) == 1
        assert entries[0].url == "http://a.com"

    def test_get_filtered_is_exact_not_prefix(self) -> None:
        """Filtering must be exact match, not prefix."""
        cl = ContentChangelog()
        cl.add_entry(_entry(url="http://a.com"))
        cl.add_entry(_entry(url="http://a.com/extra"))
        entries = cl.get_entries("http://a.com")
        assert len(entries) == 1
        assert entries[0].url == "http://a.com"

    def test_get_returns_new_list_not_internal(self) -> None:
        """get_entries must return a copy, not the internal list."""
        cl = ContentChangelog()
        cl.add_entry(_entry(url="http://a.com"))
        entries = cl.get_entries()
        # Mutating the returned list must not affect the changelog
        entries.append(_entry(url="http://injected.com"))
        assert len(cl.get_entries()) == 1

    def test_get_filtered_returns_new_list(self) -> None:
        """Filtered result must also be a new list."""
        cl = ContentChangelog()
        cl.add_entry(_entry(url="http://a.com"))
        cl.add_entry(_entry(url="http://b.com"))
        entries = cl.get_entries("http://a.com")
        entries.append(_entry(url="http://injected.com"))
        # Original changelog unaffected
        assert len(cl.get_entries("http://a.com")) == 1

    def test_get_none_returns_all(self) -> None:
        """url=None (falsy) must return ALL entries."""
        cl = ContentChangelog()
        cl.add_entry(_entry(url="http://a.com"))
        cl.add_entry(_entry(url="http://b.com"))
        entries = cl.get_entries(None)
        assert len(entries) == 2

    def test_get_empty_string_returns_all(self) -> None:
        """url='' (falsy) must return ALL entries per docstring."""
        cl = ContentChangelog()
        cl.add_entry(_entry(url="http://a.com"))
        cl.add_entry(_entry(url="http://b.com"))
        entries = cl.get_entries("")
        assert len(entries) == 2

    def test_get_whitespace_string_filters(self) -> None:
        """url='  ' (truthy) must filter by exact match (no match expected)."""
        cl = ContentChangelog()
        cl.add_entry(_entry(url="http://a.com"))
        entries = cl.get_entries("  ")
        assert entries == []

    def test_get_preserves_order(self) -> None:
        cl = ContentChangelog()
        cl.add_entry(_entry(url="http://1.com"))
        cl.add_entry(_entry(url="http://2.com"))
        cl.add_entry(_entry(url="http://3.com"))
        entries = cl.get_entries()
        assert [e.url for e in entries] == ["http://1.com", "http://2.com", "http://3.com"]

    def test_get_filtered_preserves_relative_order(self) -> None:
        cl = ContentChangelog()
        cl.add_entry(_entry(url="http://a.com", change_type="v1"))
        cl.add_entry(_entry(url="http://b.com"))
        cl.add_entry(_entry(url="http://a.com", change_type="v2"))
        cl.add_entry(_entry(url="http://b.com"))
        cl.add_entry(_entry(url="http://a.com", change_type="v3"))
        entries = cl.get_entries("http://a.com")
        assert len(entries) == 3
        assert [e.change_type for e in entries] == ["v1", "v2", "v3"]

    def test_get_idempotent(self) -> None:
        """Calling get_entries twice must return equal results."""
        cl = ContentChangelog()
        cl.add_entry(_entry(url="http://a.com"))
        r1 = cl.get_entries()
        r2 = cl.get_entries()
        assert [e.url for e in r1] == [e.url for e in r2]

    def test_get_does_not_mutate_internal_state(self) -> None:
        cl = ContentChangelog()
        cl.add_entry(_entry(url="http://a.com"))
        cl.get_entries()
        cl.get_entries("http://a.com")
        cl.get_entries("http://nonexistent.com")
        assert len(cl.get_entries()) == 1

    def test_get_unicode_url_filter(self) -> None:
        cl = ContentChangelog()
        cl.add_entry(_entry(url="http://пример.рф"))
        cl.add_entry(_entry(url="http://other.com"))
        entries = cl.get_entries("http://пример.рф")
        assert len(entries) == 1
        assert entries[0].url == "http://пример.рф"

    def test_get_none_url_raises_or_returns_all(self) -> None:
        """Passing None explicitly should return all (falsy)."""
        cl = ContentChangelog()
        cl.add_entry(_entry(url="http://a.com"))
        entries = cl.get_entries(None)
        assert len(entries) == 1


# ---------------------------------------------------------------------------
# 5. clear — state reset
# ---------------------------------------------------------------------------

class TestClear:
    """clear must remove all entries."""

    def test_clear_empty(self) -> None:
        cl = ContentChangelog()
        cl.clear()
        assert cl.get_entries() == []

    def test_clear_with_entries(self) -> None:
        cl = ContentChangelog()
        cl.add_entry(_entry(url="http://a.com"))
        cl.add_entry(_entry(url="http://b.com"))
        cl.clear()
        assert cl.get_entries() == []

    def test_clear_idempotent(self) -> None:
        cl = ContentChangelog()
        cl.add_entry(_entry(url="http://a.com"))
        cl.clear()
        cl.clear()
        assert cl.get_entries() == []

    def test_clear_then_add(self) -> None:
        cl = ContentChangelog()
        cl.add_entry(_entry(url="http://old.com"))
        cl.clear()
        cl.add_entry(_entry(url="http://new.com"))
        entries = cl.get_entries()
        assert len(entries) == 1
        assert entries[0].url == "http://new.com"

    def test_clear_does_not_affect_other_instances(self) -> None:
        cl1 = ContentChangelog()
        cl2 = ContentChangelog()
        cl1.add_entry(_entry(url="http://a.com"))
        cl2.add_entry(_entry(url="http://b.com"))
        cl1.clear()
        assert cl1.get_entries() == []
        assert len(cl2.get_entries()) == 1


# ---------------------------------------------------------------------------
# 6. Round-trip and property checks
# ---------------------------------------------------------------------------

class TestRoundTripAndProperties:
    """Property-based checks on the changelog."""

    def test_add_get_round_trip(self) -> None:
        cl = ContentChangelog()
        e = _entry(url="http://rt.com", change_type="created", details={"k": "v"})
        cl.add_entry(e)
        entries = cl.get_entries()
        assert len(entries) == 1
        assert entries[0].url == "http://rt.com"
        assert entries[0].change_type == "created"
        assert entries[0].details == {"k": "v"}

    def test_add_get_clear_round_trip(self) -> None:
        cl = ContentChangelog()
        cl.add_entry(_entry(url="http://a.com"))
        cl.add_entry(_entry(url="http://b.com"))
        assert len(cl.get_entries()) == 2
        cl.clear()
        assert len(cl.get_entries()) == 0

    def test_entry_identity_preserved_in_get(self) -> None:
        """get_entries returns the same objects (not copies of entries)."""
        cl = ContentChangelog()
        e = _entry(url="http://id.com")
        cl.add_entry(e)
        entries = cl.get_entries()
        assert entries[0] is e

    def test_details_dict_is_shared_reference(self) -> None:
        """The details dict in a returned entry is the same object."""
        cl = ContentChangelog()
        details: dict[str, Any] = {"original": True}
        e = ChangeEntry(url="u", change_type="t", timestamp="ts", details=details)
        cl.add_entry(e)
        entries = cl.get_entries()
        assert entries[0].details is details

    def test_large_changelog_performance(self) -> None:
        """Adding and retrieving 1000 entries should work correctly."""
        cl = ContentChangelog()
        for i in range(1000):
            cl.add_entry(_entry(url=f"http://{i}.com"))
        entries = cl.get_entries()
        assert len(entries) == 1000
        # Filter should work on large set
        filtered = cl.get_entries("http://500.com")
        assert len(filtered) == 1
        assert filtered[0].url == "http://500.com"

    def test_all_entries_unique_urls(self) -> None:
        """With unique URLs, filtering returns exactly one entry."""
        cl = ContentChangelog()
        urls = [f"http://unique-{i}.com" for i in range(50)]
        for u in urls:
            cl.add_entry(_entry(url=u))
        for u in urls:
            entries = cl.get_entries(u)
            assert len(entries) == 1
            assert entries[0].url == u

    def test_mixed_change_types(self) -> None:
        cl = ContentChangelog()
        types = ["created", "modified", "deleted", "restored"]
        for t in types:
            cl.add_entry(_entry(url="http://same.com", change_type=t))
        entries = cl.get_entries("http://same.com")
        assert len(entries) == 4
        assert [e.change_type for e in entries] == types


# ---------------------------------------------------------------------------
# 7. End-to-end lifecycle
# ---------------------------------------------------------------------------

class TestEndToEnd:
    """End-to-end lifecycle: add, filter, clear, re-add."""

    def test_full_lifecycle(self) -> None:
        cl = ContentChangelog()
        # Phase 1: add entries
        cl.add_entry(_entry(url="http://a.com", change_type="created"))
        cl.add_entry(_entry(url="http://b.com", change_type="created"))
        cl.add_entry(_entry(url="http://a.com", change_type="modified"))
        # Phase 2: verify
        assert len(cl.get_entries()) == 3
        assert len(cl.get_entries("http://a.com")) == 2
        assert len(cl.get_entries("http://b.com")) == 1
        # Phase 3: clear
        cl.clear()
        assert len(cl.get_entries()) == 0
        # Phase 4: re-add
        cl.add_entry(_entry(url="http://c.com", change_type="created"))
        assert len(cl.get_entries()) == 1
        assert cl.get_entries("http://c.com")[0].url == "http://c.com"

    def test_lifecycle_with_unicode(self) -> None:
        cl = ContentChangelog()
        cl.add_entry(_entry(url="http://пример.рф/страница", change_type="создан"))
        cl.add_entry(_entry(url="http://テスト. jp/ページ", change_type="変更"))
        entries = cl.get_entries()
        assert len(entries) == 2
        filtered = cl.get_entries("http://пример.рф/страница")
        assert len(filtered) == 1
        assert filtered[0].change_type == "создан"

    def test_lifecycle_with_special_chars_in_url(self) -> None:
        cl = ContentChangelog()
        url = "http://example.com/path?query=value&other=test#fragment"
        cl.add_entry(_entry(url=url, change_type="modified"))
        cl.add_entry(_entry(url="http://example.com/path?query=other", change_type="modified"))
        entries = cl.get_entries(url)
        assert len(entries) == 1
        assert entries[0].url == url
