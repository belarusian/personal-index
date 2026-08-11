#!/usr/bin/env python3
"""Generate commits 12-30 for personal-index."""

import subprocess
import os
import textwrap

def run(cmd):
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    return result.returncode, result.stdout, result.stderr

def write_file(path, content):
    os.makedirs(os.path.dirname(path) if os.path.dirname(path) else '.', exist_ok=True)
    with open(path, 'w') as f:
        f.write(textwrap.dedent(content).lstrip())

def commit(msg):
    run("git add -A")
    code, out, err = run(f'git commit -m "{msg}"')
    return code == 0

# Commit 12: content_digest.py
write_file("personal_index/content_digest.py", '''
"""Content digest module for generating content summaries and digests.

Creates daily/weekly/monthly digest emails and reports from
indexed content, highlighting new and important items.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any


class DigestFrequency(Enum):
    """How often digests should be generated."""

    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"


@dataclass
class DigestConfig:
    """Configuration for digest generation.

    Attributes:
        frequency: How often to generate digests.
        max_items: Maximum items per digest.
        min_score: Minimum content score to include.
        include_tags: Whether to include tag information.
        include_preview: Whether to include content previews.
        preview_length: Character limit for previews.
        group_by: How to group items (tag, domain, date).
        sort_by: How to sort items (score, date, title).
    """

    frequency: DigestFrequency = DigestFrequency.DAILY
    max_items: int = 20
    min_score: float = 0.0
    include_tags: bool = True
    include_preview: bool = True
    preview_length: int = 200
    group_by: str = "date"
    sort_by: str = "score"


@dataclass
class DigestItem:
    """A single item in a digest.

    Attributes:
        title: Content title.
        url: Content URL.
        preview: Content preview text.
        tags: Content tags.
        score: Content score.
        published_at: Publication date.
        domain: Source domain.
    """

    title: str
    url: str
    preview: str = ""
    tags: list[str] = field(default_factory=list)
    score: float = 0.0
    published_at: datetime | None = None
    domain: str = ""


@dataclass
class ContentDigest:
    """A complete content digest.

    Attributes:
        title: Digest title.
        period_start: Start of the digest period.
        period_end: End of the digest period.
        items: Items included in the digest.
        total_new: Total new items in period.
        top_tags: Most common tags.
        top_domains: Most common source domains.
    """

    title: str
    period_start: datetime
    period_end: datetime
    items: list[DigestItem] = field(default_factory=list)
    total_new: int = 0
    top_tags: list[str] = field(default_factory=list)
    top_domains: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Convert digest to dictionary."""
        return {
            "title": self.title,
            "period_start": self.period_start.isoformat(),
            "period_end": self.period_end.isoformat(),
            "items": [
                {
                    "title": i.title,
                    "url": i.url,
                    "preview": i.preview,
                    "tags": i.tags,
                    "score": i.score,
                }
                for i in self.items
            ],
            "total_new": self.total_new,
            "top_tags": self.top_tags,
            "top_domains": self.top_domains,
        }


class DigestGenerator:
    """Generates content digests from indexed items.

    Filters, sorts, and formats content items into digest
    reports based on configurable criteria.
    """

    def __init__(self, config: DigestConfig | None = None) -> None:
        self.config = config or DigestConfig()

    def generate(
        self,
        items: list[dict[str, Any]],
        period_start: datetime | None = None,
        period_end: datetime | None = None,
    ) -> ContentDigest:
        """Generate a digest from content items.

        Args:
            items: List of content items.
            period_start: Start of digest period.
            period_end: End of digest period.

        Returns:
            ContentDigest with filtered and formatted items.
        """
        if period_end is None:
            period_end = datetime.now()
        if period_start is None:
            delta = self._get_period_delta()
            period_start = period_end - delta

        # Filter items by period and score
        filtered = self._filter_items(items, period_start, period_end)

        # Sort items
        sorted_items = self._sort_items(filtered)

        # Limit items
        sorted_items = sorted_items[: self.config.max_items]

        # Convert to digest items
        digest_items = [self._to_digest_item(item) for item in sorted_items]

        # Compute statistics
        top_tags = self._compute_top_tags(filtered, 5)
        top_domains = self._compute_top_domains(filtered, 5)

        title = self._generate_title(period_start, period_end)

        return ContentDigest(
            title=title,
            period_start=period_start,
            period_end=period_end,
            items=digest_items,
            total_new=len(filtered),
            top_tags=top_tags,
            top_domains=top_domains,
        )

    def _get_period_delta(self) -> timedelta:
        """Get the time delta for the digest period."""
        deltas = {
            DigestFrequency.DAILY: timedelta(days=1),
            DigestFrequency.WEEKLY: timedelta(weeks=1),
            DigestFrequency.MONTHLY: timedelta(days=30),
        }
        return deltas.get(self.config.frequency, timedelta(days=1))

    def _filter_items(
        self,
        items: list[dict[str, Any]],
        start: datetime,
        end: datetime,
    ) -> list[dict[str, Any]]:
        """Filter items by date range and minimum score."""
        filtered = []
        for item in items:
            score = item.get("score", 0.0)
            if score < self.config.min_score:
                continue

            pub_date = item.get("published_at")
            if pub_date:
                if isinstance(pub_date, str):
                    pub_date = datetime.fromisoformat(pub_date)
                if not (start <= pub_date <= end):
                    continue

            filtered.append(item)
        return filtered

    def _sort_items(
        self,
        items: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Sort items by configured sort field."""
        sort_keys = {
            "score": lambda x: x.get("score", 0.0),
            "date": lambda x: x.get("published_at") or datetime.min,
            "title": lambda x: x.get("title", ""),
        }
        key_func = sort_keys.get(self.config.sort_by, sort_keys["score"])
        reverse = self.config.sort_by != "title"
        return sorted(items, key=key_func, reverse=reverse)

    def _to_digest_item(self, item: dict[str, Any]) -> DigestItem:
        """Convert a content item to a digest item."""
        preview = ""
        if self.config.include_preview:
            desc = item.get("description", item.get("content", ""))
            if isinstance(desc, str):
                preview = desc[: self.config.preview_length]

        tags = item.get("tags", [])
        if not self.config.include_tags:
            tags = []

        url = item.get("url", "")
        domain = ""
        if "://" in url:
            domain = url.split("://")[1].split("/")[0]

        return DigestItem(
            title=item.get("title", "Untitled"),
            url=url,
            preview=preview,
            tags=tags if isinstance(tags, list) else [],
            score=item.get("score", 0.0),
            published_at=item.get("published_at"),
            domain=domain,
        )

    def _compute_top_tags(
        self,
        items: list[dict[str, Any]],
        limit: int = 5,
    ) -> list[str]:
        """Compute the most common tags."""
        tag_count: dict[str, int] = {}
        for item in items:
            for tag in item.get("tags", []):
                tag_count[tag] = tag_count.get(tag, 0) + 1
        sorted_tags = sorted(tag_count.items(), key=lambda x: x[1], reverse=True)
        return [tag for tag, _ in sorted_tags[:limit]]

    def _compute_top_domains(
        self,
        items: list[dict[str, Any]],
        limit: int = 5,
    ) -> list[str]:
        """Compute the most common source domains."""
        domain_count: dict[str, int] = {}
        for item in items:
            url = item.get("url", "")
            if "://" in url:
                domain = url.split("://")[1].split("/")[0]
                domain_count[domain] = domain_count.get(domain, 0) + 1
        sorted_domains = sorted(
            domain_count.items(), key=lambda x: x[1], reverse=True,
        )
        return [domain for domain, _ in sorted_domains[:limit]]

    def _generate_title(
        self,
        start: datetime,
        end: datetime,
    ) -> str:
        """Generate a title for the digest."""
        freq_label = {
            DigestFrequency.DAILY: "Daily",
            DigestFrequency.WEEKLY: "Weekly",
            DigestFrequency.MONTHLY: "Monthly",
        }
        label = freq_label.get(self.config.frequency, "Content")
        return f"{label} Digest: {start.strftime('%b %d')} - {end.strftime('%b %d, %Y')}"
''')

commit("feat: add content_digest.py with digest generation engine")

# Commit 13: test_content_digest.py
write_file("tests/test_content_digest.py", '''
"""Tests for the content digest module."""

from datetime import datetime, timedelta

from personal_index.content_digest import (
    ContentDigest,
    DigestConfig,
    DigestFrequency,
    DigestGenerator,
    DigestItem,
)


class TestDigestConfig:
    def test_defaults(self) -> None:
        config = DigestConfig()
        assert config.frequency == DigestFrequency.DAILY
        assert config.max_items == 20
        assert config.min_score == 0.0
        assert config.include_tags is True


class TestDigestItem:
    def test_create(self) -> None:
        item = DigestItem(
            title="Test",
            url="https://example.com/test",
            tags=["python"],
            score=0.8,
        )
        assert item.title == "Test"
        assert item.tags == ["python"]


class TestContentDigest:
    def test_to_dict(self) -> None:
        digest = ContentDigest(
            title="Test Digest",
            period_start=datetime(2024, 1, 1),
            period_end=datetime(2024, 1, 2),
            items=[
                DigestItem(title="Item 1", url="https://example.com/1"),
            ],
            total_new=1,
            top_tags=["python"],
            top_domains=["example.com"],
        )
        d = digest.to_dict()
        assert d["title"] == "Test Digest"
        assert len(d["items"]) == 1
        assert d["total_new"] == 1


class TestDigestGenerator:
    def setup_method(self) -> None:
        self.now = datetime(2024, 1, 15, 12, 0)
        self.items = [
            {
                "title": "Article 1",
                "url": "https://example.com/1",
                "description": "First article description.",
                "tags": ["python", "web"],
                "score": 0.9,
                "published_at": datetime(2024, 1, 14),
            },
            {
                "title": "Article 2",
                "url": "https://example.com/2",
                "description": "Second article description.",
                "tags": ["javascript"],
                "score": 0.7,
                "published_at": datetime(2024, 1, 13),
            },
            {
                "title": "Article 3",
                "url": "https://other.com/3",
                "description": "Third article.",
                "tags": ["python", "data"],
                "score": 0.5,
                "published_at": datetime(2024, 1, 14),
            },
            {
                "title": "Low Score",
                "url": "https://example.com/low",
                "tags": ["spam"],
                "score": 0.1,
                "published_at": datetime(2024, 1, 14),
            },
        ]

    def test_generate_basic(self) -> None:
        gen = DigestGenerator()
        digest = gen.generate(
            self.items,
            period_start=datetime(2024, 1, 13),
            period_end=datetime(2024, 1, 15),
        )
        assert digest.title
        assert len(digest.items) > 0

    def test_generate_min_score_filter(self) -> None:
        config = DigestConfig(min_score=0.6)
        gen = DigestGenerator(config=config)
        digest = gen.generate(
            self.items,
            period_start=datetime(2024, 1, 13),
            period_end=datetime(2024, 1, 15),
        )
        for item in digest.items:
            assert item.score >= 0.6

    def test_generate_max_items(self) -> None:
        config = DigestConfig(max_items=1)
        gen = DigestGenerator(config=config)
        digest = gen.generate(
            self.items,
            period_start=datetime(2024, 1, 13),
            period_end=datetime(2024, 1, 15),
        )
        assert len(digest.items) <= 1

    def test_generate_sort_by_score(self) -> None:
        config = DigestConfig(sort_by="score")
        gen = DigestGenerator(config=config)
        digest = gen.generate(
            self.items,
            period_start=datetime(2024, 1, 13),
            period_end=datetime(2024, 1, 15),
        )
        scores = [i.score for i in digest.items]
        assert scores == sorted(scores, reverse=True)

    def test_generate_top_tags(self) -> None:
        gen = DigestGenerator()
        digest = gen.generate(
            self.items,
            period_start=datetime(2024, 1, 13),
            period_end=datetime(2024, 1, 15),
        )
        assert "python" in digest.top_tags

    def test_generate_top_domains(self) -> None:
        gen = DigestGenerator()
        digest = gen.generate(
            self.items,
            period_start=datetime(2024, 1, 13),
            period_end=datetime(2024, 1, 15),
        )
        assert "example.com" in digest.top_domains

    def test_generate_no_preview(self) -> None:
        config = DigestConfig(include_preview=False)
        gen = DigestGenerator(config=config)
        digest = gen.generate(
            self.items,
            period_start=datetime(2024, 1, 13),
            period_end=datetime(2024, 1, 15),
        )
        for item in digest.items:
            assert item.preview == ""

    def test_generate_no_tags(self) -> None:
        config = DigestConfig(include_tags=False)
        gen = DigestGenerator(config=config)
        digest = gen.generate(
            self.items,
            period_start=datetime(2024, 1, 13),
            period_end=datetime(2024, 1, 15),
        )
        for item in digest.items:
            assert item.tags == []

    def test_generate_empty_items(self) -> None:
        gen = DigestGenerator()
        digest = gen.generate([])
        assert len(digest.items) == 0
        assert digest.total_new == 0

    def test_generate_title(self) -> None:
        gen = DigestGenerator()
        digest = gen.generate(
            self.items,
            period_start=datetime(2024, 1, 14),
            period_end=datetime(2024, 1, 15),
        )
        assert "Daily Digest" in digest.title

    def test_generate_weekly_title(self) -> None:
        config = DigestConfig(frequency=DigestFrequency.WEEKLY)
        gen = DigestGenerator(config=config)
        digest = gen.generate(
            self.items,
            period_start=datetime(2024, 1, 8),
            period_end=datetime(2024, 1, 15),
        )
        assert "Weekly Digest" in digest.title

    def test_preview_truncation(self) -> None:
        config = DigestConfig(preview_length=10)
        gen = DigestGenerator(config=config)
        digest = gen.generate(
            self.items,
            period_start=datetime(2024, 1, 13),
            period_end=datetime(2024, 1, 15),
        )
        for item in digest.items:
            assert len(item.preview) <= 10
''')

commit("test: add comprehensive tests for content_digest module")

