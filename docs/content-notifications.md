# content-notifications — Exact Contract

Module: `personal_index/content_notifications.py` (252 lines, stdlib-only
imports: `dataclasses`, `datetime`, `enum`, `typing`).

Records content-related notifications (new bookmarks, score changes, crawl
results, digests, health warnings, …) and tracks their delivery state. Four
public types: `NotificationType` (an `Enum` of event kinds),
`NotificationChannel` (an `Enum` of delivery channels), `NotificationRule`
(a dataclass with a `matches` predicate), `Notification` (a dataclass with
`to_dict`), and `NotificationManager` (the engine: `add_rule` / `remove_rule`
/ `evaluate_event` / `get_undelivered` / `mark_delivered` /
`mark_all_delivered` / `get_recent` / `clear_old` plus the private
`_create_notification` / `_format_message`). There is **no** persistence layer
of its own: `NotificationManager` holds rules and notifications in in-memory
lists, and there is **no channel dispatch** — the `channels` field is recorded
metadata only, and the `delivered` flag is toggled purely by the caller. All
timestamps are timezone-aware UTC `datetime` objects.

## Public API

### NotificationType

`Enum`. Members (name → value string):

- `NEW_BOOKMARK = "new_bookmark"`
- `SCORE_CHANGE = "score_change"`
- `CRAWL_COMPLETE = "crawl_complete"`
- `CRAWL_ERROR = "crawl_error"`
- `TAG_ADDED = "tag_added"`
- `COLLECTION_UPDATED = "collection_updated"`
- `DIGEST_READY = "digest_ready"`
- `HEALTH_WARNING = "health_warning"`
- `BACKUP_COMPLETE = "backup_complete"`
- `SEARCH_RESULT = "search_result"`

### NotificationChannel

`Enum`. Members (name → value string):

- `LOG = "log"`
- `CONSOLE = "console"`
- `WEBHOOK = "webhook"`
- `EMAIL = "email"`
- `FILE = "file"`

These are **labels only**: nothing in the module (or the package) reads a
`NotificationChannel` to actually deliver a notification — see Contract Holes.

### NotificationRule

`@dataclass`. Fields (in order):

- `rule_id: str`
- `name: str`
- `notification_type: NotificationType`
- `channels: list[NotificationChannel] = field(default_factory=list)`
- `conditions: dict[str, Any] = field(default_factory=dict)`
- `enabled: bool = True`
- `cooldown_seconds: int = 300`

`matches(self, event: dict[str, Any]) -> bool`:

- Returns `False` immediately if `self.enabled` is `False`.
- Otherwise, for **every** `(key, value)` in `self.conditions.items()`,
  returns `False` if `event.get(key) != value`.
- Returns `True` only if **all** conditions match (logical AND). An empty
  `conditions` dict matches **any** event (as long as the rule is enabled).
- Matching is exact `!=` comparison of the event's value at `key` against the
  rule's expected `value`; there is no type coercion, no wildcard, no
  substring/regex, and no support for nested keys (a condition key is looked
  up with a single `event.get(key)`).

### Notification

`@dataclass`. Fields (in order):

- `notification_id: str`
- `notification_type: NotificationType`
- `title: str`
- `message: str`
- `timestamp: datetime`
- `channels: list[NotificationChannel] = field(default_factory=list)`
- `data: dict[str, Any] = field(default_factory=dict)`
- `delivered: bool = False`
- `delivered_at: datetime | None = None`

`to_dict(self) -> dict[str, Any]`: returns a fresh dict with exactly the keys
`notification_id`, `type`, `title`, `message`, `timestamp`, `channels`,
`data`, `delivered`, in that order. `type` is `self.notification_type.value`
(the string, not the enum member); `timestamp` is
`self.timestamp.isoformat()`; `channels` is `[c.value for c in self.channels]`
(a fresh list of value strings); `data` is the **same dict object** (not a
copy), so mutating the returned dict's `data` mutates the live notification.
Note `delivered_at` is **not** serialized by `to_dict` — only the boolean
`delivered` is.

### NotificationManager

Plain class (not a dataclass).

`__init__(self) -> None`: sets `self.rules: list[NotificationRule] = []`,
`self.notifications: list[Notification] = []`,
`self._last_sent: dict[str, datetime] = {}` (keyed by `rule_id`), and
`self._id_counter = 0`.

