# API Reference

This document provides a comprehensive API reference for all public modules in personal-index.

---

## Core Models

### `personal_index.models`

Core domain entities used throughout the system.

#### `InterestType` (Enum)

| Value | Description |
|-------|-------------|
| `KEYWORD` | Match by keyword presence |
| `TOPIC` | Match by topic presence |
| `URL_PATTERN` | Match by URL regex pattern |

#### `Interest`

A user-defined interest to track.

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `name` | `str` | — | Interest name (unique identifier) |
| `interest_type` | `InterestType` | `KEYWORD` | Type of matching |
| `value` | `str` | `""` | Single value to match |
| `keywords` | `list` | `[]` | List of keywords |
| `url_patterns` | `list` | `[]` | Regex URL patterns |
| `topics` | `list` | `[]` | Topic strings |
| `priority` | `int` | `5` | Priority (1-10) |
| `created_at` | `str` | UTC now | Creation timestamp |
| `enabled` | `bool` | `True` | Whether interest is active |

**Methods:**

- `matches(text: str, url: str = "") -> bool` — Check if text/URL matches this interest.
- `score(text: str) -> float` — Calculate relevance score for text.
- `to_dict() -> dict` — Serialize to dictionary.
- `from_dict(data: dict) -> Interest` — Deserialize from dictionary.

#### `CrawlConfig`

Configuration for web crawling behavior.

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `max_depth` | `int` | `3` | Maximum crawl depth |
| `politeness_delay` | `float` | `1.0` | Delay between requests (seconds) |
| `rate_limit` | `int` | `10` | Max requests per window |
| `max_pages_per_domain` | `int` | `100` | Max pages per domain |
| `timeout` | `int` | `30` | Request timeout (seconds) |
| `user_agent` | `str` | `"personal-index/0.1.0"` | User-Agent string |
| `respect_robots_txt` | `bool` | `True` | Respect robots.txt |
| `allowed_domains` | `list` | `[]` | Allowed domain whitelist |
| `blocked_domains` | `list` | `[]` | Blocked domain blacklist |

#### `CrawledPage`

A page that has been crawled.

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `url` | `str` | — | Page URL |
| `title` | `str` | `""` | Page title |
| `content` | `str` | `""` | Extracted text content |
| `meta_description` | `str` | `""` | Meta description |
| `status_code` | `int` | `200` | HTTP status code |
| `depth` | `int` | `0` | Crawl depth |
| `parent_url` | `str` | `""` | Parent page URL |
| `headers` | `dict` | `{}` | Response headers |
| `matched_interests` | `list` | `[]` | Matching interest names |
| `relevance_score` | `float` | `0.0` | Interest relevance score |
| `crawled_at` | `datetime` | UTC now | Crawl timestamp |

#### `IndexedPage`

A crawled and indexed page.

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `url` | `str` | — | Page URL |
| `title` | `str` | `""` | Page title |
| `content` | `str` | `""` | Page content |
| `keywords` | `list` | `[]` | Extracted keywords |
| `matched_interests` | `list` | `[]` | Matching interests |
| `crawled_at` | `str` | UTC now | Crawl timestamp |
| `domain` | `str` | `""` | Domain name |
| `status_code` | `int` | `200` | HTTP status |
| `content_length` | `int` | `0` | Content length |
| `language` | `str` | `"en"` | Language code |

#### `SearchResult`

A search result with score and snippet.

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `page` | `IndexedPage` | — | The matched page |
| `score` | `float` | `0.0` | Relevance score |
| `matched_terms` | `list` | `[]` | Terms that matched |
| `snippet` | `str` | `""` | Content snippet |

#### `Page`

A page model for the search index with UUID-based ID.

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `url` | `str` | — | Page URL |
| `title` | `str` | `""` | Page title |
| `content` | `str` | `""` | Page content |
| `meta_description` | `str` | `""` | Meta description |
| `matched_interests` | `list` | `[]` | Matching interests |
| `id` | `str` | UUID hex[:12] | Unique page ID |
| `crawled_at` | `str` | UTC now | Crawl timestamp |
| `domain` | `str` | `""` | Domain name |
| `status_code` | `int` | `200` | HTTP status |
| `content_length` | `int` | `0` | Content length |
| `language` | `str` | `"en"` | Language code |
| `keywords` | `list` | `[]` | Extracted keywords |

---

## Interest Store

### `personal_index.interest_store`

#### `InterestStore(storage_path: str)`

Persistent JSON-based storage for user interests.

