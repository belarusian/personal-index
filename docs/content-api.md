# Content API (`personal_index.content_api`)

REST-style request/response handler for content operations. The module exposes
a framework-agnostic entry point — `handle_request(method, path, body,
query_string) -> (status, payload)` — that callers adapt to their own HTTP
framework. There is no real socket, no WSGI/ASGI binding, and no routing
framework: routing is a hand-rolled `if/elif` chain over `urlparse`-derived
path parts.

## Public API

### `ContentAPI`

    class ContentAPI:
        def __init__(self, storage: dict[str, Any] | None = None) -> None
        def handle_request(self, method: str, path: str,
                           body: str | None = None,
                           query_string: str = "") -> tuple[int, dict[str, Any]]

- `__init__(storage=None)`: stores `self._store = storage or {}` (a
  `dict[str, dict[str, Any]]` keyed by string id) and `self._next_id = 1`.
  Passing `storage=None` creates a fresh empty dict; passing a dict uses it
  directly (no copy).
- `handle_request(method, path, body=None, query_string="")`:
  1. `urlparse(path)` → `path_parts = [p for p in parsed.path.strip("/").split("/") if p]`.
  2. `params = parse_qs(query_string)` (a `dict[str, list[str]]`).
  3. `handler = self._match_route(method, path_parts, params, body)`.
  4. If a handler is returned, call it and return its `(status, payload)`.
  5. Otherwise return `(404, {"error": "Not found", "path": path})`.

  **Guard inputs:** a path with no matching route (any method on an unknown
  path, or a known path with an unhandled method) → `404`. `body` is optional
  (`None` is legal); `query_string` defaults to `""`.

### Routes (the `_match_route` chain, in order)

| Path parts | Method | Handler | Success | Error paths |
|---|---|---|---|---|
| `api/v1/health` | any | `_health_check` | `200 {status:"healthy", timestamp:<UTC iso>}` | none (always 200) |
| `api/v1/stats` | any | `_get_stats` | `200 {total_items:<n>, tags:<tag_counts>}` | none (always 200) |
| `api/v1/content` | `GET` | `_list_content(params)` | `200 {items, total, page, per_page}` | `400` if `page`/`per_page` non-integer |
| `api/v1/content` | `POST` | `_create_content(body)` | `201 {item}` | `400` missing/empty body, invalid JSON, non-dict body |
| `api/v1/content` | other | — | — | `None` → `404` |
| `api/v1/content/search` | `GET` | `_search_content(params)` | `200 {results, total, query}` | `400` if `q` empty/absent |
| `api/v1/content/search` | other | — | — | `None` → `404` |
| `api/v1/content/export` | `GET` | `_export_content(params)` | `200 {format, items, total}` | none (always 200) |
| `api/v1/content/export` | other | — | — | `None` → `404` |
| `api/v1/content/{id}` (len 4) | `GET` | `_get_content(id)` | `200 {item}` | `404` id absent |
| `api/v1/content/{id}` | `PUT` | `_update_content(id, body)` | `200 {item}` | `404` id absent; `400` missing/invalid/non-dict body |
| `api/v1/content/{id}` | `DELETE` | `_delete_content(id)` | `200 {deleted:True, id}` | `404` id absent |
| `api/v1/content/{id}` | other | — | — | `None` → `404` |
| anything else | any | — | — | `None` → `404` |

Note the method-agnostic routes: `health` and `stats` match **any** method
(the chain does not check `method` for them), while `search`/`export` match
**only** `GET`. A `POST /api/v1/health` therefore returns `200`, not `405`.

### Handler behavior (exact)

- **`_list_content(params)`** — `items = list(self._store.values())`. Reads
  `page` (default `1`) and `per_page` (default `20`) from `params`; either
  non-integer → `(400, {"error": "Query parameters 'page' and 'per_page' must
  be integers"})`. `per_page = max(0, min(per_page, 100))` (capped at 100,
  floored at 0). `start = (page-1)*per_page`, `end = start+per_page`,
  `paginated = items[start:end]`. Returns `(200, {items, total: len(items),
  page, per_page})`. **Guard inputs:** `page=0` or negative → `start` negative
  → Python slice `items[-k:]` returns the *tail* of the list, not an empty
  page (a `page=0` request returns the last `per_page` items, not none).
  `per_page=0` → empty `items` slice but `total` still full.
- **`_get_content(item_id)`** — `self._store.get(item_id)`; `None` →
  `(404, {"error": "Content item '<id>' not found"})`; else `(200, {"item":
  item})`.
- **`_create_content(body)`** — `not body` → `(400, {"error": "Request body is
  required"})`; `json.JSONDecodeError` → `(400, {"error": "Invalid JSON in
  request body"})`; `not isinstance(data, dict)` → `(400, {"error": "Request
  body must be a JSON object"})`. Else `item_id = str(self._next_id)`,
  `self._next_id += 1`, builds `{id, title (default "Untitled"), description
  (default ""), link (default ""), tags (default []), created_at, updated_at}`
  (both timestamps `datetime.now(timezone.utc).isoformat()`), stores it,
  returns `(201, {"item": item})`. **No field validation** — see Contract
  Hole 1.
