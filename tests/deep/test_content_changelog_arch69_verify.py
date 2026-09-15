"""ARCH-69 verification: content_changelog.get_entries shallow-copy contract.

The implementer chose Option 1 (docstring reword, code unchanged): get_entries
returns a NEW list (shallow copy of the container) but the ChangeEntry objects
and their details dicts are SHARED references to the stored entries.

These tests pin the acceptance criteria (AC1-AC5) plus adversarial guard inputs
implied by the contract. They run against the real get_entries entry point.
"""

from __future__ import annotations

import subprocess
import sys
from typing import Any

from personal_index.content_changelog import ChangeEntry, ContentChangelog


def _entry(
    url: str = "http://example.com",
    change_type: str = "modified",
    timestamp: str = "2026-01-01T00:00:00+00:00",
    details: dict[str, Any] | None = None,
) -> ChangeEntry:
    if details is None:
        details = {}
    return ChangeEntry(url=url, change_type=change_type, timestamp=timestamp, details=details)


# ---------------------------------------------------------------------------
# AC1: the list container is always a fresh object
# ---------------------------------------------------------------------------


class TestListContainerFresh:
    def test_get_entries_returns_new_list_object(self) -> None:
        """AC1: cl.get_entries() is not cl.get_entries()."""
        cl = ContentChangelog()
        cl.add_entry(_entry(url="http://a.com"))
        assert cl.get_entries() is not cl.get_entries()

    def test_get_entries_filtered_returns_new_list_object(self) -> None:
        """AC1 (filtered branch): the filtered list is also a fresh object."""
        cl = ContentChangelog()
        cl.add_entry(_entry(url="http://a.com"))
        assert cl.get_entries("http://a.com") is not cl.get_entries("http://a.com")


# ---------------------------------------------------------------------------
# AC2: mutating a returned entry's details dict mutates the stored entry
# ---------------------------------------------------------------------------


class TestDetailsSharedReference:
    def test_mutation_of_returned_details_affects_stored(self) -> None:
        """AC2 (Option 1): mutating returned entry's details hits the store."""
        cl = ContentChangelog()
        e = _entry(url="http://a.com", details={"original": True})
        cl.add_entry(e)
        cl.get_entries()[0].details["k"] = "v"
        # The stored entry's details now contains the mutation.
        assert cl.get_entries()[0].details == {"original": True, "k": "v"}
        # And it is literally the same dict object as the one we added.
        assert e.details is cl.get_entries()[0].details

    def test_mutation_of_returned_details_filtered_branch(self) -> None:
        """AC2 (filtered branch): shared reference holds for the url filter too."""
        cl = ContentChangelog()
        e = _entry(url="http://a.com", details={})
        cl.add_entry(_entry(url="http://b.com"))
        cl.add_entry(e)
        cl.get_entries("http://a.com")[0].details["k"] = "v"
        assert cl.get_entries("http://a.com")[0].details == {"k": "v"}
        assert e.details is cl.get_entries("http://a.com")[0].details

    def test_mutation_of_returned_scalar_field_affects_stored(self) -> None:
        """AC2 (scalar): mutating a returned entry's scalar field hits the store."""
        cl = ContentChangelog()
        e = _entry(url="http://a.com", change_type="modified")
        cl.add_entry(e)
        cl.get_entries()[0].change_type = "tampered"
        assert cl.get_entries()[0].change_type == "tampered"
        assert e.change_type == "tampered"

    def test_mutation_of_returned_url_affects_stored(self) -> None:
        """AC2 (divergence input): mutating returned url breaks later filter."""
        cl = ContentChangelog()
        e = _entry(url="http://x.com")
        cl.add_entry(e)
        cl.get_entries("http://x.com")[0].url = "http://y.com"
        # The stored entry's url changed, so the old filter no longer matches.
        assert cl.get_entries("http://x.com") == []
        assert cl.get_entries("http://y.com")[0] is e


# ---------------------------------------------------------------------------
# AC3: the returned entry IS the stored object (shared, not a copy)
# ---------------------------------------------------------------------------


class TestEntryIdentity:
    def test_returned_entry_is_stored_object(self) -> None:
        """AC3 (Option 1): cl.get_entries()[0] is e."""
        cl = ContentChangelog()
        e = _entry(url="http://a.com")
        cl.add_entry(e)
        assert cl.get_entries()[0] is e

    def test_returned_entry_is_stored_object_filtered(self) -> None:
        """AC3 (filtered branch): identity holds for the url filter too."""
        cl = ContentChangelog()
        e = _entry(url="http://a.com")
        cl.add_entry(_entry(url="http://b.com"))
        cl.add_entry(e)
        assert cl.get_entries("http://a.com")[0] is e


