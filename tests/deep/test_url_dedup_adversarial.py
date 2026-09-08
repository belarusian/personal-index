"""Adversarial deep tests for personal_index.url_dedup (URLDeduplicator).

Cycle 147 - VALIDATOR probe.

Targets (never-probed subsystem in tests/deep/):
  - URLDeduplicator.normalize_url: the exact-contract docstring pins the
    ORDER and CONTENT of normalization: drop fragment; strip trailing slash
    from a non-root path; sort query params alphabetically (first value
    only); lowercase scheme + netloc; remove leading www.; remove tracking
    params (utm_*, fbclid, gclid).
  - seen_count: read-only, int, no mutation.
  - check_duplicate / add_url: exact vs fuzzy vs unique; idempotence.
  - deduplicate_urls: order + per-item results; empty list.
  - get_canonical_url / get_domain_urls / get_stats / clear.
  - one end-to-end CLI run (installed entry point).
"""

from __future__ import annotations


from personal_index.url_dedup import URLDeduplicator


# --- normalize_url: exact-contract pins ------------------------------------

def test_normalize_drops_fragment():
    d = URLDeduplicator()
    assert d.normalize_url("https://example.com/a#frag") == "https://example.com/a"


def test_normalize_strips_trailing_slash_non_root():
    d = URLDeduplicator()
    assert d.normalize_url("https://example.com/a/") == "https://example.com/a"


def test_normalize_keeps_root_slash():
    d = URLDeduplicator()
    # root path "/" must NOT be stripped to ""
    assert d.normalize_url("https://example.com/") == "https://example.com/"


def test_normalize_sorts_query_params_first_value_only():
    d = URLDeduplicator()
    out = d.normalize_url("https://example.com/?b=2&a=1")
    assert out == "https://example.com/?a=1&b=2"


def test_normalize_lowercases_scheme_and_netloc():
    d = URLDeduplicator()
    assert d.normalize_url("HTTPS://EXAMPLE.COM/Path") == "https://example.com/Path"


def test_normalize_removes_leading_www():
    d = URLDeduplicator()
    assert d.normalize_url("https://www.example.com/a") == "https://example.com/a"


def test_normalize_removes_tracking_params():
    d = URLDeduplicator()
    out = d.normalize_url("https://example.com/a?utm_source=x&b=1&fbclid=y")
    assert out == "https://example.com/a?b=1"


def test_normalize_removes_all_tracking_leaves_bare():
    d = URLDeduplicator()
    out = d.normalize_url("https://example.com/a?utm_source=x&gclid=y")
    assert out == "https://example.com/a"


def test_normalize_combines_all_steps():
    d = URLDeduplicator()
    # fragment + trailing slash + unsorted query + uppercase + www + tracking
    out = d.normalize_url("HTTPS://WWW.Example.com/Path/?utm_source=x&B=2&a=1#frag")
    assert out == "https://example.com/Path?B=2&a=1"


def test_normalize_idempotent():
    d = URLDeduplicator()
    url = "HTTPS://WWW.Example.com/Path/?utm_source=x&B=2&a=1#frag"
    once = d.normalize_url(url)
    twice = d.normalize_url(once)
    assert once == twice


def test_normalize_no_query_unchanged():
    d = URLDeduplicator()
    assert d.normalize_url("https://example.com/a") == "https://example.com/a"


def test_normalize_empty_string():
    d = URLDeduplicator()
    # empty input: urlparse yields empty; must not crash
    assert d.normalize_url("") == ""


# --- seen_count: read-only, int, no mutation --------------------------------

def test_seen_count_is_int_and_readonly():
    d = URLDeduplicator()
    assert isinstance(d.seen_count, int)
    assert d.seen_count == 0
    d.add_url("https://example.com/a")
    assert d.seen_count == 1
    # reading must not mutate
    _ = d.seen_count
    assert d.seen_count == 1


# --- check_duplicate / add_url ---------------------------------------------

def test_add_url_unique_not_duplicate():
    d = URLDeduplicator()
    r = d.add_url("https://example.com/a")
    assert r.is_duplicate is False
    assert r.reason == "unique"