`add_rule(self, rule: NotificationRule) -> None`: appends `rule` to
`self.rules`. There is **no** duplicate-`rule_id` check; adding two rules with
the same `rule_id` is allowed and both will be evaluated (and both share the
same `_last_sent` cooldown slot — see Contract Holes).

`remove_rule(self, rule_id: str) -> bool`: removes the **first** rule whose
`rule_id` equals the argument (by index) and returns `True`; returns `False`
if no rule matches. If two rules share a `rule_id`, only the first is removed.

`evaluate_event(self, event: dict[str, Any]) -> list[Notification]`:

- `now = datetime.now(timezone.utc)` is computed once.
- For **each** rule in `self.rules` (in insertion order):
  - Skip if `rule.matches(event)` is `False` (disabled rule or condition
    mismatch).
  - Skip if the rule's cooldown has not elapsed: if
    `self._last_sent.get(rule.rule_id)` is set and
    `(now - last).total_seconds() < rule.cooldown_seconds`, skip.
  - Otherwise create a notification via `_create_notification(rule, event)`,
    append it to `self.notifications`, record `now` in
    `self._last_sent[rule.rule_id]`, and append it to the returned list.
- Returns the list of generated `Notification` objects (empty if no rule
  fired). **Every matching, non-cooldown rule fires independently** — there is
  no precedence, no "first match wins", and no deduplication, so one event can
  fan out into N notifications (one per matching rule). See Contract Holes.

`get_undelivered(self) -> list[Notification]`: returns a fresh list of all
notifications where `delivered` is `False`, in insertion order.

`mark_delivered(self, notification_id: str) -> bool`: finds the **first**
notification whose `notification_id` equals the argument, sets its
`delivered = True` and `delivered_at = datetime.now(timezone.utc)`, and
returns `True`; returns `False` if no notification matches. **No channel
dispatch happens** — marking delivered does not send anything anywhere.

`mark_all_delivered(self) -> int`: sets `delivered = True` and
`delivered_at = now` on every undelivered notification and returns the count
of notifications it flipped (already-delivered ones are untouched).

`get_recent(self, limit: int = 10,
notification_type: NotificationType | None = None) -> list[Notification]`:

- Starts from `self.notifications`; if `notification_type` is not `None`,
  filters to notifications whose `notification_type` equals it.
- Returns `filtered[-limit:]` — the **last** `limit` items in insertion order
  (i.e. the most recently appended, since notifications are only ever
  appended). `limit` is not validated: a negative `limit` yields
  `filtered[-limit:]` (Python negative-slice semantics), and `limit=0` yields
  `[]`.

`clear_old(self, older_than: datetime) -> int`:

- Keeps only notifications where `n.timestamp >= older_than` (a **strictly
  inclusive** lower bound: a notification whose `timestamp` exactly equals
  `older_than` is **kept**).
- Returns the number of notifications removed (`before - after`).
- `older_than` is compared directly against the timezone-aware UTC
  `timestamp`; passing a naive `datetime` raises `TypeError` (aware vs naive
  comparison).

### Private helpers (referenced for exact semantics)

- `_create_notification(self, rule: NotificationRule,
  event: dict[str, Any]) -> Notification`: increments `self._id_counter` by 1
  and returns `Notification(notification_id=f"notif-{self._id_counter}",
  notification_type=rule.notification_type, title=rule.name,
  message=self._format_message(rule, event),
  timestamp=datetime.now(timezone.utc), channels=rule.channels,
  data=event)`. Note `channels` is the **same list object** as
  `rule.channels` (not a copy), and `data` is the **same dict object** as the
  caller's `event` (not a copy) — mutating either on the returned notification
  mutates the rule / the caller's event.
- `_format_message(self, rule: NotificationRule, event: dict[str, Any]) ->
  str`: builds `parts = [rule.name]`, then for each `(key, value)` in
  `event.items()` where `key` is one of `("title", "url", "message")`
  appends `f"{key}: {value}"`. Returns `". ".join(parts)` if more than one
  part, else `parts[0]` (just the rule name). Only those three event keys are
  ever surfaced in the message; all other event keys are ignored.

## Contract Holes

### Primary hole: the "delivery" concept is unbacked — channels are recorded but never dispatched, and `delivered` is a caller-toggled flag with no actual delivery (ARCH-50)

The module presents itself as a notification *system* with a delivery
lifecycle (`NotificationChannel`, a `channels` field on both the rule and the
notification, `delivered` / `delivered_at`, `get_undelivered`,
`mark_delivered`, `mark_all_delivered`), but **no delivery is ever performed**:

