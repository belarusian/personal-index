# Search facets (`personal_index.search_facets`)

Status: **spec** — audited against current code (cycle 175).

The in-memory faceted-search subsystem: three modules. `facet.py` holds the
data models (`FacetType`, `FacetValue`, `Facet`); `facet_builder.py` builds
facet dimensions from a document collection (`FacetBuilder`); `faceted_search.py`
is the search engine (`FacetedSearch`) plus its result container
(`SearchResults`). The package `__init__` re-exports all six names. The page
documents each method's **signature**, **exact behavior**, **guard paths** and
**return shape** — not every line verbatim.

## `facet.py` — data models

### `FacetType(Enum)`
Six members, each a string value: `CATEGORY="category"`, `TAG="tag"`,
`DATE="date"`, `STRING="string"`, `NUMBER="number"`, `BOOLEAN="boolean"`.
Used to tag a `Facet` with its dimension kind.

### `FacetValue` (dataclass)
Fields: `name: str`, `count: int = 0`.
- `to_dict() -> dict[str, Any]` — returns `{"name": self.name, "count":
  self.count}`.
- `from_dict(cls, data) -> FacetValue` (classmethod) — `name=data["name"]`
  (required), `count=data.get("count", 0)` (defaults to `0` when absent).

### `Facet` (dataclass)
Fields: `name: str`, `facet_type: FacetType = FacetType.STRING`,
`values: list[FacetValue] = field(default_factory=list)`.
- `add_value(name, count=1) -> None` — **guard path:** if a value with the
  same `name` already exists in `self.values`, its `count` is incremented in
  place (`existing.count += count`); it is never replaced. Otherwise a new
  `FacetValue(name, count)` is appended. `count` defaults to `1`. Mutates
  `self.values`; returns `None`.
- `sort_values() -> None` — sorts `self.values` in place by `count`
  descending (`reverse=True`); stable, so equal counts keep insertion order.
  Returns `None`.
- `to_dict() -> dict[str, Any]` — `{"name", "facet_type": self.facet_type.value,
  "values": [v.to_dict() ...]}` (facet_type serialized to its string value).
- `from_dict(cls, data) -> Facet` (classmethod) — `facet_type` defaults to
  `"string"` when absent and is coerced via `FacetType(ft)` when it is a str;
  `values` built from `data.get("values", [])`. `name` is required.
- `__eq__(other) -> bool` — returns `NotImplemented` for non-`Facet`;
  otherwise `self.name == other.name and self.facet_type == other.facet_type`.
  **Note:** equality ignores `values` (two facets with the same name + type are
  equal even with different value lists).

## `facet_builder.py` — `FacetBuilder`

`DEFAULT_FACET_TYPES: ClassVar[dict[str, FacetType]]` maps base field names to
types: `tags→TAG`, `category→CATEGORY`, `date→DATE`, `domain→STRING`,
`author→STRING`, `status→CATEGORY`, `score→NUMBER`, `enabled→BOOLEAN`.

### `build(items, facet_fields, max_values=50, facet_types=None) -> dict[str, Facet]`
- **guard path:** returns `{}` when `items` is empty.
- For each `field_name` in `facet_fields`: resolves the type (see
  `_resolve_facet_type`), extracts each item's values (see `_extract_values`),
  and stringifies every value (`str(value)`) before `add_value`.
- A field whose facet ends up with **no values** is skipped (absent from the
  result).
- Each included facet is sorted by count descending, then truncated to the top
  `max_values` (highest counts kept).
- Returns a dict mapping each included field name to its `Facet`.

### `aggregate(facets_a, facets_b) -> dict[str, Facet]`
- Result keys = union of both dicts' keys.
- Key in **both**: a new `Facet` is built (`facet_type` taken from `facets_a`)
  whose per-value counts are the **sum** of the two facets' counts, then
  re-sorted by count descending.
- Key in **only one**: that facet object is passed through **by reference**
  (not copied).
- Returns the merged dict.

### `_resolve_facet_type(field_name, custom_types) -> FacetType`
**Contract hole → ARCH-14.** Docstring is a blanket "Resolve the facet type
for a field." The actual resolution order is: (1) `custom_types` by full
`field_name`; (2) `custom_types` by base name (after the last `.`); (3) if that
string is a valid `FacetType` value, use it (a `ValueError` from
`FacetType(type_str)` is swallowed); (4) `DEFAULT_FACET_TYPES` by base name;
(5) `FacetType.STRING`.

### `_extract_values(item, field_name) -> list[Any]`
**Contract hole → ARCH-15.** Docstring is a blanket "Extract values from a
nested field path." Actual behavior: walks the dotted path through nested
dicts; if any intermediate value is not a dict, returns `[]`. At the leaf:
returns the list **as-is** if it is a list; wraps a non-`None` scalar in a
single-element list; returns `[]` for a missing key or a `None` leaf.