# ---------------------------------------------------------------------------
# AC4: the docstring states the exact shallow-copy semantics
# ---------------------------------------------------------------------------


class TestDocstringContract:
    def test_docstring_states_shallow_copy(self) -> None:
        """AC4: docstring names the shallow copy and shared references."""
        doc = ContentChangelog.get_entries.__doc__
        assert doc is not None
        assert "SHALLOW" in doc
        assert "SHARED" in doc
        # The old over-promising blanket phrasing is gone.
        assert "a copy, not the internal" not in doc


# ---------------------------------------------------------------------------
# AC5: filter semantics unchanged
# ---------------------------------------------------------------------------


class TestFilterSemantics:
    def test_truthy_url_exact_match_only(self) -> None:
        """AC5: truthy url returns only the exact-match entry."""
        cl = ContentChangelog()
        cl.add_entry(_entry(url="http://a.com"))
        cl.add_entry(_entry(url="http://ab.com"))
        cl.add_entry(_entry(url="http://a.com/path"))
        got = cl.get_entries("http://a.com")
        assert [e.url for e in got] == ["http://a.com"]

    def test_falsy_none_returns_all(self) -> None:
        """AC5: url=None returns all entries."""
        cl = ContentChangelog()
        cl.add_entry(_entry(url="http://a.com"))
        cl.add_entry(_entry(url="http://b.com"))
        assert len(cl.get_entries(None)) == 2

    def test_falsy_empty_string_returns_all(self) -> None:
        """AC5: url='' returns all entries."""
        cl = ContentChangelog()
        cl.add_entry(_entry(url="http://a.com"))
        cl.add_entry(_entry(url="http://b.com"))
        assert len(cl.get_entries("")) == 2

    def test_truthy_url_no_match_returns_empty(self) -> None:
        """AC5: truthy url with no match returns []."""
        cl = ContentChangelog()
        cl.add_entry(_entry(url="http://a.com"))
        assert cl.get_entries("http://nope.com") == []


# ---------------------------------------------------------------------------
# Guard inputs (empty / falsy / unicode / idempotence)
# ---------------------------------------------------------------------------


class TestGuardInputs:
    def test_empty_changelog_returns_empty_list(self) -> None:
        """Guard: empty changelog -> [] for both branches."""
        cl = ContentChangelog()
        assert cl.get_entries() == []
        assert cl.get_entries("http://x.com") == []

    def test_falsy_url_returns_all_with_shared_reference(self) -> None:
        """Guard: falsy url branch is also a shallow copy (shared refs)."""
        cl = ContentChangelog()
        e1 = _entry(url="http://a.com")
        e2 = _entry(url="http://b.com")
        cl.add_entry(e1)
        cl.add_entry(e2)
        for falsy in (None, ""):
            got = cl.get_entries(falsy)
            assert len(got) == 2
            assert got[0] is e1
            assert got[1] is e2

    def test_unicode_details_shared_reference(self) -> None:
        """Adversarial: unicode details dict is still a shared reference."""
        cl = ContentChangelog()
        e = _entry(url="http://a.com", details={"ключ": "значение"})
        cl.add_entry(e)
        cl.get_entries()[0].details["ключ"] = "изменено"
        assert cl.get_entries()[0].details == {"ключ": "изменено"}
        assert e.details is cl.get_entries()[0].details

    def test_get_entries_idempotent(self) -> None:
        """Adversarial: repeated calls return equal (but fresh) lists."""
        cl = ContentChangelog()
        cl.add_entry(_entry(url="http://a.com"))
        first = cl.get_entries()
        second = cl.get_entries()
        assert first == second
        assert first is not second

    def test_many_entries_all_shared(self) -> None:
        """Adversarial: every returned entry is the stored object."""
        cl = ContentChangelog()
        entries = [_entry(url=f"http://n{i}.com") for i in range(50)]
        for e in entries:
            cl.add_entry(e)
        got = cl.get_entries()
        assert len(got) == 50
        for stored, returned in zip(entries, got):
            assert returned is stored


# ---------------------------------------------------------------------------
# End-to-end CLI smoke (installed console script)
# ---------------------------------------------------------------------------


class TestEndToEndCli:
    def test_cli_version_runs(self) -> None:
        """End-to-end: the installed CLI responds to --version."""
        proc = subprocess.run(
            [sys.executable, "-m", "personal_index.cli", "--version"],
            capture_output=True,
            text=True,
        )
        assert proc.returncode == 0
        assert proc.stdout.strip() != ""
