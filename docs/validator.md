# Validator (dead twin)

`personal_index/validator.py` — self-contained URL + content validation module
(178 lines, stdlib-only: `logging`, `dataclasses`, `typing`, `urllib.parse`).

> **NEAR-NAME DISAMBIGUATION — read this first.** This page documents
> `personal_index/validator.py` (the module `validator`). It is a **DEAD**
> module: **0 production importers**
> (`grep -rn "from personal_index.validator import\|from .validator import\|import validator\b" personal_index/ --include=*.py`
> → nothing). It is pinned only by tests
> (`tests/test_validator.py`, `tests/deep/test_validator_url_adversarial.py`).
>
> It is **NOT** the live `personal_index/content_validation.py` documented in
> [content-validation.md](content-validation.md) (and the older
> [validation.md](validation.md) index line, which names
> `personal_index.content_validator` — a third, also-different module).
> The two modules share the SAME domain (validation) and define TWO
> incompatible `ValidationResult` and TWO incompatible `ContentValidator`
> types (see [ARCH-110](../tickets/ARCH-110.md)). A grep for "validator" or
> "ValidationResult" matches both; this page is the dead one.

## Purpose

Two independent validators over plain in-memory values, with no persistence
and no write path:

- `URLValidator` — validates a single URL string against a scheme allow-list,
  length caps, blocked domains and blocked paths.
- `ContentValidator` — validates a single content string against length,
  word-count, link-ratio and whitespace heuristics.

Both return a shared `ValidationResult` dataclass. Nothing is stored, loaded
or emitted; the result lives only in the caller's memory.

## Public API

### `ValidationResult` (dataclass)

| Field | Type | Default |
|-------|------|---------|
| `valid` | `bool` | *(required)* |
| `errors` | `list[str]` | `[]` |
| `warnings` | `list[str]` | `[]` |

- `add_error(message: str) -> None` — sets `valid = False` and appends
  `message` to `errors`.
- `add_warning(message: str) -> None` — appends `message` to `warnings`;
  does **not** change `valid`.

Note the field is named `valid` (not `is_valid`) and the elements are plain
`str` (not `ValidationError` objects) — both differ from the live
`content_validation.ValidationResult` (see contract hole below).

### `URLValidator`

Class constants: `SCHEMES = {"http","https","ftp","ftps"}`,
`MAX_URL_LENGTH = 2048`, `MAX_DOMAIN_LENGTH = 253`.

- `__init__(allowed_schemes: set[str] | None = None,
  blocked_domains: set[str] | None = None,
  blocked_paths: list[str] | None = None,
  max_url_length: int = 2048)` — `None` args fall back to the class defaults
  (`SCHEMES`, empty set, empty list, `MAX_URL_LENGTH`).
- `validate(url: str) -> ValidationResult` — guard: empty / whitespace-only
  `url` returns a result with the single error `"URL is empty"` (no other
  checks run). Otherwise strips the URL and runs, in order:
  `_check_length`, `_check_scheme`, `_check_domain`, `_check_path`,
  `_check_fragment`. The result is `valid` iff **no** error was added.
  - `_check_length` — `len(url) > max_url_length` → error.
  - `_check_scheme` — no scheme → error; `scheme.lower()` not in
    `allowed_schemes` → error.
  - `_check_domain` — no netloc → error; `len(netloc) > 253` → error;
    blocked domain → error.
  - `_check_path` — blocked path → error.
  - `_check_fragment` — a non-empty fragment → **warning** (never an error).
- `_is_blocked_domain(domain: str) -> bool` — lowercases and strips a
  trailing `.`; true if it equals a blocked entry or ends with `.<entry>`.
- `_is_blocked_path(path: str) -> bool` — true if the lowercased path
  `startswith` any lowercased blocked path.
- `validate_batch(urls: list[str]) -> list[tuple[str, ValidationResult]]` —
  `[(url, self.validate(url)) for url in urls]`.

### `ContentValidator`

Class constants: `MIN_CONTENT_LENGTH = 50`, `MAX_CONTENT_LENGTH = 10_000_000`,
`MIN_WORD_COUNT = 10`.

- `__init__(min_length: int = 50, max_length: int = 10_000_000,
  min_words: int = 10)`.
- `validate(content: str) -> ValidationResult` — guard: empty `content`
  returns a result with the single error `"Content is empty"` (no other
  checks run). Otherwise:
  - `len(content) < min_length` → **warning** ("too short").
  - `len(content) > max_length` → **warning** ("very long").
  - `len(content.split()) < min_words` → **warning** ("too few words").
  - `_has_too_many_links(content)` → **warning**.
  - `_is_mostly_whitespace(content)` → **error**.
  - The result is `valid` iff the whitespace error was not added (the soft
    limits are warnings only).
- `_has_too_many_links(content: str) -> bool` — `word_count > 0 and
  (content.count("http") / word_count) > 0.5`.
- `_is_mostly_whitespace(content: str) -> bool` — true if `content.strip()`
  is empty, or `content.count(" ") / len(content) > 0.95`.

## Invariants

- Both validators are pure and stateless per call; the only state is the
  constructor-configured thresholds.
- `ValidationResult.valid` is `True` at construction and is flipped to
  `False` only by `add_error`; warnings never affect it.
- Guard paths (empty URL / empty content) short-circuit with exactly one
  error and skip every other check.
- No I/O, no persistence, no write-back: the result is in-memory only.

## Contract hole (ARCH-110)

This module is a **dead near-twin** of the live `content_validation.py`. The
two modules define **two incompatible `ValidationResult`** and **two
incompatible `ContentValidator`** types for the same domain:

1. **`ValidationResult`** — this module's is a dataclass with `valid: bool`
   and plain `str` `errors`/`warnings`; the live
   `content_validation.ValidationResult` is a dataclass with `is_valid: bool`
   and `ValidationError`-object `errors`/`warnings` plus `items_valid` /
   `items_invalid` tallies. Same name, same domain, different field name
   (`valid` vs `is_valid`) and different element type (`str` vs
   `ValidationError`) — a consumer cannot pass one where the other is
   expected.
2. **`ContentValidator`** — this module's validates a single `str` (length /
   word-count / link-ratio / whitespace); the live
   `content_validation.ContentValidator` validates `list[dict]` items
   (required fields / title / url / score / dates). Same name, same domain,
   completely different input type and checks.
3. **`URLValidator` is orphaned** — it exists **only** in this dead module.
   The live `content_validation` validates URLs only as a sub-check of dict
   items; there is no live standalone URL validator, so the scheme allow-list
   / blocked-domain / blocked-path surface here has no live home.

The module has **0 production importers**; it is pinned only by
`tests/test_validator.py` and `tests/deep/test_validator_url_adversarial.py`.
See [ARCH-110](../tickets/ARCH-110.md) for the decision the implementer must
make (retire the dead twin vs. promote `URLValidator` into the live surface).
