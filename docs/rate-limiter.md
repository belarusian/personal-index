# rate_limiter — Exact Contract

Module: `personal_index/rate_limiter.py` (160 lines)

Per-domain rate limiting using a token-bucket algorithm. Three public types:
`RateLimitConfig` (a dataclass), `RateLimitStatus` (a dataclass), and
`RateLimiter` (a plain class) backed by one `TokenBucket` per domain. Time is
measured with `time.monotonic()`; each `TokenBucket` is guarded by its own
`threading.RLock`, and `RateLimiter` guards its `_buckets` / `_configs` dicts
with a single `threading.Lock`.

## Public API

### RateLimitConfig

A `@dataclass` with three fields:

- `max_requests: int = 10`
- `window_seconds: float = 60.0`
- `burst_size: int | None = None`

`__post_init__` does exactly one thing: if `burst_size is None`, set
`burst_size = max_requests`. **No bounds validation** of any field (see
contract holes).

### RateLimitStatus

A `@dataclass` with four fields:

- `remaining: int`
- `limit: int`
- `reset_at: float`
- `retry_after: float = 0.0`

### TokenBucket

One bucket per domain. State: `_max_tokens` (int, **assigned but never read**
— see contract holes), `_burst_size` (int), `_refill_rate` (float),
`_tokens` (float), `_last_refill` (float, `time.monotonic()`), `_lock`
(`threading.RLock`).

#### Constructor

- `__init__(self, config: RateLimitConfig) -> None`
  Sets `_max_tokens = config.max_requests`,
  `_burst_size = config.burst_size if config.burst_size is not None else
  config.max_requests`, `_refill_rate = config.max_requests /
  config.window_seconds`, `_tokens = float(_burst_size)`,
  `_last_refill = time.monotonic()`, `_lock = threading.RLock()`.
  **`_refill_rate` divides by `window_seconds` with no guard** (see contract
  holes).

#### Refill

- `_refill(self) -> None` (private)
  `now = time.monotonic()`; `elapsed = now - _last_refill`;
  `_tokens = min(_burst_size, _tokens + elapsed * _refill_rate)`;
  `_last_refill = now`. Tokens are capped at `_burst_size`.

#### Acquire / wait / status

- `acquire(self) -> bool`
  Under `_lock`: `_refill()`; if `_tokens >= 1.0`, decrement by `1.0` and
  return `True`; otherwise return `False` (no token consumed).

- `wait_time(self) -> float`
  Under `_lock`: `_refill()`; if `_tokens >= 1.0` return `0.0`; otherwise
  return `(1.0 - _tokens) / _refill_rate`. **Divides by `_refill_rate` with no
  guard** (see contract holes).

- `status(self) -> RateLimitStatus`
  Under `_lock`: `_refill()`; `remaining = int(_tokens)`;
  `reset_at = time.monotonic() + (_burst_size - _tokens) / _refill_rate`;
  returns `RateLimitStatus(remaining=remaining, limit=_burst_size,
  reset_at=reset_at, retry_after=self.wait_time())`. **Divides by
  `_refill_rate` with no guard** (see contract holes). Note `status()` calls
  `self.wait_time()`, which re-acquires the same `RLock` (reentrant, safe).

### RateLimiter

State: `_default_config` (`RateLimitConfig`), `_buckets: dict[str,
TokenBucket]`, `_configs: dict[str, RateLimitConfig]`, `_lock`
(`threading.Lock`).

#### Constructor

- `__init__(self, default_config: RateLimitConfig | None = None) -> None`
  `_default_config = default_config or RateLimitConfig()`; `_buckets = {}`;
  `_configs = {}`; `_lock = threading.Lock()`.

#### Config

- `set_domain_config(self, domain: str, config: RateLimitConfig) -> None`
  Under `_lock`: `_configs[domain] = config` and **replaces** the bucket with
  a fresh `TokenBucket(config)` (any tokens the old bucket held are discarded).

- `_get_bucket(self, domain: str) -> TokenBucket` (private)
  If `domain not in _buckets`, create `TokenBucket(_configs.get(domain,
  _default_config))` and store it. Returns the bucket. A domain that has never
  been configured uses `_default_config`.

#### Request path

- `can_request(self, domain: str) -> bool`
  `bucket = _get_bucket(domain)`; `return bucket.acquire()`. **Consumes one
  token when it returns `True`** (it is not a side-effect-free probe); returns
  `False` without consuming when the budget is exhausted. Callers that only
  want to inspect the budget should use `get_status()` / `get_wait_time()`.