# Commit 14: content_notifications.py
write_file("personal_index/content_notifications.py", '''
"""Content notification system for personal-index.

Manages notification rules, triggers, and delivery for
content-related events such as new bookmarks, score changes,
and crawl results.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class NotificationType(Enum):
    """Types of content notifications."""

    NEW_BOOKMARK = "new_bookmark"
    SCORE_CHANGE = "score_change"
    CRAWL_COMPLETE = "crawl_complete"
    CRAWL_ERROR = "crawl_error"
    TAG_ADDED = "tag_added"
    COLLECTION_UPDATED = "collection_updated"
    DIGEST_READY = "digest_ready"
    HEALTH_WARNING = "health_warning"
    BACKUP_COMPLETE = "backup_complete"
    SEARCH_RESULT = "search_result"


class NotificationChannel(Enum):
    """Channels for delivering notifications."""

    LOG = "log"
    CONSOLE = "console"
    WEBHOOK = "webhook"
    EMAIL = "email"
    FILE = "file"


@dataclass
class NotificationRule:
    """A rule that determines when notifications are triggered.

    Attributes:
        rule_id: Unique identifier for the rule.
        name: Human-readable rule name.
        notification_type: Type of notification to trigger.
        channels: Channels to deliver to.
        conditions: Conditions that must be met.
        enabled: Whether the rule is active.
        cooldown_seconds: Minimum seconds between notifications.
    """

    rule_id: str
    name: str
    notification_type: NotificationType
    channels: list[NotificationChannel] = field(default_factory=list)
    conditions: dict[str, Any] = field(default_factory=dict)
    enabled: bool = True
    cooldown_seconds: int = 300

    def matches(self, event: dict[str, Any]) -> bool:
        """Check if an event matches this rule's conditions."""
        if not self.enabled:
            return False
        for key, value in self.conditions.items():
            if event.get(key) != value:
                return False
        return True


@dataclass
class Notification:
    """A single notification.

    Attributes:
        notification_id: Unique identifier.
        notification_type: Type of notification.
        title: Notification title.
        message: Notification message body.
        timestamp: When the notification was created.
        channels: Channels to deliver to.
        data: Additional notification data.
        delivered: Whether the notification has been delivered.
        delivered_at: When the notification was delivered.
    """

    notification_id: str
    notification_type: NotificationType
    title: str
    message: str
    timestamp: datetime
    channels: list[NotificationChannel] = field(default_factory=list)
    data: dict[str, Any] = field(default_factory=dict)
    delivered: bool = False
    delivered_at: datetime | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "notification_id": self.notification_id,
            "type": self.notification_type.value,
            "title": self.title,
            "message": self.message,
            "timestamp": self.timestamp.isoformat(),
            "channels": [c.value for c in self.channels],
            "data": self.data,
            "delivered": self.delivered,
        }


class NotificationManager:
    """Manages notification rules and delivery.

    Stores rules, evaluates events against rules, and
    delivers notifications through configured channels.
    """

    def __init__(self) -> None:
        self.rules: list[NotificationRule] = []
        self.notifications: list[Notification] = []
        self._last_sent: dict[str, datetime] = {}
        self._id_counter = 0

    def add_rule(self, rule: NotificationRule) -> None:
        """Add a notification rule."""
        self.rules.append(rule)

    def remove_rule(self, rule_id: str) -> bool:
        """Remove a notification rule by ID."""
        for i, rule in enumerate(self.rules):
            if rule.rule_id == rule_id:
                self.rules.pop(i)
                return True
        return False

    def evaluate_event(self, event: dict[str, Any]) -> list[Notification]:
        """Evaluate an event against all rules and generate notifications.

        Args:
            event: Event data to evaluate.

        Returns:
            List of generated notifications.
        """
        generated = []
        now = datetime.now()

        for rule in self.rules:
            if not rule.matches(event):
                continue

            # Check cooldown
            last = self._last_sent.get(rule.rule_id)
            if last and (now - last).total_seconds() < rule.cooldown_seconds:
                continue

            notification = self._create_notification(rule, event)
            self.notifications.append(notification)
            self._last_sent[rule.rule_id] = now
            generated.append(notification)

        return generated

    def get_undelivered(self) -> list[Notification]:
        """Get all undelivered notifications."""
        return [n for n in self.notifications if not n.delivered]

    def mark_delivered(self, notification_id: str) -> bool:
        """Mark a notification as delivered."""
        for n in self.notifications:
            if n.notification_id == notification_id:
                n.delivered = True
                n.delivered_at = datetime.now()
                return True
        return False

    def mark_all_delivered(self) -> int:
        """Mark all undelivered notifications as delivered."""
        count = 0
        for n in self.notifications:
            if not n.delivered:
                n.delivered = True
                n.delivered_at = datetime.now()
                count += 1
        return count

    def get_recent(
        self,
        limit: int = 10,
        notification_type: NotificationType | None = None,
    ) -> list[Notification]:
        """Get recent notifications, optionally filtered by type."""
        filtered = self.notifications
        if notification_type:
            filtered = [
                n for n in filtered
                if n.notification_type == notification_type
            ]
        return filtered[-limit:]

    def clear_old(self, older_than: datetime) -> int:
        """Clear notifications older than the given time."""
        before = len(self.notifications)
        self.notifications = [
            n for n in self.notifications
            if n.timestamp >= older_than
        ]
        return before - len(self.notifications)

    def _create_notification(
        self,
        rule: NotificationRule,
        event: dict[str, Any],
    ) -> Notification:
        """Create a notification from a rule and event."""
        self._id_counter += 1
        return Notification(
            notification_id=f"notif-{self._id_counter}",
            notification_type=rule.notification_type,
            title=rule.name,
            message=self._format_message(rule, event),
            timestamp=datetime.now(),
            channels=rule.channels,
            data=event,
        )

    def _format_message(
        self,
        rule: NotificationRule,
        event: dict[str, Any],
    ) -> str:
        """Format a notification message."""
        parts = [rule.name]
        for key, value in event.items():
            if key in ("title", "url", "message"):
                parts.append(f"{key}: {value}")
        return ". ".join(parts) if len(parts) > 1 else parts[0]
''')

commit("feat: add content_notifications.py with notification manager")

# Commit 15: test_content_notifications.py
write_file("tests/test_content_notifications.py", '''
"""Tests for the content notification module."""

from datetime import datetime, timedelta

import pytest

from personal_index.content_notifications import (
    Notification,
    NotificationChannel,
    NotificationManager,
    NotificationRule,
    NotificationType,
)


class TestNotificationRule:
    def test_create_rule(self) -> None:
        rule = NotificationRule(
            rule_id="r1",
            name="New Bookmark Alert",
            notification_type=NotificationType.NEW_BOOKMARK,
            channels=[NotificationChannel.LOG],
        )
        assert rule.enabled is True
        assert rule.cooldown_seconds == 300

    def test_matches_enabled(self) -> None:
        rule = NotificationRule(
            rule_id="r1",
            name="Test",
            notification_type=NotificationType.NEW_BOOKMARK,
            conditions={"type": "bookmark"},
        )
        assert rule.matches({"type": "bookmark"}) is True
        assert rule.matches({"type": "other"}) is False

    def test_matches_disabled(self) -> None:
        rule = NotificationRule(
            rule_id="r1",
            name="Test",
            notification_type=NotificationType.NEW_BOOKMARK,
            enabled=False,
        )
        assert rule.matches({}) is False

    def test_matches_empty_conditions(self) -> None:
        rule = NotificationRule(
            rule_id="r1",
            name="Test",
            notification_type=NotificationType.NEW_BOOKMARK,
        )
        assert rule.matches({"anything": "goes"}) is True


class TestNotification:
    def test_create(self) -> None:
        n = Notification(
            notification_id="n1",
            notification_type=NotificationType.NEW_BOOKMARK,
            title="New Bookmark",
            message="A new bookmark was added.",
            timestamp=datetime.now(),
        )
        assert n.delivered is False

    def test_to_dict(self) -> None:
        n = Notification(
            notification_id="n1",
            notification_type=NotificationType.NEW_BOOKMARK,
            title="Test",
            message="Message",
            timestamp=datetime(2024, 1, 1),
            channels=[NotificationChannel.LOG],
        )
        d = n.to_dict()
        assert d["type"] == "new_bookmark"
        assert d["delivered"] is False


class TestNotificationManager:
    def setup_method(self) -> None:
        self.manager = NotificationManager()

    def test_add_rule(self) -> None:
        rule = NotificationRule(
            rule_id="r1",
            name="Test Rule",
            notification_type=NotificationType.NEW_BOOKMARK,
        )
        self.manager.add_rule(rule)
        assert len(self.manager.rules) == 1

    def test_remove_rule(self) -> None:
        rule = NotificationRule(
            rule_id="r1",
            name="Test Rule",
            notification_type=NotificationType.NEW_BOOKMARK,
        )
        self.manager.add_rule(rule)
        assert self.manager.remove_rule("r1") is True
        assert len(self.manager.rules) == 0

    def test_remove_nonexistent_rule(self) -> None:
        assert self.manager.remove_rule("nonexistent") is False

    def test_evaluate_event_matches(self) -> None:
        rule = NotificationRule(
            rule_id="r1",
            name="Bookmark Alert",
            notification_type=NotificationType.NEW_BOOKMARK,
            conditions={"action": "bookmark"},
        )
        self.manager.add_rule(rule)
        notifications = self.manager.evaluate_event({"action": "bookmark"})
        assert len(notifications) == 1
        assert notifications[0].notification_type == NotificationType.NEW_BOOKMARK

    def test_evaluate_event_no_match(self) -> None:
        rule = NotificationRule(
            rule_id="r1",
            name="Bookmark Alert",
            notification_type=NotificationType.NEW_BOOKMARK,
            conditions={"action": "bookmark"},
        )
        self.manager.add_rule(rule)
        notifications = self.manager.evaluate_event({"action": "delete"})
        assert len(notifications) == 0

    def test_evaluate_cooldown(self) -> None:
        rule = NotificationRule(
            rule_id="r1",
            name="Test",
            notification_type=NotificationType.NEW_BOOKMARK,
            cooldown_seconds=3600,
        )
        self.manager.add_rule(rule)
        self.manager.evaluate_event({"action": "bookmark"})
        # Second call within cooldown should not generate
        notifications = self.manager.evaluate_event({"action": "bookmark"})
        assert len(notifications) == 0

    def test_get_undelivered(self) -> None:
        rule = NotificationRule(
            rule_id="r1",
            name="Test",
            notification_type=NotificationType.NEW_BOOKMARK,
        )
        self.manager.add_rule(rule)
        self.manager.evaluate_event({"action": "bookmark"})
        undelivered = self.manager.get_undelivered()
        assert len(undelivered) == 1

    def test_mark_delivered(self) -> None:
        rule = NotificationRule(
            rule_id="r1",
            name="Test",
            notification_type=NotificationType.NEW_BOOKMARK,
        )
        self.manager.add_rule(rule)
        self.manager.evaluate_event({"action": "bookmark"})
        notif = self.manager.notifications[0]
        assert self.manager.mark_delivered(notif.notification_id) is True
        assert notif.delivered is True
        assert notif.delivered_at is not None

    def test_mark_all_delivered(self) -> None:
        rule = NotificationRule(
            rule_id="r1",
            name="Test",
            notification_type=NotificationType.NEW_BOOKMARK,
        )
        self.manager.add_rule(rule)
        self.manager.evaluate_event({"action": "bookmark"})
        self.manager.evaluate_event({"action": "bookmark", "extra": "data"})
        count = self.manager.mark_all_delivered()
        assert count == 2

    def test_get_recent(self) -> None:
        rule = NotificationRule(
            rule_id="r1",
            name="Test",
            notification_type=NotificationType.NEW_BOOKMARK,
        )
        self.manager.add_rule(rule)
        self.manager.evaluate_event({"action": "bookmark"})
        recent = self.manager.get_recent(limit=5)
        assert len(recent) == 1

    def test_get_recent_by_type(self) -> None:
        rule1 = NotificationRule(
            rule_id="r1",
            name="Bookmark",
            notification_type=NotificationType.NEW_BOOKMARK,
        )
        rule2 = NotificationRule(
            rule_id="r2",
            name="Crawl",
            notification_type=NotificationType.CRAWL_COMPLETE,
        )
        self.manager.add_rule(rule1)
        self.manager.add_rule(rule2)
        self.manager.evaluate_event({"action": "bookmark"})
        self.manager.evaluate_event({"action": "crawl"})
        recent = self.manager.get_recent(
            notification_type=NotificationType.NEW_BOOKMARK,
        )
        assert len(recent) == 1
        assert recent[0].notification_type == NotificationType.NEW_BOOKMARK

    def test_clear_old(self) -> None:
        old_time = datetime.now() - timedelta(hours=1)
        self.manager.notifications.append(Notification(
            notification_id="old",
            notification_type=NotificationType.NEW_BOOKMARK,
            title="Old",
            message="Old notification",
            timestamp=old_time,
        ))
        self.manager.notifications.append(Notification(
            notification_id="new",
            notification_type=NotificationType.NEW_BOOKMARK,
            title="New",
            message="New notification",
            timestamp=datetime.now(),
        ))
        cleared = self.manager.clear_old(datetime.now() - timedelta(minutes=30))
        assert cleared == 1
        assert len(self.manager.notifications) == 1
''')

commit("test: add comprehensive tests for content_notifications module")

