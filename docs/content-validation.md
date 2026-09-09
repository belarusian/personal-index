# Content Validation

`personal_index/content_validation.py` — self-contained content validation subsystem (242 lines, stdlib-only: `dataclasses`, `datetime`, `typing`).

## Public API

### `ValidationError` (dataclass)

| Field | Type | Default |
|-------|------|---------|
| `field` | `str` | *(required)* |
| `message` | `str` | *(required)* |
| `severity` | `str` | `"error"` |
| `value` | `Any` | `None` |

A single validation finding. `severity` is `"error"` (set by `add_error`) or `"warning"` (set by `add_warning`).

### `ValidationResult` (dataclass)

| Attribute | Type | Default |
|-----------|------|---------|
| `is_valid` | `bool` | `True` |
| `errors` | `list[ValidationError]` | `[]` |
| `warnings` | `list[ValidationError]` | `[]` |
| `items_valid` | `int` | `0` |
| `items_invalid` | `int` | `0` |

| Method | Signature | Behavior |
|--------|-----------|----------|
| `add_error` | `(field: str, message: str, value: Any = None) -> None` | Appends `ValidationError(field, message, value)` (severity defaults to `"error"`) to `errors`; sets `is_valid = False` |
| `add_warning` | `(field: str, message: str, value: Any = None) -> None` | Appends `ValidationError(field, message, severity="warning", value)` to `warnings`; does **not** change `is_valid` |
| `to_dict` | `() -> dict[str, Any]` | Returns a 6-key dict: `is_valid`, `error_count` (= `len(errors)`), `warning_count` (= `len(warnings)`), `items_valid`, `items_invalid`, and `errors` (a projected list of `{"field", "message"}` — drops `severity` and `value`). Warnings are **not** included (only their count). |

> **Verdict semantics:** `is_valid` is `False` iff at least one **error** was recorded. Warnings never invalidate. `items_valid` / `items_invalid` are per-item tallies maintained by `validate`.

### `ContentValidator`

| Method | Signature | Behavior |
|--------|-----------|----------|
| `__init__` | `(required_fields: list[str] \| None = None, max_title_length: int = 500, max_url_length: int = 2048) -> None` | `self.required_fields = required_fields or ["id", "url"]`; stores `max_title_length`, `max_url_length` |
| `validate` | `(items: list[dict[str, Any]]) -> ValidationResult` | One `ValidationResult` for the whole batch. For each item runs `_validate_item`; tallies `items_valid` / `items_invalid`; returns the accumulated result |
| `validate_single` | `(item: dict[str, Any]) -> ValidationResult` | Returns `self.validate([item])` |

#### Per-item checks (run in order by `_validate_item(item, index, result) -> bool`)

Each check receives `prefix = f"item[{index}]"` and returns a `bool` (except `_validate_title`, which is warning-only and does not affect the item verdict).

| Check | Guard | Finding | Severity |
|-------|-------|---------|----------|
| `_check_required_fields` | `field_name not in item` for each `required_fields` | `Required field '{field}' is missing` | error |
| `_validate_url` | `url` truthy but `_is_valid_url(url)` is False | `Invalid URL: {url}` (value=url) | error |
| `_validate_url` | `len(url) > max_url_length` | `URL exceeds max length of {max_url_length}` | error |
| `_validate_title` | `title` truthy and `len(title) > max_title_length` | `Title exceeds recommended length of {max_title_length}` | **warning** |
| `_validate_score` | `score is not None` and `not isinstance(score, (int, float))` | `Score must be a number` | error |
| `_validate_score` | `score is not None` and `not (0.0 <= score <= 1.0)` | `Score {score} is outside typical range [0, 1]` | **warning** |
| `_validate_dates` | `date_val` truthy and `_is_valid_date(date_val)` is False, for each of `("published_at", "updated_at")` | `Invalid date format: {date_val}` | error |

An item is **valid** iff `_check_required_fields`, `_validate_url`, `_validate_score`, and `_validate_dates` all return True (title is warning-only and never invalidates).

#### Private helpers

| Method | Signature | Behavior |
|--------|-----------|----------|
| `_is_valid_url` | `(url: str) -> bool` | `False` if `url` is empty; otherwise `url.startswith(("http://", "https://"))` |
| `_is_valid_date` | `(value: Any) -> bool` | `True` if `value` is a `datetime`; `True` if `value` is a `str` parseable by `datetime.fromisoformat`; `False` otherwise |

## Contract Holes

**ARCH-51 (most important):** `_is_valid_url` is a naive scheme-prefix check — it accepts any string beginning with `http://` or `https://` **regardless of whether a host is present**. So `url="http://"` (no host), `"https://"` (no host), and `"http:// "` (trailing space, no host) all pass validation, and a content item carrying such a URL is reported valid. The fix is to require a non-empty host (e.g. via `urllib.parse.urlparse`: `scheme in ("http","https")` and `netloc` non-empty).

Secondary notes (not ticketed this cycle):
- `_validate_score` accepts `bool` as a valid score because `bool` is a subclass of `int` in Python (`isinstance(True, (int, float))` is `True`), so `score=True`/`score=False` pass.
- `_check_required_fields` checks **presence only** (`field_name not in item`); a present-but-`None` value (e.g. `{"id": None}`) passes the required-field check.
- `to_dict` is lossy and asymmetric: it drops `severity` and `value` from each error and omits the warnings list entirely (only `warning_count` is emitted).
