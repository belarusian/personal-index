#!/usr/bin/env python3
"""Generate 202 commits for personal-index with real code and tests."""

import subprocess
import os
import textwrap

def run(cmd):
    """Run a shell command."""
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    return result.returncode, result.stdout, result.stderr

def write_file(path, content):
    """Write a file with proper directory creation."""
    os.makedirs(os.path.dirname(path) if os.path.dirname(path) else '.', exist_ok=True)
    with open(path, 'w') as f:
        f.write(textwrap.dedent(content).lstrip())

def commit(msg):
    """Stage all changes and commit."""
    run("git add -A")
    code, out, err = run(f'git commit -m "{msg}"')
    return code == 0

# ============================================================
# BATCH 1-10: Content Scoring/Ranking Module
# ============================================================

# Commit 1: content_scoring.py
write_file("personal_index/content_scoring.py", '''
"""Content scoring and ranking engine for personal-index.

Provides algorithms to score content items based on multiple factors
including recency, relevance, user engagement, and content quality.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any


class ScoreFactor(Enum):
    """Factors that contribute to content scoring."""

    RECENCY = "recency"
    RELEVANCE = "relevance"
    ENGAGEMENT = "engagement"
    QUALITY = "quality"
    AUTHORITY = "authority"
    FRESHNESS = "freshness"


@dataclass
class ScoreWeights:
    """Configurable weights for each scoring factor.

    Attributes:
        recency: Weight for how recent the content is (0.0-1.0).
        relevance: Weight for keyword/topic relevance (0.0-1.0).
        engagement: Weight for user engagement signals (0.0-1.0).
        quality: Weight for content quality signals (0.0-1.0).
        authority: Weight for source authority (0.0-1.0).
        freshness: Weight for content freshness (0.0-1.0).
    """

    recency: float = 0.2
    relevance: float = 0.25
    engagement: float = 0.15
    quality: float = 0.15
    authority: float = 0.1
    freshness: float = 0.15

    def normalize(self) -> ScoreWeights:
        """Normalize weights so they sum to 1.0."""
        total = sum([
            self.recency, self.relevance, self.engagement,
            self.quality, self.authority, self.freshness,
        ])
        if total == 0:
            return ScoreWeights()
        return ScoreWeights(
            recency=self.recency / total,
            relevance=self.relevance / total,
            engagement=self.engagement / total,
            quality=self.quality / total,
            authority=self.authority / total,
            freshness=self.freshness / total,
        )


@dataclass
class ContentScore:
    """Result of scoring a content item.

    Attributes:
        total: Overall composite score (0.0-1.0).
        recency: Score for recency factor.
        relevance: Score for relevance factor.
        engagement: Score for engagement factor.
        quality: Score for quality factor.
        authority: Score for authority factor.
        freshness: Score for freshness factor.
        factors: Dict mapping factor names to individual scores.
    """

    total: float = 0.0
    recency: float = 0.0
    relevance: float = 0.0
    engagement: float = 0.0
    quality: float = 0.0
    authority: float = 0.0
    freshness: float = 0.0
    factors: dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert score to dictionary representation."""
        return {
            "total": round(self.total, 4),
            "recency": round(self.recency, 4),
            "relevance": round(self.relevance, 4),
            "engagement": round(self.engagement, 4),
            "quality": round(self.quality, 4),
            "authority": round(self.authority, 4),
            "freshness": round(self.freshness, 4),
            "factors": self.factors,
        }


class ContentScorer:
    """Scores content items based on configurable factors.

    Uses a weighted combination of multiple scoring factors to produce
    a composite score for each content item.
    """

    def __init__(self, weights: ScoreWeights | None = None) -> None:
        self.weights = (weights or ScoreWeights()).normalize()

    def score(
        self,
        *,
        published_at: datetime | None = None,
        updated_at: datetime | None = None,
        keyword_matches: int = 0,
        total_keywords: int = 1,
        view_count: int = 0,
        bookmark_count: int = 0,
        share_count: int = 0,
        word_count: int = 0,
        has_images: bool = False,
        has_code: bool = False,
        domain_authority: float = 0.5,
        is_verified_source: bool = False,
        last_crawled: datetime | None = None,
        change_frequency: str = "monthly",
    ) -> ContentScore:
        """Calculate composite score for a content item.

        Args:
            published_at: When the content was published.
            updated_at: When the content was last updated.
            keyword_matches: Number of matching keywords.
            total_keywords: Total keywords searched.
            view_count: Number of views.
            bookmark_count: Number of bookmarks.
            share_count: Number of shares.
            word_count: Word count of the content.
            has_images: Whether content has images.
            has_code: Whether content has code blocks.
            domain_authority: Authority score of the source domain.
            is_verified_source: Whether the source is verified.
            last_crawled: When the content was last crawled.
            change_frequency: Expected change frequency of the source.

        Returns:
            ContentScore with total and per-factor scores.
        """
        recency = self._score_recency(published_at, updated_at)
        relevance = self._score_relevance(keyword_matches, total_keywords)
        engagement = self._score_engagement(
            view_count, bookmark_count, share_count,
        )
        quality = self._score_quality(word_count, has_images, has_code)
        authority = self._score_authority(domain_authority, is_verified_source)
        freshness = self._score_freshness(
            last_crawled, change_frequency, updated_at,
        )

        total = (
            self.weights.recency * recency
            + self.weights.relevance * relevance
            + self.weights.engagement * engagement
            + self.weights.quality * quality
            + self.weights.authority * authority
            + self.weights.freshness * freshness
        )

        return ContentScore(
            total=round(total, 4),
            recency=round(recency, 4),
            relevance=round(relevance, 4),
            engagement=round(engagement, 4),
            quality=round(quality, 4),
            authority=round(authority, 4),
            freshness=round(freshness, 4),
            factors={
                "recency": recency,
                "relevance": relevance,
                "engagement": engagement,
                "quality": quality,
                "authority": authority,
                "freshness": freshness,
            },
        )

    def _score_recency(
        self,
        published_at: datetime | None,
        updated_at: datetime | None,
    ) -> float:
        """Score based on how recent the content is.

        Uses exponential decay: newer content scores higher.
        """
        now = datetime.now()
        date = updated_at or published_at or now
        age_days = max(0, (now - date).days)
        # Exponential decay: half-life of 30 days
        return round(math.exp(-math.log(2) * age_days / 30), 4)

    def _score_relevance(
        self,
        keyword_matches: int,
        total_keywords: int,
    ) -> float:
        """Score based on keyword relevance."""
        if total_keywords == 0:
            return 0.0
        return round(min(1.0, keyword_matches / total_keywords), 4)

    def _score_engagement(
        self,
        view_count: int,
        bookmark_count: int,
        share_count: int,
    ) -> float:
        """Score based on engagement signals.

        Uses logarithmic scaling to prevent high-volume items from
        dominating.
        """
        engagement = (
            math.log1p(view_count) * 0.4
            + math.log1p(bookmark_count) * 0.4
            + math.log1p(share_count) * 0.2
        )
        # Normalize to 0-1 range (cap at log1p(1000) ~ 6.9)
        max_engagement = math.log1p(1000)
        return round(min(1.0, engagement / max_engagement), 4)

    def _score_quality(
        self,
        word_count: int,
        has_images: bool,
        has_code: bool,
    ) -> float:
        """Score based on content quality signals."""
        # Longer content tends to be higher quality (diminishing returns)
        length_score = min(1.0, math.log1p(word_count) / math.log1p(3000))
        # Bonus for rich media
        media_bonus = 0.1 if has_images else 0.0
        code_bonus = 0.05 if has_code else 0.0
        return round(min(1.0, length_score + media_bonus + code_bonus), 4)

    def _score_authority(
        self,
        domain_authority: float,
        is_verified_source: bool,
    ) -> float:
        """Score based on source authority."""
        score = domain_authority
        if is_verified_source:
            score = min(1.0, score + 0.1)
        return round(score, 4)

    def _score_freshness(
        self,
        last_crawled: datetime | None,
        change_frequency: str,
        updated_at: datetime | None,
    ) -> float:
        """Score based on content freshness."""
        now = datetime.now()
        if last_crawled is None:
            return 0.5

        age_hours = max(0, (now - last_crawled).total_seconds() / 3600)

        # Expected update intervals by frequency
        frequency_hours: dict[str, float] = {
            "hourly": 1,
            "daily": 24,
            "weekly": 168,
            "monthly": 720,
            "yearly": 8760,
            "never": float("inf"),
        }
        expected = frequency_hours.get(change_frequency, 720)

        if expected == float("inf"):
            return 1.0

        # Score decreases as we exceed expected update interval
        ratio = age_hours / expected
        return round(max(0.0, min(1.0, 1.0 - ratio * 0.5)), 4)

    def rank(
        self,
        items: list[dict[str, Any]],
        *,
        limit: int = 10,
    ) -> list[tuple[dict[str, Any], ContentScore]]:
        """Rank a list of content items by score.

        Args:
            items: List of content item dicts with scoring fields.
            limit: Maximum number of items to return.

        Returns:
            List of (item, score) tuples sorted by score descending.
        """
        scored = []
        for item in items:
            score = self.score(**item)
            scored.append((item, score))
        scored.sort(key=lambda x: x[1].total, reverse=True)
        return scored[:limit]
''')