- `wait_for_request(self, domain: str, timeout: float = 30.0) -> bool`
  `bucket = _get_bucket(domain)`; `deadline = time.monotonic() + timeout`;
  loop while `time.monotonic() < deadline`: if `bucket.acquire()` succeeds
  return `True`; else `wait = bucket.wait_time()` and, if `wait > 0`,
  `time.sleep(min(wait, deadline - time.monotonic()))`. Returns `False` on
  timeout. **Blocking** (sleeps); a domain with `_refill_rate == 0` never
  refills, so this loops until `timeout` and returns `False`.

#### Introspection

- `get_status(self, domain: str) -> RateLimitStatus`
  `bucket = _get_bucket(domain)`; `return bucket.status()`.

- `get_wait_time(self, domain: str) -> float`
  `bucket = _get_bucket(domain)`; `return bucket.wait_time()`.

#### Reset

- `reset_domain(self, domain: str) -> None`
  Under `_lock`: `config = _configs.get(domain, _default_config)`;
  `_buckets[domain] = TokenBucket(config)` (fresh bucket, tokens discarded).

- `reset_all(self) -> None`
  Under `_lock`: for every `domain, config in _configs.items()`, replace the
  bucket with a fresh `TokenBucket(config)`; then for every domain in
  `_buckets` that is **not** in `_configs` (i.e. created via the default
  config), replace it with a fresh `TokenBucket(_default_config)`.

- `get_all_statuses(self) -> dict[str, RateLimitStatus]`
  `{domain: bucket.status() for domain, bucket in self._buckets.items()}` —
  one entry per domain that has a bucket (configured or default-created).

## Contract Holes

### (ARCH-37) `RateLimitConfig` numeric fields are unvalidated — `window_seconds == 0` and `max_requests <= 0` raise `ZeroDivisionError`

`RateLimitConfig.__post_init__` only normalizes `burst_size is None` to
`max_requests`; it performs **no bounds check** on `max_requests`,
`window_seconds`, or `burst_size`. Two degenerate configs crash the module:

- **`window_seconds == 0`** → `TokenBucket.__init__` computes
  `_refill_rate = config.max_requests / config.window_seconds` and raises
  `ZeroDivisionError` at construction time (the first `can_request` /
  `get_status` / `get_wait_time` call that lazily creates the bucket).
- **`max_requests <= 0`** → `_refill_rate == 0` (or negative). Construction
  succeeds, but the first `wait_time()` (`(1.0 - _tokens) / _refill_rate`) or
  `status()` (`(_burst_size - _tokens) / _refill_rate`) call raises
  `ZeroDivisionError`. With `max_requests == 0` the bucket also starts at
  `_tokens = 0.0`, so `acquire()` is permanently `False` and
  `wait_for_request()` spins until `timeout` before returning `False`.

A negative `window_seconds` is equally unguarded: it makes `_refill_rate`
negative, so `_refill()` *decreases* `_tokens` over time (the budget drains
instead of refilling) and `wait_time()` / `status()` compute a negative
wait / a `reset_at` in the past.

This is the single most important hole in the module: the config is the only
input surface, and the two most natural "tight limit" values (`window_seconds
== 0` for "no window", `max_requests == 0` for "block all") are exactly the
ones that crash rather than degrade. A defensible contract: `__post_init__`
validates `max_requests >= 1`, `window_seconds > 0`, and
`burst_size >= 1` (raising `ValueError` on violation), so a degenerate config
fails fast at construction with a clear message instead of a
`ZeroDivisionError` deep in the request path.

### Secondary holes (documented, not separately ticketed)

- **`_max_tokens` is a dead field.** `TokenBucket.__init__` assigns
  `_max_tokens = config.max_requests` but no method ever reads it; the
  effective cap is `_burst_size`. It is misleading state.
- **`burst_size` is unbounded relative to `max_requests`.** A `burst_size`
  larger than `max_requests` lets the bucket start with more tokens than the
  steady-state rate can sustain (a legitimate burst, but undocumented); a
  `burst_size` of `0` or negative makes `acquire()` permanently `False`
  without any error.
- **`set_domain_config` / `reset_domain` discard in-flight tokens.** Both
  replace the bucket with a fresh one, so any tokens the old bucket held are
  lost silently (a config change mid-crawl resets the budget).