# Commit 16: content_cache.py
write_file("personal_index/content_cache.py", '''
"""Content caching layer for personal-index.

Provides in-memory and file-based caching for content items,
search results, and computed scores to improve performance.
"""

from __future__ import annotations

import hashlib
import json
import time
from collections import OrderedDict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Generic, TypeVar

T = TypeVar("T")


@dataclass
class CacheEntry:
    """A single cache entry with metadata.

    Attributes:
        key: Cache key.
        value: Cached value.
        created_at: When the entry was created.
        expires_at: When the entry expires (None for no expiry).
        access_count: Number of times the entry was accessed.
        size_bytes: Approximate size in bytes.
    """

    key: str
    value: Any
    created_at: float
    expires_at: float | None = None
    access_count: int = 0
    size_bytes: int = 0


@dataclass
class CacheStats:
    """Statistics about cache performance.

    Attributes:
        hits: Number of cache hits.
        misses: Number of cache misses.
        evictions: Number of entries evicted.
        size: Current number of entries.
        hit_rate: Cache hit rate (0.0-1.0).
    """

    hits: int = 0
    misses: int = 0
    evictions: int = 0
    size: int = 0

    @property
    def hit_rate(self) -> float:
        """Calculate hit rate."""
        total = self.hits + self.misses
        return self.hits / total if total > 0 else 0.0


class MemoryCache:
    """In-memory LRU cache with TTL support.

    Provides fast caching with configurable maximum size
    and time-to-live for entries.
    """

    def __init__(
        self,
        max_size: int = 1000,
        default_ttl: float | None = None,
    ) -> None:
        self.max_size = max_size
        self.default_ttl = default_ttl
        self._store: OrderedDict[str, CacheEntry] = OrderedDict()
        self._stats = CacheStats()

    def get(self, key: str, default: Any = None) -> Any:
        """Get a value from the cache.

        Args:
            key: Cache key.
            default: Default value if key not found.

        Returns:
            Cached value or default.
        """
        entry = self._store.get(key)
        if entry is None:
            self._stats.misses += 1
            return default

        # Check expiry
        if entry.expires_at and time.time() > entry.expires_at:
            del self._store[key]
            self._stats.misses += 1
            return default

        # Move to end (most recently used)
        self._store.move_to_end(key)
        entry.access_count += 1
        self._stats.hits += 1
        return entry.value

    def set(self, key: str, value: Any, ttl: float | None = None) -> None:
        """Set a value in the cache.

        Args:
            key: Cache key.
            value: Value to cache.
            ttl: Time-to-live in seconds (None uses default).
        """
        if key in self._store:
            del self._store[key]

        # Evict if at capacity
        while len(self._store) >= self.max_size:
            self._evict_lru()

        effective_ttl = ttl if ttl is not None else self.default_ttl
        expires_at = time.time() + effective_ttl if effective_ttl else None

        entry = CacheEntry(
            key=key,
            value=value,
            created_at=time.time(),
            expires_at=expires_at,
            size_bytes=self._estimate_size(value),
        )
        self._store[key] = entry

    def delete(self, key: str) -> bool:
        """Delete a key from the cache.

        Args:
            key: Cache key to delete.

        Returns:
            True if the key was found and deleted.
        """
        if key in self._store:
            del self._store[key]
            return True
        return False

    def clear(self) -> None:
        """Clear all entries from the cache."""
        self._store.clear()

    def has(self, key: str) -> bool:
        """Check if a key exists in the cache."""
        entry = self._store.get(key)
        if entry is None:
            return False
        if entry.expires_at and time.time() > entry.expires_at:
            del self._store[key]
            return False
        return True

    def keys(self) -> list[str]:
        """Get all non-expired keys."""
        expired = [
            k for k, v in self._store.items()
            if v.expires_at and time.time() > v.expires_at
        ]
        for k in expired:
            del self._store[k]
        return list(self._store.keys())

    def size(self) -> int:
        """Get current number of entries."""
        return len(self._store)

    def get_stats(self) -> CacheStats:
        """Get cache statistics."""
        self._stats.size = len(self._store)
        return self._stats

    def _evict_lru(self) -> None:
        """Evict the least recently used entry."""
        if self._store:
            self._store.popitem(last=False)
            self._stats.evictions += 1

    def _estimate_size(self, value: Any) -> int:
        """Estimate the size of a value in bytes."""
        try:
            return len(json.dumps(value, default=str))
        except (TypeError, ValueError):
            return len(str(value))


class FileCache:
    """File-based cache for persisting cached data.

    Stores cache entries as JSON files on disk with
    automatic cleanup of expired entries.
    """

    def __init__(
        self,
        cache_dir: str | Path,
        default_ttl: float | None = 3600,
    ) -> None:
        self.cache_dir = Path(cache_dir)
        self.default_ttl = default_ttl
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def get(self, key: str, default: Any = None) -> Any:
        """Get a value from the file cache."""
        filepath = self._get_filepath(key)
        if not filepath.exists():
            return default

        try:
            data = json.loads(filepath.read_text())
            if data.get("expires_at") and time.time() > data["expires_at"]:
                filepath.unlink()
                return default
            return data["value"]
        except (json.JSONDecodeError, KeyError):
            return default

    def set(self, key: str, value: Any, ttl: float | None = None) -> None:
        """Set a value in the file cache."""
        filepath = self._get_filepath(key)
        effective_ttl = ttl if ttl is not None else self.default_ttl
        expires_at = time.time() + effective_ttl if effective_ttl else None

        data = {
            "value": value,
            "created_at": time.time(),
            "expires_at": expires_at,
        }
        filepath.write_text(json.dumps(data, default=str), encoding="utf-8")

    def delete(self, key: str) -> bool:
        """Delete a key from the file cache."""
        filepath = self._get_filepath(key)
        if filepath.exists():
            filepath.unlink()
            return True
        return False

    def clear(self) -> None:
        """Clear all entries from the file cache."""
        for filepath in self.cache_dir.glob("*.json"):
            filepath.unlink()

    def cleanup_expired(self) -> int:
        """Remove expired entries. Returns count of removed entries."""
        removed = 0
        for filepath in self.cache_dir.glob("*.json"):
            try:
                data = json.loads(filepath.read_text())
                if data.get("expires_at") and time.time() > data["expires_at"]:
                    filepath.unlink()
                    removed += 1
            except (json.JSONDecodeError, KeyError):
                filepath.unlink()
                removed += 1
        return removed

    def _get_filepath(self, key: str) -> Path:
        """Get the file path for a cache key."""
        hash_key = hashlib.sha256(key.encode()).hexdigest()[:16]
        return self.cache_dir / f"{hash_key}.json"
''')

commit("feat: add content_cache.py with MemoryCache and FileCache")

# Commit 17: test_content_cache.py
write_file("tests/test_content_cache.py", '''
"""Tests for the content cache module."""

import time
from pathlib import Path

import pytest

from personal_index.content_cache import (
    CacheEntry,
    CacheStats,
    FileCache,
    MemoryCache,
)


class TestCacheEntry:
    def test_create(self) -> None:
        entry = CacheEntry(
            key="test",
            value="data",
            created_at=time.time(),
        )
        assert entry.key == "test"
        assert entry.access_count == 0


class TestCacheStats:
    def test_hit_rate_zero(self) -> None:
        stats = CacheStats()
        assert stats.hit_rate == 0.0

    def test_hit_rate_perfect(self) -> None:
        stats = CacheStats(hits=10, misses=0)
        assert stats.hit_rate == 1.0

    def test_hit_rate_half(self) -> None:
        stats = CacheStats(hits=5, misses=5)
        assert stats.hit_rate == 0.5


class TestMemoryCache:
    def setup_method(self) -> None:
        self.cache = MemoryCache(max_size=5)

    def test_set_and_get(self) -> None:
        self.cache.set("key1", "value1")
        assert self.cache.get("key1") == "value1"

    def test_get_default(self) -> None:
        assert self.cache.get("nonexistent") is None
        assert self.cache.get("nonexistent", "default") == "default"

    def test_delete(self) -> None:
        self.cache.set("key1", "value1")
        assert self.cache.delete("key1") is True
        assert self.cache.get("key1") is None

    def test_delete_nonexistent(self) -> None:
        assert self.cache.delete("nonexistent") is False

    def test_clear(self) -> None:
        self.cache.set("key1", "value1")
        self.cache.set("key2", "value2")
        self.cache.clear()
        assert self.cache.size() == 0

    def test_has(self) -> None:
        self.cache.set("key1", "value1")
        assert self.cache.has("key1") is True
        assert self.cache.has("nonexistent") is False

    def test_lru_eviction(self) -> None:
        for i in range(6):
            self.cache.set(f"key{i}", f"value{i}")
        # First key should be evicted
        assert self.cache.get("key0") is None
        assert self.cache.get("key5") == "value5"

    def test_lru_access_updates_order(self) -> None:
        self.cache.set("key1", "value1")
        self.cache.set("key2", "value2")
        self.cache.set("key3", "value3")
        # Access key1 to make it recently used
        self.cache.get("key1")
        # Add more to trigger eviction
        self.cache.set("key4", "value4")
        self.cache.set("key5", "value5")
        # key2 should be evicted (least recently used)
        assert self.cache.get("key2") is None
        assert self.cache.get("key1") == "value1"

    def test_ttl_expiry(self) -> None:
        self.cache.set("key1", "value1", ttl=0.1)
        assert self.cache.get("key1") == "value1"
        time.sleep(0.15)
        assert self.cache.get("key1") is None

    def test_default_ttl(self) -> None:
        cache = MemoryCache(default_ttl=0.1)
        cache.set("key1", "value1")
        assert cache.get("key1") == "value1"
        time.sleep(0.15)
        assert cache.get("key1") is None

    def test_access_count(self) -> None:
        self.cache.set("key1", "value1")
        self.cache.get("key1")
        self.cache.get("key1")
        entry = self.cache._store["key1"]
        assert entry.access_count == 2

    def test_stats(self) -> None:
        self.cache.set("key1", "value1")
        self.cache.get("key1")  # hit
        self.cache.get("missing")  # miss
        stats = self.cache.get_stats()
        assert stats.hits == 1
        assert stats.misses == 1
        assert stats.hit_rate == 0.5

    def test_keys(self) -> None:
        self.cache.set("key1", "value1")
        self.cache.set("key2", "value2")
        keys = self.cache.keys()
        assert set(keys) == {"key1", "key2"}

    def test_update_existing_key(self) -> None:
        self.cache.set("key1", "value1")
        self.cache.set("key1", "value2")
        assert self.cache.get("key1") == "value2"
        assert self.cache.size() == 1

    def test_complex_values(self) -> None:
        data = {"nested": {"key": [1, 2, 3]}}
        self.cache.set("complex", data)
        result = self.cache.get("complex")
        assert result == data


class TestFileCache:
    def test_set_and_get(self, tmp_path: Path) -> None:
        cache = FileCache(tmp_path / "cache")
        cache.set("key1", {"data": "value"})
        result = cache.get("key1")
        assert result == {"data": "value"}

    def test_get_default(self, tmp_path: Path) -> None:
        cache = FileCache(tmp_path / "cache")
        assert cache.get("nonexistent") is None
        assert cache.get("nonexistent", "default") == "default"

    def test_delete(self, tmp_path: Path) -> None:
        cache = FileCache(tmp_path / "cache")
        cache.set("key1", "value1")
        assert cache.delete("key1") is True
        assert cache.get("key1") is None

    def test_clear(self, tmp_path: Path) -> None:
        cache = FileCache(tmp_path / "cache")
        cache.set("key1", "value1")
        cache.set("key2", "value2")
        cache.clear()
        assert cache.get("key1") is None
        assert cache.get("key2") is None

    def test_cleanup_expired(self, tmp_path: Path) -> None:
        cache = FileCache(tmp_path / "cache", default_ttl=0.1)
        cache.set("key1", "value1")
        cache.set("key2", "value2", ttl=3600)
        time.sleep(0.15)
        removed = cache.cleanup_expired()
        assert removed == 1
        assert cache.get("key2") == "value2"

    def test_ttl_expiry(self, tmp_path: Path) -> None:
        cache = FileCache(tmp_path / "cache", default_ttl=0.1)
        cache.set("key1", "value1")
        assert cache.get("key1") == "value1"
        time.sleep(0.15)
        assert cache.get("key1") is None
''')

commit("test: add comprehensive tests for content_cache module")