commit("feat: add content_scoring.py with scoring engine and factor weights")

# Commit 2: test_content_scoring.py
write_file("tests/test_content_scoring.py", '''
"""Tests for the content scoring and ranking module."""

from datetime import datetime, timedelta

import pytest

from personal_index.content_scoring import (
    ContentScore,
    ContentScorer,
    ScoreFactor,
    ScoreWeights,
)


class TestScoreWeights:
    def test_default_weights(self) -> None:
        w = ScoreWeights()
        assert w.recency == 0.2
        assert w.relevance == 0.25
        assert w.engagement == 0.15
        assert w.quality == 0.15
        assert w.authority == 0.1
        assert w.freshness == 0.15

    def test_normalize_equal_weights(self) -> None:
        w = ScoreWeights(
            recency=1, relevance=1, engagement=1,
            quality=1, authority=1, freshness=1,
        )
        n = w.normalize()
        assert abs(sum([
            n.recency, n.relevance, n.engagement,
            n.quality, n.authority, n.freshness,
        ]) - 1.0) < 0.001

    def test_normalize_zero_weights(self) -> None:
        w = ScoreWeights(
            recency=0, relevance=0, engagement=0,
            quality=0, authority=0, freshness=0,
        )
        n = w.normalize()
        assert n.recency == 0.2  # Falls back to defaults

    def test_normalize_custom_weights(self) -> None:
        w = ScoreWeights(recency=0.5, relevance=0.5)
        n = w.normalize()
        assert abs(n.recency - 0.5) < 0.001
        assert abs(n.relevance - 0.5) < 0.001


class TestContentScore:
    def test_default_score(self) -> None:
        s = ContentScore()
        assert s.total == 0.0
        assert s.factors == {}

    def test_to_dict(self) -> None:
        s = ContentScore(
            total=0.75, recency=0.9, relevance=0.8,
            engagement=0.6, quality=0.7, authority=0.5,
            freshness=0.8,
        )
        d = s.to_dict()
        assert d["total"] == 0.75
        assert d["recency"] == 0.9
        assert isinstance(d["factors"], dict)


class TestContentScorer:
    def setup_method(self) -> None:
        self.scorer = ContentScorer()

    def test_score_all_defaults(self) -> None:
        result = self.scorer.score()
        assert isinstance(result, ContentScore)
        assert 0.0 <= result.total <= 1.0

    def test_score_perfect_relevance(self) -> None:
        result = self.scorer.score(
            keyword_matches=10, total_keywords=10,
        )
        assert result.relevance == 1.0

    def test_score_zero_relevance(self) -> None:
        result = self.scorer.score(
            keyword_matches=0, total_keywords=10,
        )
        assert result.relevance == 0.0

    def test_score_high_engagement(self) -> None:
        result = self.scorer.score(
            view_count=1000, bookmark_count=100, share_count=50,
        )
        assert result.engagement > 0.5

    def test_score_low_engagement(self) -> None:
        result = self.scorer.score(
            view_count=0, bookmark_count=0, share_count=0,
        )
        assert result.engagement == 0.0

    def test_score_quality_with_images(self) -> None:
        result = self.scorer.score(
            word_count=1000, has_images=True,
        )
        assert result.quality > self.scorer.score(word_count=1000).quality

    def test_score_authority_verified(self) -> None:
        result = self.scorer.score(
            domain_authority=0.8, is_verified_source=True,
        )
        assert result.authority > self.scorer.score(
            domain_authority=0.8, is_verified_source=False,
        ).authority

    def test_score_recency_new_content(self) -> None:
        now = datetime.now()
        result = self.scorer.score(published_at=now)
        assert result.recency > 0.9

    def test_score_recency_old_content(self) -> None:
        old = datetime.now() - timedelta(days=365)
        result = self.scorer.score(published_at=old)
        assert result.recency < 0.1

    def test_custom_weights(self) -> None:
        weights = ScoreWeights(relevance=1.0)
        scorer = ContentScorer(weights=weights)
        result = scorer.score(keyword_matches=5, total_keywords=5)
        assert result.total == pytest.approx(1.0, abs=0.01)

    def test_rank_returns_sorted(self) -> None:
        items = [
            {"keyword_matches": 10, "total_keywords": 10},
            {"keyword_matches": 0, "total_keywords": 10},
            {"keyword_matches": 5, "total_keywords": 10},
        ]
        ranked = self.scorer.rank(items)
        assert len(ranked) == 3
        assert ranked[0][1].total >= ranked[1][1].total
        assert ranked[1][1].total >= ranked[2][1].total

    def test_rank_limit(self) -> None:
        items = [{"keyword_matches": i, "total_keywords": 10} for i in range(20)]
        ranked = self.scorer.rank(items, limit=5)
        assert len(ranked) == 5

    def test_score_freshness_never(self) -> None:
        result = self.scorer.score(
            last_crawled=datetime.now(), change_frequency="never",
        )
        assert result.freshness == 1.0

    def test_score_freshness_recent(self) -> None:
        result = self.scorer.score(
            last_crawled=datetime.now(), change_frequency="daily",
        )
        assert result.freshness > 0.9

    def test_score_freshness_stale(self) -> None:
        old = datetime.now() - timedelta(days=100)
        result = self.scorer.score(
            last_crawled=old, change_frequency="daily",
        )
        assert result.freshness < 0.5
''')

