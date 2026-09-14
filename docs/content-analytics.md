# Content Analytics (`personal_index.content_analytics`)

In-memory analytics over a flat list of content items. The module exposes one
class, `ContentAnalytics`, that accumulates `dict` items and computes tag
counts, title/description length statistics, link ratios, and tag
distributions. It is a pure in-memory aggregator: there is no persistence, no
serialization (`to_dict`/`from_dict`), no validation of item shape, and no
dedup. It is currently referenced only by its tests — no production module in
`personal_index/` imports it (see Secondary notes).

## Public API

### `ContentAnalytics`

    class ContentAnalytics:
        def __init__(self) -> None
        def add_items(self, items: list[dict[str, Any]]) -> None
        @property
        def total_items(self) -> int
        def get_tag_counts(self) -> dict[str, int]
        @staticmethod
        def _text_length(value: Any) -> int
        def get_title_lengths(self) -> list[int]
        def get_avg_title_length(self) -> float
        def get_description_lengths(self) -> list[int]
        def get_avg_description_length(self) -> float
        def get_items_with_links(self) -> list[dict[str, Any]]
        def get_link_ratio(self) -> float
        def get_tag_distribution(self) -> dict[str, float]
        def get_items_by_tag(self, tag: str) -> list[dict[str, Any]]
        def get_unique_tags_count(self) -> int
        def clear(self) -> None

- `__init__()`: `self._items: list[dict[str, Any]] = []`. No arguments, no
  pre-seeding.
- `add_items(items)`: `self._items.extend(items)`. **Appends the dicts by
  reference** — no copy, no validation, no dedup. Adding the same dict object
  twice stores two references to it; adding two distinct dicts with the same
  `id` is allowed (no uniqueness constraint). Returns `None`.
- `total_items` (property): `len(self._items)`.
- `get_tag_counts()`: builds a `Counter` over the `tags` of every item and
  returns `dict(counter)`. **Only a `list` `tags` value is counted** — the
  body does `tags = item.get("tags", [])` then `if isinstance(tags, list):
  counter.update(tags)`. A missing `tags` key, a `None` value, and a
  **non-list** value (e.g. the string `"abc"`) are all **ignored**. Duplicate
  tags within one item are each counted (`["a", "a", "a"]` → `{"a": 3}`);
  unicode tags are counted verbatim.
- `_text_length(value)` (staticmethod): `None` → `0`; any other value →
  `len(str(value))`. A **present `None`** counts as no text (0); a **missing**
  key also yields `0` because `item.get("title")` returns `None`. A non-string
  value is coerced via `str()` first (e.g. `123` → `3`).
- `get_title_lengths()`: `[self._text_length(item.get("title")) for item in
  self._items]` — one int per item, in insertion order.
- `get_avg_title_length()`: `0.0` when there are no items; otherwise
  `sum(lengths) / len(lengths)`.
- `get_description_lengths()` / `get_avg_description_length()`: identical
  shape to the title variants, reading the `description` key.
- `get_items_with_links()`: `[item for item in self._items if item.get("link")]`
  — returns the items whose `link` value is **truthy**. A missing `link` key,
  `None`, `""`, or `0` are all excluded. **Returns the stored dicts by
  reference** (see Contract Hole 2).
- `get_link_ratio()`: `0.0` when there are no items; otherwise
  `len(get_items_with_links()) / len(self._items)` — a float in `[0.0, 1.0]`.
- `get_tag_distribution()`: `total = sum(get_tag_counts().values())`; returns
  `{}` when `total == 0`; otherwise `{tag: count / total * 100 for ...}` —
  percentages that sum to `100.0`. Because it derives from `get_tag_counts`,
  it inherits the same "only list `tags` are counted" rule.
- `get_items_by_tag(tag)`: `[item for item in self._items if tag in
  (item.get("tags") or [])]`. A missing `tags` key or a `None` value is
  normalized to `[]` by the `or []` (so those items never match). **For a
  non-list `tags` value the `in` operator falls back to substring matching** —
  see Contract Hole 1. **Returns the stored dicts by reference** (see Contract
  Hole 2).
- `get_unique_tags_count()`: `len(get_tag_counts())` — the number of distinct
  tags that `get_tag_counts` would count (i.e. only list `tags`).
- `clear()`: `self._items.clear()`. Empties the internal list in place.
  Returns `None`. Idempotent (clearing an empty store is a no-op).