# Commit 18: content_batch.py
write_file("personal_index/content_batch.py", '''
"""Batch processing for content operations in personal-index.

Provides utilities for processing content items in batches,
with support for parallel execution, error handling, and
progress tracking.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable

BatchProcessor = Callable[[list[dict[str, Any]]], list[dict[str, Any]]]


@dataclass
class BatchResult:
    """Result of a batch processing operation.

    Attributes:
        batch_id: Unique identifier for the batch.
        total_items: Total items in the batch.
        processed: Number of items successfully processed.
        failed: Number of items that failed.
        errors: List of error details.
        started_at: When processing started.
        completed_at: When processing completed.
        duration_seconds: Processing duration.
        output: Processed output items.
    """

    batch_id: str
    total_items: int
    processed: int = 0
    failed: int = 0
    errors: list[dict[str, Any]] = field(default_factory=list)
    started_at: datetime | None = None
    completed_at: datetime | None = None
    duration_seconds: float = 0.0
    output: list[dict[str, Any]] = field(default_factory=list)

    @property
    def success_rate(self) -> float:
        """Calculate success rate."""
        if self.total_items == 0:
            return 0.0
        return self.processed / self.total_items

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "batch_id": self.batch_id,
            "total_items": self.total_items,
            "processed": self.processed,
            "failed": self.failed,
            "errors": self.errors,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "duration_seconds": self.duration_seconds,
            "success_rate": round(self.success_rate, 4),
        }


class BatchProcessor:
    """Processes content items in configurable batch sizes.

    Supports custom processing functions, error handling,
    and progress callbacks.
    """

    def __init__(
        self,
        batch_size: int = 100,
        processor: BatchProcessor | None = None,
        on_progress: Callable[[int, int], None] | None = None,
    ) -> None:
        self.batch_size = batch_size
        self.processor = processor or self._default_processor
        self.on_progress = on_progress
        self._batch_counter = 0

    def process(
        self,
        items: list[dict[str, Any]],
    ) -> BatchResult:
        """Process all items in batches.

        Args:
            items: List of content items to process.

        Returns:
            BatchResult with processing statistics.
        """
        self._batch_counter += 1
        batch_id = f"batch-{self._batch_counter}"
        result = BatchResult(
            batch_id=batch_id,
            total_items=len(items),
            started_at=datetime.now(),
        )

        total = len(items)
        processed_count = 0

        for i in range(0, total, self.batch_size):
            batch = items[i : i + self.batch_size]
            try:
                output = self.processor(batch)
                result.output.extend(output)
                result.processed += len(batch)
            except Exception as e:
                result.failed += len(batch)
                result.errors.append({
                    "batch_start": i,
                    "batch_size": len(batch),
                    "error": str(e),
                })

            processed_count += len(batch)
            if self.on_progress:
                self.on_progress(processed_count, total)

        result.completed_at = datetime.now()
        if result.started_at:
            result.duration_seconds = (
                result.completed_at - result.started_at
            ).total_seconds()

        return result

    def process_with_retry(
        self,
        items: list[dict[str, Any]],
        max_retries: int = 3,
    ) -> BatchResult:
        """Process items with retry logic for failed batches.

        Args:
            items: List of content items.
            max_retries: Maximum retry attempts per batch.

        Returns:
            BatchResult with processing statistics.
        """
        self._batch_counter += 1
        batch_id = f"batch-{self._batch_counter}"
        result = BatchResult(
            batch_id=batch_id,
            total_items=len(items),
            started_at=datetime.now(),
        )

        total = len(items)
        processed_count = 0

        for i in range(0, total, self.batch_size):
            batch = items[i : i + self.batch_size]
            success = False

            for attempt in range(max_retries):
                try:
                    output = self.processor(batch)
                    result.output.extend(output)
                    result.processed += len(batch)
                    success = True
                    break
                except Exception as e:
                    if attempt == max_retries - 1:
                        result.failed += len(batch)
                        result.errors.append({
                            "batch_start": i,
                            "attempts": attempt + 1,
                            "error": str(e),
                        })

            processed_count += len(batch)
            if self.on_progress:
                self.on_progress(processed_count, total)

        result.completed_at = datetime.now()
        if result.started_at:
            result.duration_seconds = (
                result.completed_at - result.started_at
            ).total_seconds()

        return result

    def _default_processor(
        self,
        items: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Default processor that returns items unchanged."""
        return items

    def process_item_by_item(
        self,
        items: list[dict[str, Any]],
        item_processor: Callable[[dict[str, Any]], dict[str, Any]],
    ) -> BatchResult:
        """Process items individually with per-item error handling.

        Args:
            items: List of content items.
            item_processor: Function to process each item.

        Returns:
            BatchResult with processing statistics.
        """
        self._batch_counter += 1
        batch_id = f"batch-{self._batch_counter}"
        result = BatchResult(
            batch_id=batch_id,
            total_items=len(items),
            started_at=datetime.now(),
        )

        for i, item in enumerate(items):
            try:
                output = item_processor(item)
                result.output.append(output)
                result.processed += 1
            except Exception as e:
                result.failed += 1
                result.errors.append({
                    "item_index": i,
                    "item_id": item.get("id", "unknown"),
                    "error": str(e),
                })

            if self.on_progress:
                self.on_progress(i + 1, len(items))

        result.completed_at = datetime.now()
        if result.started_at:
            result.duration_seconds = (
                result.completed_at - result.started_at
            ).total_seconds()

        return result
''')

commit("feat: add content_batch.py with batch processing engine")

# Commit 19: test_content_batch.py
write_file("tests/test_content_batch.py", '''
"""Tests for the content batch processing module."""

from datetime import datetime

from personal_index.content_batch import BatchProcessor, BatchResult


class TestBatchResult:
    def test_create(self) -> None:
        result = BatchResult(batch_id="b1", total_items=10)
        assert result.processed == 0
        assert result.failed == 0
        assert result.success_rate == 0.0

    def test_success_rate(self) -> None:
        result = BatchResult(batch_id="b1", total_items=10)
        result.processed = 8
        result.failed = 2
        assert result.success_rate == 0.8

    def test_to_dict(self) -> None:
        result = BatchResult(
            batch_id="b1",
            total_items=10,
            processed=8,
            started_at=datetime(2024, 1, 1),
            completed_at=datetime(2024, 1, 1, 0, 0, 5),
        )
        d = result.to_dict()
        assert d["batch_id"] == "b1"
        assert d["success_rate"] == 0.8


class TestBatchProcessor:
    def setup_method(self) -> None:
        self.items = [{"id": str(i), "value": i} for i in range(25)]

    def test_process_default(self) -> None:
        processor = BatchProcessor(batch_size=10)
        result = processor.process(self.items)
        assert result.total_items == 25
        assert result.processed == 25
        assert result.failed == 0

    def test_process_custom(self) -> None:
        def double_value(batch):
            return [{"id": i["id"], "value": i["value"] * 2} for i in batch]

        processor = BatchProcessor(batch_size=10, processor=double_value)
        result = processor.process(self.items)
        assert result.processed == 25
        assert result.output[0]["value"] == 0
        assert result.output[5]["value"] == 10

    def test_process_error(self) -> None:
        def failing_processor(batch):
            raise ValueError("Processing failed")

        processor = BatchProcessor(batch_size=10, processor=failing_processor)
        result = processor.process(self.items)
        assert result.failed == 25
        assert len(result.errors) > 0

    def test_process_progress(self) -> None:
        progress_calls = []

        def on_progress(current, total):
            progress_calls.append((current, total))

        processor = BatchProcessor(
            batch_size=10, on_progress=on_progress,
        )
        processor.process(self.items)
        assert len(progress_calls) == 3  # 3 batches
        assert progress_calls[-1] == (25, 25)

    def test_process_with_retry_success(self) -> None:
        call_count = [0]

        def flaky_processor(batch):
            call_count[0] += 1
            if call_count[0] == 1:
                raise ValueError("Temporary failure")
            return batch

        processor = BatchProcessor(
            batch_size=25, processor=flaky_processor,
        )
        result = processor.process_with_retry(self.items, max_retries=3)
        assert result.processed == 25

    def test_process_with_retry_exhausted(self) -> None:
        def always_fail(batch):
            raise ValueError("Always fails")

        processor = BatchProcessor(
            batch_size=25, processor=always_fail,
        )
        result = processor.process_with_retry(self.items, max_retries=2)
        assert result.failed == 25
        assert len(result.errors) == 1
        assert result.errors[0]["attempts"] == 2

    def test_process_item_by_item(self) -> None:
        processor = BatchProcessor(batch_size=10)
        result = processor.process_item_by_item(
            self.items,
            item_processor=lambda item: {**item, "processed": True},
        )
        assert result.processed == 25
        assert all(item.get("processed") for item in result.output)

    def test_process_item_by_item_partial_failure(self) -> None:
        def sometimes_fail(item):
            if item["value"] == 5:
                raise ValueError("Item 5 fails")
            return {**item, "processed": True}

        processor = BatchProcessor(batch_size=10)
        result = processor.process_item_by_item(
            self.items,
            item_processor=sometimes_fail,
        )
        assert result.processed == 24
        assert result.failed == 1
        assert len(result.errors) == 1
        assert result.errors[0]["item_index"] == 5

    def test_batch_id_uniqueness(self) -> None:
        processor = BatchProcessor(batch_size=10)
        r1 = processor.process(self.items)
        r2 = processor.process(self.items)
        assert r1.batch_id != r2.batch_id

    def test_empty_items(self) -> None:
        processor = BatchProcessor(batch_size=10)
        result = processor.process([])
        assert result.total_items == 0
        assert result.processed == 0
        assert result.output == []

    def test_duration_tracking(self) -> None:
        processor = BatchProcessor(batch_size=10)
        result = processor.process(self.items)
        assert result.started_at is not None
        assert result.completed_at is not None
        assert result.duration_seconds >= 0
''')

commit("test: add comprehensive tests for content_batch module")

# Commit 20: content_scheduler.py
write_file("personal_index/content_scheduler.py", '''
"""Content scheduling module for personal-index.

Manages scheduled tasks such as periodic crawls, digest generation,
and content refresh with cron-like scheduling support.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable


class ScheduleType(Enum):
    """Types of scheduling patterns."""

    ONCE = "once"
    HOURLY = "hourly"
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    CRON = "cron"


@dataclass
class ScheduledTask:
    """A scheduled task definition.

    Attributes:
        task_id: Unique identifier.
        name: Human-readable task name.
        schedule_type: Type of schedule.
        next_run: When the task should next run.
        last_run: When the task last ran.
        run_count: Number of times the task has run.
        enabled: Whether the task is enabled.
        callback: Function to call when task runs.
        cron_expression: Cron expression for CRON type.
        max_runs: Maximum number of runs (None for unlimited).
        metadata: Additional task metadata.
    """

    task_id: str
    name: str
    schedule_type: ScheduleType = ScheduleType.ONCE
    next_run: datetime | None = None
    last_run: datetime | None = None
    run_count: int = 0
    enabled: bool = True
    callback: Callable | None = None
    cron_expression: str | None = None
    max_runs: int | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def is_due(self, now: datetime | None = None) -> bool:
        """Check if the task is due to run."""
        if not self.enabled:
            return False
        if self.next_run is None:
            return True
        check_time = now or datetime.now()
        return check_time >= self.next_run

    def mark_run(self, now: datetime | None = None) -> None:
        """Mark the task as having run and schedule next run."""
        run_time = now or datetime.now()
        self.last_run = run_time
        self.run_count += 1
        self.next_run = self._calculate_next_run(run_time)

    def _calculate_next_run(self, last_run: datetime) -> datetime | None:
        """Calculate when the task should next run."""
        if self.max_runs and self.run_count >= self.max_runs:
            return None

        intervals = {
            ScheduleType.HOURLY: timedelta(hours=1),
            ScheduleType.DAILY: timedelta(days=1),
            ScheduleType.WEEKLY: timedelta(weeks=1),
            ScheduleType.MONTHLY: timedelta(days=30),
        }

        if self.schedule_type == ScheduleType.ONCE:
            return None

        delta = intervals.get(self.schedule_type)
        if delta:
            return last_run + delta

        return None


@dataclass
class TaskRunRecord:
    """Record of a task execution.

    Attributes:
        task_id: ID of the task that ran.
        started_at: When the task started.
        completed_at: When the task completed.
        success: Whether the task succeeded.
        duration_seconds: How long the task took.
        result: Task result data.
        error: Error message if task failed.
    """

    task_id: str
    started_at: datetime
    completed_at: datetime | None = None
    success: bool = False
    duration_seconds: float = 0.0
    result: dict[str, Any] = field(default_factory=dict)
    error: str | None = None


class TaskScheduler:
    """Manages and executes scheduled tasks.

    Provides task registration, scheduling, and execution
    with history tracking.
    """

    def __init__(self) -> None:
        self.tasks: dict[str, ScheduledTask] = {}
        self.run_history: list[TaskRunRecord] = []

    def register(
        self,
        task_id: str,
        name: str,
        schedule_type: ScheduleType = ScheduleType.ONCE,
        next_run: datetime | None = None,
        callback: Callable | None = None,
        **kwargs: Any,
    ) -> ScheduledTask:
        """Register a new scheduled task.

        Args:
            task_id: Unique task identifier.
            name: Human-readable name.
            schedule_type: Schedule type.
            next_run: When to first run.
            callback: Function to execute.
            **kwargs: Additional task parameters.

        Returns:
            The registered ScheduledTask.
        """
        task = ScheduledTask(
            task_id=task_id,
            name=name,
            schedule_type=schedule_type,
            next_run=next_run,
            callback=callback,
            **kwargs,
        )
        self.tasks[task_id] = task
        return task

    def remove(self, task_id: str) -> bool:
        """Remove a scheduled task."""
        if task_id in self.tasks:
            del self.tasks[task_id]
            return True
        return False

    def get_due_tasks(
        self,
        now: datetime | None = None,
    ) -> list[ScheduledTask]:
        """Get all tasks that are due to run."""
        return [t for t in self.tasks.values() if t.is_due(now)]

    def run_due(
        self,
        now: datetime | None = None,
    ) -> list[TaskRunRecord]:
        """Run all due tasks and return records.

        Args:
            now: Current time (defaults to now).

        Returns:
            List of TaskRunRecord for executed tasks.
        """
        due_tasks = self.get_due_tasks(now)
        records = []

        for task in due_tasks:
            record = self._execute_task(task, now)
            records.append(record)
            self.run_history.append(record)

        return records

    def get_task(self, task_id: str) -> ScheduledTask | None:
        """Get a task by ID."""
        return self.tasks.get(task_id)

    def get_history(
        self,
        task_id: str | None = None,
        limit: int = 10,
    ) -> list[TaskRunRecord]:
        """Get task run history, optionally filtered by task."""
        history = self.run_history
        if task_id:
            history = [r for r in history if r.task_id == task_id]
        return history[-limit:]

    def get_stats(self) -> dict[str, Any]:
        """Get scheduler statistics."""
        total = len(self.tasks)
        enabled = sum(1 for t in self.tasks.values() if t.enabled)
        total_runs = sum(t.run_count for t in self.tasks.values())
        return {
            "total_tasks": total,
            "enabled_tasks": enabled,
            "disabled_tasks": total - enabled,
            "total_runs": total_runs,
            "history_size": len(self.run_history),
        }

    def _execute_task(
        self,
        task: ScheduledTask,
        now: datetime | None = None,
    ) -> TaskRunRecord:
        """Execute a single task."""
        start_time = now or datetime.now()
        record = TaskRunRecord(
            task_id=task.task_id,
            started_at=start_time,
        )

        try:
            if task.callback:
                result = task.callback()
                record.result = (
                    result if isinstance(result, dict)
                    else {"output": str(result)}
                )
            record.success = True
        except Exception as e:
            record.error = str(e)
            record.success = False

        end_time = now or datetime.now()
        record.completed_at = end_time
        record.duration_seconds = (
            end_time - start_time
        ).total_seconds()

        task.mark_run(now)
        return record
''')