commit("test: add comprehensive tests for content_scoring module")

# Commit 3: content_timeline.py
write_file("personal_index/content_timeline.py", '''
"""Content timeline module for tracking content history and events.

Provides functionality to build and query timelines of content-related
events such as creation, updates, bookmarks, and crawls.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class TimelineEventType(Enum):
    """Types of events that can appear in a content timeline."""

    CREATED = "created"
    UPDATED = "updated"
    BOOKMARKED = "bookmarked"
    UNBOOKMARKED = "unbookmarked"
    CRAWLED = "crawled"
    INDEXED = "indexed"
    TAGGED = "tagged"
    CATEGORIZED = "categorized"
    SHARED = "shared"
    VIEWED = "viewed"
    DELETED = "deleted"
    RESTORED = "restored"
    SCORE_CHANGED = "score_changed"


@dataclass
class TimelineEvent:
    """A single event in the content timeline.

    Attributes:
        event_id: Unique identifier for the event.
        event_type: Type of the event.
        timestamp: When the event occurred.
        content_id: ID of the content item this event relates to.
        metadata: Additional event-specific data.
        source: Origin of the event (e.g., 'crawler', 'user', 'system').
    """

    event_id: str
    event_type: TimelineEventType
    timestamp: datetime
    content_id: str
    metadata: dict[str, Any] = field(default_factory=dict)
    source: str = "system"

    def to_dict(self) -> dict[str, Any]:
        """Convert event to dictionary."""
        return {
            "event_id": self.event_id,
            "event_type": self.event_type.value,
            "timestamp": self.timestamp.isoformat(),
            "content_id": self.content_id,
            "metadata": self.metadata,
            "source": self.source,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> TimelineEvent:
        """Create event from dictionary."""
        return cls(
            event_id=data["event_id"],
            event_type=TimelineEventType(data["event_type"]),
            timestamp=datetime.fromisoformat(data["timestamp"]),
            content_id=data["content_id"],
            metadata=data.get("metadata", {}),
            source=data.get("source", "system"),
        )


@dataclass
class Timeline:
    """A collection of timeline events for one or more content items.

    Attributes:
        events: List of timeline events.
        content_ids: Set of content IDs in this timeline.
    """

    events: list[TimelineEvent] = field(default_factory=list)
    content_ids: set[str] = field(default_factory=set)

    def add_event(self, event: TimelineEvent) -> None:
        """Add an event to the timeline."""
        self.events.append(event)
        self.content_ids.add(event.content_id)
        self.events.sort(key=lambda e: e.timestamp)

    def get_events_for_content(
        self,
        content_id: str,
    ) -> list[TimelineEvent]:
        """Get all events for a specific content item."""
        return [e for e in self.events if e.content_id == content_id]

    def get_events_by_type(
        self,
        event_type: TimelineEventType,
    ) -> list[TimelineEvent]:
        """Get all events of a specific type."""
        return [e for e in self.events if e.event_type == event_type]

    def get_events_in_range(
        self,
        start: datetime,
        end: datetime,
    ) -> list[TimelineEvent]:
        """Get events within a time range."""
        return [
            e for e in self.events
            if start <= e.timestamp <= end
        ]

    def get_latest_event(
        self,
        content_id: str | None = None,
    ) -> TimelineEvent | None:
        """Get the most recent event, optionally filtered by content."""
        events = (
            self.get_events_for_content(content_id)
            if content_id
            else self.events
        )
        return events[-1] if events else None

    def get_event_count(self) -> int:
        """Get total number of events."""
        return len(self.events)

    def get_content_event_count(self, content_id: str) -> int:
        """Get number of events for a specific content item."""
        return len(self.get_events_for_content(content_id))

    def to_dict(self) -> dict[str, Any]:
        """Convert timeline to dictionary."""
        return {
            "events": [e.to_dict() for e in self.events],
            "content_ids": list(self.content_ids),
            "event_count": len(self.events),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Timeline:
        """Create timeline from dictionary."""
        timeline = cls()
        for event_data in data.get("events", []):
            timeline.add_event(TimelineEvent.from_dict(event_data))
        return timeline
''')

commit("feat: add content_timeline.py with timeline events and queries")

