# url_history — `personal_index.url_history`

Spec page (matches CURRENT code as of cycle 244).

`url_history.py` tracks URL visit history with in-memory storage and JSON
persistence. It exposes two public types: the `URLVisit` dataclass (a single
visit record) and the `URLHistory` container (the ordered list of visits plus
persistence and stats).

## `URLVisit` (dataclass, line 14)

Fields (in declaration order): `url: str`, `timestamp: str = ""`,
`status_code: int = 0`, `content_length: int = 0`, `title: str = ""`,
`user_agent: str = ""`, `response_time_ms: float = 0.0`, `error: str = ""`.

- `__post_init__(self)` (line 25): if `timestamp` is empty, it is set to
  `datetime.now(timezone.utc).isoformat()`. A non-empty `timestamp` is left
  untouched.
- `to_dict(self) -> dict[str, Any]` (line 29): returns a dict with **exactly
  8 keys** (`url`, `timestamp`, `status_code`, `content_length`, `title`,
  `user_agent`, `response_time_ms`, `error`); no mutation of the instance.
- `from_dict(cls, data: dict[str, Any]) -> URLVisit` (line 44): constructs via
  `cls(**data)`, so **every key in `data` must be a `URLVisit` field name** and
  **`url` must be present** (it has no default). Keys absent from `data` fall
  back to the dataclass defaults. A key that is not a field name, or a missing
  `url`, raises `TypeError` from the dataclass constructor.

## `URLHistory` (line 56)

`__init__(self, max_entries: int = 10000)` (line 59): stores `max_entries` and
an empty `_history` list.

- `record(self, url, status_code=200, content_length=0, title="",
  user_agent="", response_time_ms=0.0, error="") -> URLVisit` (line 63):
  builds a `URLVisit` (timestamp auto-filled by `__post_init__`), appends it,
  calls `_trim()`, and returns the visit.
- `get_visits(self, url=None, since=None, limit=100) -> list[URLVisit]`
  (line 81): filters by exact `url` (when truthy) and by `timestamp >= since`
  (when truthy), then returns the **last `abs(limit)`** results (or all, when
  `limit` is falsy). Order is insertion order (oldest first).
- `get_unique_urls(self) -> list[str]` (line 92): iterates `_history` in
  **reverse** (newest first) and returns each URL once, so the list is ordered
  **most-recently-visited first**.
- `get_stats(self) -> dict[str, Any]` (line 102): for an empty history returns
  `{"total_visits": 0, "unique_urls": 0, "avg_response_time_ms": 0.0,
  "error_count": 0, "success_count": 0}`. Otherwise `total_visits` = len,
  `unique_urls` = distinct URL count, `error_count` = visits with
  `status_code >= 400` **or** a non-empty `error`, `success_count` = total -
  errors, and `avg_response_time_ms` = mean of the `response_time_ms > 0`
  values rounded to 2 places (0.0 when none are positive).
- `get_domain_stats(self) -> dict[str, dict[str, int]]` (line 128): groups
  visits by `urlparse(url).netloc` (falling back to `"unknown"` when the
  netloc is empty **or** `urlparse` raises `ValueError`). Each domain maps to
  `{"visits": <count>, "errors": <count>}` where errors use the same
  `status_code >= 400 or error` rule as `get_stats`.
- `clear(self) -> int` (line 143): empties `_history` and returns the number
  of entries removed.
- `save(self, filepath: str) -> None` (line 149): creates parent dirs, writes
  `[v.to_dict() for v in _history]` as indented JSON.
- `load(self, filepath: str) -> int` (line 157): returns `0` when the file is
  missing, when the JSON is invalid (`json.JSONDecodeError`), or when the
  parsed value is not a list. Otherwise it replaces `_history` with
  `[URLVisit.from_dict(d) for d in data]`, calls `_trim()`, and returns the
  number of visits loaded. **Contract hole (ARCH-76):** the
  `URLVisit.from_dict(d)` comprehension runs **outside** the
  `try/except json.JSONDecodeError` block, so a valid-JSON list whose records
  carry an unexpected key or omit `url` raises `TypeError` instead of
  degrading gracefully — see ARCH-76.
- `_trim(self) -> None` (line 173): when `len(_history) > max_entries`, keeps
  only the **last** `max_entries` entries (evicts the oldest).

## Contract hole (ARCH-76)
`load()` promises graceful degradation ("Returns count loaded") for missing /
invalid-JSON / non-list inputs, but a valid-JSON list containing a malformed
record (unexpected key, or missing `url`) raises `TypeError` from
`URLVisit.from_dict` because that comprehension is not inside the
`try/except`. See `tickets/ARCH-76.md`.