commit("feat: add content_scheduler.py with task scheduling engine")

# Commit 21: test_content_scheduler.py
write_file("tests/test_content_scheduler.py", '''
"""Tests for the content scheduler module."""

from datetime import datetime, timedelta

from personal_index.content_scheduler import (
    ScheduleType,
    ScheduledTask,
    TaskRunRecord,
    TaskScheduler,
)


class TestScheduledTask:
    def test_create(self) -> None:
        task = ScheduledTask(
            task_id="t1",
            name="Test Task",
            schedule_type=ScheduleType.DAILY,
        )
        assert task.enabled is True
        assert task.run_count == 0

    def test_is_due_no_next_run(self) -> None:
        task = ScheduledTask(
            task_id="t1",
            name="Test",
        )
        assert task.is_due() is True

    def test_is_due_enabled(self) -> None:
        task = ScheduledTask(
            task_id="t1",
            name="Test",
            next_run=datetime(2024, 1, 1),
        )
        now = datetime(2024, 1, 2)
        assert task.is_due(now) is True

    def test_is_due_not_yet(self) -> None:
        task = ScheduledTask(
            task_id="t1",
            name="Test",
            next_run=datetime(2025, 1, 1),
        )
        now = datetime(2024, 1, 1)
        assert task.is_due(now) is False

    def test_is_due_disabled(self) -> None:
        task = ScheduledTask(
            task_id="t1",
            name="Test",
            enabled=False,
            next_run=datetime(2020, 1, 1),
        )
        assert task.is_due() is False

    def test_mark_run_daily(self) -> None:
        task = ScheduledTask(
            task_id="t1",
            name="Test",
            schedule_type=ScheduleType.DAILY,
        )
        now = datetime(2024, 1, 1)
        task.mark_run(now)
        assert task.run_count == 1
        assert task.last_run == now
        assert task.next_run == datetime(2024, 1, 2)

    def test_mark_run_once(self) -> None:
        task = ScheduledTask(
            task_id="t1",
            name="Test",
            schedule_type=ScheduleType.ONCE,
        )
        task.mark_run(datetime(2024, 1, 1))
        assert task.next_run is None

    def test_max_runs(self) -> None:
        task = ScheduledTask(
            task_id="t1",
            name="Test",
            schedule_type=ScheduleType.DAILY,
            max_runs=2,
        )
        task.mark_run(datetime(2024, 1, 1))
        task.mark_run(datetime(2024, 1, 2))
        assert task.next_run is None


class TestTaskScheduler:
    def setup_method(self) -> None:
        self.scheduler = TaskScheduler()

    def test_register_task(self) -> None:
        task = self.scheduler.register(
            "t1", "Test Task", ScheduleType.DAILY,
        )
        assert self.scheduler.get_task("t1") is task

    def test_remove_task(self) -> None:
        self.scheduler.register("t1", "Test Task")
        assert self.scheduler.remove("t1") is True
        assert self.scheduler.get_task("t1") is None

    def test_remove_nonexistent(self) -> None:
        assert self.scheduler.remove("nonexistent") is False

    def test_get_due_tasks(self) -> None:
        self.scheduler.register(
            "t1", "Due Task",
            next_run=datetime(2024, 1, 1),
        )
        self.scheduler.register(
            "t2", "Future Task",
            next_run=datetime(2025, 1, 1),
        )
        due = self.scheduler.get_due_tasks(datetime(2024, 6, 1))
        assert len(due) == 1
        assert due[0].task_id == "t1"

    def test_run_due(self) -> None:
        results = []

        def callback():
            results.append("executed")
            return {"status": "ok"}

        self.scheduler.register(
            "t1", "Test Task",
            next_run=datetime(2024, 1, 1),
            callback=callback,
        )
        records = self.scheduler.run_due(datetime(2024, 1, 2))
        assert len(records) == 1
        assert records[0].success is True
        assert len(results) == 1

    def test_run_due_callback_error(self) -> None:
        def failing_callback():
            raise ValueError("Task failed")

        self.scheduler.register(
            "t1", "Failing Task",
            next_run=datetime(2024, 1, 1),
            callback=failing_callback,
        )
        records = self.scheduler.run_due(datetime(2024, 1, 2))
        assert len(records) == 1
        assert records[0].success is False
        assert records[0].error == "Task failed"

    def test_run_due_no_callback(self) -> None:
        self.scheduler.register(
            "t1", "No Callback",
            next_run=datetime(2024, 1, 1),
        )
        records = self.scheduler.run_due(datetime(2024, 1, 2))
        assert len(records) == 1
        assert records[0].success is True

    def test_get_history(self) -> None:
        self.scheduler.register(
            "t1", "Test",
            next_run=datetime(2024, 1, 1),
        )
        self.scheduler.run_due(datetime(2024, 1, 2))
        history = self.scheduler.get_history("t1")
        assert len(history) == 1

    def test_get_history_limit(self) -> None:
        for i in range(15):
            self.scheduler.register(
                f"t{i}", f"Task {i}",
                next_run=datetime(2024, 1, 1),
            )
        self.scheduler.run_due(datetime(2024, 1, 2))
        history = self.scheduler.get_history(limit=5)
        assert len(history) == 5

    def test_get_stats(self) -> None:
        self.scheduler.register("t1", "Enabled")
        self.scheduler.register("t2", "Disabled", enabled=False)
        stats = self.scheduler.get_stats()
        assert stats["total_tasks"] == 2
        assert stats["enabled_tasks"] == 1
        assert stats["disabled_tasks"] == 1

    def test_task_schedules_next_run(self) -> None:
        self.scheduler.register(
            "t1", "Daily Task",
            schedule_type=ScheduleType.DAILY,
            next_run=datetime(2024, 1, 1),
        )
        self.scheduler.run_due(datetime(2024, 1, 1))
        task = self.scheduler.get_task("t1")
        assert task is not None
        assert task.next_run == datetime(2024, 1, 2)
''')

commit("test: add comprehensive tests for content_scheduler module")

# Commit 22: content_webhooks.py
write_file("personal_index/content_webhooks.py", '''
"""Webhook integration for personal-index content events.

Provides webhook registration, delivery, and retry logic
for notifying external services about content changes.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class WebhookEventType(Enum):
    """Types of webhook events."""

    CONTENT_ADDED = "content.added"
    CONTENT_UPDATED = "content.updated"
    CONTENT_DELETED = "content.deleted"
    BOOKMARK_ADDED = "bookmark.added"
    BOOKMARK_REMOVED = "bookmark.removed"
    TAG_ADDED = "tag.added"
    TAG_REMOVED = "tag.removed"
    CRAWL_STARTED = "crawl.started"
    CRAWL_COMPLETED = "crawl.completed"
    COLLECTION_CHANGED = "collection.changed"


@dataclass
class WebhookEndpoint:
    """A registered webhook endpoint.

    Attributes:
        endpoint_id: Unique identifier.
        url: Webhook URL.
        secret: Secret for signing payloads.
        events: Event types to subscribe to.
        enabled: Whether the endpoint is active.
        created_at: When the endpoint was registered.
        last_triggered: When the endpoint was last triggered.
        failure_count: Consecutive failure count.
        max_retries: Maximum retry attempts.
        retry_delay: Base delay between retries in seconds.
    """

    endpoint_id: str
    url: str
    secret: str | None = None
    events: list[WebhookEventType] = field(default_factory=list)
    enabled: bool = True
    created_at: datetime | None = None
    last_triggered: datetime | None = None
    failure_count: int = 0
    max_retries: int = 3
    retry_delay: float = 1.0

    def __post_init__(self) -> None:
        if self.created_at is None:
            self.created_at = datetime.now()

    def should_retry(self) -> bool:
        """Check if the endpoint should retry after failures."""
        return self.failure_count < self.max_retries


@dataclass
class WebhookPayload:
    """A webhook payload to be delivered.

    Attributes:
        payload_id: Unique identifier.
        event_type: Type of event.
        data: Event data.
        endpoint_id: Target endpoint ID.
        url: Target URL.
        attempts: Number of delivery attempts.
        delivered: Whether delivery succeeded.
        delivered_at: When delivery succeeded.
        last_error: Last error message.
        signature: HMAC signature of the payload.
    """

    payload_id: str
    event_type: WebhookEventType
    data: dict[str, Any]
    endpoint_id: str
    url: str
    attempts: int = 0
    delivered: bool = False
    delivered_at: datetime | None = None
    last_error: str | None = None
    signature: str | None = None


class WebhookManager:
    """Manages webhook endpoints and payload delivery.

    Handles endpoint registration, event dispatching,
    payload signing, and retry logic.
    """

    def __init__(self) -> None:
        self.endpoints: dict[str, WebhookEndpoint] = {}
        self.pending: list[WebhookPayload] = []
        self.delivered: list[WebhookPayload] = []
        self._id_counter = 0

    def register_endpoint(
        self,
        url: str,
        events: list[WebhookEventType] | None = None,
        secret: str | None = None,
        **kwargs: Any,
    ) -> WebhookEndpoint:
        """Register a new webhook endpoint.

        Args:
            url: Webhook URL.
            events: Event types to subscribe to.
            secret: Secret for payload signing.
            **kwargs: Additional endpoint parameters.

        Returns:
            The registered WebhookEndpoint.
        """
        self._id_counter += 1
        endpoint_id = f"wh-{self._id_counter}"
        endpoint = WebhookEndpoint(
            endpoint_id=endpoint_id,
            url=url,
            secret=secret,
            events=events or list(WebhookEventType),
            **kwargs,
        )
        self.endpoints[endpoint_id] = endpoint
        return endpoint

    def remove_endpoint(self, endpoint_id: str) -> bool:
        """Remove a webhook endpoint."""
        if endpoint_id in self.endpoints:
            del self.endpoints[endpoint_id]
            return True
        return False

    def dispatch_event(
        self,
        event_type: WebhookEventType,
        data: dict[str, Any],
    ) -> list[WebhookPayload]:
        """Dispatch an event to matching endpoints.

        Args:
            event_type: Type of event.
            data: Event data.

        Returns:
            List of created webhook payloads.
        """
        payloads = []

        for endpoint in self.endpoints.values():
            if not endpoint.enabled:
                continue
            if event_type not in endpoint.events:
                continue

            payload = self._create_payload(endpoint, event_type, data)
            self.pending.append(payload)
            payloads.append(payload)
            endpoint.last_triggered = datetime.now()

        return payloads

    def get_pending(self) -> list[WebhookPayload]:
        """Get all pending webhook payloads."""
        return self.pending

    def get_delivered(self) -> list[WebhookPayload]:
        """Get all delivered webhook payloads."""
        return self.delivered

    def mark_delivered(self, payload_id: str) -> bool:
        """Mark a payload as delivered."""
        for payload in self.pending:
            if payload.payload_id == payload_id:
                payload.delivered = True
                payload.delivered_at = datetime.now()
                self.pending.remove(payload)
                self.delivered.append(payload)
                # Reset failure count for endpoint
                endpoint = self.endpoints.get(payload.endpoint_id)
                if endpoint:
                    endpoint.failure_count = 0
                return True
        return False

    def mark_failed(self, payload_id: str, error: str) -> bool:
        """Mark a payload as failed and schedule retry if possible."""
        for payload in self.pending:
            if payload.payload_id == payload_id:
                payload.attempts += 1
                payload.last_error = error
                endpoint = self.endpoints.get(payload.endpoint_id)
                if endpoint:
                    endpoint.failure_count += 1
                    if not endpoint.should_retry():
                        self.pending.remove(payload)
                        self.delivered.append(payload)
                return True
        return False

    def get_stats(self) -> dict[str, Any]:
        """Get webhook manager statistics."""
        return {
            "total_endpoints": len(self.endpoints),
            "enabled_endpoints": sum(
                1 for e in self.endpoints.values() if e.enabled,
            ),
            "pending_payloads": len(self.pending),
            "delivered_payloads": len(self.delivered),
        }

    def _create_payload(
        self,
        endpoint: WebhookEndpoint,
        event_type: WebhookEventType,
        data: dict[str, Any],
    ) -> WebhookPayload:
        """Create a webhook payload with optional signing."""
        payload_data = {
            "event": event_type.value,
            "timestamp": datetime.now().isoformat(),
            "data": data,
        }

        signature = None
        if endpoint.secret:
            body = json.dumps(payload_data, sort_keys=True)
            signature = self._sign(body, endpoint.secret)

        return WebhookPayload(
            payload_id=f"pl-{self._id_counter}-{int(time.time())}",
            event_type=event_type,
            data=data,
            endpoint_id=endpoint.endpoint_id,
            url=endpoint.url,
            signature=signature,
        )

    def _sign(self, body: str, secret: str) -> str:
        """Create HMAC signature for a payload."""
        return hmac.new(
            secret.encode(),
            body.encode(),
            hashlib.sha256,
        ).hexdigest()

    def get_payload_json(self, payload: WebhookPayload) -> str:
        """Get the JSON body for a payload."""
        return json.dumps({
            "event": payload.event_type.value,
            "timestamp": datetime.now().isoformat(),
            "data": payload.data,
        }, sort_keys=True)
''')

commit("feat: add content_webhooks.py with webhook manager and signing")