# Commit 4: test_content_timeline.py
write_file("tests/test_content_timeline.py", '''
"""Tests for the content timeline module."""

from datetime import datetime, timedelta

import pytest

from personal_index.content_timeline import (
    Timeline,
    TimelineEvent,
    TimelineEventType,
)


class TestTimelineEvent:
    def test_create_event(self) -> None:
        event = TimelineEvent(
            event_id="evt-1",
            event_type=TimelineEventType.CREATED,
            timestamp=datetime(2024, 1, 1),
            content_id="content-1",
        )
        assert event.event_id == "evt-1"
        assert event.event_type == TimelineEventType.CREATED
        assert event.source == "system"

    def test_event_to_dict(self) -> None:
        event = TimelineEvent(
            event_id="evt-1",
            event_type=TimelineEventType.BOOKMARKED,
            timestamp=datetime(2024, 1, 1, 12, 0),
            content_id="content-1",
            metadata={"user": "alice"},
            source="user",
        )
        d = event.to_dict()
        assert d["event_type"] == "bookmarked"
        assert d["metadata"]["user"] == "alice"
        assert d["source"] == "user"

    def test_event_from_dict(self) -> None:
        data = {
            "event_id": "evt-1",
            "event_type": "created",
            "timestamp": "2024-01-01T00:00:00",
            "content_id": "content-1",
            "metadata": {"key": "value"},
            "source": "crawler",
        }
        event = TimelineEvent.from_dict(data)
        assert event.event_type == TimelineEventType.CREATED
        assert event.source == "crawler"
        assert event.metadata == {"key": "value"}

    def test_event_custom_metadata(self) -> None:
        event = TimelineEvent(
            event_id="evt-1",
            event_type=TimelineEventType.TAGGED,
            timestamp=datetime.now(),
            content_id="content-1",
            metadata={"tags": ["python", "web"]},
        )
        assert "tags" in event.metadata


class TestTimeline:
    def test_empty_timeline(self) -> None:
        t = Timeline()
        assert t.get_event_count() == 0
        assert t.content_ids == set()

    def test_add_event(self) -> None:
        t = Timeline()
        event = TimelineEvent(
            event_id="evt-1",
            event_type=TimelineEventType.CREATED,
            timestamp=datetime(2024, 1, 1),
            content_id="content-1",
        )
        t.add_event(event)
        assert t.get_event_count() == 1
        assert "content-1" in t.content_ids

    def test_events_sorted_by_time(self) -> None:
        t = Timeline()
        t.add_event(TimelineEvent(
            event_id="evt-2",
            event_type=TimelineEventType.UPDATED,
            timestamp=datetime(2024, 1, 2),
            content_id="content-1",
        ))
        t.add_event(TimelineEvent(
            event_id="evt-1",
            event_type=TimelineEventType.CREATED,
            timestamp=datetime(2024, 1, 1),
            content_id="content-1",
        ))
        assert t.events[0].event_id == "evt-1"
        assert t.events[1].event_id == "evt-2"

    def test_get_events_for_content(self) -> None:
        t = Timeline()
        t.add_event(TimelineEvent(
            event_id="evt-1",
            event_type=TimelineEventType.CREATED,
            timestamp=datetime(2024, 1, 1),
            content_id="content-1",
        ))
        t.add_event(TimelineEvent(
            event_id="evt-2",
            event_type=TimelineEventType.CREATED,
            timestamp=datetime(2024, 1, 2),
            content_id="content-2",
        ))
        events = t.get_events_for_content("content-1")
        assert len(events) == 1
        assert events[0].content_id == "content-1"

    def test_get_events_by_type(self) -> None:
        t = Timeline()
        t.add_event(TimelineEvent(
            event_id="evt-1",
            event_type=TimelineEventType.CREATED,
            timestamp=datetime(2024, 1, 1),
            content_id="content-1",
        ))
        t.add_event(TimelineEvent(
            event_id="evt-2",
            event_type=TimelineEventType.BOOKMARKED,
            timestamp=datetime(2024, 1, 2),
            content_id="content-1",
        ))
        events = t.get_events_by_type(TimelineEventType.BOOKMARKED)
        assert len(events) == 1
        assert events[0].event_type == TimelineEventType.BOOKMARKED

    def test_get_events_in_range(self) -> None:
        t = Timeline()
        t.add_event(TimelineEvent(
            event_id="evt-1",
            event_type=TimelineEventType.CREATED,
            timestamp=datetime(2024, 1, 1),
            content_id="content-1",
        ))
        t.add_event(TimelineEvent(
            event_id="evt-2",
            event_type=TimelineEventType.UPDATED,
            timestamp=datetime(2024, 1, 15),
            content_id="content-1",
        ))
        t.add_event(TimelineEvent(
            event_id="evt-3",
            event_type=TimelineEventType.DELETED,
            timestamp=datetime(2024, 2, 1),
            content_id="content-1",
        ))
        events = t.get_events_in_range(
            datetime(2024, 1, 10), datetime(2024, 1, 20),
        )
        assert len(events) == 1
        assert events[0].event_id == "evt-2"

    def test_get_latest_event(self) -> None:
        t = Timeline()
        t.add_event(TimelineEvent(
            event_id="evt-1",
            event_type=TimelineEventType.CREATED,
            timestamp=datetime(2024, 1, 1),
            content_id="content-1",
        ))
        t.add_event(TimelineEvent(
            event_id="evt-2",
            event_type=TimelineEventType.UPDATED,
            timestamp=datetime(2024, 1, 2),
            content_id="content-1",
        ))
        latest = t.get_latest_event()
        assert latest is not None
        assert latest.event_id == "evt-2"

    def test_get_latest_event_empty(self) -> None:
        t = Timeline()
        assert t.get_latest_event() is None

    def test_get_latest_event_by_content(self) -> None:
        t = Timeline()
        t.add_event(TimelineEvent(
            event_id="evt-1",
            event_type=TimelineEventType.CREATED,
            timestamp=datetime(2024, 1, 1),
            content_id="content-1",
        ))
        t.add_event(TimelineEvent(
            event_id="evt-2",
            event_type=TimelineEventType.CREATED,
            timestamp=datetime(2024, 1, 2),
            content_id="content-2",
        ))
        latest = t.get_latest_event("content-1")
        assert latest is not None
        assert latest.content_id == "content-1"

    def test_get_content_event_count(self) -> None:
        t = Timeline()
        for i in range(5):
            t.add_event(TimelineEvent(
                event_id=f"evt-{i}",
                event_type=TimelineEventType.CREATED,
                timestamp=datetime(2024, 1, i + 1),
                content_id="content-1",
            ))
        assert t.get_content_event_count("content-1") == 5
        assert t.get_content_event_count("content-2") == 0

    def test_to_dict_and_from_dict(self) -> None:
        t = Timeline()
        t.add_event(TimelineEvent(
            event_id="evt-1",
            event_type=TimelineEventType.CREATED,
            timestamp=datetime(2024, 1, 1),
            content_id="content-1",
        ))
        d = t.to_dict()
        t2 = Timeline.from_dict(d)
        assert t2.get_event_count() == 1
        assert t2.events[0].event_id == "evt-1"
''')

