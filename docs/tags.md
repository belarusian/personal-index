# tags — Exact Contract

Module: `personal_index/tags.py` (194 lines)

Tag/label system for organizing indexed pages. Two public types: `Tag`
(a 4-field `@dataclass`) and `TagStore` (persistent storage for tags and
their page associations, backed by a single JSON file at `store_path`).
There is no locking; `TagStore` is single-threaded by contract.

## Public API

### Tag

`@dataclass` with fields:

- `name: str`
- `color: str = "#3498db"`
- `description: str = ""`
- `created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())`
  — set to the current UTC ISO-8601 timestamp at construction time.

Equality / ordering are keyed on `name` only (color/description/created_at
are ignored):

- `__hash__(self) -> int` — `hash(self.name)`.
- `__eq__(self, other) -> bool` — `self.name == other.name` when `other` is
  a `Tag`, else `False`.
- `__lt__(self, other)` — `self.name < other.name` when `other` is a `Tag`,
  else `NotImplemented`.

So two `Tag` objects with the same name are equal and hash-equal regardless
of color/description/created_at; a `Tag` is never equal to a non-`Tag`.

### TagStore

`@dataclass` with fields:

- `store_path: str | None = None`
- `_tags: dict[str, Tag] = field(default_factory=dict, repr=False)` — the
  tag registry, keyed by name.
- `_page_tags: dict[str, set[str]] = field(default_factory=dict, repr=False)`
  — page associations, keyed by URL, value the set of tag names on that page.

`__post_init__(self)` — if `store_path` is set **and** the file exists,
calls `_load()`. A missing file or a `None` path leaves the store empty
(no error).

Private helpers (not part of the public contract, but they define the
persistence behavior):

- `_load(self) -> None` — no-op when `store_path` is falsy. Otherwise reads
  the JSON file; if the top-level value is not a dict it resets both
  `_tags` and `_page_tags` to empty and returns. Otherwise it rebuilds
  `_tags` from `data["tags"]` (each entry via `Tag(name, color, description,
  created_at)`, each defaulting to `#3498db`/`""`/`""`) and `_page_tags`
  from `data["page_tags"]`, converting each URL's list back to a `set`. On
  `json.JSONDecodeError`, `KeyError`, or `TypeError` it **silently resets
  both to empty** (no error, no log, no backup).
- `_save(self) -> None` — no-op when `store_path` is falsy. Otherwise
  `mkdir(parents=True, exist_ok=True)` on the parent, then writes
  `{"tags": {...}, "page_tags": {url: list(tags)}}` to the file with
  `json.dump(..., indent=2)`. Writes **directly to the target file** — no
  temp-file-and-rename, no fsync, no backup of the previous contents.

Tag registry:

- `create_tag(self, name: str, color: str = "#3498db", description: str = "") -> Tag`
  — constructs a fresh `Tag(name, color, description)` (so `created_at` is
  the **current** time) and assigns it to `self._tags[name]`, then `_save()`.
  If a tag with the same name already exists it is **replaced in place**:
  the new color/description/created_at win, and the tag's existing page
  associations in `_page_tags` are **preserved** (they key on the name, which
  is unchanged). Returns the new `Tag`.
- `get_tag(self, name: str) -> Tag | None` — `self._tags.get(name)`.
- `list_tags(self) -> list[Tag]` — `list(self._tags.values())` (insertion
  order, not sorted).
- `delete_tag(self, name: str) -> bool` — no-op returning `False` when the
  name is not registered. Otherwise deletes the tag, `discard`s the name
  from every page's tag set, `_save()`, returns `True`.

Page associations:

- `add_tag_to_page(self, url: str, tag_name: str) -> bool` — **auto-creates**
  the tag (with default color/description) if `tag_name` is not registered;
  creates the page's set if the URL is unseen; adds the name; `_save()`;
  always returns `True`.
- `remove_tag_from_page(self, url: str, tag_name: str) -> bool` — returns
  `True` only if the tag was actually present on the page (and removed it,
  then `_save()`); `False` when the page had no such tag (a no-op, no save).
- `get_tags_for_page(self, url: str) -> list[Tag]` — returns the `Tag`
  object for each recorded name that is **still registered**; a dangling
  name (recorded on the page but no longer in `_tags`) is silently dropped,
  so the result may be shorter than the recorded name set.
- `get_tags_for_url(self, url: str) -> list[Tag]` — alias for
  `get_tags_for_page`.
- `get_pages_for_tag(self, tag_name: str) -> list[str]` — returns `[]` when
  the tag is not registered; otherwise the list of URLs whose tag set
  contains the name (insertion order).
- `search_by_tag(self, tag_name: str) -> list[str]` — alias for
  `get_pages_for_tag`.

Counts / lifecycle:

- `get_tag_count(self) -> int` — `len(self._tags)`.
- `get_tagged_page_count(self) -> int` — number of URLs whose tag set is
  non-empty.
- `save(self) -> None` — public alias for `_save`.
- `remove_page(self, url: str) -> bool` — returns `False` when the URL is
  not in `_page_tags`; otherwise deletes the page's tag set, `_save()`,
  returns `True`.
- `clear(self) -> None` — clears both `_tags` and `_page_tags`, `_save()`.

## Contract Holes

**Primary hole — `create_tag`'s replace/overwrite semantic is
underspecified (ARCH-41).** The docstring says "Create a tag, or replace an
existing tag with the same name," but the body silently does three things on
a name collision that the contract never states:

1. It **overwrites** the existing tag's `color` and `description` with the
   new values (no merge, no error, no "already exists" signal).
2. It **resets `created_at` to the current time**, destroying the original
   creation timestamp — a caller updating a tag's color unknowingly rewrites
   its age.
3. It **preserves the tag's page associations** (they key on the name), so a
   "replace" is really a metadata overwrite that keeps the old links.

The fix must make this semantic explicit — either a distinct
`update_tag`/`rename` path that preserves `created_at`, or a documented
overwrite-with-fresh-timestamp default plus a guard that refuses (or warns
on) a silent replace — without changing the happy-path signature.

Secondary holes (same persistence class as ARCH-39/ARCH-40, not re-filed
here): `_save` is non-atomic (direct write, no temp-file-and-rename) and
`_load` silently resets the whole store to empty on `JSONDecodeError`/
`KeyError`/`TypeError`, so an interrupted write destroys the tag store with
no signal. Also: `add_tag_to_page` auto-creates a default tag as a side
effect (a caller that mistypes a tag name silently registers a new one), and
`get_tags_for_page` silently drops dangling names.
