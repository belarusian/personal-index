"""Tests for the content notification module."""

from datetime import datetime, timedelta, timezone

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
            timestamp=datetime.now(tz=timezone.utc),
        )
        assert n.delivered is False

    def test_to_dict(self) -> None:
        n = Notification(
            notification_id="n1",
            notification_type=NotificationType.NEW_BOOKMARK,
            title="Test",
            message="Message",
            timestamp=datetime(2024, 1, 1, tzinfo=timezone.utc),
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
            cooldown_seconds=0,
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
        old_time = datetime.now(tz=timezone.utc) - timedelta(hours=1)
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
            timestamp=datetime.now(tz=timezone.utc),
        ))
        cleared = self.manager.clear_old(datetime.now(tz=timezone.utc) - timedelta(minutes=30))
        assert cleared == 1
        assert len(self.manager.notifications) == 1


class TestNotificationManagerDocstring:
    def test_docstring_does_not_promise_channel_delivery(self) -> None:
        """Regression: class docstring must not over-promise capabilities.

        NotificationManager stores rules, evaluates events against rules to
        generate notifications, and tracks delivery state via the delivered
        flag (set externally by mark_delivered/mark_all_delivered). It has
        no send/dispatch/emit/deliver method and the channels field is
        stored but never used to perform delivery, so its docstring must not
        claim it 'delivers notifications' through channels (TICKET-331).
        """
        doc = (NotificationManager.__doc__ or "").lower()
        assert "delivers notifications" not in doc


class TestModuleDeliveryStateDocstring:
    """Pin the corrected module docstring claim (TICKET-367).

    The module docstring previously claimed it manages "delivery". The code
    never dispatches to a channel: it records notifications and toggles their
    delivered flag via mark_delivered/mark_all_delivered. This test witnesses
    the real mechanism against the returned object, not the docstring wording.
    """

    def test_fresh_manager_holds_no_notifications(self) -> None:
        mgr = NotificationManager()
        assert mgr.get_undelivered() == []
        assert mgr.notifications == []

    def test_evaluate_records_undelivered_not_delivered(self) -> None:
        mgr = NotificationManager()
        rule = NotificationRule(
            rule_id="r1",
            name="Alert",
            notification_type=NotificationType.NEW_BOOKMARK,
            channels=[NotificationChannel.WEBHOOK],
            conditions={"type": "bookmark"},
        )
        mgr.add_rule(rule)
        generated = mgr.evaluate_event({"type": "bookmark"})
        assert len(generated) == 1
        assert generated[0].delivered is False
        assert mgr.get_undelivered() == generated
        # mark_delivered only flips the flag; nothing was dispatched.
        assert mgr.mark_delivered(generated[0].notification_id) is True
        assert generated[0].delivered is True
        assert mgr.get_undelivered() == []