- The module's own docstring states "no channel dispatch is performed."
  Nothing in `personal_index/content_notifications.py` — and nothing else in
  the package — reads a `NotificationChannel` to send a notification anywhere.
  `NotificationChannel` is a dead label: choosing `WEBHOOK` vs `EMAIL` vs
  `FILE` changes nothing observable.
- `mark_delivered` / `mark_all_delivered` flip `delivered` to `True` and stamp
  `delivered_at` **without sending anything**. There is no code path that
  transitions a notification to `delivered` as a *consequence* of an actual
  send; the only way a notification becomes "delivered" is for the caller to
  call the mark methods. A notification can therefore be reported as
  delivered while it has never been transmitted to any channel.
- `get_undelivered` is correspondingly meaningless as a "queue to send": it
  returns notifications that have not yet been *marked* delivered, not
  notifications that are pending an actual dispatch.

Because the public contract (the `NotificationManager` docstring — "tracks
their delivery state" — and the `Notification`/`NotificationRule` field
docstrings — "Channels to deliver to") implies that the `channels` field
drives real delivery and that `delivered` reflects a real send, a caller
cannot tell from the contract that the entire delivery lifecycle is
unbacked metadata. This is the single most important hole: the subsystem's
core promise (deliver content notifications through configured channels) is
not implemented at all, and the `delivered` flag gives a false signal that
delivery occurred.

The fix is to make the relationship explicit and either implement or remove
the delivery concept (state it in the `NotificationManager` docstring + this
page):

- **Option A (implement dispatch):** add a real dispatch step (e.g. a
  `deliver(notification)` / `dispatch_all()` method, or a pluggable
  channel-handler registry) that actually sends a notification to each of its
  `channels` and only then sets `delivered = True` / `delivered_at`. The
  `delivered` flag must then be a *consequence* of a real send, and
  `get_undelivered` becomes a genuine pending-send queue.
- **Option B (document it as record-only):** keep the current behavior and
  state explicitly in the `NotificationManager` docstring and
  `docs/content-notifications.md` that this module is a **record-and-track**
  store only — that `channels` is descriptive metadata with no dispatch
  backend, that `delivered` is a caller-managed flag (not evidence of a real
  send), and that any actual delivery must be performed by an external
  consumer that reads `get_undelivered()` and then calls `mark_delivered`.

Whichever option is chosen, the postcondition must hold and be stated: a
caller reading the `NotificationManager` docstring must know, without reading
the source, whether `delivered = True` means "actually sent to the channels"
or "marked by the caller with no send performed."

### Secondary notes (not ticketed)

- **Multiple-rule fan-out in `evaluate_event`:** every matching, non-cooldown
  rule fires independently — there is no precedence, no "first match wins",
  and no deduplication, so a single event can fan out into N notifications
  (one per matching rule). This is a defined behavior (not a hole), but the
  contract does not state that fan-out is unbounded or that the returned list
  is ordered by rule insertion order.
- **Shared `rule_id` cooldown slot:** `_last_sent` is keyed by `rule_id`, and
  `add_rule` performs no duplicate-`rule_id` check. Two rules added with the
  same `rule_id` share one cooldown slot, so firing one suppresses the other
  for `cooldown_seconds`; `remove_rule` removes only the first match. The
  contract does not state that `rule_id` must be unique.
- **Aliased collections:** `_create_notification` sets `channels` to the
  rule's `channels` list object and `data` to the caller's `event` dict object
  (both un-copied), and `Notification.to_dict` aliases the `data` dict — so
  mutating a notification's `channels`/`data` mutates the rule or the caller's
  event, and mutating the returned dict's `data` mutates the live
  notification.
- **`to_dict` omits `delivered_at`:** the serialized form carries the boolean
  `delivered` but not the `delivered_at` timestamp, so a round-trip through
  `to_dict` loses the delivery time.
- **`get_recent` negative/zero `limit`:** `limit` is not validated; a negative
  `limit` uses Python negative-slice semantics and `limit=0` returns `[]`.
- **`clear_old` boundary is inclusive:** a notification whose `timestamp`
  exactly equals `older_than` is kept (the filter is `n.timestamp >=
  older_than`), and passing a naive `older_than` against the timezone-aware
  `timestamp` raises `TypeError`.
