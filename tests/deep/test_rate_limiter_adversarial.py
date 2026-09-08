"""Adversarial deep tests for personal_index.rate_limiter (TokenBucket / RateLimiter).

Probes the token-bucket rate limiter contract: guard inputs (empty/whitespace/
unicode/duplicate domain keys), the documented "can_request consumes a token"
side-effect contract, exhaustion + refill over time, wait_time/status
properties, per-domain isolation, reset idempotence, and one end-to-end run
through the installed CLI.
"""

from __future__ import annotations

import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path

from personal_index.rate_limiter import (
    RateLimitConfig,
    RateLimitStatus,
    RateLimiter,
    TokenBucket,
)


# ---------------------------------------------------------------------------
# RateLimitConfig
# ---------------------------------------------------------------------------

def test_config_defaults():
    c = RateLimitConfig()
    assert c.max_requests == 10
    assert c.window_seconds == 60.0
    assert c.burst_size == 10  # None -> max_requests


def test_config_burst_none_falls_back_to_max():
    c = RateLimitConfig(max_requests=5, burst_size=None)
    assert c.burst_size == 5


def test_config_explicit_burst_preserved():
    c = RateLimitConfig(max_requests=5, burst_size=2)
    assert c.burst_size == 2


# ---------------------------------------------------------------------------
# TokenBucket - basic acquire / exhaustion
# ---------------------------------------------------------------------------

def test_bucket_starts_full_and_consumes():
    b = TokenBucket(RateLimitConfig(max_requests=3, window_seconds=60.0))
    assert b.acquire() is True
    assert b.acquire() is True
    assert b.acquire() is True
    # exhausted
    assert b.acquire() is False


def test_bucket_wait_time_zero_when_full():
    b = TokenBucket(RateLimitConfig(max_requests=3, window_seconds=60.0))
    assert b.wait_time() == 0.0


def test_bucket_wait_time_positive_when_exhausted():
    b = TokenBucket(RateLimitConfig(max_requests=2, window_seconds=10.0))
    b.acquire()
    b.acquire()
    wt = b.wait_time()
    # refill rate = 2/10 = 0.2 tokens/s; need ~1 token -> ~5s
    assert 0.0 < wt <= 5.5


def test_bucket_status_fields():
    b = TokenBucket(RateLimitConfig(max_requests=4, window_seconds=60.0))
    s = b.status()
    assert isinstance(s, RateLimitStatus)
    assert s.limit == 4
    assert s.remaining == 4
    assert s.retry_after == 0.0
    # reset_at is a finite monotonic timestamp (>= now within clock jitter)
    assert s.reset_at >= time.monotonic() - 1.0


def test_bucket_status_remaining_decreases():
    b = TokenBucket(RateLimitConfig(max_requests=4, window_seconds=60.0))
    b.acquire()
    s = b.status()
    assert s.remaining == 3


def test_bucket_refills_over_time():
    b = TokenBucket(RateLimitConfig(max_requests=2, window_seconds=0.1))
    b.acquire()
    b.acquire()
    assert b.acquire() is False
    time.sleep(0.15)  # refill rate 20/s -> ~3 tokens capped at burst 2
    assert b.acquire() is True


def test_bucket_refill_capped_at_burst():
    b = TokenBucket(RateLimitConfig(max_requests=2, window_seconds=0.05))
    time.sleep(0.2)  # far more than enough to overfill
    # should be capped at burst (2 tokens), not unbounded
    assert b.acquire() is True
    assert b.acquire() is True
    assert b.acquire() is False


# ---------------------------------------------------------------------------
# RateLimiter - per-domain isolation + documented consume contract
# ---------------------------------------------------------------------------

def test_limiter_default_config_used():
    rl = RateLimiter()
    assert rl.can_request("example.com") is True


def test_limiter_can_request_consumes_token():
    rl = RateLimiter(RateLimitConfig(max_requests=2, window_seconds=60.0))
    assert rl.can_request("a.com") is True
    assert rl.can_request("a.com") is True
    # budget exhausted -> False, and does NOT consume further
    assert rl.can_request("a.com") is False


def test_limiter_domains_are_isolated():
    rl = RateLimiter(RateLimitConfig(max_requests=1, window_seconds=60.0))
    assert rl.can_request("a.com") is True
    assert rl.can_request("a.com") is False
    # a different domain has its own full budget
    assert rl.can_request("b.com") is True


def test_limiter_set_domain_config():
    rl = RateLimiter()
    rl.set_domain_config("strict.com", RateLimitConfig(max_requests=1, window_seconds=60.0))
    assert rl.can_request("strict.com") is True
    assert rl.can_request("strict.com") is False
    # default domain unaffected
    assert rl.can_request("default.com") is True


def test_limiter_get_status():
    rl = RateLimiter(RateLimitConfig(max_requests=3, window_seconds=60.0))
    rl.can_request("x.com")
    s = rl.get_status("x.com")
    assert isinstance(s, RateLimitStatus)
    assert s.remaining == 2
    assert s.limit == 3


def test_limiter_get_wait_time():
    rl = RateLimiter(RateLimitConfig(max_requests=1, window_seconds=10.0))
    rl.can_request("y.com")
    wt = rl.get_wait_time("y.com")
    assert 0.0 < wt <= 10.5


def test_limiter_reset_domain():
    rl = RateLimiter(RateLimitConfig(max_requests=1, window_seconds=60.0))
    rl.can_request("z.com")
    assert rl.can_request("z.com") is False
    rl.reset_domain("z.com")
    assert rl.can_request("z.com") is True