commit("test: add comprehensive tests for content_timeline module")

# Commit 5: content_export/json_export.py
write_file("personal_index/content_export/__init__.py", '''
"""Content export module for personal-index.

Provides functionality to export content in various formats
including JSON, CSV, and Markdown.
"""

from personal_index.content_export.json_export import JsonExporter
from personal_index.content_export.csv_export import CsvExporter
from personal_index.content_export.markdown_export import MarkdownExporter

__all__ = [
    "CsvExporter",
    "JsonExporter",
    "MarkdownExporter",
]
''')

commit("feat: create content_export package with __init__.py")

# Commit 6: json_export.py
write_file("personal_index/content_export/json_export.py", '''
"""JSON export functionality for personal-index content.

Exports content items, bookmarks, tags, and metadata to JSON format
with configurable options for pretty printing and field selection.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any


@dataclass
class JsonExportOptions:
    """Options for JSON export.

    Attributes:
        indent: Number of spaces for indentation (None for compact).
        sort_keys: Whether to sort dictionary keys.
        include_metadata: Whether to include content metadata.
        include_tags: Whether to include content tags.
        include_scores: Whether to include content scores.
        fields: Specific fields to include (None for all).
        exclude_fields: Fields to exclude from export.
    """

    indent: int | None = 2
    sort_keys: bool = True
    include_metadata: bool = True
    include_tags: bool = True
    include_scores: bool = False
    fields: list[str] | None = None
    exclude_fields: list[str] = field(default_factory=list)


class JsonExporter:
    """Exports content data to JSON format.

    Supports exporting individual items or collections with
    configurable field selection and formatting.
    """

    def __init__(self, options: JsonExportOptions | None = None) -> None:
        self.options = options or JsonExportOptions()

    def export_item(self, item: dict[str, Any]) -> str:
        """Export a single content item to JSON string.

        Args:
            item: Content item dictionary.

        Returns:
            JSON string representation of the item.
        """
        filtered = self._filter_fields(item)
        return json.dumps(filtered, indent=self.options.indent,
                         sort_keys=self.options.sort_keys,
                         default=str)

    def export_items(self, items: list[dict[str, Any]]) -> str:
        """Export multiple content items to JSON string.

        Args:
            items: List of content item dictionaries.

        Returns:
            JSON string representation of the items list.
        """
        filtered = [self._filter_fields(item) for item in items]
        return json.dumps(filtered, indent=self.options.indent,
                         sort_keys=self.options.sort_keys,
                         default=str)

    def export_to_file(
        self,
        items: list[dict[str, Any]],
        filepath: str | Path,
    ) -> int:
        """Export items to a JSON file.

        Args:
            items: List of content item dictionaries.
            filepath: Path to the output file.

        Returns:
            Number of items exported.
        """
        filepath = Path(filepath)
        filepath.parent.mkdir(parents=True, exist_ok=True)
        content = self.export_items(items)
        filepath.write_text(content, encoding="utf-8")
        return len(items)

    def export_collection(
        self,
        name: str,
        items: list[dict[str, Any]],
        metadata: dict[str, Any] | None = None,
    ) -> str:
        """Export a named collection with metadata.

        Args:
            name: Name of the collection.
            items: List of content items.
            metadata: Optional collection metadata.

        Returns:
            JSON string of the collection.
        """
        collection = {
            "collection_name": name,
            "exported_at": datetime.now().isoformat(),
            "item_count": len(items),
            "items": [self._filter_fields(item) for item in items],
        }
        if metadata:
            collection["metadata"] = metadata
        return json.dumps(collection, indent=self.options.indent,
                         sort_keys=self.options.sort_keys,
                         default=str)

    def _filter_fields(self, item: dict[str, Any]) -> dict[str, Any]:
        """Filter item fields based on export options."""
        result = dict(item)

        if not self.options.include_metadata:
            result.pop("metadata", None)

        if not self.options.include_tags:
            result.pop("tags", None)

        if not self.options.include_scores:
            result.pop("score", None)
            result.pop("score_details", None)

        for field_name in self.options.exclude_fields:
            result.pop(field_name, None)

        if self.options.fields:
            result = {
                k: v for k, v in result.items()
                if k in self.options.fields
            }

        return result

    def export_summary(
        self,
        items: list[dict[str, Any]],
    ) -> str:
        """Export a summary of the collection.

        Args:
            items: List of content items.

        Returns:
            JSON string with summary statistics.
        """
        total = len(items)
        tagged = sum(1 for i in items if i.get("tags"))
        bookmarked = sum(1 for i in items if i.get("bookmarked"))

        domains = set()
        for item in items:
            url = item.get("url", "")
            if "://" in url:
                domain = url.split("://")[1].split("/")[0]
                domains.add(domain)

        summary = {
            "total_items": total,
            "tagged_items": tagged,
            "bookmarked_items": bookmarked,
            "unique_domains": len(domains),
            "exported_at": datetime.now().isoformat(),
        }
        return json.dumps(summary, indent=self.options.indent,
                         sort_keys=self.options.sort_keys)
''')

commit("feat: add json_export.py with JsonExporter and export options")