# Commit 23: test_content_webhooks.py
write_file("tests/test_content_webhooks.py", '''
"""Tests for the content webhooks module."""

from personal_index.content_webhooks import (
    WebhookEndpoint,
    WebhookEventType,
    WebhookManager,
    WebhookPayload,
)


class TestWebhookEndpoint:
    def test_create(self) -> None:
        endpoint = WebhookEndpoint(
            endpoint_id="wh-1",
            url="https://example.com/webhook",
        )
        assert endpoint.enabled is True
        assert endpoint.failure_count == 0

    def test_should_retry(self) -> None:
        endpoint = WebhookEndpoint(
            endpoint_id="wh-1",
            url="https://example.com/webhook",
            max_retries=3,
        )
        assert endpoint.should_retry() is True
        endpoint.failure_count = 2
        assert endpoint.should_retry() is True
        endpoint.failure_count = 3
        assert endpoint.should_retry() is False


class TestWebhookManager:
    def setup_method(self) -> None:
        self.manager = WebhookManager()

    def test_register_endpoint(self) -> None:
        endpoint = self.manager.register_endpoint(
            "https://example.com/webhook",
            events=[WebhookEventType.CONTENT_ADDED],
        )
        assert endpoint.endpoint_id
        assert endpoint.url == "https://example.com/webhook"

    def test_remove_endpoint(self) -> None:
        self.manager.register_endpoint("https://example.com/webhook")
        endpoints = list(self.manager.endpoints.keys())
        assert self.manager.remove_endpoint(endpoints[0]) is True
        assert len(self.manager.endpoints) == 0

    def test_dispatch_event(self) -> None:
        self.manager.register_endpoint(
            "https://example.com/webhook",
            events=[WebhookEventType.CONTENT_ADDED],
        )
        payloads = self.manager.dispatch_event(
            WebhookEventType.CONTENT_ADDED,
            {"title": "New Content"},
        )
        assert len(payloads) == 1
        assert payloads[0].event_type == WebhookEventType.CONTENT_ADDED

    def test_dispatch_event_no_match(self) -> None:
        self.manager.register_endpoint(
            "https://example.com/webhook",
            events=[WebhookEventType.BOOKMARK_ADDED],
        )
        payloads = self.manager.dispatch_event(
            WebhookEventType.CONTENT_ADDED,
            {"title": "New Content"},
        )
        assert len(payloads) == 0

    def test_dispatch_disabled_endpoint(self) -> None:
        self.manager.register_endpoint(
            "https://example.com/webhook",
            events=[WebhookEventType.CONTENT_ADDED],
            enabled=False,
        )
        payloads = self.manager.dispatch_event(
            WebhookEventType.CONTENT_ADDED,
            {"title": "New Content"},
        )
        assert len(payloads) == 0

    def test_dispatch_all_events(self) -> None:
        self.manager.register_endpoint(
            "https://example.com/webhook",
        )
        payloads = self.manager.dispatch_event(
            WebhookEventType.CONTENT_ADDED,
            {"title": "New Content"},
        )
        assert len(payloads) == 1

    def test_mark_delivered(self) -> None:
        self.manager.register_endpoint(
            "https://example.com/webhook",
            events=[WebhookEventType.CONTENT_ADDED],
        )
        payloads = self.manager.dispatch_event(
            WebhookEventType.CONTENT_ADDED,
            {"title": "New Content"},
        )
        payload_id = payloads[0].payload_id
        assert self.manager.mark_delivered(payload_id) is True
        assert len(self.manager.get_pending()) == 0
        assert len(self.manager.get_delivered()) == 1

    def test_mark_failed(self) -> None:
        self.manager.register_endpoint(
            "https://example.com/webhook",
            events=[WebhookEventType.CONTENT_ADDED],
            max_retries=1,
        )
        payloads = self.manager.dispatch_event(
            WebhookEventType.CONTENT_ADDED,
            {"title": "New Content"},
        )
        payload_id = payloads[0].payload_id
        assert self.manager.mark_failed(payload_id, "Connection error") is True
        assert len(self.manager.get_pending()) == 0

    def test_payload_signing(self) -> None:
        self.manager.register_endpoint(
            "https://example.com/webhook",
            events=[WebhookEventType.CONTENT_ADDED],
            secret="my-secret",
        )
        payloads = self.manager.dispatch_event(
            WebhookEventType.CONTENT_ADDED,
            {"title": "New Content"},
        )
        assert payloads[0].signature is not None
        assert len(payloads[0].signature) == 64  # SHA-256 hex

    def test_get_stats(self) -> None:
        self.manager.register_endpoint("https://example.com/webhook")
        stats = self.manager.get_stats()
        assert stats["total_endpoints"] == 1
        assert stats["enabled_endpoints"] == 1

    def test_get_payload_json(self) -> None:
        self.manager.register_endpoint(
            "https://example.com/webhook",
            events=[WebhookEventType.CONTENT_ADDED],
        )
        payloads = self.manager.dispatch_event(
            WebhookEventType.CONTENT_ADDED,
            {"title": "New Content"},
        )
        json_str = self.manager.get_payload_json(payloads[0])
        assert "content.added" in json_str
        assert "New Content" in json_str

    def test_multiple_endpoints(self) -> None:
        self.manager.register_endpoint(
            "https://example.com/hook1",
            events=[WebhookEventType.CONTENT_ADDED],
        )
        self.manager.register_endpoint(
            "https://example.com/hook2",
            events=[WebhookEventType.CONTENT_ADDED],
        )
        payloads = self.manager.dispatch_event(
            WebhookEventType.CONTENT_ADDED,
            {"title": "New Content"},
        )
        assert len(payloads) == 2
''')

commit("test: add comprehensive tests for content_webhooks module")

# Commit 24: content_analytics.py
write_file("personal_index/content_analytics.py", '''
"""Content analytics module for personal-index.

Provides analytics and insights about content collections,
including trends, distributions, and performance metrics.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any


@dataclass
class ContentAnalytics:
    """Analytics report for a content collection.

    Attributes:
        total_items: Total number of content items.
        unique_domains: Number of unique source domains.
        unique_tags: Number of unique tags.
        avg_score: Average content score.
        avg_word_count: Average word count.
        bookmarked_count: Number of bookmarked items.
        tagged_count: Number of tagged items.
        top_domains: Most common source domains.
        top_tags: Most common tags.
        score_distribution: Score distribution buckets.
        daily_counts: Items per day.
        oldest_item: Date of oldest item.
        newest_item: Date of newest item.
    """

    total_items: int = 0
    unique_domains: int = 0
    unique_tags: int = 0
    avg_score: float = 0.0
    avg_word_count: float = 0.0
    bookmarked_count: int = 0
    tagged_count: int = 0
    top_domains: list[tuple[str, int]] = field(default_factory=list)
    top_tags: list[tuple[str, int]] = field(default_factory=list)
    score_distribution: dict[str, int] = field(default_factory=dict)
    daily_counts: dict[str, int] = field(default_factory=dict)
    oldest_item: datetime | None = None
    newest_item: datetime | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "total_items": self.total_items,
            "unique_domains": self.unique_domains,
            "unique_tags": self.unique_tags,
            "avg_score": round(self.avg_score, 4),
            "avg_word_count": round(self.avg_word_count, 1),
            "bookmarked_count": self.bookmarked_count,
            "tagged_count": self.tagged_count,
            "top_domains": self.top_domains,
            "top_tags": self.top_tags,
            "score_distribution": self.score_distribution,
            "daily_counts": self.daily_counts,
            "oldest_item": self.oldest_item.isoformat() if self.oldest_item else None,
            "newest_item": self.newest_item.isoformat() if self.newest_item else None,
        }


class AnalyticsEngine:
    """Computes analytics from content collections.

    Analyzes content items to produce insights about
    distributions, trends, and quality metrics.
    """

    def analyze(
        self,
        items: list[dict[str, Any]],
        top_n: int = 10,
    ) -> ContentAnalytics:
        """Analyze a collection of content items.

        Args:
            items: List of content item dictionaries.
            top_n: Number of top items to include.

        Returns:
            ContentAnalytics report.
        """
        if not items:
            return ContentAnalytics()

        analytics = ContentAnalytics()
        analytics.total_items = len(items)

        # Domain analysis
        domains = Counter()
        for item in items:
            url = item.get("url", "")
            if "://" in url:
                domain = url.split("://")[1].split("/")[0]
                domains[domain] += 1

        analytics.unique_domains = len(domains)
        analytics.top_domains = domains.most_common(top_n)

        # Tag analysis
        tags = Counter()
        tagged_count = 0
        for item in items:
            item_tags = item.get("tags", [])
            if item_tags:
                tagged_count += 1
                for tag in item_tags:
                    tags[tag] += 1

        analytics.unique_tags = len(tags)
        analytics.tagged_count = tagged_count
        analytics.top_tags = tags.most_common(top_n)

        # Score analysis
        scores = [item.get("score", 0.0) for item in items if "score" in item]
        if scores:
            analytics.avg_score = sum(scores) / len(scores)
            analytics.score_distribution = self._score_buckets(scores)

        # Word count analysis
        word_counts = [
            item.get("word_count", 0)
            for item in items
            if "word_count" in item
        ]
        if word_counts:
            analytics.avg_word_count = sum(word_counts) / len(word_counts)

        # Bookmark analysis
        analytics.bookmarked_count = sum(
            1 for item in items if item.get("bookmarked")
        )

        # Date analysis
        dates = []
        for item in items:
            pub = item.get("published_at")
            if pub:
                if isinstance(pub, str):
                    pub = datetime.fromisoformat(pub)
                dates.append(pub)

        if dates:
            analytics.oldest_item = min(dates)
            analytics.newest_item = max(dates)
            analytics.daily_counts = self._daily_counts(dates)

        return analytics

    def _score_buckets(
        self,
        scores: list[float],
    ) -> dict[str, int]:
        """Categorize scores into buckets."""
        buckets = {
            "excellent (0.8-1.0)": 0,
            "good (0.6-0.8)": 0,
            "average (0.4-0.6)": 0,
            "below_avg (0.2-0.4)": 0,
            "poor (0.0-0.2)": 0,
        }
        for score in scores:
            if score >= 0.8:
                buckets["excellent (0.8-1.0)"] += 1
            elif score >= 0.6:
                buckets["good (0.6-0.8)"] += 1
            elif score >= 0.4:
                buckets["average (0.4-0.6)"] += 1
            elif score >= 0.2:
                buckets["below_avg (0.2-0.4)"] += 1
            else:
                buckets["poor (0.0-0.2)"] += 1
        return buckets

    def _daily_counts(
        self,
        dates: list[datetime],
    ) -> dict[str, int]:
        """Count items per day."""
        counts: dict[str, int] = defaultdict(int)
        for date in dates:
            key = date.strftime("%Y-%m-%d")
            counts[key] += 1
        return dict(counts)

    def compare_periods(
        self,
        items: list[dict[str, Any]],
        period1_start: datetime,
        period1_end: datetime,
        period2_start: datetime,
        period2_end: datetime,
    ) -> dict[str, Any]:
        """Compare analytics between two time periods.

        Args:
            items: List of content items.
            period1_start: Start of first period.
            period1_end: End of first period.
            period2_start: Start of second period.
            period2_end: End of second period.

        Returns:
            Comparison dictionary with both periods and changes.
        """
        period1_items = [
            item for item in items
            if self._in_period(item, period1_start, period1_end)
        ]
        period2_items = [
            item for item in items
            if self._in_period(item, period2_start, period2_end)
        ]

        analytics1 = self.analyze(period1_items)
        analytics2 = self.analyze(period2_items)

        return {
            "period1": analytics1.to_dict(),
            "period2": analytics2.to_dict(),
            "changes": {
                "item_count": analytics2.total_items - analytics1.total_items,
                "avg_score": round(
                    analytics2.avg_score - analytics1.avg_score, 4,
                ),
                "unique_domains": analytics2.unique_domains - analytics1.unique_domains,
                "unique_tags": analytics2.unique_tags - analytics1.unique_tags,
            },
        }

    def _in_period(
        self,
        item: dict[str, Any],
        start: datetime,
        end: datetime,
    ) -> bool:
        """Check if an item falls within a time period."""
        pub = item.get("published_at")
        if pub is None:
            return False
        if isinstance(pub, str):
            pub = datetime.fromisoformat(pub)
        return start <= pub <= end
''')

commit("feat: add content_analytics.py with analytics engine")

# Commit 25: test_content_analytics.py
write_file("tests/test_content_analytics.py", '''
"""Tests for the content analytics module."""

from datetime import datetime

from personal_index.content_analytics import (
    AnalyticsEngine,
    ContentAnalytics,
)


class TestContentAnalytics:
    def test_to_dict(self) -> None:
        analytics = ContentAnalytics(
            total_items=100,
            unique_domains=10,
            unique_tags=25,
            avg_score=0.75,
            bookmarked_count=20,
        )
        d = analytics.to_dict()
        assert d["total_items"] == 100
        assert d["avg_score"] == 0.75


class TestAnalyticsEngine:
    def setup_method(self) -> None:
        self.engine = AnalyticsEngine()
        self.items = [
            {
                "id": str(i),
                "title": f"Article {i}",
                "url": f"https://example{i % 3}.com/article/{i}",
                "tags": ["python", "web"] if i % 2 == 0 else ["javascript"],
                "score": 0.5 + (i % 10) * 0.05,
                "word_count": 500 + i * 100,
                "bookmarked": i % 3 == 0,
                "published_at": datetime(2024, 1, 1 + (i % 7)),
            }
            for i in range(20)
        ]

    def test_analyze_empty(self) -> None:
        analytics = self.engine.analyze([])
        assert analytics.total_items == 0

    def test_analyze_total_items(self) -> None:
        analytics = self.engine.analyze(self.items)
        assert analytics.total_items == 20

    def test_analyze_unique_domains(self) -> None:
        analytics = self.engine.analyze(self.items)
        assert analytics.unique_domains == 3

    def test_analyze_top_domains(self) -> None:
        analytics = self.engine.analyze(self.items)
        assert len(analytics.top_domains) > 0
        assert analytics.top_domains[0][0].startswith("example")

    def test_analyze_top_tags(self) -> None:
        analytics = self.engine.analyze(self.items)
        assert len(analytics.top_tags) > 0

    def test_analyze_avg_score(self) -> None:
        analytics = self.engine.analyze(self.items)
        assert analytics.avg_score > 0
        assert analytics.avg_score < 1.0

    def test_analyze_score_distribution(self) -> None:
        analytics = self.engine.analyze(self.items)
        assert "excellent (0.8-1.0)" in analytics.score_distribution

    def test_analyze_bookmarked(self) -> None:
        analytics = self.engine.analyze(self.items)
        assert analytics.bookmarked_count > 0

    def test_analyze_tagged(self) -> None:
        analytics = self.engine.analyze(self.items)
        assert analytics.tagged_count == 20  # All items have tags

    def test_analyze_dates(self) -> None:
        analytics = self.engine.analyze(self.items)
        assert analytics.oldest_item is not None
        assert analytics.newest_item is not None
        assert analytics.oldest_item <= analytics.newest_item

    def test_analyze_daily_counts(self) -> None:
        analytics = self.engine.analyze(self.items)
        assert len(analytics.daily_counts) > 0

    def test_analyze_avg_word_count(self) -> None:
        analytics = self.engine.analyze(self.items)
        assert analytics.avg_word_count > 0

    def test_compare_periods(self) -> None:
        comparison = self.engine.compare_periods(
            self.items,
            period1_start=datetime(2024, 1, 1),
            period1_end=datetime(2024, 1, 3),
            period2_start=datetime(2024, 1, 4),
            period2_end=datetime(2024, 1, 7),
        )
        assert "period1" in comparison
        assert "period2" in comparison
        assert "changes" in comparison

    def test_analyze_to_dict(self) -> None:
        analytics = self.engine.analyze(self.items)
        d = analytics.to_dict()
        assert "total_items" in d
        assert "top_domains" in d
        assert "score_distribution" in d
''')

