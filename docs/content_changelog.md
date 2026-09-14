# Content Changelog (`personal_index.content_changelog`)

In-memory change-log for content items. The module exposes one dataclass
(`ChangeEntry`) and one container (`ContentChangelog`) that records, filters,
and clears change entries. It is a pure in-memory store: there is no
persistence, no serialization (`to_dict`/`from_dict`), no timestamp
normalization, and no validation of `change_type`/`timestamp`/`url` values.
It is currently referenced only by its tests — no production module in
`personal_index/` imports it (see Secondary notes).

## Public API

### `ChangeEntry`

    @dataclass
    class ChangeEntry:
        url: str
        change_type: str
        timestamp: str
        details: dict[str, Any] = field(default_factory=dict)

- A plain `@dataclass` (not `frozen`, not `kw_only`). All four fields are
  positional-or-keyword; only `details` has a default.
- `details` uses `field(default_factory=dict)`, so each entry gets its **own**
  `details` dict (no shared mutable default).
- **No runtime type enforcement.** The `str` annotations on `url` /
  `change_type` / `timestamp` are not checked at construction: `None`, an
  `int`, or any other object is accepted and stored verbatim (a plain
  `@dataclass` does not validate). `details` is likewise not checked to be a
  `dict`.

### `ContentChangelog`

    class ContentChangelog:
        def __init__(self) -> None
        def add_entry(self, entry: ChangeEntry) -> None
        def get_entries(self, url: str | None = None) -> list[ChangeEntry]
        def clear(self) -> None

- `__init__()`: `self._entries: list[ChangeEntry] = []`. No arguments, no
  pre-seeding.
- `add_entry(entry)`: `self._entries.append(entry)`. **Appends the object by
  reference** — no copy, no validation, no dedup. Adding the same object twice
  stores two references to it; adding two distinct entries with the same `url`
  is allowed (no uniqueness constraint). Returns `None`.
- `get_entries(url=None)`:
  - **`url` truthy** → returns `[e for e in self._entries if e.url == url]` —
    a **new list** of the entries whose `e.url` **exactly equals** `url`
    (exact string match, not substring or prefix).
  - **`url` falsy** (`None` or `""`) → returns `list(self._entries)` — a new
    list of **all** entries.
  - **Guard inputs:** an empty changelog returns `[]` in both cases. A
    whitespace-only `url` (e.g. `" "`) is truthy, so it filters (and matches
    nothing unless an entry's `url` is literally `" "`).
  - **Enforced copy contract (shallow):** the returned list is a NEW
    shallow copy of the internal list — the list container is always a
    fresh object, but the `ChangeEntry` objects inside it and their
    `details` dicts are **shared references** to the stored entries.
    Mutating a returned entry or its `details` dict mutates the stored
    entry. This is the documented contract (see former Contract Hole 1,
    now enforced by the docstring and pinning tests).
- `clear()`: `self._entries.clear()`. Empties the internal list in place.
  Returns `None`. Idempotent (clearing an empty changelog is a no-op).

## Contract Holes

### Hole 1 (RESOLVED) — `get_entries` returns a shallow copy: entry objects and `details` dicts are shared (ARCH-69)

`get_entries`'s docstring says it returns "A NEW list of ``ChangeEntry``
objects (a copy, not the internal list)". That is **true only of the list
container**. The returned list is a shallow copy: the `ChangeEntry` instances
inside it are the **same objects** held by `self._entries`, and each entry's
`details` dict is the **same dict** object. This is pinned by the existing
deep tests `test_entry_identity_preserved_in_get` (`entries[0] is e`) and
`test_details_dict_is_shared_reference` (`entries[0].details is details`).

Consequence: the "copy" wording over-promises safety. A caller that mutates a
returned entry corrupts the internal store:

- `cl.get_entries()[0].details["k"] = "v"` → the **stored** entry's `details`
  now contains `"k": "v"` (same dict object).
- `cl.get_entries()[0].change_type = "tampered"` → the **stored** entry's
  `change_type` is now `"tampered"` (same object).
- `cl.get_entries("http://x.com")[0].url = "http://y.com"` → the stored
  entry's `url` changes, so a subsequent `get_entries("http://x.com")` no
  longer matches it.

The docstring's "a copy, not the internal list" reads as "mutating the result
is safe," which is false for the entry objects and their `details` dicts. This
is the same "advertised safety not actually provided" class as ARCH-66/67/68.

**Resolved (ARCH-69):** the `get_entries` docstring now states the exact
shallow-copy contract — the list is a new shallow copy, but the
`ChangeEntry` objects and their `details` dicts are shared references — and
the pinning tests `test_get_entries_shallow_copy_details_shared`,
`test_get_entries_empty_changelog_returns_empty_list`, and
`test_get_entries_falsy_url_returns_all_shallow` pin that behavior. The
docstring, the code, and the tests now all agree.

## Secondary notes

- **No production callers.** `grep -rn "ContentChangelog\|ChangeEntry"
  personal_index/` (excluding the module itself) returns nothing — the module
  is exercised only by `tests/test_content_changelog.py` and
  `tests/deep/test_content_changelog_adversarial.py`. It is a standalone
  utility with no wiring into the pipeline.
- **No `to_dict`/`from_dict`.** Unlike most sibling content modules, there is
  no serialization surface, so a changelog cannot be persisted or reloaded.
- **No `change_type` vocabulary.** `change_type` is an unconstrained `str`;
  the tests use `"added"`/`"modified"`/`"deleted"`/`"v1"`/`"v2"` but the code
  accepts any value (including `None`).
- **`timestamp` is not parsed or normalized.** It is stored verbatim as a
  `str`; no ISO-8601 validation, no ordering guarantee. Entries are returned
  in insertion order (append order), not timestamp order.
- **`add_entry` is not idempotent and has no cap.** Repeated adds grow the
  list unboundedly; there is no size limit, no dedup, and no overwrite-by-url
  semantics.
- **`clear` empties in place.** After `clear()`, prior `get_entries` results
  (which share the entry objects) still reference the same `ChangeEntry`
  objects, but the internal list is empty so subsequent `get_entries()`
  returns `[]`.
