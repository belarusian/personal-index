# ARCH-50: content-notifications — channels are recorded but never dispatched, and `delivered` is a caller-toggled flag with no actual send

Status: CLAIMED (cycle 254, impl254/content-notifications-delivered-contract)
Component: `personal_index/content_notifications.py`
Issue: (to be filed)
Refs: ARCH-2 (#983 umbrella)

## Symptom

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

## Public contract (the fix must preserve the happy path)

- All public methods keep their current signatures and behavior:
  `NotificationType` / `NotificationChannel` (enums), `NotificationRule.matches`,
  `Notification.to_dict`, and `NotificationManager.__init__` / `add_rule` /
  `remove_rule` / `evaluate_event` / `get_undelivered` / `mark_delivered` /
  `mark_all_delivered` / `get_recent` / `clear_old`, plus the private
  `_create_notification` / `_format_message`.
- The relationship between the `delivered` flag and actual channel delivery
  must be made explicit (pick one and state it in the `NotificationManager`
  docstring + `docs/content-notifications.md`):
  - **Option A (implement dispatch):** add a real dispatch step (e.g. a
    `deliver(notification)` / `dispatch_all()` method, or a pluggable
    channel-handler registry) that actually sends a notification to each of
    its `channels` and only then sets `delivered = True` / `delivered_at`.
    The `delivered` flag must then be a *consequence* of a real send, and
    `get_undelivered` becomes a genuine pending-send queue.
  - **Option B (document it as record-only):** keep the current behavior and
    state explicitly in the `NotificationManager` docstring and
    `docs/content-notifications.md` that this module is a **record-and-track**
    store only — that `channels` is descriptive metadata with no dispatch
    backend, that `delivered` is a caller-managed flag (not evidence of a real
    send), and that any actual delivery must be performed by an external
    consumer that reads `get_undelivered()` and then calls `mark_delivered`.
- Whichever option is chosen, the postcondition must hold and be stated: a
  caller reading the `NotificationManager` docstring must know, without
  reading the source, whether `delivered = True` means "actually sent to the
  channels" or "marked by the caller with no send performed."

## Acceptance criteria

1. The happy path is unchanged: `evaluate_event` still fires every matching,
   non-cooldown rule (in insertion order), `get_undelivered` / `mark_delivered`
   / `mark_all_delivered` / `get_recent` / `clear_old` behave exactly as
   documented in `docs/content-notifications.md`, and `Notification.to_dict`
   keeps its exact key set and aliasing behavior.
2. The relationship between the `delivered` flag and actual channel delivery
   is stated in the `NotificationManager` docstring and in
   `docs/content-notifications.md` (Option A: `delivered = True` is set only
   after a real send to the notification's channels; Option B: `delivered` is
   a caller-managed flag with no dispatch backend and `channels` is
   descriptive metadata only).
3. If Option A: a notification's `delivered` is `False` until a dispatch step
   has actually sent it to each of its `channels`, and `get_undelivered`
   returns exactly the notifications not yet sent; a notification with an
   empty `channels` list has a defined, documented outcome (e.g. immediately
   delivered, or left undelivered — stated explicitly).
4. If Option B: the docstring and the docs page both state that no dispatch
   backend exists, that `delivered` is caller-managed, and that any real
   delivery is the responsibility of an external consumer — and no
   caller-facing API implies that `delivered = True` means a real send
   occurred.

## Pinning tests to add (tests/test_content_notifications.py)

- `test_evaluate_event_fires_all_matching_rules` (happy path) — two enabled
  rules whose conditions both match one event yield two notifications in
  insertion order; pins the current fan-out behavior so the fix does not
  change clean multi-rule input.
- `test_delivered_flag_semantics` (the contract hole) — after
  `mark_delivered`, the notification's `delivered` is `True` and
  `delivered_at` is set, and the test asserts the documented meaning of that
  flag: under Option A it also asserts a real send was performed (e.g. a
  handler was invoked for each channel); under Option B it asserts the
  docstring states no send occurred and that `channels` is metadata only. This
  single test pins the whole contract hole.
- `test_get_undelivered_is_pending_queue` (guard path) — with a mix of
  delivered and undelivered notifications, `get_undelivered` returns exactly
  the undelivered ones in insertion order; under Option A this is the
  pending-send queue, and the test pins that it does not include
  already-sent notifications.

## Docs update (same PR)

`docs/content-notifications.md` "Contract Holes" section (already authored in
this PR) names this as the primary hole; the implementer must update the
`NotificationManager` entry in the "Public API" section to state the chosen
delivered-vs-dispatch relationship once implemented.
