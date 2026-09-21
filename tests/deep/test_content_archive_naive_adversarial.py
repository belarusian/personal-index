"""Adversarial deep tests for ContentArchiver.archive_old naive-datetime handling.

QA-62: archive_old does ``datetime.fromisoformat(saved_at)`` then compares
``saved_time < cutoff`` where ``cutoff`` is UTC-aware. A *naive* ISO timestamp
(no tz suffix) parses fine (it is NOT "unparseable") but ``naive < aware``
raises ``TypeError``, which is caught and silently skipped. The docstring
contract says:

    "Only items whose ``archived_at`` field is non-None are considered; ...
     Unparseable ``archived_at`` values are silently skipped."

A naive ISO string is parseable and non-None, so it MUST be considered and
archived when old. Instead it is silently dropped (stays ACTIVE). The recency
scorer (content_scoring._score_recency) explicitly normalizes naive -> UTC,
so the archiver is inconsistent with the rest of the codebase.

The xfail-strict pin documents the defect; the armor pins pin the correct
behavior that must hold regardless.
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

import pytest

from personal_index.content_archive.archive_entry import ArchiveStatus
from personal_index.content_archive.archiver import ContentArchiver


def _old_naive_iso():
    """A naive ISO timestamp ~6 years in the past (no tz suffix)."""
    return (datetime.now(timezone.utc) - timedelta(days=2000)).replace(
        tzinfo=None
    ).isoformat()


def _old_aware_iso():
    """An aware ISO timestamp ~6 years in the past (UTC)."""
    return (datetime.now(timezone.utc) - timedelta(days=2000)).isoformat()


def _recent_naive_iso():
    """A naive ISO timestamp ~1 day in the past (no tz suffix)."""
    return (datetime.now(timezone.utc) - timedelta(days=1)).replace(
        tzinfo=None
    ).isoformat()


class TestArchiveOldNaiveDatetime:
    """archive_old must consider parseable naive timestamps (QA-62)."""

    @pytest.mark.xfail(
        strict=True,
        reason=(
            "QA-62: naive ISO saved_at is parseable and non-None so the "
            "docstring contract requires it to be considered and archived "
            "when old; instead naive<aware raises TypeError and the item is "
            "silently skipped (stays ACTIVE). See tickets/QA-62.md."
        ),
    )
    def test_naive_old_timestamp_is_archived(self):
        archiver = ContentArchiver(days_threshold=30)
        archiver.add_item("naive_old", "x", saved_at=_old_naive_iso())
        archived = archiver.archive_old()
        assert "naive_old" in archived
        assert archiver.get_item("naive_old").status == ArchiveStatus.ARCHIVED

    def test_aware_old_timestamp_is_archived(self):
        """Armor: the aware path already works and must keep working."""
        archiver = ContentArchiver(days_threshold=30)
        archiver.add_item("aware_old", "x", saved_at=_old_aware_iso())
        archived = archiver.archive_old()
        assert "aware_old" in archived
        assert archiver.get_item("aware_old").status == ArchiveStatus.ARCHIVED

    def test_naive_recent_timestamp_not_archived(self):
        """Armor: a naive timestamp within the threshold must NOT archive."""
        archiver = ContentArchiver(days_threshold=30)
        archiver.add_item("naive_recent", "x", saved_at=_recent_naive_iso())
        archived = archiver.archive_old()
        assert "naive_recent" not in archived
        assert archiver.get_item("naive_recent").status == ArchiveStatus.ACTIVE

    def test_naive_and_aware_old_both_considered(self):
        """Armor: with a naive item present, the aware item still archives.

        Pins that the naive item's silent-skip does not corrupt iteration over
        the other items (no early break / no exception leak).
        """
        archiver = ContentArchiver(days_threshold=30)
        archiver.add_item("naive_old", "x", saved_at=_old_naive_iso())
        archiver.add_item("aware_old", "y", saved_at=_old_aware_iso())
        archived = archiver.archive_old()
        assert "aware_old" in archived
        assert archiver.get_item("aware_old").status == ArchiveStatus.ARCHIVED

    def test_archive_old_idempotent(self):
        """Armor: a second archive_old call returns no new ids (already archived)."""
        archiver = ContentArchiver(days_threshold=30)
        archiver.add_item("aware_old", "x", saved_at=_old_aware_iso())
        first = archiver.archive_old()
        second = archiver.archive_old()
        assert "aware_old" in first
        assert "aware_old" not in second

    def test_unparseable_still_skipped(self):
        """Armor: genuinely unparseable values are still silently skipped."""
        archiver = ContentArchiver(days_threshold=0)
        archiver.add_item("bad", "x", saved_at="not-a-date")
        assert archiver.archive_old() == []
        assert archiver.get_item("bad").status == ArchiveStatus.ACTIVE

    def test_none_saved_at_never_archives(self):
        """Armor: saved_at=None is never archived regardless of threshold."""
        archiver = ContentArchiver(days_threshold=0)
        archiver.add_item("no_ts", "x")
        assert archiver.archive_old() == []
        assert archiver.get_item("no_ts").status == ArchiveStatus.ACTIVE


class TestArchiveEndToEndWorkflow:
    """End-to-end run through the public API (the archiver is library-only,
    no CLI command is registered for it)."""

    def test_full_lifecycle_with_export(self, tmp_path):
        archiver = ContentArchiver(days_threshold=30)
        archiver.add_item("a", "alpha", saved_at=_old_aware_iso())
        archiver.add_item("b", "beta", saved_at=_old_aware_iso())
        archiver.add_item("c", "gamma")  # no timestamp -> never archives

        archived = archiver.archive_old()
        assert set(archived) == {"a", "b"}
        assert archiver.get_stats()["archived_items"] == 2

        out = tmp_path / "archived.json"
        archiver.export_archived(str(out))
        assert out.exists()
        data = json.loads(out.read_text())
        assert {e["item_id"] for e in data} == {"a", "b"}

        assert archiver.restore_item("a") is True
        assert archiver.get_item("a").status == ArchiveStatus.ACTIVE
        assert archiver.get_stats()["archived_items"] == 1

        deleted = archiver.delete_archived()
        assert deleted == ["b"]
        assert archiver.get_item("b") is None