# Commit 7: test_json_export.py
write_file("tests/test_json_export.py", '''
"""Tests for the JSON export module."""

import json
from pathlib import Path

import pytest

from personal_index.content_export.json_export import (
    JsonExportOptions,
    JsonExporter,
)


class TestJsonExportOptions:
    def test_defaults(self) -> None:
        opts = JsonExportOptions()
        assert opts.indent == 2
        assert opts.sort_keys is True
        assert opts.include_metadata is True
        assert opts.include_tags is True
        assert opts.include_scores is False
        assert opts.fields is None
        assert opts.exclude_fields == []


class TestJsonExporter:
    def setup_method(self) -> None:
        self.exporter = JsonExporter()
        self.items = [
            {
                "id": "1",
                "title": "Test Article",
                "url": "https://example.com/article",
                "tags": ["python", "web"],
                "metadata": {"author": "Alice"},
                "score": 0.85,
                "bookmarked": True,
            },
            {
                "id": "2",
                "title": "Another Article",
                "url": "https://example.com/other",
                "tags": ["javascript"],
                "metadata": {"author": "Bob"},
                "score": 0.72,
                "bookmarked": False,
            },
        ]

    def test_export_single_item(self) -> None:
        result = self.exporter.export_item(self.items[0])
        data = json.loads(result)
        assert data["id"] == "1"
        assert data["title"] == "Test Article"

    def test_export_multiple_items(self) -> None:
        result = self.exporter.export_items(self.items)
        data = json.loads(result)
        assert len(data) == 2
        assert data[0]["id"] == "1"
        assert data[1]["id"] == "2"

    def test_export_to_file(self, tmp_path: Path) -> None:
        filepath = tmp_path / "export.json"
        count = self.exporter.export_to_file(self.items, filepath)
        assert count == 2
        assert filepath.exists()
        data = json.loads(filepath.read_text())
        assert len(data) == 2

    def test_export_to_file_creates_dirs(self, tmp_path: Path) -> None:
        filepath = tmp_path / "sub" / "dir" / "export.json"
        count = self.exporter.export_to_file(self.items, filepath)
        assert count == 2
        assert filepath.exists()

    def test_export_collection(self) -> None:
        result = self.exporter.export_collection(
            "My Collection", self.items,
            metadata={"created_by": "test"},
        )
        data = json.loads(result)
        assert data["collection_name"] == "My Collection"
        assert data["item_count"] == 2
        assert data["metadata"]["created_by"] == "test"

    def test_exclude_scores(self) -> None:
        opts = JsonExportOptions(include_scores=False)
        exporter = JsonExporter(options=opts)
        result = exporter.export_item(self.items[0])
        data = json.loads(result)
        assert "score" not in data

    def test_include_scores(self) -> None:
        opts = JsonExportOptions(include_scores=True)
        exporter = JsonExporter(options=opts)
        result = exporter.export_item(self.items[0])
        data = json.loads(result)
        assert "score" in data
        assert data["score"] == 0.85

    def test_exclude_tags(self) -> None:
        opts = JsonExportOptions(include_tags=False)
        exporter = JsonExporter(options=opts)
        result = exporter.export_item(self.items[0])
        data = json.loads(result)
        assert "tags" not in data

    def test_exclude_metadata(self) -> None:
        opts = JsonExportOptions(include_metadata=False)
        exporter = JsonExporter(options=opts)
        result = exporter.export_item(self.items[0])
        data = json.loads(result)
        assert "metadata" not in data

    def test_field_selection(self) -> None:
        opts = JsonExportOptions(fields=["id", "title"])
        exporter = JsonExporter(options=opts)
        result = exporter.export_item(self.items[0])
        data = json.loads(result)
        assert set(data.keys()) == {"id", "title"}

    def test_exclude_fields(self) -> None:
        opts = JsonExportOptions(exclude_fields=["tags", "metadata"])
        exporter = JsonExporter(options=opts)
        result = exporter.export_item(self.items[0])
        data = json.loads(result)
        assert "tags" not in data
        assert "metadata" not in data

    def test_compact_output(self) -> None:
        opts = JsonExportOptions(indent=None)
        exporter = JsonExporter(options=opts)
        result = exporter.export_item(self.items[0])
        assert "\n" not in result

    def test_export_summary(self) -> None:
        result = self.exporter.export_summary(self.items)
        data = json.loads(result)
        assert data["total_items"] == 2
        assert data["tagged_items"] == 2
        assert data["bookmarked_items"] == 1
        assert data["unique_domains"] == 1

    def test_export_empty_items(self) -> None:
        result = self.exporter.export_items([])
        data = json.loads(result)
        assert data == []

    def test_export_preserves_order(self) -> None:
        opts = JsonExportOptions(sort_keys=False)
        exporter = JsonExporter(options=opts)
        result = exporter.export_item(self.items[0])
        data = json.loads(result)
        assert list(data.keys())[0] == "id"
''')

commit("test: add comprehensive tests for json_export module")