def test_add_url_exact_duplicate():
    d = URLDeduplicator()
    d.add_url("https://example.com/a")
    r = d.add_url("https://example.com/a#frag")  # normalizes to same
    assert r.is_duplicate is True
    assert r.reason == "exact_match"
    assert r.similarity_score == 1.0


def test_add_url_duplicate_does_not_inflate_seen_count():
    d = URLDeduplicator()
    d.add_url("https://example.com/a")
    d.add_url("https://example.com/a")
    assert d.seen_count == 1


def test_check_duplicate_is_readonly():
    d = URLDeduplicator()
    d.add_url("https://example.com/a")
    before = d.seen_count
    r = d.check_duplicate("https://example.com/a")
    assert r.is_duplicate is True
    assert d.seen_count == before


def test_add_url_idempotent_state():
    d = URLDeduplicator()
    d.add_url("https://example.com/a")
    d.add_url("https://example.com/a")
    d.add_url("https://example.com/a")
    assert d.seen_count == 1


# --- deduplicate_urls -------------------------------------------------------

def test_deduplicate_urls_empty():
    d = URLDeduplicator()
    unique, results = d.deduplicate_urls([])
    assert unique == []
    assert results == []


def test_deduplicate_urls_preserves_order_and_results():
    d = URLDeduplicator()
    urls = ["https://example.com/a", "https://example.com/b", "https://example.com/a"]
    unique, results = d.deduplicate_urls(urls)
    assert unique == ["https://example.com/a", "https://example.com/b"]
    assert len(results) == 3
    assert results[0].is_duplicate is False
    assert results[1].is_duplicate is False
    assert results[2].is_duplicate is True


def test_deduplicate_urls_all_unique():
    d = URLDeduplicator()
    urls = ["https://example.com/a", "https://example.com/b"]
    unique, results = d.deduplicate_urls(urls)
    assert unique == urls
    assert all(not r.is_duplicate for r in results)


# --- get_canonical_url / get_domain_urls / get_stats / clear ----------------

def test_get_canonical_url_first_seen():
    d = URLDeduplicator()
    d.add_url("https://example.com/a")
    assert d.get_canonical_url("https://example.com/a") == "https://example.com/a"


def test_get_canonical_url_unknown_is_none():
    d = URLDeduplicator()
    assert d.get_canonical_url("https://example.com/never") is None


def test_get_domain_urls():
    d = URLDeduplicator()
    d.add_url("https://example.com/a")
    d.add_url("https://example.com/b")
    assert d.get_domain_urls("example.com") == ["https://example.com/a", "https://example.com/b"]


def test_get_domain_urls_case_insensitive_and_www():
    d = URLDeduplicator()
    d.add_url("https://www.example.com/a")
    assert d.get_domain_urls("WWW.Example.com") == ["https://www.example.com/a"]


def test_get_domain_urls_unknown_empty():
    d = URLDeduplicator()
    assert d.get_domain_urls("nope.com") == []


def test_get_stats_shape():
    d = URLDeduplicator()
    d.add_url("https://example.com/a")
    s = d.get_stats()
    assert s["total_seen"] == 1
    assert s["total_domains"] == 1
    assert s["total_duplicate_groups"] == 0


def test_clear_resets_state():
    d = URLDeduplicator()
    d.add_url("https://example.com/a")
    d.clear()
    assert d.seen_count == 0
    assert d.get_domain_urls("example.com") == []
    assert d.get_canonical_url("https://example.com/a") is None


# --- end-to-end CLI ---------------------------------------------------------

def test_end_to_end_cli_init_and_export(tmp_path):
    """End-to-end: init + export on an empty index (exit 0, no crash)."""
    from click.testing import CliRunner

    from personal_index.cli import main

    dd = str(tmp_path / "data")
    runner = CliRunner()
    r = runner.invoke(main, ["init", "--data-dir", dd])
    assert r.exit_code == 0, r.output
    r = runner.invoke(main, ["export", "--format", "json", "--data-dir", dd])
    assert r.exit_code == 0, r.output
    assert "No indexed content to export." in r.output
