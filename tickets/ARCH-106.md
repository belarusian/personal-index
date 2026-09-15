# ARCH-106 — notifications.py `Notification.read` is a bare boolean with no delivery timestamp, diverging from the live twin's `delivered` + `delivered_at` contract

- **Status:** OPEN
- **Kind:** ARCH (architect-authored contract; implementer claims/implements; validator verifies; architect closes)
- **Component:** personal_index/notifications.py (DEAD module — 0 importers; see docs/notifications.md) + personal_index/content_notifications.py (the live record-and-track twin it was meant to mirror)
- **Issue:** #<TBD>

## Symptom

`notifications.py` is a dead parallel implementation of the notification
system: it is never imported anywhere in `personal_index/` (witness below),
and it is a **dispatch** system (handlers + `notify()`) where the live twin
`content_notifications.py` is a **record-and-track** system (rules +
`delivered` flag, no dispatch). The two modules share the class names
`Notification` and `NotificationManager` but their contracts have silently
diverged.

The concrete, verifiable hole is the **read/delivery-state contract**:

1. The dead module's `Notification` carries a bare **`read: bool = False`**
   (notifications.py:52) and **no delivery timestamp field at all**.
2. `InMemoryHandler.mark_all_read()` (notifications.py:189) sets
   `n.read = True` and returns a count — it never stamps a time.
3. The live twin's `Notification` carries **`delivered: bool`**
   (content_notifications.py:99) **and `delivered_at: datetime | None`**
   (content_notifications.py:100), and its `mark_all_delivered()`
   (content_notifications.py:202) sets `delivered = True` **and stamps
   `delivered_at = datetime.now(timezone.utc)`** (content_notifications.py:208)
   on every transition.

So the dead module's "read" state is **untimestamped** while the live twin's
"delivered" state is **timestamped**. A consumer that mirrors the live
twin's contract (reading `delivered_at` to know *when* a notification was
consumed) cannot do so against the dead module: the field does not exist, and
`mark_all_read()` does not record a time. This is the dead-module +
divergent-contract class (ARCH-100/102/105 pattern): the module ships a
public `read`/`mark_all_read` API whose contract (timestamped consumption
state) it does not fulfill, and which is incompatible with the live twin it
was meant to mirror.

## Evidence (file:line)

DEAD-MODULE witness:
- `grep -rn 'import notifications\|from personal_index.notifications\|from .notifications\|from personal_index import notifications' personal_index/ --include=*.py`
  returns **nothing** (rc=1) — notifications.py is never wired.
- Its only consumers are tests: `tests/test_notifications.py:10`
  (`from personal_index.notifications import ...`) and
  `tests/deep/test_zero_cap_eviction_sweep_adversarial.py:30`
  (`from personal_index.notifications import InMemoryHandler, Notification`).

Dead-module read-state (untimestamped):
- personal_index/notifications.py:52 — `read: bool = False` (the only
  consumption-state field; no `*_at` timestamp field exists on the dataclass).
- personal_index/notifications.py:189 — `def mark_all_read(self) -> int:`.
- personal_index/notifications.py:193-196 — body sets `n.read = True` and
  increments `count`; **no timestamp is written**.
- personal_index/notifications.py:181 — `get_unread()` filters on `not n.read`.

Live-twin read-state (timestamped) — the contract the dead module diverges from:
- personal_index/content_notifications.py:99 — `delivered: bool = False`.
- personal_index/content_notifications.py:100 — `delivered_at: datetime | None = None`.
- personal_index/content_notifications.py:202 — `def mark_all_delivered(self) -> int:`.
- personal_index/content_notifications.py:207-208 — body sets
  `n.delivered = True` **and** `n.delivered_at = datetime.now(timezone.utc)`.
- personal_index/content_notifications.py:197-198 — `mark_delivered` does the
  same stamp for a single notification.

## Proposed fix (implementer)

Two acceptable resolutions; pick one and record it in the ticket:

(a) **Align the dead module to the live twin's contract** (preferred if the
    module is ever revived): add a `read_at: datetime | None = None` field to
    `Notification` (notifications.py:43) and stamp it in
    `InMemoryHandler.mark_all_read()` (notifications.py:189) exactly as the
    live twin stamps `delivered_at` — so the read-state is timestamped and
    the two `Notification` types' consumption-state contracts agree.

(b) **Explicitly defer / document the divergence** (if the module stays dead):
    keep `read` untimestamped but state in the `Notification` docstring and in
    docs/notifications.md that `read` is a bare, untimestamped flag and is
    intentionally NOT the live twin's `delivered`/`delivered_at` contract —
    so a future reader does not assume the two are interchangeable.

Either way, the docs/notifications.md "Known contract holes" entry must
reflect the chosen resolution.

## Acceptance criteria

- [ ] The dead-module status (0 importers) is stated in docs/notifications.md
      header (done in this PR) and in this ticket.
- [ ] The near-name distinction from `content_notifications.py` is stated in
      the page header (done in this PR).
- [ ] The `read` (untimestamped) vs `delivered`+`delivered_at` (timestamped)
      divergence is pinned with file:line evidence (above).
- [ ] A resolution (a) or (b) is chosen and the docs page updated to match.
- [ ] Pinning test (implementer, tests/** — NOT the architect's path): one
      behavior test that constructs a `Notification`, calls
      `InMemoryHandler.mark_all_read()`, and asserts the read-state contract
      the chosen resolution states — for (a) assert `read_at` is a non-None
      `datetime` after `mark_all_read()` (guard path: a fresh unread
      notification has `read_at is None`); for (b) assert `read` is `True`
      and that no `read_at`/`delivered_at` attribute is set, pinning the
      documented divergence.

## Self-review checklist (architect)

- [x] Component + public contract (signature, behavior, error paths, guard
      inputs) stated.
- [x] Acceptance criteria present.
- [x] Pinning test specified (implementer's to write; architect never writes
      tests/**).
- [x] Matching docs/notifications.md update shipped in the SAME PR.
- [x] DEAD-MODULE witness (0 importers) recorded.
- [x] Near-name-collision disambiguation (notifications vs
      content_notifications) recorded.
- [x] No personal_index/** or tests/** written by the architect.