**Methods:**

- `add(interest: Interest) -> None` — Add an interest.
- `remove(name: str) -> bool` — Remove by name. Returns `True` if found.
- `get(name: str) -> Optional[Interest]` — Get by name.
- `list_all(enabled_only: bool = False) -> List[Interest]` — List all interests.
- `toggle(name: str) -> Optional[Interest]` — Toggle enabled status.
- `update_priority(name: str, priority: int) -> Optional[Interest]` — Update priority (clamped 1-10).
- `matches_any(text: str, url: str = "") -> List[Interest]` — Find matching interests.
- `total_score(text: str) -> float` — Aggregate relevance score.

---

## Crawler

### `personal_index.crawler.main`

#### `CrawlerConfig`

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `max_depth` | `int` | `3` | Maximum crawl depth |
| `max_pages` | `int` | `100` | Maximum pages to crawl |
| `delay` | `float` | `1.0` | Politeness delay (seconds) |
| `timeout` | `int` | `10` | Request timeout (seconds) |
| `respect_robots` | `bool` | `True` | Respect robots.txt |
| `allowed_domains` | `List[str]` | `[]` | Domain whitelist |
| `user_agent` | `str` | `"PersonalIndex/0.1.0"` | User-Agent string |

#### `Crawler(config: Optional[CrawlerConfig] = None, interest_store: Optional[InterestStore] = None)`

Web crawler with depth control and politeness.

**Properties:**

- `pages_crawled: int` — Number of pages crawled.
- `results: List[CrawledPage]` — Crawled page results.

**Methods:**

- `crawl(seed_urls: List[str], max_depth: int = None) -> List[CrawledPage]` — Start crawling from seed URLs.
- `close() -> None` — Close the HTTP session.

> **Note:** `WebCrawler` is an alias for `Crawler` for backward compatibility.

---

## Search Index

### `personal_index.search_index`

#### `SearchIndex(index_path: str)`

In-memory search index with JSON persistence.

**Methods:**

- `add(page: CrawledPage) -> None` — Add a page to the index.
- `remove(url: str) -> bool` — Remove a page by URL.
- `get(url: str) -> Optional[CrawledPage]` — Get a page by URL.
- `search(query: str, limit: int = 10) -> List[dict]` — Search the index.
- `get_page_count() -> int` — Number of indexed pages.
- `list_pages() -> List[CrawledPage]` — List all pages.
- `clear() -> None` — Clear the index.

### `personal_index.index` (CLI-facing)

#### `SearchIndex(db_path: Optional[str] = None)`

CLI-facing search index with stop-word filtering.

**Methods:**

- `add_page(page: IndexedPage) -> int` — Add a page. Returns page count.
- `remove_page(url: str) -> bool` — Remove a page.
- `get_page(url: str) -> Optional[IndexedPage]` — Get a page.
- `get_page_count() -> int` — Page count.
- `list_pages() -> List[IndexedPage]` — List all pages sorted by score.
- `clear() -> None` — Clear the index.
- `search(query: str, limit: int = 10) -> List[SearchResult]` — Search with snippets.
- `close() -> None` — Save and close.
- Context manager support: `with SearchIndex() as idx: ...`

---

## Scheduler

### `personal_index.scheduler`

#### `ScheduleConfig`

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `interval_hours` | `int` | `24` | Hours between runs |
| `enabled` | `bool` | `True` | Whether job is active |
| `seed_urls` | `List[str]` | `[]` | URLs to crawl |
| `max_pages_per_run` | `int` | `50` | Max pages per run |
| `crawl_depth` | `int` | `2` | Crawl depth |
| `delay` | `float` | `1.0` | Politeness delay |

#### `ScheduleEntry`

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `name` | `str` | — | Job name |
| `config` | `ScheduleConfig` | — | Job configuration |
| `run_count` | `int` | `0` | Total runs |
| `total_pages_indexed` | `int` | `0` | Total pages indexed |
| `last_run` | `Optional[datetime]` | `None` | Last run time |
| `next_run` | `Optional[datetime]` | `None` | Next scheduled run |

#### `Scheduler(interest_store, search_index, schedule_store)`

Manages scheduled crawling jobs.

**Methods:**

