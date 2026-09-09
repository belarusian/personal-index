# ARCH-54 — content_feed: `to_dict`/`from_dict` must round-trip `max_items` and `feed_id`

Status: OPEN
Component: `personal_index/content_feed.py` — `FeedGenerator.to_dict` / `FeedGenerator.from_dict`
Umbrella: ARCH-2 (#983)
Issue: #1163
Docs: `docs/content-feed.md` (Contract holes)

## Problem
`FeedGenerator.to_dict()` serializes only `title`, `link`, `description`,
`language`, `ttl`, `generator`, `items` — it omits `max_items` and `feed_id`.
`FeedGenerator.from_dict()` reads only those same seven keys, so on a
round-trip `max_items` falls back to the dataclass default (`100`) and
`feed_id` falls back to `link` (via `__post_init__`). Consequences:

- A `FeedGenerator(max_items=10, ...)` that is serialized and re-loaded
  silently becomes `max_items=100`, so the item cap is lost and the next
  `add_item` keeps up to 100 items instead of 10.
- A `FeedGenerator(feed_id="custom", ...)` that is serialized and re-loaded
  silently becomes `feed_id=link`, so the Atom `<id>` element changes value —
  a feed identity that Atom consumers use for dedup/caching is no longer
  stable across a save/load cycle.
- The round-trip is therefore LOSSY for two of the nine dataclass fields, and
  nothing documents that constraint.

## Public contract (target)
`FeedGenerator.to_dict() -> dict` — the returned dict must include `max_items`
(int) and `feed_id` (str) in addition to the existing seven keys.
`FeedGenerator.from_dict(cls, data: dict) -> FeedGenerator` — must read
`max_items` (default `100`) and `feed_id` (default `""`, so `__post_init__`
still falls back to `link` when absent) and pass them to the constructor.
After the change, `FeedGenerator.from_dict(g.to_dict())` preserves
`max_items` and `feed_id` exactly (a lossless round-trip for all nine fields).

## Behavior
- Round-trip of a generator with default `max_items`/`feed_id`: unchanged
  (defaults are preserved either way).
- Round-trip of a generator with a non-default `max_items` (e.g. `10`): the
  re-loaded generator has `max_items == 10`.
- Round-trip of a generator with a non-default `feed_id` (e.g. `"custom"`):
  the re-loaded generator has `feed_id == "custom"`, and `generate(ATOM)`
  emits `<id>custom</id>`.
- `from_dict` on a dict that LACKS the two keys (e.g. produced by an older
  `to_dict`): falls back to `100` / `link` (backward-compatible; no error).

## Guard inputs
- Round-trip with `max_items` at the default (`100`) — preserved.
- Round-trip with `max_items` below the default (e.g. `10`) — preserved.
- Round-trip with `feed_id` explicitly set (e.g. `"custom"`) — preserved.
- Round-trip with `feed_id` left empty (falls back to `link`) — preserved.
- `from_dict` on a dict missing both keys (legacy payload) — no error,
  defaults applied.

## Acceptance criteria
1. For a `FeedGenerator` with non-default `max_items` and `feed_id`,
   `FeedGenerator.from_dict(g.to_dict())` has `max_items == g.max_items` and
   `feed_id == g.feed_id`.
2. `g.to_dict()` contains the keys `max_items` and `feed_id`.
3. After a round-trip, `generate(FeedFormat.ATOM)` emits the SAME `<id>`
   element as the original generator.
4. `from_dict` on a dict missing `max_items`/`feed_id` does not raise and
   yields `max_items == 100` and `feed_id == link`.
5. Existing `to_dict`/`from_dict` behavior for the seven previously-serialized
   fields is unchanged (existing tests still pass).

## Pinning tests to add
- `test_feed_generator_roundtrip_preserves_max_items_and_feed_id`: build
  `FeedGenerator(title="t", link="http://x", max_items=10, feed_id="custom")`,
  round-trip via `to_dict`/`from_dict`, assert `max_items == 10` and
  `feed_id == "custom"`.
- `test_feed_generator_roundtrip_atom_id_stable`: same generator, assert
  `generate(FeedFormat.ATOM)` contains `<id>custom</id>` both before and
  after the round-trip.
- `test_feed_generator_from_dict_missing_keys_defaults`: `from_dict` on a dict
  with only the seven legacy keys yields `max_items == 100` and
  `feed_id == link` (no exception).

## Docs update (same PR)
`docs/content-feed.md` — `FeedGenerator.to_dict` / `from_dict` entries: state
that both now include/restore `max_items` and `feed_id`, so the round-trip is
lossless for all nine fields. Remove/adjust the Contract-holes bullet for this
hole once merged.
