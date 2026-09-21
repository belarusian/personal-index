"""Adversarial deep tests for the naive-vs-aware datetime seam class (cycle 338).

CLASS SWEEP (cycle 338) re-ran `grep -rn fromisoformat personal_index/` and
traced every non-pycache call site to its public entry point and its
downstream comparison/subtraction/sort context. Three NEW unfiled seam members
were found (the per-item parse is guarded by `except (ValueError, TypeError)`
or is parse-only, but a DOWNSTREAM sort/min/comparison of the parsed results
sits OUTSIDE that guard, so a mixed naive+aware list passes every per-item
parse and only fails at the aggregation step, raising an uncaught TypeError out
of a public entry point):

  1. personal_index/content_feed.py:107
     FeedGenerator.add_item sorts by `i.published`. A naive `published`
     (produced by FeedItem.from_dict from a naive ISO string) mixed with an
     aware `published` (the __post_init__ default) raises TypeError at the sort.

  2. personal_index/content_timeline/timeline.py:37 (add_event) and :67 (add_entry)
     Timeline.add_event / add_entry sort by `timestamp`. A naive timestamp
     (produced by TimelineEvent.from_dict / TimelineEntry.from_dict from a naive
     ISO string) mixed with an aware timestamp (the default) raises TypeError.

  3. personal_index/content_backup/backup_store.py:95-97 (list_backups) and
     :126 (_evict_oldest). A naive timestamp (produced by import_from_file from
     a naive ISO string) mixed with an aware timestamp (add_backup default)
     raises TypeError at the sort/min.

The pins below assert the CORRECTED contract (a mixed naive+aware list sorts
without error). They currently FAIL with TypeError, so they are marked
xfail-strict to document the defect while keeping main green. Once the
implementer lands the fix (normalize naive -> UTC at the parse site), the
validator flips each pin to a hard pass and VERIFIES (QA-67).
"""

from __future__ import annotations

import json
from datetime import datetime, timezone

import pytest

from personal_index.content_backup.backup_store import BackupEntry, BackupStore
from personal_index.content_feed import FeedGenerator, FeedItem
from personal_index.content_timeline.timeline import Timeline
from personal_index.content_timeline.timeline_event import TimelineEvent


