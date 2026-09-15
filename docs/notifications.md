# notifications — spec

> **DEAD MODULE — 0 importers.** `personal_index/notifications.py` is never
> imported or registered anywhere in `personal_index/` (witness:
> `grep -rn 'import notifications\|from personal_index.notifications\|from
> .notifications' personal_index/ --include=*.py` returns nothing). It is a
> dead parallel implementation. Its only consumers are the test suite
> (`tests/test_notifications.py`, `tests/deep/test_zero_cap_eviction_sweep_adversarial.py`).
>
> **NEAR-NAME-COLLISION DISAMBIGUATION.** This page documents
> `personal_index/notifications.py` (the **dispatch** system: handlers +
> `notify()`). It is a DIFFERENT module from
> `personal_index/content_notifications.py` (the **record-and-track** system:
> rules + `delivered` flag), which is covered by
> [content-notifications.md](content-notifications.md). The two modules share
> the class names `Notification` and `NotificationManager` but have
> **divergent, incompatible contracts** — do not conflate them. The live
> twin is `content_notifications` (imported by the pipeline); this module is
> dead.

## Purpose

A standalone notification **dispatch** system: build a `Notification`, attach
one or more `NotificationHandler`s, and `notify()` fans the notification out
to every handler. This is a dispatch model — the opposite of the live
twin's record-and-track model (which stores notifications and toggles a
`delivered` flag without ever sending).

## Public API

### Enums
- `NotificationLevel` (notifications.py:20) — `INFO/WARNING/ERROR/CRITICAL`
  (str values `info/warning/error/critical`).
- `NotificationType` (notifications.py:28) — 10 members
  (`CRAWL_COMPLETE`, `CRAWL_ERROR`, `SEARCH_HIT`, `NEW_CONTENT`,
  `INTEREST_MATCH`, `BACKUP_COMPLETE`, `BACKUP_ERROR`, `SCHEDULE_TRIGGER`,
  `RATE_LIMIT`, `STORAGE_FULL`).

### `Notification` (dataclass, notifications.py:43)
Fields: `notification_id: str = ""`, `notification_type: str = ""`,
`level: str = "info"`, `title: str = ""`, `message: str = ""`,
`timestamp: str = ""`, `metadata: dict[str, Any] = {}`, **`read: bool = False`**.
- `__post_init__` (notifications.py:54) — fills `timestamp` (UTC isoformat)
  and `notification_id` (`notif_<ms>_<id%10000>`) when empty.
- `to_dict()` (notifications.py:60) — `asdict(self)`.
- `from_dict(cls, data)` (notifications.py:69) — `cls(**data)`.

> **Divergence from the live twin.** The live twin's `Notification`
> (content_notifications.py:77) uses `notification_type: NotificationType`
> (an **Enum**, not a str), `channels: list[NotificationChannel]`,
> `data: dict`, **`delivered: bool`**, and **`delivered_at: datetime | None`**.
> This module's `Notification` uses a **str** `notification_type`, a
> `level: str`, a `metadata` dict, and a bare **`read: bool`** with **no
> delivery timestamp**. The two `Notification` types are not
> interchangeable.

### `NotificationHandler` (ABC, notifications.py:81)
Abstract `handle(notification) -> bool` and `close() -> None`.

Concrete handlers:
- `ConsoleHandler` (notifications.py:93) — `handle` logs via `logger.info`
  with a level prefix; always returns `True`.
- `FileHandler` (notifications.py:122) — `handle` appends
  `json.dumps(notification.to_dict())` to `~/.personal_index/notifications.log`
  (a real filesystem side effect); returns `False` on `OSError`.
- `InMemoryHandler` (notifications.py:150) — `handle` appends to an internal
  list, evicting to the last `max_size` entries (or clearing entirely when
  `max_size <= 0`). Accessors: `get_all()` (notifications.py:173),
  `get_unread()` (notifications.py:181), `mark_all_read()` (notifications.py:189),
  `clear()` (notifications.py:202), `close()` (notifications.py:212).

### `NotificationManager` (notifications.py:217)
- `add_handler(handler)` (notifications.py:224) /
  `remove_handler(handler) -> bool` (notifications.py:228).
- `add_filter(fn)` (notifications.py:235) — a notification is dispatched only
  if **all** filters return truthy.
- `notify(notification) -> int` (notifications.py:239) — dispatches to every
  handler, returns the count of handlers whose `handle()` returned `True`;
  a handler exception is logged and skipped.
- Convenience emitters: `notify_crawl_complete` (notifications.py:252),
  `notify_crawl_error` (notifications.py:262), `notify_new_content`
  (notifications.py:272), `notify_interest_match` (notifications.py:282).
- `close()` (notifications.py:292) — closes and clears all handlers.

## Invariants

1. `notify()` returns the number of handlers that reported success, not a
   boolean; a failing handler is logged and does not abort the fan-out.
2. Filters are conjunctive: with one or more filters, a notification is
   dispatched only if every filter passes; with no filters it always
   dispatches.
3. `InMemoryHandler` bounds its list to `max_size` (most-recent kept);
   `max_size <= 0` clears the list on every `handle`.

## Known contract holes

- **ARCH-106** — the dead module's `Notification.read` flag is a bare boolean
  with **no delivery timestamp**, diverging from the live twin's
  `delivered` + `delivered_at` contract: `InMemoryHandler.mark_all_read()`
  (notifications.py:189) sets `read = True` but never stamps a time, so the
  read-state is untimestamped, unlike the live twin's
  `mark_all_delivered()` (content_notifications.py:202) which stamps
  `delivered_at`. See tickets/ARCH-106.md.
