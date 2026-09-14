"""Cycle 210 - VALIDATOR VERIFY pass for ARCH-33/36/37/39/40/41.

Each ticket is at `Status: IMPLEMENTED`. This file runs the ticket's
pinning behavior against current main plus ONE adversarial input the
contract implies. If the code matches the contract the ticket flips to
`Status: VERIFIED`; a red test here would instead be filed as a QA ticket
and pinned xfail-strict (validator role: no product-code fixes).
"""

from __future__ import annotations

import json
import logging

import pytest

from personal_index.bookmarks import Bookmark, BookmarkManager
from personal_index.content_enricher import ContentEnricher
from personal_index.rate_limiter import RateLimitConfig, TokenBucket
from personal_index.models import IndexedPage
from personal_index.storage import Storage
from personal_index.tags import TagStore
from personal_index.url_dedup import URLDeduplicator


# ── ARCH-33: content_enricher batch_enrich passes HTML through ──────────

def test_arch33_batch_enrich_passes_html_through():
    """Adversarial: a 3-tuple item must yield the SAME has_* flags as the
    single enrich path for the same (title, text, html)."""
    e = ContentEnricher()
    title = "t"
    text = "some body text"
    html = "<pre>code</pre><a href='x'>l</a><img src='i'>"
    single = e.enrich(title, text, html)
    assert single.has_code is True
    assert single.has_links is True
    assert single.has_images is True
    batch = e.batch_enrich([(title, text, html)])
    assert len(batch) == 1
    assert batch[0].has_code is True
    assert batch[0].has_links is True
    assert batch[0].has_images is True


def test_arch33_batch_enrich_2tuple_backcompat_flags_false():
    """Adversarial: a 2-tuple item is html=None -> flags stay False (default)."""
    e = ContentEnricher()
    batch = e.batch_enrich([("t", "body")])
    assert batch[0].has_code is False
    assert batch[0].has_links is False
    assert batch[0].has_images is False


# ── ARCH-36: url_dedup get_duplicates/get_stats report detected dups ────

def test_arch36_get_duplicates_reports_exact_duplicate():
    d = URLDeduplicator()
    d.add_url("https://a.com/x")
    r = d.add_url("https://a.com/x/")  # normalizes identically -> exact dup
    assert r.is_duplicate is True
    dups = d.get_duplicates()
    assert dups == {"https://a.com/x": ["https://a.com/x/"]}
    assert d.get_stats()["total_duplicate_groups"] == 1


def test_arch36_get_duplicates_reports_fuzzy_duplicate():
    d = URLDeduplicator(fuzzy_threshold=0.5)
    d.add_url("https://a.com/article-1")
    r = d.add_url("https://a.com/article-11")  # same domain, high path ratio
    assert r.is_duplicate is True
    assert r.reason == "fuzzy_match"
    dups = d.get_duplicates()
    assert dups == {"https://a.com/article-1": ["https://a.com/article-11"]}
    assert d.get_stats()["total_duplicate_groups"] == 1


def test_arch36_clear_resets_recorded_duplicates():
    d = URLDeduplicator()
    d.add_url("https://a.com/x")
    d.add_url("https://a.com/x/")
    assert d.get_duplicates() != {}
    d.clear()
    assert d.get_duplicates() == {}
    assert d.get_stats()["total_duplicate_groups"] == 0


# ── ARCH-37: rate_limiter config validation fails fast with ValueError ──

@pytest.mark.parametrize(
    "kwargs",
    [
        {"max_requests": 0},
        {"window_seconds": 0},
        {"burst_size": 0},
        {"max_requests": -1},
        {"window_seconds": -5},
    ],
)
def test_arch37_config_degenerate_raises_valueerror(kwargs):
    with pytest.raises(ValueError):
        RateLimitConfig(**kwargs)


def test_arch37_valid_config_constructs_and_bucket_runs():
    cfg = RateLimitConfig(max_requests=5, window_seconds=10)
    assert cfg.burst_size == 5  # None -> max_requests normalization
    bucket = TokenBucket(cfg)
    assert bucket.acquire() is True
    assert bucket.wait_time() >= 0.0
    st = bucket.status()
    assert st.remaining >= 0


# ── ARCH-39: bookmarks load merge mode ──────────────────────────────────