- **`_update_content(item_id, body)`** — `item_id not in self._store` →
  `(404, ...)`; then the same three body guards as `_create_content` (400).
  Else partial-updates: for each of `title/description/link/tags` present in
  the parsed data, sets `item[key]`; always refreshes `item["updated_at"]`;
  returns `(200, {"item": item})`. **No field validation** — see Contract
  Hole 1.
- **`_delete_content(item_id)`** — `item_id not in self._store` → `(404, ...)`;
  else `self._store.pop(item_id)`, returns `(200, {"deleted": True, "id":
  item_id})`.
- **`_search_content(params)`** — `q = params.get("q", [""])[0]`; `not q` →
  `(400, {"error": "Search query parameter 'q' is required"})`. Else
  case-insensitive substring match of `q` against each item's
  `f"{title} {description}".lower()`; returns `(200, {results, total:
  len(results), query: q})`.
- **`_export_content(params)`** — `fmt = params.get("format", ["json"])[0]`;
  `items = list(self._store.values())`; returns `(200, {format: fmt, items,
  total: len(items)})`. **`fmt` is echoed, never applied** — see Contract
  Hole 2.
- **`_health_check()`** — `(200, {status: "healthy", timestamp: <UTC iso>})`.
- **`_get_stats()`** — `(200, {total_items: len(self._store), tags:
  self._collect_tags()})`.
- **`_collect_tags()`** — `dict[str, int]` of each tag → count across all
  items' `tags` lists (missing `tags` treated as `[]`).

### `RequestLogger` (middleware)

    class RequestLogger:
        def __init__(self, api) -> None
        def handle_request(self, method, path, body=None, query_string="") -> tuple[int, dict[str, Any]]
        @property
        def log(self) -> list[dict[str, Any]]
        def clear_log(self) -> None

- `__init__(api)`: wraps an inner `api` (any object with `handle_request`);
  `self._log = []`.
- `handle_request(...)`: records `{method, path, timestamp:<UTC iso>}`, calls
  `self.api.handle_request(...)`, appends `status` to the entry, returns the
  inner `(status, response)` unchanged.
- `log` (property): returns a **copy** (`list(self._log)`), so mutating the
  returned list does not affect the logger.
- `clear_log()`: `self._log.clear()`.

## Contract Holes

### Hole 1 — `_validate_content` field validation is wired into the request path (ARCH-68, resolved)

`ContentAPI._validate_content(data)` (line 318) enforces: `data` must be a
`dict`; `title` (if present) must be a `str` of length ≤ 200; `tags` (if
present) must be a `list`. **It IS called by `_create_content` (line 187) and
`_update_content` (line 231)** — a non-empty error list maps to
``(400, {"error": <first error>})`` before the item is stored/updated.

Consequence: the advertised validation IS enforced on the real path.
- `POST /api/v1/content` with `{"title": "x"*201}` → **`400`**; the
  over-length title is rejected and not stored.
- `POST /api/v1/content` with `{"tags": "not-a-list"}` → **`400`**; the
  non-list tags are rejected and not stored.
- `PUT /api/v1/content/{id}` with the same bodies → **`400`**.

The method's own contract (its docstring) and the public `handle_request`
contract (what a caller actually observes) now agree.

**Fix confirmed (ARCH-68, verified by validator cycle 222):** `_validate_content`
is wired into the `_create_content` / `_update_content` request path and the
behavior is pinned by `tests/deep/test_content_api_adversarial.py`; no code or
test change is required.

### Hole 2 — `_export_content` `format` param is read and echoed, never applied

`_export_content` reads `fmt = params.get("format", ["json"])[0]` and returns
`(200, {format: fmt, items, total})`. `fmt` is **echoed back verbatim but
never used to shape the output**: `?format=csv` and `?format=xml` both return
the identical JSON-shaped `items` list. The docstring says "Export all content
items in the requested format," which over-promises: the format is a label,
not a serializer. **Fix direction:** either implement per-format serialization
(csv/xml/etc.) or reword the docstring to state that `format` is an
echoed label and the payload is always the JSON-shaped `items` list.

## Secondary notes

- **`page=0` / negative `page`** in `_list_content` produce a negative
  `start`, so Python's slice semantics return the *tail* of the list rather
  than an empty page. A `page=0` request returns the last `per_page` items.
  This is not an error path (no `400`); it is a silent off-by-one in
  pagination.
- **`per_page` is floored at 0** (`max(0, min(per_page, 100))`), so
  `per_page=0` returns an empty `items` list while `total` is still the full
  count.
- **`_store` is shared by reference** when a `storage` dict is passed to
  `__init__` (no copy); mutating the returned `item` dicts via
  `handle_request` mutates the caller's dict.
- **`_next_id` is not reset** when a `storage` dict is passed in; ids always
  start at `1` regardless of the pre-populated store, so a pre-seeded store
  can collide with a freshly created id.
- **Method-agnostic `health`/`stats`** routes match any HTTP method (no
  `405`), while `search`/`export` are `GET`-only.
- **`RequestLogger.log` returns a copy**; `clear_log` empties the internal
  list. The logger adds no filtering, no error capture beyond `status`, and
  no request/response body logging.