# Commit 8: csv_export.py
write_file("personal_index/content_export/csv_export.py", '''
"""CSV export functionality for personal-index content.

Exports content items to CSV format with configurable columns,
delimiters, and encoding options.
"""

from __future__ import annotations

import csv
import io
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any


@dataclass
class CsvExportOptions:
    """Options for CSV export.

    Attributes:
        delimiter: Column delimiter character.
        quotechar: Quote character for fields.
        quoting: CSV quoting mode.
        encoding: File encoding.
        include_header: Whether to include header row.
        columns: Specific columns to include (None for all).
        flatten_nested: Whether to flatten nested dicts.
        separator_nested: Separator for flattened nested keys.
    """

    delimiter: str = ","
    quotechar: str = '"'
    quoting: int = csv.QUOTE_MINIMAL
    encoding: str = "utf-8"
    include_header: bool = True
    columns: list[str] | None = None
    flatten_nested: bool = True
    separator_nested: str = "."


class CsvExporter:
    """Exports content data to CSV format.

    Handles nested data structures, date formatting, and
    configurable column selection.
    """

    def __init__(self, options: CsvExportOptions | None = None) -> None:
        self.options = options or CsvExportOptions()

    def export_items(self, items: list[dict[str, Any]]) -> str:
        """Export items to CSV string.

        Args:
            items: List of content item dictionaries.

        Returns:
            CSV string representation.
        """
        if not items:
            return ""

        output = io.StringIO()
        processed = [self._process_item(item) for item in items]
        columns = self._get_columns(processed)

        writer = csv.DictWriter(
            output,
            fieldnames=columns,
            delimiter=self.options.delimiter,
            quotechar=self.options.quotechar,
            quoting=self.options.quoting,
        )

        if self.options.include_header:
            writer.writeheader()

        for item in processed:
            row = {col: item.get(col, "") for col in columns}
            writer.writerow(row)

        return output.getvalue()

    def export_to_file(
        self,
        items: list[dict[str, Any]],
        filepath: str | Path,
    ) -> int:
        """Export items to a CSV file.

        Args:
            items: List of content item dictionaries.
            filepath: Path to the output file.

        Returns:
            Number of items exported.
        """
        filepath = Path(filepath)
        filepath.parent.mkdir(parents=True, exist_ok=True)
        content = self.export_items(items)
        filepath.write_text(content, encoding=self.options.encoding)
        return len(items)

    def _process_item(self, item: dict[str, Any]) -> dict[str, Any]:
        """Process a single item for CSV export."""
        result: dict[str, Any] = {}
        for key, value in item.items():
            if self.options.flatten_nested and isinstance(value, dict):
                for sub_key, sub_value in value.items():
                    flat_key = (
                        f"{key}{self.options.separator_nested}{sub_key}"
                    )
                    result[flat_key] = self._format_value(sub_value)
            else:
                result[key] = self._format_value(value)
        return result

    def _format_value(self, value: Any) -> str:
        """Format a value for CSV output."""
        if value is None:
            return ""
        if isinstance(value, datetime):
            return value.isoformat()
        if isinstance(value, (list, set)):
            return "; ".join(str(v) for v in value)
        if isinstance(value, bool):
            return str(value).lower()
        return str(value)

    def _get_columns(
        self,
        items: list[dict[str, Any]],
    ) -> list[str]:
        """Determine columns from items."""
        all_columns = set()
        for item in items:
            all_columns.update(item.keys())

        if self.options.columns:
            return [
                c for c in self.options.columns
                if c in all_columns
            ]
        return sorted(all_columns)
''')

commit("feat: add csv_export.py with CsvExporter and nested data support")

# Commit 9: test_csv_export.py
write_file("tests/test_csv_export.py", '''
"""Tests for the CSV export module."""

from pathlib import Path

import pytest

from personal_index.content_export.csv_export import (
    CsvExportOptions,
    CsvExporter,
)


class TestCsvExportOptions:
    def test_defaults(self) -> None:
        opts = CsvExportOptions()
        assert opts.delimiter == ","
        assert opts.quotechar == '"'
        assert opts.include_header is True
        assert opts.flatten_nested is True


class TestCsvExporter:
    def setup_method(self) -> None:
        self.exporter = CsvExporter()
        self.items = [
            {
                "id": "1",
                "title": "Test Article",
                "url": "https://example.com/article",
                "tags": ["python", "web"],
                "metadata": {"author": "Alice", "date": "2024-01-01"},
                "score": 0.85,
                "bookmarked": True,
            },
            {
                "id": "2",
                "title": "Another Article",
                "url": "https://example.com/other",
                "tags": ["javascript"],
                "metadata": {"author": "Bob"},
                "score": 0.72,
                "bookmarked": False,
            },
        ]

    def test_export_basic(self) -> None:
        result = self.exporter.export_items(self.items)
        lines = result.strip().split("\\n")
        assert len(lines) == 3  # header + 2 items
        assert "id" in lines[0]
        assert "title" in lines[0]

    def test_export_no_header(self) -> None:
        opts = CsvExportOptions(include_header=False)
        exporter = CsvExporter(options=opts)
        result = exporter.export_items(self.items)
        lines = result.strip().split("\\n")
        assert len(lines) == 2

    def test_export_flattened_nested(self) -> None:
        result = self.exporter.export_items(self.items)
        assert "metadata.author" in result

    def test_export_no_flatten(self) -> None:
        opts = CsvExportOptions(flatten_nested=False)
        exporter = CsvExporter(options=opts)
        result = exporter.export_items(self.items)
        assert "metadata" in result
        assert "metadata.author" not in result

    def test_export_tags_as_string(self) -> None:
        result = self.exporter.export_items(self.items)
        assert "python; web" in result

    def test_export_boolean(self) -> None:
        result = self.exporter.export_items(self.items)
        assert "true" in result.lower()

    def test_export_to_file(self, tmp_path: Path) -> None:
        filepath = tmp_path / "export.csv"
        count = self.exporter.export_to_file(self.items, filepath)
        assert count == 2
        assert filepath.exists()
        content = filepath.read_text()
        assert "id" in content

    def test_export_empty(self) -> None:
        result = self.exporter.export_items([])
        assert result == ""

    def test_custom_delimiter(self) -> None:
        opts = CsvExportOptions(delimiter="\\t")
        exporter = CsvExporter(options=opts)
        result = exporter.export_items(self.items)
        assert "\\t" in result

    def test_column_selection(self) -> None:
        opts = CsvExportOptions(columns=["id", "title"])
        exporter = CsvExporter(options=opts)
        result = exporter.export_items(self.items)
        lines = result.strip().split("\\n")
        assert "url" not in lines[0]
        assert "id" in lines[0]
        assert "title" in lines[0]

    def test_none_values(self) -> None:
        items = [{"id": "1", "title": None}]
        result = self.exporter.export_items(items)
        assert result.strip().split("\\n")[1] == '1,""'

    def test_custom_separator_nested(self) -> None:
        opts = CsvExportOptions(separator_nested="_")
        exporter = CsvExporter(options=opts)
        result = exporter.export_items(self.items)
        assert "metadata_author" in result
''')

commit("test: add comprehensive tests for csv_export module")