# ---------------------------------------------------------------------------
# Site 1: content_feed.FeedGenerator.add_item sort (content_feed.py:107)
# ---------------------------------------------------------------------------
class TestContentFeedNaiveAwareSeam:
    @pytest.mark.xfail(
        strict=True,
        reason="QA-67: naive-vs-aware seam at FeedGenerator.add_item sort "
        "(content_feed.py:107); mixed naive+aware published raises TypeError",
    )
    def test_mixed_naive_aware_published_sorts_without_error(self):
        g = FeedGenerator(title="t", link="http://x")
        g.add_item(
            FeedItem(
                title="naive",
                link="http://x/n",
                published=datetime(2024, 1, 1, 0, 0, 0),
            )
        )
        g.add_item(
            FeedItem(
                title="aware",
                link="http://x/a",
                published=datetime(2024, 1, 2, 0, 0, 0, tzinfo=timezone.utc),
            )
        )
        # Corrected contract: mixed list sorts without TypeError.
        assert [i.title for i in g.items] in (["aware", "naive"], ["naive", "aware"])

    def test_all_aware_published_sorts(self):
        g = FeedGenerator(title="t", link="http://x")
        g.add_item(
            FeedItem(
                title="old",
                link="http://x/old",
                published=datetime(2024, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
            )
        )
        g.add_item(
            FeedItem(
                title="new",
                link="http://x/new",
                published=datetime(2024, 1, 2, 0, 0, 0, tzinfo=timezone.utc),
            )
        )
        assert [i.title for i in g.items] == ["new", "old"]

    def test_all_naive_published_sorts(self):
        g = FeedGenerator(title="t", link="http://x")
        g.add_item(
            FeedItem(
                title="old",
                link="http://x/old",
                published=datetime(2024, 1, 1, 0, 0, 0),
            )
        )
        g.add_item(
            FeedItem(
                title="new",
                link="http://x/new",
                published=datetime(2024, 1, 2, 0, 0, 0),
            )
        )
        assert [i.title for i in g.items] == ["new", "old"]

    def test_from_dict_naive_string_yields_naive_published(self):
        # Documents the source of the naive datetime: a naive ISO string.
        item = FeedItem.from_dict(
            {"title": "t", "link": "http://x", "published": "2024-01-01T00:00:00"}
        )
        assert item.published is not None
        assert item.published.tzinfo is None


# ---------------------------------------------------------------------------
# Site 2: content_timeline.Timeline.add_event / add_entry sort
# ---------------------------------------------------------------------------
class TestTimelineNaiveAwareSeam:
    @pytest.mark.xfail(
        strict=True,
        reason="QA-67: naive-vs-aware seam at Timeline.add_event sort "
        "(timeline.py:37); mixed naive+aware timestamp raises TypeError",
    )
    def test_mixed_naive_aware_event_sorts_without_error(self):
        tl = Timeline()
        tl.add_event(
            TimelineEvent.from_dict(
                {"event_id": "e1", "timestamp": "2024-01-01T00:00:00"}
            )
        )
        tl.add_event(
            TimelineEvent.from_dict(
                {"event_id": "e2", "timestamp": "2024-01-02T00:00:00+00:00"}
            )
        )
        # Corrected contract: mixed list sorts without TypeError.
        assert {e.event_id for e in tl.events} == {"e1", "e2"}

    @pytest.mark.xfail(
        strict=True,
        reason="QA-67: naive-vs-aware seam at Timeline.add_entry sort "
        "(timeline.py:67); mixed naive+aware timestamp raises TypeError",
    )
    def test_mixed_naive_aware_entry_sorts_without_error(self):
        tl = Timeline()
        tl.add_entry(
            item_id="i1",
            title="naive",
            timestamp=datetime(2024, 1, 1, 0, 0, 0),
        )
        tl.add_entry(
            item_id="i2",
            title="aware",
            timestamp=datetime(2024, 1, 2, 0, 0, 0, tzinfo=timezone.utc),
        )
        # Corrected contract: mixed list sorts without TypeError.
        assert {e.item_id for e in tl.entries} == {"i1", "i2"}

    def test_all_aware_event_sorts(self):
        tl = Timeline()
        tl.add_event(
            TimelineEvent.from_dict(
                {"event_id": "e1", "timestamp": "2024-01-01T00:00:00+00:00"}
            )
        )
        tl.add_event(
            TimelineEvent.from_dict(
                {"event_id": "e2", "timestamp": "2024-01-02T00:00:00+00:00"}
            )
        )
        assert [e.event_id for e in tl.events] == ["e1", "e2"]

    def test_from_dict_naive_string_yields_naive_timestamp(self):
        ev = TimelineEvent.from_dict(
            {"event_id": "e1", "timestamp": "2024-01-01T00:00:00"}
        )
        assert ev.timestamp.tzinfo is None


# ---------------------------------------------------------------------------
# Site 3: content_backup.BackupStore.list_backups / _evict_oldest
# ---------------------------------------------------------------------------
class TestBackupStoreNaiveAwareSeam:
    @pytest.mark.xfail(
        strict=True,
        reason="QA-67: naive-vs-aware seam at BackupStore.list_backups sort "
        "(backup_store.py:95-97); mixed naive+aware timestamp raises TypeError",
    )
    def test_mixed_naive_aware_list_backups_without_error(self):
        bs = BackupStore()
        bs.backups["b1"] = BackupEntry(
            backup_id="b1",
            timestamp=datetime(2024, 1, 1, 0, 0, 0),
            item_count=1,
            data={},
        )
        bs.backups["b2"] = BackupEntry(
            backup_id="b2",
            timestamp=datetime(2024, 1, 2, 0, 0, 0, tzinfo=timezone.utc),
            item_count=1,
            data={},
        )
        # Corrected contract: mixed list sorts without TypeError.
        assert {b.backup_id for b in bs.list_backups()} == {"b1", "b2"}

    @pytest.mark.xfail(
        strict=True,
        reason="QA-67: naive-vs-aware seam at BackupStore._evict_oldest min "
        "(backup_store.py:126); mixed naive+aware timestamp raises TypeError",
    )
    def test_mixed_naive_aware_evict_oldest_without_error(self):
        bs = BackupStore()
        bs.backups["b1"] = BackupEntry(
            backup_id="b1",
            timestamp=datetime(2024, 1, 1, 0, 0, 0),
            item_count=1,
            data={},
        )
        bs.backups["b2"] = BackupEntry(
            backup_id="b2",
            timestamp=datetime(2024, 1, 2, 0, 0, 0, tzinfo=timezone.utc),
            item_count=1,
            data={},
        )
        # Corrected contract: min() over mixed list works without TypeError.
        bs._evict_oldest()
        assert len(bs.backups) == 1

    def test_all_aware_list_backups(self):
        bs = BackupStore()
        bs.backups["b1"] = BackupEntry(
            backup_id="b1",
            timestamp=datetime(2024, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
            item_count=1,
            data={},
        )
        bs.backups["b2"] = BackupEntry(
            backup_id="b2",
            timestamp=datetime(2024, 1, 2, 0, 0, 0, tzinfo=timezone.utc),
            item_count=1,
            data={},
        )
        assert [b.backup_id for b in bs.list_backups()] == ["b2", "b1"]

    def test_import_from_file_naive_string_yields_naive_timestamp(self, tmp_path):
        # Documents the source of the naive datetime: a naive ISO string in a
        # backup JSON file, loaded through the public import_from_file.
        f = tmp_path / "backup.json"
        f.write_text(
            json.dumps(
                {
                    "backup_id": "b1",
                    "timestamp": "2024-01-01T00:00:00",
                    "item_count": 1,
                    "items": [{"url": "http://x"}],
                }
            )
        )
        bs = BackupStore()
        entry = bs.import_from_file(str(f))
        assert entry.timestamp.tzinfo is None


# ---------------------------------------------------------------------------
# End-to-end CLI run (installed CLI, per-cycle requirement)
# ---------------------------------------------------------------------------
class TestCliEndToEnd:
    def test_cli_init_and_search_round_trip(self, tmp_path):
        import subprocess
        import sys

        data_dir = tmp_path / "data"
        data_dir.mkdir()
        config_path = data_dir / "config.yaml"
        base = [sys.executable, "-m", "personal_index.cli", "--data-dir", str(data_dir)]

        init = subprocess.run(
            base + ["init", "--config", str(config_path)],
            capture_output=True,
            text=True,
            timeout=120,
        )
        assert init.returncode == 0, f"init failed: {init.stderr}"

        search = subprocess.run(
            base + ["search", "python"],
            capture_output=True,
            text=True,
            timeout=120,
        )
        assert search.returncode == 0, f"search failed: {search.stderr}"
        combined = (search.stdout + search.stderr).lower()
        assert "no indexed content found" in combined