## Contract Holes

### Hole 1 — `get_items_by_tag` substring-matches a string `tags` value, diverging from `get_tag_counts` (ARCH-70)

The two tag methods disagree on how they treat a **non-list** `tags` value.

- `get_tag_counts` (line 26) guards with `if isinstance(tags, list)` before
  counting, so a string `tags` value is **ignored**. This is pinned by the
  existing deep test `test_non_list_tags_ignored`
  (`{"tags": "not-a-list"}` → `get_tag_counts() == {"a": 1}`, the string
  contributes nothing).
- `get_items_by_tag` (line 81) does `tag in (item.get("tags") or [])` with
  **no `isinstance` guard**. When `tags` is a **string**, Python's `in`
  operator performs **substring matching**: `"a" in "abc"` is `True`. So an
  item with `tags="abc"` **matches** `get_items_by_tag("a")`, `("b")`, and
  `("c")` — the very value that `get_tag_counts` ignores.

Consequence: the two tag methods give contradictory answers for the same item.
For `a.add_items([{"id": 1, "tags": "abc"}])`:
- `a.get_tag_counts()` → `{}` (the string is ignored).
- `a.get_items_by_tag("a")` → `[{"id": 1, "tags": "abc"}]` (substring match).

A caller that filters items by tag and then reports tag counts (or vice versa)
sees items that "have tag `a`" that the tag-count/distribution/unique-count
methods claim do not exist. This is a genuine correctness divergence, not a
stylistic one: substring matching on a tag field is almost certainly
unintended. This is the same "two methods disagree on the same input" class as
ARCH-66/67/68.

**Fix direction (implementer):** make the two agree. Preferred: guard
`get_items_by_tag` with the same `isinstance(tags, list)` check as
`get_tag_counts`, so a non-list `tags` value is ignored by **both** methods
(`get_items_by_tag("a")` on `tags="abc"` → `[]`). Add ONE pinning test that
feeds a string `tags` value and asserts both methods agree (see Pinning
tests). The existing deep tests `test_non_list_tags_ignored`,
`test_get_items_by_tag_returns_matching`, `test_get_items_by_tag_missing_tags_key`,
and `test_get_items_by_tag_none_tags_key` remain correct and must not change.

### Hole 2 — `get_items_with_links` / `get_items_by_tag` return shared references to the stored item dicts

Both `get_items_with_links` (line 64) and `get_items_by_tag` (line 81) return
the **same `dict` objects** held by `self._items` (list comprehensions over
`self._items`, no copy). A caller that mutates a returned item dict mutates
the stored item:

- `a.get_items_with_links()[0]["title"] = "tampered"` → the **stored** item's
  `title` is now `"tampered"`.
- `a.get_items_by_tag("a")[0]["tags"].append("z")` → the **stored** item's
  `tags` list now contains `"z"`.

This is the same "advertised safety not actually provided" class as ARCH-69
(`ContentChangelog.get_entries` shallow copy). It is documented here for
completeness; the ticket (ARCH-70) targets the more consequential Hole 1.

## Secondary notes

- **No production callers.** `grep -rn "ContentAnalytics" personal_index/`
  (excluding the module itself) returns only a `docs_dashboard_metadata.json`
  entry — no production Python module imports it. It is exercised only by
  `tests/test_content_analytics.py` and
  `tests/deep/test_content_analytics_adversarial.py`. It is a standalone
  utility with no wiring into the pipeline.
- **No `to_dict`/`from_dict`.** There is no serialization surface, so an
  analytics store cannot be persisted or reloaded.
- **Items are unvalidated dicts.** `add_items` accepts any `list[dict]`; there
  is no required-key check. Every accessor tolerates missing keys via
  `item.get(...)` (with `or []` / `or None` normalization), so a `{}` item
  contributes `0` to lengths, is excluded from link/tag results, and is
  counted in `total_items`.
- **`_text_length` coerces via `str()`.** A non-string `title`/`description`
  (e.g. an `int`) is measured as `len(str(value))`, not rejected.
- **`get_link_ratio` uses truthiness, not presence.** An item with
  `link=""` or `link=None` is not counted as "having a link" even though the
  key is present.
- **`clear` empties in place.** After `clear()`, prior `get_items_with_links`
  / `get_items_by_tag` results (which share the item dicts) still reference
  the same dicts, but the internal list is empty so subsequent queries return
  `[]`.