# Commit 10: markdown_export.py
write_file("personal_index/content_export/markdown_export.py", '''
"""Markdown export functionality for personal-index content.

Exports content items to formatted Markdown documents with
headings, links, tags, and metadata.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any


class MarkdownExporter:
    """Exports content data to Markdown format.

    Generates readable Markdown documents with proper formatting
    for content items, collections, and summaries.
    """

    def export_item(self, item: dict[str, Any]) -> str:
        """Export a single content item to Markdown.

        Args:
            item: Content item dictionary.

        Returns:
            Markdown string for the item.
        """
        lines = []
        title = item.get("title", "Untitled")
        url = item.get("url", "")
        lines.append(f"## {title}")
        lines.append("")

        if url:
            lines.append(f"[{title}]({url})")
            lines.append("")

        if item.get("description"):
            lines.append(item["description"])
            lines.append("")

        if item.get("tags"):
            tags = item["tags"]
            if isinstance(tags, list):
                tag_str = ", ".join(f"`{t}`" for t in tags)
            else:
                tag_str = str(tags)
            lines.append(f"**Tags:** {tag_str}")
            lines.append("")

        if item.get("bookmarked"):
            lines.append("*Bookmarked*")
            lines.append("")

        if item.get("score") is not None:
            lines.append(f"**Score:** {item['score']:.2f}")
            lines.append("")

        if item.get("metadata"):
            lines.append("### Metadata")
            lines.append("")
            for key, value in item["metadata"].items():
                lines.append(f"- **{key}:** {value}")
            lines.append("")

        return "\\n".join(lines)

    def export_items(
        self,
        items: list[dict[str, Any]],
        title: str = "Content Export",
    ) -> str:
        """Export multiple items to a Markdown document.

        Args:
            items: List of content items.
            title: Document title.

        Returns:
            Complete Markdown document string.
        """
        lines = [f"# {title}", ""]
        lines.append(f"*Exported at: {datetime.now().strftime('%Y-%m-%d %H:%M')}*")
        lines.append("")
        lines.append("---")
        lines.append("")

        for item in items:
            lines.append(self.export_item(item))
            lines.append("---")
            lines.append("")

        return "\\n".join(lines)

    def export_to_file(
        self,
        items: list[dict[str, Any]],
        filepath: str | Path,
        title: str = "Content Export",
    ) -> int:
        """Export items to a Markdown file.

        Args:
            items: List of content items.
            filepath: Path to the output file.
            title: Document title.

        Returns:
            Number of items exported.
        """
        filepath = Path(filepath)
        filepath.parent.mkdir(parents=True, exist_ok=True)
        content = self.export_items(items, title=title)
        filepath.write_text(content, encoding="utf-8")
        return len(items)

    def export_table(
        self,
        items: list[dict[str, Any]],
        columns: list[str] | None = None,
    ) -> str:
        """Export items as a Markdown table.

        Args:
            items: List of content items.
            columns: Columns to include (None for common ones).

        Returns:
            Markdown table string.
        """
        if not items:
            return ""

        if columns is None:
            columns = ["title", "url", "tags", "score", "bookmarked"]

        # Filter to available columns
        available = set()
        for item in items:
            available.update(item.keys())
        columns = [c for c in columns if c in available]

        # Header
        header = "| " + " | ".join(columns) + " |"
        separator = "| " + " | ".join("---" for _ in columns) + " |"

        lines = [header, separator]

        for item in items:
            row_parts = []
            for col in columns:
                value = item.get(col, "")
                if isinstance(value, list):
                    value = ", ".join(str(v) for v in value)
                elif isinstance(value, bool):
                    value = "Yes" if value else "No"
                elif isinstance(value, float):
                    value = f"{value:.2f}"
                row_parts.append(str(value))
            lines.append("| " + " | ".join(row_parts) + " |")

        return "\\n".join(lines)
''')

commit("feat: add markdown_export.py with MarkdownExporter and table support")

# Commit 11: test_markdown_export.py
write_file("tests/test_markdown_export.py", '''
"""Tests for the Markdown export module."""

from pathlib import Path

from personal_index.content_export.markdown_export import MarkdownExporter


class TestMarkdownExporter:
    def setup_method(self) -> None:
        self.exporter = MarkdownExporter()
        self.items = [
            {
                "id": "1",
                "title": "Test Article",
                "url": "https://example.com/article",
                "description": "A test article about Python.",
                "tags": ["python", "web"],
                "score": 0.85,
                "bookmarked": True,
                "metadata": {"author": "Alice", "date": "2024-01-01"},
            },
            {
                "id": "2",
                "title": "Another Article",
                "url": "https://example.com/other",
                "tags": ["javascript"],
                "score": 0.72,
                "bookmarked": False,
            },
        ]

    def test_export_single_item(self) -> None:
        result = self.exporter.export_item(self.items[0])
        assert "## Test Article" in result
        assert "[Test Article](https://example.com/article)" in result
        assert "A test article about Python." in result

    def test_export_item_tags(self) -> None:
        result = self.exporter.export_item(self.items[0])
        assert "`python`" in result
        assert "`web`" in result

    def test_export_item_bookmarked(self) -> None:
        result = self.exporter.export_item(self.items[0])
        assert "*Bookmarked*" in result

    def test_export_item_score(self) -> None:
        result = self.exporter.export_item(self.items[0])
        assert "Score" in result

    def test_export_item_metadata(self) -> None:
        result = self.exporter.export_item(self.items[0])
        assert "### Metadata" in result
        assert "author" in result

    def test_export_multiple_items(self) -> None:
        result = self.exporter.export_items(self.items)
        assert "# Content Export" in result
        assert "## Test Article" in result
        assert "## Another Article" in result

    def test_export_to_file(self, tmp_path: Path) -> None:
        filepath = tmp_path / "export.md"
        count = self.exporter.export_to_file(self.items, filepath)
        assert count == 2
        assert filepath.exists()
        content = filepath.read_text()
        assert "## Test Article" in content

    def test_export_table(self) -> None:
        result = self.exporter.export_table(self.items)
        lines = result.split("\\n")
        assert len(lines) == 4  # header + separator + 2 rows
        assert "|" in lines[0]
        assert "---" in lines[1]

    def test_export_table_custom_columns(self) -> None:
        result = self.exporter.export_table(
            self.items, columns=["title", "score"],
        )
        lines = result.split("\\n")
        assert "title" in lines[0]
        assert "score" in lines[0]
        assert "url" not in lines[0]

    def test_export_table_boolean(self) -> None:
        result = self.exporter.export_table(self.items)
        assert "Yes" in result or "No" in result

    def test_export_table_empty(self) -> None:
        result = self.exporter.export_table([])
        assert result == ""

    def test_export_untitled_item(self) -> None:
        item = {"id": "1", "url": "https://example.com"}
        result = self.exporter.export_item(item)
        assert "## Untitled" in result

    def test_export_item_no_url(self) -> None:
        item = {"id": "1", "title": "No URL"}
        result = self.exporter.export_item(item)
        assert "http" not in result
''')

commit("test: add comprehensive tests for markdown_export module")

print(f"Completed 11 commits so far")
run("git log --oneline | head -15")