## `faceted_search.py` — `FacetedSearch` + `SearchResults`

### `SearchResults` (dataclass)
Fields: `results: list[dict]`, `facets: dict[str, Facet]`, `total: int = 0`,
`page: int = 1`, `page_size: int = 20`.
- `__getitem__(key) -> Any` — `getattr(self, key)` (dict-style access).
- `__contains__(key) -> bool` — `True` iff `key` is a str and is an attribute
  name; `False` otherwise.
- `keys() -> list[str]` — the hardcoded `["results", "facets", "total", "page",
  "page_size"]`.
- `to_dict() -> dict[str, Any]` — `facets` serialized via each `Facet.to_dict()`.

### `FacetedSearch`
State: `_documents: dict[str, dict]` (id → doc, with `id` injected), and a
`_facet_builder = FacetBuilder()`.

- `add_document(doc_id, data) -> None` — stores `{"id": doc_id, **data}` under
  `doc_id` (a later add with the same id overwrites).
- `remove_document(doc_id) -> None` — `pop(doc_id, None)`; a missing id is a
  no-op (no error).
- `get_documents() -> list[dict]` — `list(self._documents.values())` (a copy of
  the values list; the dicts themselves are shared).
- `get_available_facets() -> list[str]` — **Contract hole → ARCH-16.** Docstring
  is a blanket "Get list of available facet fields." Actual behavior: returns
  `[]` when there are no documents; otherwise inspects **only the first
  document** (`next(iter(...))`), skips the `id` key, and includes a field only
  if its value is a `list`, `str`, `int`, `float` or `bool` (nested dicts are
  excluded). Returns the sorted field names.
- `clear() -> None` — empties `_documents`.
- `_extract_text(doc) -> str` — concatenates every string value and every
  string item of list values, joined by a space and lowercased. Non-string
  scalars (int/float/bool) are excluded.
- `search(query, filters=None, facet_fields=None, page=1, page_size=20) ->
  SearchResults` — exact contract (already documented in the code):
  - `query.strip()` falsy → text filtering skipped (all docs considered);
    non-empty → keep docs sharing ≥1 query token, sorted by match score
    descending (score = matched query tokens / total query tokens).
  - `filters` truthy → AND-ed on top of the text results.
  - `total` = count after text + filter (before pagination).
  - pagination: `start = (page-1)*page_size`; `results = docs[start:start+page_size]`.
  - `facets` built from the **filtered** docs (not the paginated slice), only
    when `facet_fields` is truthy; else `{}`.
- `_apply_text_search(docs, query) -> list[dict]` — tokenizes the query and
  each doc's `_extract_text` with `[a-z0-9]+`; keeps docs with a non-empty
  token intersection, sorted by `len(intersection)/len(query_tokens)`
  descending.
- `_get_nested_value(doc, field_name) -> Any` — dotted-path lookup; returns
  `None` when a key is missing or an intermediate value is not a dict.
- `_matches_all_filters(doc, filters) -> bool` — **Contract hole →
  ARCH-17.** Docstring is a blanket "Check if a document matches all filters."
  Actual dispatch per `(field_name, filter_value)`:
  - `filter_value` is a **dict** → range/special operators via
    `_matches_range_filter` (must satisfy every operator present; a `None` doc
    value always fails).
  - `filter_value` is a **list** → if the doc value is a list, the two must
    share ≥1 element; otherwise the doc value must be `in` the list.
  - otherwise (scalar) → exact match, **case-insensitive for two strings**
    (`.lower()`), else `!=`.
  Returns `True` only if every filter passes.
- `_matches_range_filter(doc_value, filter_spec) -> bool` — `None` doc value →
  `False`; else the value (date-parsed when possible) must satisfy every
  present operator among `$between`, `$gte`, `$lte`, `$gt`, `$lt`, `$in`,
  `$not` (absent operators pass).
- `_parse_date_value(value) -> Any` — returns `value` for `datetime`/`int`/
  `float`; for a str, `datetime.fromisoformat(value)` on success else `None`;
  `None` for anything else. Callers treat `None` as the "not a date" sentinel.

## Contract holes

- `FacetBuilder._resolve_facet_type` blanket docstring (5-step resolution order
  not enumerated) → ARCH-14.
- `FacetBuilder._extract_values` blanket docstring (list/scalar/missing
  semantics not enumerated) → ARCH-15.
- `FacetedSearch.get_available_facets` blanket docstring ("first document only"
  + "excludes `id`/nested dicts" not stated) → ARCH-16.
- `FacetedSearch._matches_all_filters` blanket docstring (dict/list/scalar
  dispatch + case-insensitive string match not enumerated) → ARCH-17.