- `add_schedule(name, seed_urls, interval_hours=24, ...) -> ScheduleEntry` — Add a job.
- `add_job(name, seed_urls, interval_hours=24, ...) -> ScheduleEntry` — Alias for `add_schedule`.
- `remove_schedule(name) -> bool` — Remove a job.
- `remove_job(name) -> bool` — Alias for `remove_schedule`.
- `toggle_schedule(name) -> Optional[ScheduleEntry]` — Toggle enabled.
- `get_due_schedules() -> List[ScheduleEntry]` — Get jobs due to run.
- `update_next_run_times() -> None` — Recalculate next run times.
- `run_schedule(name) -> int` — Run a job. Returns pages indexed.
- `list_jobs() -> List[ScheduleEntry]` — List all jobs.

---

## Content Pipeline

### `personal_index.pipeline`

#### `PipelineStep(name: str, handler: Callable[[dict], dict], enabled: bool = True, on_error: str = "continue")`

A single pipeline step.

**Methods:**

- `execute(data: dict) -> dict` — Execute the step on data.

#### `PipelineResult(success: bool, data: dict, steps_executed: int, steps_failed: int, errors: list)`

Result of running a pipeline.

#### `ContentPipeline(name: str = "default")`

Sequential pipeline for processing content.

**Methods:**

- `add_step(name, handler, enabled=True, on_error="continue") -> ContentPipeline` — Add a step (chainable).
- `remove_step(name) -> bool` — Remove a step.
- `disable_step(name) -> bool` — Disable a step.
- `enable_step(name) -> bool` — Enable a step.
- `run(data: dict) -> PipelineResult` — Run the pipeline.
- `get_step(name) -> Optional[PipelineStep]` — Get a step by name.
- `clear() -> None` — Remove all steps.

**Properties:**

- `step_count: int` — Total number of steps.
- `enabled_steps: list[str]` — Names of enabled steps.

---

## REST API

### `personal_index.api.server`

#### `create_app(config: Optional[AppConfig] = None, middleware: Optional[list] = None) -> FastAPI`

Create and configure the FastAPI application.

### `personal_index.api.routes`

#### `register_routes(app, search_index=None, index_instance=None)`

Register all API routes on the FastAPI app.