def test_arch39_load_merge_preserves_created_at_and_upserts(tmp_path):
    path = tmp_path / "bm.json"
    file_bms = [
        {"url": "https://a.com", "title": "file-title", "created_at": "2020-01-01T00:00:00+00:00"},
        {"url": "https://file-only.com", "title": "fo", "created_at": "2021-01-01T00:00:00+00:00"},
    ]
    path.write_text(json.dumps(file_bms))
    mgr = BookmarkManager()
    mem = Bookmark(url="https://a.com", title="mem-title", created_at="2019-05-05T00:00:00+00:00")
    mgr.add(mem)
    mgr.add(Bookmark(url="https://mem-only.com", title="mo", created_at="2018-01-01T00:00:00+00:00"))
    n = mgr.load(str(path), merge=True)
    assert n == 2  # number read from file
    a = mgr.get("https://a.com")
    assert a is not None
    assert a.created_at == "2019-05-05T00:00:00+00:00"  # preserved on collision
    assert a.title == "file-title"  # upserted
    assert mgr.get("https://mem-only.com") is not None  # memory-only kept
    assert mgr.get("https://file-only.com") is not None  # file-only added


def test_arch39_load_default_replaces(tmp_path):
    path = tmp_path / "bm.json"
    path.write_text(json.dumps([{"url": "https://file.com", "title": "f"}]))
    mgr = BookmarkManager()
    mgr.add(Bookmark(url="https://unsaved.com", title="u"))
    n = mgr.load(str(path))  # default merge=False
    assert n == 1
    assert mgr.get("https://unsaved.com") is None  # unsaved discarded
    assert mgr.get("https://file.com") is not None


def test_arch39_load_merge_guard_paths_untouched(tmp_path):
    mgr = BookmarkManager()
    mgr.add(Bookmark(url="https://keep.com", title="k"))
    # missing file
    assert mgr.load(str(tmp_path / "nope.json"), merge=True) == 0
    assert mgr.get("https://keep.com") is not None
    # malformed JSON
    bad = tmp_path / "bad.json"
    bad.write_text("{not json")
    assert mgr.load(str(bad), merge=True) == 0
    assert mgr.get("https://keep.com") is not None
    # non-list top level
    nl = tmp_path / "nl.json"
    nl.write_text(json.dumps({"url": "x"}))
    assert mgr.load(str(nl), merge=True) == 0
    assert mgr.get("https://keep.com") is not None


def test_arch39_load_no_path_raises_valueerror():
    mgr = BookmarkManager()
    with pytest.raises(ValueError):
        mgr.load()
    with pytest.raises(ValueError):
        mgr.load(merge=True)


# ── ARCH-40: storage atomic write + corruption recovery from backup ─────

def test_arch40_atomic_roundtrip_no_tmp_left(tmp_path):
    s = Storage(data_dir=str(tmp_path))
    s.add_page(IndexedPage(url="https://x.com", title="X"))
    got = s.get_page("https://x.com")
    assert got is not None
    assert got.title == "X"
    assert not list(tmp_path.glob("*.tmp"))


def test_arch40_corrupt_target_recovers_from_backup(tmp_path, caplog):
    s = Storage(data_dir=str(tmp_path))
    s.add_page(IndexedPage(url="https://x.com", title="X"))
    # simulate interrupted write: valid .bak, truncated target
    bak = tmp_path / "pages.json.bak"
    bak.write_text(json.dumps([IndexedPage(url="https://x.com", title="X").to_dict()]))
    (tmp_path / "pages.json").write_text('{"truncated": [1,')
    with caplog.at_level(logging.WARNING):
        pages = s.get_pages()
    assert len(pages) == 1
    assert pages[0].url == "https://x.com"
    assert pages[0].title == "X"
    assert any("corrupt" in r.message.lower() for r in caplog.records)


def test_arch40_corrupt_target_no_backup_returns_default(tmp_path):
    d = tmp_path / "d"
    d.mkdir()
    (d / "interests.json").write_text("[]")
    (d / "config.json").write_text("{}")
    (d / "pages.json").write_text('{"truncated": [1,')
    s = Storage(data_dir=str(d))
    assert s.get_pages() == []


# ── ARCH-41: tags create_tag preserves created_at on collision ──────────

def test_arch41_create_tag_collision_preserves_created_at(tmp_path):
    ts = TagStore(store_path=str(tmp_path / "t.json"))
    first = ts.create_tag("python", color="#111111", description="d1")
    ts.add_tag_to_page("https://p.com", "python")
    second = ts.create_tag("python", color="#222222", description="d2")
    assert second.created_at == first.created_at  # preserved, not reset
    assert second.color == "#222222"  # metadata overwritten
    assert second.description == "d2"
    # page association preserved (keys on name)
    assert any(t.name == "python" for t in ts.get_tags_for_page("https://p.com"))