commit("test: add comprehensive tests for content_analytics module")

# Commit 26: content_merger.py
write_file("personal_index/content_merger.py", '''
"""Content merging utilities for personal-index.

Provides functionality to merge content from multiple sources,
deduplicate entries, and resolve conflicts.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class MergeResult:
    """Result of a content merge operation.

    Attributes:
        total_input: Total items across all sources.
        merged_count: Number of items in merged output.
        duplicates_removed: Number of duplicates removed.
        conflicts_resolved: Number of conflicts resolved.
        source_counts: Items per source.
        merge_time_ms: Time taken to merge.
    """

    total_input: int = 0
    merged_count: int = 0
    duplicates_removed: int = 0
    conflicts_resolved: int = 0
    source_counts: dict[str, int] = field(default_factory=dict)
    merge_time_ms: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "total_input": self.total_input,
            "merged_count": self.merged_count,
            "duplicates_removed": self.duplicates_removed,
            "conflicts_resolved": self.conflicts_resolved,
            "source_counts": self.source_counts,
            "merge_time_ms": round(self.merge_time_ms, 2),
        }


class ContentMerger:
    """Merges content from multiple sources with deduplication.

    Supports merging by URL, by ID, or by content hash,
    with configurable conflict resolution strategies.
    """

    def __init__(
        self,
        dedup_key: str = "url",
        conflict_strategy: str = "newest",
    ) -> None:
        self.dedup_key = dedup_key
        self.conflict_strategy = conflict_strategy

    def merge(
        self,
        sources: dict[str, list[dict[str, Any]]],
    ) -> tuple[list[dict[str, Any]], MergeResult]:
        """Merge content from multiple sources.

        Args:
            sources: Dict mapping source names to item lists.
            conflict_strategy: How to resolve conflicts.

        Returns:
            Tuple of (merged items, MergeResult).
        """
        import time

        start = time.time()
        result = MergeResult()
        result.source_counts = {
            name: len(items) for name, items in sources.items()
        }
        result.total_input = sum(result.source_counts.values())

        merged: dict[str, dict[str, Any]] = {}
        conflicts = 0

        for source_name, items in sources.items():
            for item in items:
                key = item.get(self.dedup_key, "")
                if not key:
                    # No dedup key, just add
                    item_id = item.get("id", f"merged-{len(merged)}")
                    merged[item_id] = {**item, "_source": source_name}
                    continue

                if key not in merged:
                    merged[key] = {**item, "_source": source_name}
                else:
                    conflicts += 1
                    existing = merged[key]
                    winner = self._resolve_conflict(
                        existing, item, source_name,
                    )
                    merged[key] = winner

        result.conflicts_resolved = conflicts
        result.merged_count = len(merged)
        result.duplicates_removed = result.total_input - result.merged_count
        result.merge_time_ms = (time.time() - start) * 1000

        return list(merged.values()), result

    def merge_with_priority(
        self,
        sources: dict[str, list[dict[str, Any]]],
        priority_order: list[str] | None = None,
    ) -> tuple[list[dict[str, Any]], MergeResult]:
        """Merge sources with priority ordering.

        Higher priority sources win conflicts.

        Args:
            sources: Dict mapping source names to item lists.
            priority_order: List of source names in priority order.

        Returns:
            Tuple of (merged items, MergeResult).
        """
        if priority_order is None:
            priority_order = list(sources.keys())

        # Process sources in reverse priority order
        # so higher priority sources overwrite
        ordered_sources = {}
        for name in reversed(priority_order):
            if name in sources:
                ordered_sources[name] = sources[name]

        # Add any sources not in priority order
        for name, items in sources.items():
            if name not in ordered_sources:
                ordered_sources[name] = items

        return self.merge(ordered_sources)

    def merge_tags(
        self,
        items: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Merge duplicate tags within each item.

        Args:
            items: List of content items.

        Returns:
            Items with deduplicated tags.
        """
        result = []
        for item in items:
            new_item = dict(item)
            tags = item.get("tags", [])
            if isinstance(tags, list):
                seen: set[str] = set()
                unique_tags = []
                for tag in tags:
                    if tag not in seen:
                        seen.add(tag)
                        unique_tags.append(tag)
                new_item["tags"] = unique_tags
            result.append(new_item)
        return result

    def _resolve_conflict(
        self,
        existing: dict[str, Any],
        new_item: dict[str, Any],
        new_source: str,
    ) -> dict[str, Any]:
        """Resolve a conflict between two items with the same key."""
        if self.conflict_strategy == "newest":
            existing_date = self._get_date(existing)
            new_date = self._get_date(new_item)
            if new_date and (not existing_date or new_date > existing_date):
                return {**new_item, "_source": new_source}
            return existing

        elif self.conflict_strategy == "highest_score":
            existing_score = existing.get("score", 0.0)
            new_score = new_item.get("score", 0.0)
            if new_score > existing_score:
                return {**new_item, "_source": new_source}
            return existing

        elif self.conflict_strategy == "merge_tags":
            existing_tags = set(existing.get("tags", []))
            new_tags = set(new_item.get("tags", []))
            merged_tags = list(existing_tags | new_tags)
            result = dict(new_item)
            result["tags"] = merged_tags
            result["_source"] = f"{existing.get('_source', '')},{new_source}"
            return result

        # Default: keep existing
        return existing

    def _get_date(
        self,
        item: dict[str, Any],
    ) -> datetime | None:
        """Get the date from an item."""
        for key in ("updated_at", "published_at", "date"):
            value = item.get(key)
            if value:
                if isinstance(value, str):
                    return datetime.fromisoformat(value)
                if isinstance(value, datetime):
                    return value
        return None
''')

commit("feat: add content_merger.py with merge and deduplication")

# Commit 27: test_content_merger.py
write_file("tests/test_content_merger.py", '''
"""Tests for the content merger module."""

from datetime import datetime

from personal_index.content_merger import ContentMerger, MergeResult


class TestMergeResult:
    def test_to_dict(self) -> None:
        result = MergeResult(
            total_input=100,
            merged_count=80,
            duplicates_removed=20,
            conflicts_resolved=5,
        )
        d = result.to_dict()
        assert d["total_input"] == 100
        assert d["duplicates_removed"] == 20


class TestContentMerger:
    def setup_method(self) -> None:
        self.merger = ContentMerger(dedup_key="url")

    def test_merge_no_duplicates(self) -> None:
        sources = {
            "source1": [
                {"id": "1", "url": "https://a.com/1", "title": "A1"},
            ],
            "source2": [
                {"id": "2", "url": "https://b.com/2", "title": "B2"},
            ],
        }
        items, result = self.merger.merge(sources)
        assert len(items) == 2
        assert result.duplicates_removed == 0

    def test_merge_duplicates(self) -> None:
        sources = {
            "source1": [
                {"id": "1", "url": "https://a.com/1", "title": "A1"},
            ],
            "source2": [
                {"id": "1", "url": "https://a.com/1", "title": "A1 Updated"},
            ],
        }
        items, result = self.merger.merge(sources)
        assert len(items) == 1
        assert result.duplicates_removed == 1
        assert result.conflicts_resolved == 1

    def test_merge_conflict_newest(self) -> None:
        self.merger = ContentMerger(dedup_key="url", conflict_strategy="newest")
        sources = {
            "source1": [
                {
                    "id": "1",
                    "url": "https://a.com/1",
                    "title": "Old",
                    "published_at": datetime(2024, 1, 1),
                },
            ],
            "source2": [
                {
                    "id": "1",
                    "url": "https://a.com/1",
                    "title": "New",
                    "published_at": datetime(2024, 1, 2),
                },
            ],
        }
        items, _ = self.merger.merge(sources)
        assert items[0]["title"] == "New"

    def test_merge_conflict_highest_score(self) -> None:
        self.merger = ContentMerger(
            dedup_key="url", conflict_strategy="highest_score",
        )
        sources = {
            "source1": [
                {"id": "1", "url": "https://a.com/1", "score": 0.5},
            ],
            "source2": [
                {"id": "1", "url": "https://a.com/1", "score": 0.9},
            ],
        }
        items, _ = self.merger.merge(sources)
        assert items[0]["score"] == 0.9

    def test_merge_conflict_merge_tags(self) -> None:
        self.merger = ContentMerger(
            dedup_key="url", conflict_strategy="merge_tags",
        )
        sources = {
            "source1": [
                {"id": "1", "url": "https://a.com/1", "tags": ["python"]},
            ],
            "source2": [
                {"id": "1", "url": "https://a.com/1", "tags": ["web"]},
            ],
        }
        items, _ = self.merger.merge(sources)
        tags = set(items[0]["tags"])
        assert "python" in tags
        assert "web" in tags

    def test_merge_with_priority(self) -> None:
        sources = {
            "low": [
                {"id": "1", "url": "https://a.com/1", "title": "Low"},
            ],
            "high": [
                {"id": "1", "url": "https://a.com/1", "title": "High"},
            ],
        }
        items, _ = self.merger.merge_with_priority(
            sources, priority_order=["high", "low"],
        )
        assert items[0]["title"] == "High"

    def test_merge_tags_dedup(self) -> None:
        items = [
            {"id": "1", "tags": ["python", "python", "web", "web"]},
        ]
        result = self.merger.merge_tags(items)
        assert len(result[0]["tags"]) == 2

    def test_merge_empty_sources(self) -> None:
        items, result = self.merger.merge({})
        assert len(items) == 0
        assert result.total_input == 0

    def test_merge_missing_dedup_key(self) -> None:
        sources = {
            "source1": [
                {"id": "1", "title": "No URL"},
            ],
        }
        items, result = self.merger.merge(sources)
        assert len(items) == 1
''')

commit("test: add comprehensive tests for content_merger module")

# Commit 28: content_validation.py
write_file("personal_index/content_validation.py", '''
"""Content validation module for personal-index.

Provides validation rules and validators for content items,
ensuring data quality and consistency.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class ValidationError:
    """A single validation error.

    Attributes:
        field: The field that failed validation.
        message: Human-readable error message.
        severity: Error severity level.
        value: The invalid value.
    """

    field: str
    message: str
    severity: str = "error"
    value: Any = None


@dataclass
class ValidationResult:
    """Result of validating content items.

    Attributes:
        is_valid: Whether all items passed validation.
        errors: List of validation errors.
        warnings: List of validation warnings.
        items_valid: Number of valid items.
        items_invalid: Number of invalid items.
    """

    is_valid: bool = True
    errors: list[ValidationError] = field(default_factory=list)
    warnings: list[ValidationError] = field(default_factory=list)
    items_valid: int = 0
    items_invalid: int = 0

    def add_error(
        self,
        field: str,
        message: str,
        value: Any = None,
    ) -> None:
        """Add a validation error."""
        self.errors.append(ValidationError(
            field=field, message=message, value=value,
        ))
        self.is_valid = False

    def add_warning(
        self,
        field: str,
        message: str,
        value: Any = None,
    ) -> None:
        """Add a validation warning."""
        self.warnings.append(ValidationError(
            field=field, message=message, severity="warning", value=value,
        ))

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "is_valid": self.is_valid,
            "error_count": len(self.errors),
            "warning_count": len(self.warnings),
            "items_valid": self.items_valid,
            "items_invalid": self.items_invalid,
            "errors": [
                {"field": e.field, "message": e.message}
                for e in self.errors
            ],
        }


class ContentValidator:
    """Validates content items against defined rules.

    Checks for required fields, valid URLs, proper date formats,
    and configurable custom rules.
    """

    def __init__(
        self,
        required_fields: list[str] | None = None,
        max_title_length: int = 500,
        max_url_length: int = 2048,
    ) -> None:
        self.required_fields = required_fields or ["id", "url"]
        self.max_title_length = max_title_length
        self.max_url_length = max_url_length

    def validate(
        self,
        items: list[dict[str, Any]],
    ) -> ValidationResult:
        """Validate a list of content items.

        Args:
            items: List of content item dictionaries.

        Returns:
            ValidationResult with errors and warnings.
        """
        result = ValidationResult()

        for i, item in enumerate(items):
            item_valid = True
            prefix = f"item[{i}]"

            # Check required fields
            for field_name in self.required_fields:
                if field_name not in item:
                    result.add_error(
                        f"{prefix}.{field_name}",
                        f"Required field '{field_name}' is missing",
                    )
                    item_valid = False

            # Validate URL
            url = item.get("url", "")
            if url:
                if not self._is_valid_url(url):
                    result.add_error(
                        f"{prefix}.url",
                        f"Invalid URL: {url}",
                        value=url,
                    )
                    item_valid = False
                elif len(url) > self.max_url_length:
                    result.add_error(
                        f"{prefix}.url",
                        f"URL exceeds max length of {self.max_url_length}",
                    )
                    item_valid = False

            # Validate title
            title = item.get("title", "")
            if title and len(title) > self.max_title_length:
                result.add_warning(
                    f"{prefix}.title",
                    f"Title exceeds recommended length of {self.max_title_length}",
                )

            # Validate score range
            score = item.get("score")
            if score is not None:
                if not isinstance(score, (int, float)):
                    result.add_error(
                        f"{prefix}.score",
                        "Score must be a number",
                    )
                    item_valid = False
                elif not (0.0 <= score <= 1.0):
                    result.add_warning(
                        f"{prefix}.score",
                        f"Score {score} is outside typical range [0, 1]",
                    )

            # Validate date fields
            for date_field in ("published_at", "updated_at"):
                date_val = item.get(date_field)
                if date_val and not self._is_valid_date(date_val):
                    result.add_error(
                        f"{prefix}.{date_field}",
                        f"Invalid date format: {date_val}",
                    )
                    item_valid = False

            if item_valid:
                result.items_valid += 1
            else:
                result.items_invalid += 1

        return result

    def validate_single(self, item: dict[str, Any]) -> ValidationResult:
        """Validate a single content item."""
        return self.validate([item])

    def _is_valid_url(self, url: str) -> bool:
        """Check if a URL is valid."""
        if not url:
            return False
        return url.startswith(("http://", "https://"))

    def _is_valid_date(self, value: Any) -> bool:
        """Check if a value is a valid date."""
        if isinstance(value, datetime):
            return True
        if isinstance(value, str):
            try:
                datetime.fromisoformat(value)
                return True
            except ValueError:
                return False
        return False
''')