**Endpoints:**

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/v1/health` | Health check |
| `GET` | `/api/v1/search?q=&limit=20&offset=0` | Search indexed pages |
| `GET` | `/api/v1/pages?limit=50&offset=0&domain=` | List indexed pages |
| `GET` | `/api/v1/pages/{page_id}` | Get a specific page |
| `GET` | `/api/v1/stats` | Get indexing statistics |
| `GET` | `/api/v1/interests` | List configured interests |

### `personal_index.api.models`

#### `APIResponse[T]`

Standard API response wrapper.

- `success: bool` — Whether the request succeeded.
- `data: Optional[T]` — Response data.
- `error: Optional[str]` — Error code.
- `message: Optional[str]` — Human-readable message.
- `meta: Dict[str, Any]` — Additional metadata.

**Class methods:**

- `APIResponse.ok(data, message="Success")` — Create success response.
- `APIResponse.error(message, error_code=None)` — Create error response.

#### `PaginatedResponse[T]`

Paginated response with metadata.

- `items: List[T]` — Items on this page.
- `total: int` — Total items.
- `page: int` — Current page (1-based).
- `page_size: int` — Items per page.
- `has_next: bool` — Whether more pages exist.
- `has_prev: bool` — Whether previous pages exist.
- `total_pages: int` (property) — Total number of pages.

#### `SearchRequest`

Search request parameters.

- `q: str` — Search query.
- `limit: int = 20` — Max results (1-100).
- `offset: int = 0` — Result offset.
- `filters: Dict[str, str]` — Additional filters.
- `sort_by: Optional[str]` — Sort field.
- `sort_order: str = "desc"` — Sort direction.

**Methods:**

- `validate() -> List[str]` — Return validation errors.

#### `SearchResponse`

Search response with results.

- `query: str` — Original query.
- `results: List[Dict]` — Result items.
- `total: int` — Total results.
- `limit: int` — Limit applied.
- `offset: int` — Offset applied.
- `execution_time_ms: float` — Query execution time.

#### `ErrorResponse`

Error response with details.

- `error: str` — Error code.
- `message: str` — Error message.
- `status_code: int = 400` — HTTP status code.
- `details: Dict[str, Any]` — Additional details.

#### Exception Classes

| Exception | Status | Error Code | Description |
|-----------|--------|------------|-------------|
| `APIError` | 400 | `bad_request` | Base API exception |
| `NotFoundError` | 404 | `not_found` | Resource not found |
| `ValidationError` | 422 | `validation_error` | Request validation failed |
| `UnauthorizedError` | 401 | `unauthorized` | Authentication required |
| `ForbiddenError` | 403 | `forbidden` | Permission denied |

### `personal_index.api.pagination`

#### `paginate(items, page=1, page_size=20) -> PaginatedResult[T]`

Paginate a sequence using page numbers.

#### `paginate_with_offset(items, offset=0, limit=20) -> PaginatedResult[T]`

Paginate a sequence using offset/limit.

#### `PageInfo`

| Field | Type | Description |
|-------|------|-------------|
| `page` | `int` | Current page (1-based) |
| `page_size` | `int` | Items per page |
| `total_items` | `int` | Total item count |
| `total_pages` | `int` | Total page count |
| `has_next` | `bool` | More pages after |
| `has_prev` | `bool` | Pages before |
| `start_index` | `int` (property) | First index on page |
| `end_index` | `int` (property) | Last index on page |

### `personal_index.api.handlers`

#### `ErrorHandler(app, debug=False)`

ASGI middleware for error handling. Catches `APIError` and generic exceptions.

#### `TimingMiddleware(app)`

Adds `X-Response-Time-Ms` header to responses.

#### `ContentTypeMiddleware(app)`

Ensures `Content-Type: application/json` on responses.

#### `handle_api_error(exc: Exception) -> APIResponse`

Convert an exception to an API response.

### `personal_index.api.middleware`

#### `RequestLoggingMiddleware(app, log_body=False)`

Logs all incoming requests with method, path, status, and duration.

#### `CORSHeadersMiddleware(app, allowed_origins, allowed_methods, allowed_headers)`

Adds CORS headers to responses. Handles OPTIONS preflight.

#### `RequestIdMiddleware(app)`

Assigns a unique `X-Request-Id` to each request.

#### `create_middleware_stack(app, enable_logging=True, enable_cors=True, enable_request_id=True, cors_origins=None)`

Create a middleware stack. Wraps app in RequestId → Logging → CORS order.

### `personal_index.api.rate_limit_middleware`

#### `RateLimitRule(max_requests, window_seconds, key="ip", path_pattern=None, methods=None)`

A rate limiting rule.

**Methods:**

- `matches(method, path) -> bool` — Check if rule matches request.

#### `SlidingWindowRateLimiter(rules=None)`

Sliding window rate limiter.

**Methods:**

- `is_allowed(identifier, method, path) -> Tuple[bool, Dict]` — Check if request is allowed.
- `get_status(identifier) -> Dict` — Get rate limit status.
- `reset(identifier=None)` — Reset limits.

#### `RateLimitMiddleware(app, limiter=None, key_extractor=None)`

ASGI middleware for rate limiting.

---

## Authentication

### `personal_index.auth.tokens`

#### `TokenPayload(sub, iat, exp, jti, roles, metadata)`

JWT token payload data.

**Methods:**

- `to_dict() -> Dict` — Serialize payload.
- `from_dict(data) -> TokenPayload` — Deserialize payload.

#### `JWTManager(secret, algorithm="HS256", default_ttl=3600)`

JWT token creation and verification using HMAC-SHA256.

**Methods:**

- `create(payload: TokenPayload) -> str` — Create a signed JWT.
- `verify(token: str) -> Optional[TokenPayload]` — Verify and decode a JWT.
- `refresh(token: str) -> str` — Refresh an expired token.

### `personal_index.auth.api_keys`

#### `APIKey`

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `key_id` | `str` | UUID hex[:16] | Unique key ID |
| `name` | `str` | `""` | Key name |
| `hashed_key` | `str` | `""` | Hashed key value |
| `prefix` | `str` | `"pk_"` | Key prefix |
| `owner` | `str` | `""` | Key owner |
| `permissions` | `List[str]` | `[]` | Granted permissions |
| `created_at` | `str` | UTC now | Creation time |
| `expires_at` | `Optional[str]` | `None` | Expiration time |
| `last_used_at` | `Optional[str]` | `None` | Last usage time |
| `usage_count` | `int` | `0` | Total uses |
| `is_active` | `bool` | `True` | Whether key is active |

### `personal_index.auth.permissions`

#### `Permission` (Enum)

| Value | Description |
|-------|-------------|
| `READ_INDEX` | `read:index` |
| `WRITE_INDEX` | `write:index` |
| `DELETE_INDEX` | `delete:index` |
| `READ_CONFIG` | `read:config` |
| `WRITE_CONFIG` | `write:config` |
| `READ_STATS` | `read:stats` |
| `MANAGE_USERS` | `manage:users` |
| `MANAGE_KEYS` | `manage:keys` |
| `RUN_CRAWL` | `run:crawl` |
| `VIEW_DASHBOARD` | `view:dashboard` |

#### `Role` (Enum)

| Value | Permissions |
|-------|-------------|
| `ADMIN` | All permissions |
| `EDITOR` | Read/write/delete index, read config/stats, view dashboard |
| `VIEWER` | Read index, read stats, view dashboard |
| `CRAWLER` | Read index, run crawl |

### `personal_index.auth.sessions`

#### `Session`

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `session_id` | `str` | UUID hex | Unique session ID |
| `user_id` | `str` | `""` | Associated user |
| `created_at` | `float` | time.time() | Creation timestamp |
| `last_accessed` | `float` | time.time() | Last access time |
| `expires_at` | `Optional[float]` | `None` | Expiration time |
| `data` | `Dict[str, Any]` | `{}` | Session data |
| `ip_address` | `str` | `""` | Client IP |
| `user_agent` | `str` | `""` | Client user agent |
| `is_active` | `bool` | `True` | Whether session is active |

**Methods:**

- `is_expired() -> bool` — Check if session has expired.
- `to_dict() -> Dict` — Serialize session.

### `personal_index.auth.passwords`

#### `PasswordConfig(algorithm="sha256", iterations=100_000, salt_length=32, key_length=32)`

Password hashing configuration.

**Functions:**

- `hash_password(password: str, config=None) -> str` — Hash a password with PBKDF2-HMAC-SHA256.
- `verify_password(password: str, hashed: str) -> bool` — Verify a password against a hash.

---

## Configuration

### `personal_index.config.models`

#### `MatchMode` (Enum)

| Value | Description |
|-------|-------------|
| `ANY` | Match any keyword |
| `ALL` | Match all keywords |
| `REGEX` | Match as regex pattern |

#### `Interest` (config model)

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `name` | `str` | — | Interest name |
| `keywords` | `List[str]` | `[]` | Keywords |
| `url_patterns` | `List[str]` | `[]` | URL patterns |
| `match_mode` | `MatchMode` | `ANY` | Matching mode |
| `priority` | `int` | `5` | Priority (clamped 1-10) |
| `enabled` | `bool` | `True` | Active status |

#### `CrawlerConfig` (config model)

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `max_depth` | `int` | `3` | Max crawl depth |
| `politeness_delay` | `float` | `1.0` | Delay between requests |
| `rate_limit` | `int` | `10` | Rate limit |
| `timeout` | `int` | `30` | Request timeout |
| `respect_robots_txt` | `bool` | `True` | Respect robots.txt |
| `max_concurrent_requests` | `int` | `5` | Max concurrent requests |
| `user_agent` | `str` | `"PersonalIndex/0.1.0"` | User-Agent |

#### `SchedulerConfig`

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `enabled` | `bool` | `False` | Scheduling enabled |
| `interval_hours` | `int` | `24` | Default interval |

#### `IndexConfig`

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `index_path` | `str` | `".personal_index"` | Index file path |
| `enable_stemming` | `bool` | `True` | Enable word stemming |

#### `AppConfig`

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `data_dir` | `str` | `".personal_index"` | Data directory |
| `interests` | `List[Interest]` | `[]` | Configured interests |
| `crawler` | `CrawlerConfig` | default | Crawler settings |
| `scheduler` | `SchedulerConfig` | default | Scheduler settings |
| `index` | `IndexConfig` | default | Index settings |

---

## CLI

### `personal_index.cli`

Entry point: `personal_index`

**Commands:**

| Command | Description |
|---------|-------------|
| `personal_index interests add` | Add a new interest |
| `personal_index interests list` | List all interests |
| `personal_index interests remove` | Remove an interest |
| `personal_index interests toggle` | Toggle interest on/off |
| `personal_index search <query>` | Search indexed pages |
| `personal_index crawl <url>` | Crawl a URL |
| `personal_index index count` | Show indexed page count |
| `personal_index index list` | List indexed pages |
| `personal_index index clear` | Clear the index |
| `personal_index schedule add` | Add a scheduled job |
| `personal_index schedule list` | List scheduled jobs |
| `personal_index schedule remove` | Remove a scheduled job |
| `personal_index config show` | Show current config |
| `personal_index config set-crawler` | Set crawler config |
| `personal_index config set-schedule` | Set schedule config |
