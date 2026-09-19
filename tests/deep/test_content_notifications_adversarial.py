"""Adversarial deep tests for personal_index.content_notifications.

Cycle 277 - VALIDATOR probe of a never-probed subsystem (content_notifications).

content_notifications is a record-and-track notification store (no channel
dispatch). The contract is pinned from the module docstrings:

- NotificationRule.matches: disabled rule -> False; empty conditions -> True
  (matches any event); a condition is satisfied only when event.get(key) ==
  value for EVERY condition (all-keys AND); a missing event key -> False.
- Notification.to_dict: stable 8-key dict; type/channels serialized to .value;
  timestamp to isoformat; delivered flag preserved.
- NotificationManager.add_rule / remove_rule: remove_rule returns True iff a
  rule with that rule_id existed; duplicate rule_ids are allowed (both stored,
  remove_rule removes only the first match).
- evaluate_event: fires a notification per matching enabled rule whose cooldown
  has elapsed; a rule within cooldown is skipped; empty event still fires a
  rule with empty conditions; generated notifications are appended to
  self.notifications and returned.
- get_undelivered: only delivered==False notifications.
- mark_delivered: True iff a notification with that id existed; stamps
  delivered_at; idempotent (second call still True, no double count).
- mark_all_delivered: returns the count of previously-undelivered notifications;
  idempotent (second call returns 0).
- get_recent: limit<=0 -> all; negative limit -> last abs(limit) (floor via abs);
  type filter narrows before the slice.
- clear_old: removes notifications with timestamp < older_than; returns the
  removed count; idempotent.
- _format_message: rule name alone when no title/url/message keys; appends
  "key: value" for each of title/url/message present; unicode preserved.

The negative-slice "top N" CLASS SWEEP for this cycle found NO new public
leak site: every [:var] / [-var:] slice in personal_index/ carries a floor
guard (limit<=0 -> [] or max(0, ...) or -abs(limit):). See the cycle-277
sweep table in the gate log.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from click.testing import CliRunner

from personal_index.cli import main
from personal_index.content_notifications import (
    Notification,
    NotificationChannel,
    NotificationManager,
    NotificationRule,
    NotificationType,
)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _rule(
    rule_id: str = "r1",
    ntype: NotificationType = NotificationType.NEW_BOOKMARK,
    conditions: dict | None = None,
    enabled: bool = True,
    cooldown: int = 300,
    name: str | None = None,
) -> NotificationRule:
    return NotificationRule(
        rule_id=rule_id,
        name=name if name is not None else f"rule-{rule_id}",
        notification_type=ntype,
        channels=[NotificationChannel.LOG],
        conditions=conditions or {},
        enabled=enabled,
        cooldown_seconds=cooldown,
    )


class TestRuleMatches:
    """NotificationRule.matches contract."""

    def test_disabled_rule_never_matches(self):
        r = _rule(enabled=False, conditions={})
        assert r.matches({"anything": 1}) is False

    def test_empty_conditions_match_any_event(self):
        r = _rule(conditions={})
        assert r.matches({}) is True
        assert r.matches({"a": 1, "b": "x"}) is True

    def test_single_condition_match(self):
        r = _rule(conditions={"type": "new_bookmark"})
        assert r.matches({"type": "new_bookmark"}) is True

    def test_single_condition_mismatch(self):
        r = _rule(conditions={"type": "new_bookmark"})
        assert r.matches({"type": "crawl_complete"}) is False

    def test_missing_event_key_is_mismatch(self):
        r = _rule(conditions={"type": "new_bookmark"})
        assert r.matches({}) is False

    def test_all_conditions_must_hold(self):
        r = _rule(conditions={"type": "x", "score": 5})
        assert r.matches({"type": "x", "score": 5}) is True
        # one key wrong -> False
        assert r.matches({"type": "x", "score": 6}) is False
        # one key missing -> False
        assert r.matches({"type": "x"}) is False

    def test_none_value_condition(self):
        r = _rule(conditions={"flag": None})
        assert r.matches({"flag": None}) is True
        assert r.matches({"flag": 0}) is False

    def test_unicode_condition_roundtrip(self):
        r = _rule(conditions={"tag": "café-日本語"})
        assert r.matches({"tag": "café-日本語"}) is True
        assert r.matches({"tag": "cafe-日本語"}) is False


class TestNotificationToDict:
    """Notification.to_dict contract."""

    def test_to_dict_keys_and_serialization(self):
        ts = _now()
        n = Notification(
            notification_id="notif-1",
            notification_type=NotificationType.SCORE_CHANGE,
            title="T",
            message="M",
            timestamp=ts,
            channels=[NotificationChannel.WEBHOOK, NotificationChannel.EMAIL],
            data={"k": "v"},
            delivered=False,
        )
        d = n.to_dict()
        assert set(d) == {
            "notification_id", "type", "title", "message",
            "timestamp", "channels", "data", "delivered",
        }
        assert d["type"] == "score_change"
        assert d["channels"] == ["webhook", "email"]
        assert d["timestamp"] == ts.isoformat()
        assert d["delivered"] is False
        assert d["data"] == {"k": "v"}

    def test_to_dict_delivered_true_preserved(self):
        n = Notification(
            notification_id="n", notification_type=NotificationType.TAG_ADDED,
            title="t", message="m", timestamp=_now(), delivered=True,
        )
        assert n.to_dict()["delivered"] is True

    def test_to_dict_empty_channels_and_data(self):
        n = Notification(
            notification_id="n", notification_type=NotificationType.TAG_ADDED,
            title="t", message="m", timestamp=_now(),
        )
        d = n.to_dict()
        assert d["channels"] == []
        assert d["data"] == {}


class TestRuleManagement:
    """add_rule / remove_rule contract."""

    def test_add_and_remove_existing(self):
        m = NotificationManager()
        m.add_rule(_rule("a"))
        assert len(m.rules) == 1
        assert m.remove_rule("a") is True
        assert len(m.rules) == 0

    def test_remove_nonexistent_returns_false(self):
        m = NotificationManager()
        assert m.remove_rule("ghost") is False

    def test_duplicate_rule_ids_both_stored(self):
        m = NotificationManager()
        m.add_rule(_rule("dup"))
        m.add_rule(_rule("dup"))
        assert len(m.rules) == 2
        # remove_rule removes only the FIRST match
        assert m.remove_rule("dup") is True
        assert len(m.rules) == 1
        assert m.remove_rule("dup") is True
        assert len(m.rules) == 0


class TestEvaluateEvent:
    """evaluate_event contract."""

    def test_no_rules_no_notifications(self):
        m = NotificationManager()
        assert m.evaluate_event({"a": 1}) == []

    def test_matching_rule_fires(self):
        m = NotificationManager()
        m.add_rule(_rule("r", conditions={"type": "new_bookmark"}))
        out = m.evaluate_event({"type": "new_bookmark"})
        assert len(out) == 1
        assert out[0].notification_type == NotificationType.NEW_BOOKMARK
        assert len(m.notifications) == 1

    def test_nonmatching_rule_does_not_fire(self):
        m = NotificationManager()
        m.add_rule(_rule("r", conditions={"type": "new_bookmark"}))
        assert m.evaluate_event({"type": "crawl_error"}) == []
        assert m.notifications == []

    def test_disabled_rule_does_not_fire(self):
        m = NotificationManager()
        m.add_rule(_rule("r", conditions={}, enabled=False))
        assert m.evaluate_event({}) == []

    def test_empty_event_fires_empty_condition_rule(self):
        m = NotificationManager()
        m.add_rule(_rule("r", conditions={}))
        out = m.evaluate_event({})
        assert len(out) == 1

    def test_cooldown_suppresses_second_fire(self):
        m = NotificationManager()
        m.add_rule(_rule("r", conditions={}, cooldown=300))
        first = m.evaluate_event({})
        assert len(first) == 1
        # immediately again -> within cooldown -> suppressed
        second = m.evaluate_event({})
        assert second == []
        assert len(m.notifications) == 1

    def test_cooldown_zero_always_fires(self):
        m = NotificationManager()
        m.add_rule(_rule("r", conditions={}, cooldown=0))
        assert len(m.evaluate_event({})) == 1
        assert len(m.evaluate_event({})) == 1
        assert len(m.notifications) == 2

    def test_multiple_matching_rules_all_fire(self):
        m = NotificationManager()
        m.add_rule(_rule("a", conditions={}))
        m.add_rule(_rule("b", conditions={}))
        out = m.evaluate_event({})
        assert len(out) == 2
        assert {n.notification_id for n in out} == {"notif-1", "notif-2"}

    def test_unicode_event_data_preserved(self):
        m = NotificationManager()
        m.add_rule(_rule("r", conditions={}))
        out = m.evaluate_event({"title": "café", "url": "https://x/日本語"})
        assert out[0].data == {"title": "café", "url": "https://x/日本語"}


class TestDeliveryState:
    """get_undelivered / mark_delivered / mark_all_delivered contract."""

    def _seed(self, n: int) -> NotificationManager:
        m = NotificationManager()
        for i in range(n):
            m.add_rule(_rule(f"r{i}", conditions={}))
        m.evaluate_event({})
        return m

    def test_get_undelivered_all_when_none_delivered(self):
        m = self._seed(3)
        assert len(m.get_undelivered()) == 3

    def test_mark_delivered_existing(self):
        m = self._seed(2)
        nid = m.notifications[0].notification_id
        assert m.mark_delivered(nid) is True
        assert m.notifications[0].delivered is True
        assert m.notifications[0].delivered_at is not None
        assert len(m.get_undelivered()) == 1

    def test_mark_delivered_nonexistent_returns_false(self):
        m = self._seed(1)
        assert m.mark_delivered("ghost") is False

    def test_mark_delivered_idempotent(self):
        m = self._seed(1)
        nid = m.notifications[0].notification_id
        assert m.mark_delivered(nid) is True
        # second call: still found, still True, no crash
        assert m.mark_delivered(nid) is True
        assert len(m.get_undelivered()) == 0

    def test_mark_all_delivered_counts_only_undelivered(self):
        m = self._seed(3)
        m.mark_delivered(m.notifications[0].notification_id)
        # 2 remain undelivered
        assert m.mark_all_delivered() == 2
        assert m.get_undelivered() == []

    def test_mark_all_delivered_idempotent(self):
        m = self._seed(2)
        assert m.mark_all_delivered() == 2
        assert m.mark_all_delivered() == 0


class TestGetRecent:
    """get_recent contract (negative-slice floor via abs)."""

    def _seed(self, n: int) -> NotificationManager:
        m = NotificationManager()
        for i in range(n):
            m.add_rule(_rule(f"r{i}", conditions={}))
        m.evaluate_event({})
        return m

    def test_default_limit(self):
        m = self._seed(15)
        assert len(m.get_recent()) == 10  # default limit=10

    def test_zero_limit_returns_all(self):
        m = self._seed(5)
        assert len(m.get_recent(limit=0)) == 5

    def test_negative_limit_uses_abs_floor(self):
        m = self._seed(10)
        # -abs(-3) = last 3
        assert len(m.get_recent(limit=-3)) == 3
        # negative larger than population -> all
        assert len(m.get_recent(limit=-100)) == 10

    def test_positive_limit(self):
        m = self._seed(10)
        assert len(m.get_recent(limit=4)) == 4

    def test_type_filter_narrows_before_slice(self):
        m = NotificationManager()
        m.add_rule(_rule("a", ntype=NotificationType.NEW_BOOKMARK, conditions={}))
        m.add_rule(_rule("b", ntype=NotificationType.CRAWL_ERROR, conditions={}))
        m.add_rule(_rule("c", ntype=NotificationType.NEW_BOOKMARK, conditions={}))
        m.evaluate_event({})
        assert len(m.get_recent(notification_type=NotificationType.NEW_BOOKMARK)) == 2
        assert len(m.get_recent(notification_type=NotificationType.CRAWL_ERROR)) == 1
        # filter + limit
        assert len(m.get_recent(limit=1, notification_type=NotificationType.NEW_BOOKMARK)) == 1


class TestClearOld:
    """clear_old contract."""

    def _mk(self, ts: datetime) -> Notification:
        return Notification(
            notification_id=f"n-{ts.isoformat()}",
            notification_type=NotificationType.TAG_ADDED,
            title="t", message="m", timestamp=ts,
        )

    def test_clear_old_removes_only_older(self):
        m = NotificationManager()
        base = _now()
        m.notifications = [
            self._mk(base - timedelta(hours=3)),
            self._mk(base - timedelta(hours=1)),
            self._mk(base),
        ]
        removed = m.clear_old(base - timedelta(hours=2))
        assert removed == 1
        assert len(m.notifications) == 2

    def test_clear_old_idempotent(self):
        m = NotificationManager()
        base = _now()
        m.notifications = [self._mk(base - timedelta(hours=5))]
        assert m.clear_old(base) == 1
        assert m.clear_old(base) == 0
        assert m.notifications == []

    def test_clear_old_none_older(self):
        m = NotificationManager()
        base = _now()
        m.notifications = [self._mk(base)]
        assert m.clear_old(base - timedelta(hours=1)) == 0
        assert len(m.notifications) == 1


class TestFormatMessage:
    """_format_message contract."""

    def test_name_only_when_no_known_keys(self):
        m = NotificationManager()
        r = _rule("r", name="MyRule")
        assert m._format_message(r, {"other": 1}) == "MyRule"

    def test_appends_known_keys_in_order(self):
        m = NotificationManager()
        r = _rule("r", name="MyRule")
        msg = m._format_message(r, {"title": "T", "url": "U", "message": "M"})
        assert msg == "MyRule. title: T. url: U. message: M"

    def test_unicode_preserved(self):
        m = NotificationManager()
        r = _rule("r", name="R")
        msg = m._format_message(r, {"title": "café"})
        assert msg == "R. title: café"

    def test_empty_event_name_only(self):
        m = NotificationManager()
        r = _rule("r", name="R")
        assert m._format_message(r, {}) == "R"


class TestEndToEndCLI:
    """End-to-end CLI run (the installed console entry point).

    content_notifications is not wired to a CLI subcommand, so the e2e run
    exercises the installed CLI's `init` command to prove the console entry
    point resolves and runs green in this environment.
    """

    def test_cli_init_runs_green(self, tmp_path):
        runner = CliRunner()
        dd = str(tmp_path / "data")
        result = runner.invoke(main, ["init", "--data-dir", dd])
        assert result.exit_code == 0, result.output