commit("feat: add content_validation.py with content validator")

# Commit 29: test_content_validation.py
write_file("tests/test_content_validation.py", '''
"""Tests for the content validation module."""

from datetime import datetime

from personal_index.content_validation import (
    ContentValidator,
    ValidationError,
    ValidationResult,
)


class TestValidationError:
    def test_create(self) -> None:
        error = ValidationError(
            field="url",
            message="Invalid URL",
            severity="error",
        )
        assert error.severity == "error"


class TestValidationResult:
    def test_create(self) -> None:
        result = ValidationResult()
        assert result.is_valid is True
        assert len(result.errors) == 0

    def test_add_error(self) -> None:
        result = ValidationResult()
        result.add_error("url", "Invalid URL")
        assert result.is_valid is False
        assert len(result.errors) == 1

    def test_add_warning(self) -> None:
        result = ValidationResult()
        result.add_warning("title", "Too long")
        assert result.is_valid is True
        assert len(result.warnings) == 1

    def test_to_dict(self) -> None:
        result = ValidationResult()
        result.add_error("url", "Invalid")
        d = result.to_dict()
        assert d["is_valid"] is False
        assert d["error_count"] == 1


class TestContentValidator:
    def setup_method(self) -> None:
        self.validator = ContentValidator()

    def test_valid_item(self) -> None:
        item = {"id": "1", "url": "https://example.com"}
        result = self.validator.validate([item])
        assert result.is_valid is True
        assert result.items_valid == 1

    def test_missing_required_field(self) -> None:
        item = {"id": "1"}  # Missing url
        result = self.validator.validate([item])
        assert result.is_valid is False
        assert len(result.errors) == 1

    def test_invalid_url(self) -> None:
        item = {"id": "1", "url": "not-a-url"}
        result = self.validator.validate([item])
        assert result.is_valid is False

    def test_url_too_long(self) -> None:
        item = {"id": "1", "url": "https://" + "a" * 2049}
        result = self.validator.validate([item])
        assert result.is_valid is False

    def test_title_too_long(self) -> None:
        item = {
            "id": "1",
            "url": "https://example.com",
            "title": "x" * 501,
        }
        result = self.validator.validate([item])
        assert result.is_valid is True  # Warning, not error
        assert len(result.warnings) == 1

    def test_invalid_score_type(self) -> None:
        item = {"id": "1", "url": "https://example.com", "score": "high"}
        result = self.validator.validate([item])
        assert result.is_valid is False

    def test_score_out_of_range(self) -> None:
        item = {"id": "1", "url": "https://example.com", "score": 1.5}
        result = self.validator.validate([item])
        assert result.is_valid is True  # Warning
        assert len(result.warnings) == 1

    def test_invalid_date(self) -> None:
        item = {
            "id": "1",
            "url": "https://example.com",
            "published_at": "not-a-date",
        }
        result = self.validator.validate([item])
        assert result.is_valid is False

    def test_valid_date_string(self) -> None:
        item = {
            "id": "1",
            "url": "https://example.com",
            "published_at": "2024-01-01T00:00:00",
        }
        result = self.validator.validate([item])
        assert result.is_valid is True

    def test_valid_date_object(self) -> None:
        item = {
            "id": "1",
            "url": "https://example.com",
            "published_at": datetime(2024, 1, 1),
        }
        result = self.validator.validate([item])
        assert result.is_valid is True

    def test_custom_required_fields(self) -> None:
        validator = ContentValidator(
            required_fields=["id", "url", "title"],
        )
        item = {"id": "1", "url": "https://example.com"}
        result = validator.validate([item])
        assert result.is_valid is False

    def test_multiple_items(self) -> None:
        items = [
            {"id": "1", "url": "https://example.com"},
            {"id": "2"},  # Missing url
            {"id": "3", "url": "https://example.com"},
        ]
        result = self.validator.validate(items)
        assert result.items_valid == 2
        assert result.items_invalid == 1

    def test_validate_single(self) -> None:
        item = {"id": "1", "url": "https://example.com"}
        result = self.validator.validate_single(item)
        assert result.is_valid is True
''')

commit("test: add comprehensive tests for content_validation module")

# Commit 30: content_transform.py
write_file("personal_index/content_transform.py", '''
"""Content transformation pipeline for personal-index.

Provides a chain of transformation functions that can be
applied to content items for normalization, enrichment,
and formatting.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable


TransformFn = Callable[[dict[str, Any]], dict[str, Any]]


@dataclass
class TransformPipeline:
    """A pipeline of content transformations.

    Attributes:
        name: Pipeline name.
        transforms: Ordered list of transformation functions.
        metadata: Pipeline metadata.
    """

    name: str = "default"
    transforms: list[tuple[str, TransformFn]] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def add(
        self,
        name: str,
        transform: TransformFn,
    ) -> TransformPipeline:
        """Add a transformation to the pipeline.

        Args:
            name: Name of the transformation.
            transform: Transformation function.

        Returns:
            Self for chaining.
        """
        self.transforms.append((name, transform))
        return self

    def apply(self, item: dict[str, Any]) -> dict[str, Any]:
        """Apply all transformations to an item.

        Args:
            item: Content item to transform.

        Returns:
            Transformed content item.
        """
        result = dict(item)
        for name, transform in self.transforms:
            try:
                result = transform(result)
            except Exception:
                # Skip failed transforms, continue pipeline
                pass
        return result

    def apply_batch(
        self,
        items: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Apply pipeline to a batch of items.

        Args:
            items: List of content items.

        Returns:
            List of transformed items.
        """
        return [self.apply(item) for item in items]


# Built-in transforms


def normalize_url(item: dict[str, Any]) -> dict[str, Any]:
    """Normalize URL by removing trailing slashes and fragments."""
    url = item.get("url", "")
    if url:
        url = url.rstrip("/")
        if "#" in url:
            url = url.split("#")[0]
        item["url"] = url
    return item


def normalize_title(item: dict[str, Any]) -> dict[str, Any]:
    """Normalize title by stripping whitespace and lowercasing."""
    title = item.get("title", "")
    if title:
        item["title"] = title.strip()
    return item


def normalize_tags(item: dict[str, Any]) -> dict[str, Any]:
    """Normalize tags by lowercasing and stripping."""
    tags = item.get("tags", [])
    if isinstance(tags, list):
        item["tags"] = [
            tag.strip().lower() for tag in tags if tag
        ]
    return item


def add_domain(item: dict[str, Any]) -> dict[str, Any]:
    """Extract and add domain from URL."""
    url = item.get("url", "")
    if "://" in url:
        domain = url.split("://")[1].split("/")[0]
        item["domain"] = domain
    return item


def add_word_count(item: dict[str, Any]) -> dict[str, Any]:
    """Add word count from content or description."""
    content = item.get("content", item.get("description", ""))
    if isinstance(content, str):
        item["word_count"] = len(content.split())
    return item


def add_timestamp(item: dict[str, Any]) -> dict[str, Any]:
    """Add processing timestamp."""
    item["processed_at"] = datetime.now().isoformat()
    return item


def filter_by_score(
    min_score: float,
) -> TransformFn:
    """Create a transform that filters items below min_score.

    Args:
        min_score: Minimum score threshold.

    Returns:
        Transform function.
    """
    def transform(item: dict[str, Any]) -> dict[str, Any]:
        score = item.get("score", 0.0)
        if score < min_score:
            item["_filtered"] = True
        return item
    return transform


def enrich_with_defaults(item: dict[str, Any]) -> dict[str, Any]:
    """Add default values for missing fields."""
    defaults = {
        "tags": [],
        "score": 0.0,
        "bookmarked": False,
        "metadata": {},
    }
    for key, value in defaults.items():
        if key not in item:
            item[key] = value
    return item


def create_standard_pipeline() -> TransformPipeline:
    """Create a standard transformation pipeline.

    Returns:
        Configured TransformPipeline.
    """
    return TransformPipeline(name="standard").add(
        "normalize_url", normalize_url,
    ).add(
        "normalize_title", normalize_title,
    ).add(
        "normalize_tags", normalize_tags,
    ).add(
        "add_domain", add_domain,
    ).add(
        "add_word_count", add_word_count,
    ).add(
        "enrich_with_defaults", enrich_with_defaults,
    ).add(
        "add_timestamp", add_timestamp,
    )
''')

commit("feat: add content_transform.py with transformation pipeline")

# Commit 31: test_content_transform.py
write_file("tests/test_content_transform.py", '''
"""Tests for the content transform module."""

from personal_index.content_transform import (
    TransformPipeline,
    add_domain,
    add_timestamp,
    add_word_count,
    create_standard_pipeline,
    enrich_with_defaults,
    filter_by_score,
    normalize_tags,
    normalize_title,
    normalize_url,
)


class TestTransformPipeline:
    def test_create(self) -> None:
        pipeline = TransformPipeline(name="test")
        assert pipeline.name == "test"
        assert len(pipeline.transforms) == 0

    def test_add_transform(self) -> None:
        pipeline = TransformPipeline()
        result = pipeline.add("test", lambda x: x)
        assert result is pipeline  # Chaining
        assert len(pipeline.transforms) == 1

    def test_apply(self) -> None:
        pipeline = TransformPipeline().add(
            "upper_title",
            lambda item: {**item, "title": item.get("title", "").upper()},
        )
        result = pipeline.apply({"title": "hello"})
        assert result["title"] == "HELLO"

    def test_apply_batch(self) -> None:
        pipeline = TransformPipeline().add(
            "add_key",
            lambda item: {**item, "processed": True},
        )
        items = [{"id": "1"}, {"id": "2"}]
        result = pipeline.apply_batch(items)
        assert all(item.get("processed") for item in result)

    def test_failed_transform_skipped(self) -> None:
        def failing(item):
            raise ValueError("fail")

        pipeline = TransformPipeline().add(
            "fail", failing,
        ).add(
            "add_key",
            lambda item: {**item, "ok": True},
        )
        result = pipeline.apply({"id": "1"})
        assert result.get("ok") is True


class TestBuiltInTransforms:
    def test_normalize_url_trailing_slash(self) -> None:
        item = {"url": "https://example.com/"}
        result = normalize_url(item)
        assert result["url"] == "https://example.com"

    def test_normalize_url_fragment(self) -> None:
        item = {"url": "https://example.com/page#section"}
        result = normalize_url(item)
        assert result["url"] == "https://example.com/page"

    def test_normalize_title(self) -> None:
        item = {"title": "  Hello World  "}
        result = normalize_title(item)
        assert result["title"] == "Hello World"

    def test_normalize_tags(self) -> None:
        item = {"tags": [" Python ", " WEB ", ""]}
        result = normalize_tags(item)
        assert result["tags"] == ["python", "web"]

    def test_add_domain(self) -> None:
        item = {"url": "https://example.com/path"}
        result = add_domain(item)
        assert result["domain"] == "example.com"

    def test_add_word_count(self) -> None:
        item = {"content": "Hello world this is a test"}
        result = add_word_count(item)
        assert result["word_count"] == 6

    def test_add_timestamp(self) -> None:
        item = {"id": "1"}
        result = add_timestamp(item)
        assert "processed_at" in result

    def test_filter_by_score(self) -> None:
        transform = filter_by_score(0.5)
        item = {"id": "1", "score": 0.3}
        result = transform(item)
        assert result.get("_filtered") is True

    def test_enrich_with_defaults(self) -> None:
        item = {"id": "1"}
        result = enrich_with_defaults(item)
        assert result["tags"] == []
        assert result["score"] == 0.0
        assert result["bookmarked"] is False


class TestStandardPipeline:
    def test_standard_pipeline(self) -> None:
        pipeline = create_standard_pipeline()
        assert len(pipeline.transforms) == 7

    def test_standard_pipeline_apply(self) -> None:
        pipeline = create_standard_pipeline()
        item = {
            "url": "https://example.com/",
            "title": "  Test  ",
            "tags": [" Python "],
            "content": "Hello world",
        }
        result = pipeline.apply(item)
        assert result["url"] == "https://example.com"
        assert result["title"] == "Test"
        assert result["tags"] == ["python"]
        assert result["domain"] == "example.com"
        assert result["word_count"] == 2
        assert "processed_at" in result
''')

commit("test: add comprehensive tests for content_transform module")

print(f"Completed 31 commits total")
run("git log --oneline | wc -l")