def test_limiter_reset_all():
    rl = RateLimiter(RateLimitConfig(max_requests=1, window_seconds=60.0))
    rl.can_request("a.com")
    rl.can_request("b.com")
    assert rl.can_request("a.com") is False
    assert rl.can_request("b.com") is False
    rl.reset_all()
    assert rl.can_request("a.com") is True
    assert rl.can_request("b.com") is True


def test_limiter_get_all_statuses():
    rl = RateLimiter(RateLimitConfig(max_requests=2, window_seconds=60.0))
    rl.can_request("a.com")
    rl.can_request("b.com")
    statuses = rl.get_all_statuses()
    assert set(statuses.keys()) == {"a.com", "b.com"}
    assert statuses["a.com"].remaining == 1
    assert statuses["b.com"].remaining == 1


def test_limiter_wait_for_request_returns_true_when_available():
    rl = RateLimiter(RateLimitConfig(max_requests=1, window_seconds=60.0))
    assert rl.wait_for_request("w.com", timeout=1.0) is True


def test_limiter_wait_for_request_times_out_when_exhausted():
    rl = RateLimiter(RateLimitConfig(max_requests=1, window_seconds=60.0))
    rl.can_request("w.com")  # exhaust
    # window is 60s, so refill within a 0.2s timeout is impossible
    assert rl.wait_for_request("w.com", timeout=0.2) is False


# ---------------------------------------------------------------------------
# Guard inputs: empty / whitespace / unicode / duplicate domain keys
# ---------------------------------------------------------------------------

def test_limiter_empty_domain_key_isolated():
    rl = RateLimiter(RateLimitConfig(max_requests=1, window_seconds=60.0))
    assert rl.can_request("") is True
    assert rl.can_request("") is False
    # a real domain is unaffected by the empty-key bucket
    assert rl.can_request("real.com") is True


def test_limiter_whitespace_domain_key():
    rl = RateLimiter(RateLimitConfig(max_requests=1, window_seconds=60.0))
    assert rl.can_request("   ") is True
    assert rl.can_request("   ") is False


def test_limiter_unicode_domain_key():
    rl = RateLimiter(RateLimitConfig(max_requests=1, window_seconds=60.0))
    domain = "exämple.çom"
    assert rl.can_request(domain) is True
    assert rl.can_request(domain) is False
    s = rl.get_status(domain)
    assert s.remaining == 0


def test_limiter_duplicate_domain_reuses_bucket():
    rl = RateLimiter(RateLimitConfig(max_requests=1, window_seconds=60.0))
    assert rl.can_request("dup.com") is True
    # second call to the SAME domain must hit the same (now empty) bucket
    assert rl.can_request("dup.com") is False


def test_limiter_set_domain_config_overwrites_bucket():
    rl = RateLimiter()
    rl.can_request("c.com")  # uses default config bucket
    # reconfiguring the domain resets its bucket to the new config
    rl.set_domain_config("c.com", RateLimitConfig(max_requests=1, window_seconds=60.0))
    assert rl.can_request("c.com") is True
    assert rl.can_request("c.com") is False


# ---------------------------------------------------------------------------
# Idempotence / property checks
# ---------------------------------------------------------------------------

def test_reset_domain_idempotent():
    rl = RateLimiter(RateLimitConfig(max_requests=1, window_seconds=60.0))
    rl.can_request("i.com")
    rl.reset_domain("i.com")
    rl.reset_domain("i.com")  # second reset is a no-op on a fresh bucket
    assert rl.can_request("i.com") is True


def test_reset_all_idempotent():
    rl = RateLimiter(RateLimitConfig(max_requests=1, window_seconds=60.0))
    rl.can_request("a.com")
    rl.reset_all()
    rl.reset_all()
    assert rl.can_request("a.com") is True


def test_status_remaining_never_exceeds_limit():
    rl = RateLimiter(RateLimitConfig(max_requests=3, window_seconds=60.0))
    for _ in range(5):
        s = rl.get_status("p.com")
        assert 0 <= s.remaining <= s.limit


def test_concurrent_acquire_respects_budget():
    """Many threads racing acquire() must never exceed the token budget."""
    budget = 5
    b = TokenBucket(RateLimitConfig(max_requests=budget, window_seconds=60.0))
    granted = []
    lock = threading.Lock()

    def worker():
        if b.acquire():
            with lock:
                granted.append(1)

    threads = [threading.Thread(target=worker) for _ in range(50)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert len(granted) <= budget


# ---------------------------------------------------------------------------
# end-to-end CLI run
# ---------------------------------------------------------------------------

def test_cli_end_to_end_init_import_search():
    with tempfile.TemporaryDirectory() as tmp:
        data_dir = Path(tmp)
        r = subprocess.run(
            [sys.executable, "-m", "personal_index", "init", "--data-dir", str(data_dir)],
            capture_output=True, text=True,
        )
        assert r.returncode == 0, r.stderr
        f = data_dir / "page.html"
        f.write_text("<html><body><h1>python programming</h1><p>python is great</p></body></html>")
        r = subprocess.run(
            [sys.executable, "-m", "personal_index", "import", str(f), "--data-dir", str(data_dir)],
            capture_output=True, text=True,
        )
        assert r.returncode == 0, r.stderr
        r = subprocess.run(
            [sys.executable, "-m", "personal_index", "search", "python", "--data-dir", str(data_dir)],
            capture_output=True, text=True,
        )
        assert r.returncode == 0, r.stderr
        assert "python" in (r.stdout + r.stderr).lower()
