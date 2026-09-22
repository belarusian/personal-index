"""Adversarial deep tests for pipeline_orchestrator INTERNAL helpers.

The e2e file (test_pipeline_orchestrator_e2e_adversarial.py) pins the
file-based end-to-end flow and the stats file pins the counter invariants.
This file pins the INTERNAL helpers those two files do NOT reach directly:

  - PipelineResult.summary()  (str projection, empty vs populated)
  - _score_page               (neutral score, interest match, empty content)
  - _tag_page                 (empty / unicode / over-long / duplicate tags)
  - _read_file_as_page        (missing -> None, empty file, markdown title)
  - _ensure_dirs / _init_stores idempotence (call twice, no crash)
  - close() idempotence       (call twice, no error)
  - run() / run_from_files()  with empty seed_urls / empty filepaths
  - search() limit=0 / negative / empty / whitespace query

All pins are regression armor: they must PASS on current main.
"""

import os
import tempfile

import pytest

from personal_index.models import CrawledPage, Interest
from personal_index.pipeline_orchestrator import PipelineOrchestrator, PipelineResult


@pytest.fixture
def tmp_data_dir():
    with tempfile.TemporaryDirectory() as d:
        yield d


@pytest.fixture
def orchestrator(tmp_data_dir):
    return PipelineOrchestrator(data_dir=tmp_data_dir)


# ---------------------------------------------------------------------------
# PipelineResult.summary()
# ---------------------------------------------------------------------------

def test_summary_empty_result_is_str_projection():
    """summary() on a default (empty) PipelineResult is a non-empty str."""
    s = PipelineResult().summary()
    assert isinstance(s, str)
    assert s.startswith("Pipeline Result")
    # Every stat line is present in the projection.
    for label in (
        "Pages crawled",
        "Pages extracted",
        "Pages filtered",
        "Pages scored",
        "Pages tagged",
        "Pages indexed",
        "Tags applied",
        "Errors",
        "Time",
    ):
        assert label in s


def test_summary_populated_reflects_stats():
    """summary() reflects populated stats (crawled count appears)."""
    result = PipelineResult()
    result.stats.pages_crawled = 7
    result.errors = ["boom"]
    s = result.summary()
    assert "Pages crawled:    7" in s
    assert "Errors:           1" in s


# ---------------------------------------------------------------------------
# _score_page
# ---------------------------------------------------------------------------

def test_score_page_neutral_when_no_interests(orchestrator):
    """With no interests configured, _score_page returns the neutral 0.5."""
    page = CrawledPage(url="http://x", title="t", content="hello world foo bar")
    assert orchestrator._score_page(page) == 0.5


def test_score_page_interest_match_populates_matched_interests(orchestrator):
    """A keyword match raises the score above neutral and records the interest."""
    orchestrator.interest_store.add(
        Interest(name="python", keywords=["python", "django"])
    )
    page = CrawledPage(
        url="http://y", title="t", content="I love python and django"
    )
    score = orchestrator._score_page(page)
    assert score > 0.5
    assert "python" in page.matched_interests


def test_score_page_empty_content_is_finite(orchestrator):
    """Empty content must not crash and must yield a finite score."""
    page = CrawledPage(url="http://z", title="t", content="")
    score = orchestrator._score_page(page)
    assert isinstance(score, float)
    assert score == score  # not NaN


# ---------------------------------------------------------------------------
# _tag_page
# ---------------------------------------------------------------------------

def test_tag_page_empty_content_returns_list(orchestrator):
    """Empty content yields a list (possibly empty), never crashes."""
    page = CrawledPage(url="http://e", title="", content="")
    tags = orchestrator._tag_page(page)
    assert isinstance(tags, list)


def test_tag_page_unicode_content_no_crash(orchestrator):
    """Unicode title/content must not crash and returns a list of str."""
    page = CrawledPage(url="http://u", title="テスト", content="日本語のテキスト python")
    tags = orchestrator._tag_page(page)
    assert isinstance(tags, list)
    assert all(isinstance(t, str) for t in tags)


def test_tag_page_over_long_content_bounded(orchestrator):
    """Over-long content returns a bounded tag list (max_keywords=5 cap)."""
    page = CrawledPage(url="http://l", title="long", content="python " * 5000)
    tags = orchestrator._tag_page(page)
    assert isinstance(tags, list)
    assert len(tags) <= 10  # interest tags + up to 5 keyword tags


def test_tag_page_interest_match_includes_interest_name(orchestrator):
    """A matching interest contributes its name to the tag list."""
    orchestrator.interest_store.add(
        Interest(name="python", keywords=["python"])
    )
    page = CrawledPage(url="http://w", title="Python guide", content="python django")
    tags = orchestrator._tag_page(page)
    assert "python" in tags


# ---------------------------------------------------------------------------
# _read_file_as_page
# ---------------------------------------------------------------------------

def test_read_file_as_page_missing_returns_none(orchestrator):
    """A missing file returns None (OSError path)."""
    assert orchestrator._read_file_as_page("/nonexistent/nope.txt") is None


def test_read_file_as_page_empty_file(orchestrator, tmp_data_dir):
    """An empty file yields a page with empty content and word_count 0."""
    path = os.path.join(tmp_data_dir, "empty.txt")
    with open(path, "w") as f:
        f.write("")
    page = orchestrator._read_file_as_page(path)
    assert page is not None
    assert page.content == ""
    assert page.word_count == 0


def test_read_file_as_page_markdown_title(orchestrator, tmp_data_dir):
    """A leading '# ' line becomes the title; word_count reflects content."""
    path = os.path.join(tmp_data_dir, "md.txt")
    with open(path, "w") as f:
        f.write("# My Title\nbody text here")
    page = orchestrator._read_file_as_page(path)
    assert page is not None
    assert page.title == "My Title"
    assert page.word_count > 0


def test_read_file_as_page_non_markdown_title_is_basename(orchestrator, tmp_data_dir):
    """Without a leading '# ', the title falls back to the basename."""
    path = os.path.join(tmp_data_dir, "plain.txt")
    with open(path, "w") as f:
        f.write("just some body text")
    page = orchestrator._read_file_as_page(path)
    assert page is not None
    assert page.title == "plain.txt"


# ---------------------------------------------------------------------------
# _ensure_dirs / _init_stores idempotence
# ---------------------------------------------------------------------------

def test_ensure_dirs_idempotent(orchestrator, tmp_data_dir):
    """Calling _ensure_dirs twice does not crash and keeps the subdirs."""
    orchestrator._ensure_dirs(tmp_data_dir)
    orchestrator._ensure_dirs(tmp_data_dir)
    for sub in ("cache", "archive", "backups"):
        assert os.path.isdir(os.path.join(tmp_data_dir, sub))


def test_init_stores_idempotent(orchestrator, tmp_data_dir):
    """Calling _init_stores twice does not crash and re-binds the stores."""
    orchestrator._init_stores(tmp_data_dir)
    orchestrator._init_stores(tmp_data_dir)
    assert orchestrator.interest_store is not None
    assert orchestrator.tag_store is not None
    assert orchestrator.search_index is not None


# ---------------------------------------------------------------------------
# close() idempotence
# ---------------------------------------------------------------------------

def test_close_idempotent(orchestrator):
    """Calling close() twice does not raise."""
    orchestrator.close()
    orchestrator.close()  # no error


# ---------------------------------------------------------------------------
# run() / run_from_files() with empty inputs
# ---------------------------------------------------------------------------

def test_run_empty_seed_urls(orchestrator):
    """run([]) succeeds with zero crawled pages and no errors."""
    result = orchestrator.run([])
    assert result.success is True
    assert result.stats.pages_crawled == 0
    assert result.errors == []


def test_run_from_files_empty(orchestrator):
    """run_from_files([]) succeeds with zero crawled pages and no errors."""
    result = orchestrator.run_from_files([])
    assert result.success is True
    assert result.stats.pages_crawled == 0
    assert result.errors == []


# ---------------------------------------------------------------------------
# search() limit / query edges (empty index)
# ---------------------------------------------------------------------------

def test_search_zero_limit_empty_index(orchestrator):
    """search with limit=0 returns an empty list."""
    assert orchestrator.search("python", limit=0) == []


def test_search_negative_limit_empty_index(orchestrator):
    """search with a negative limit returns an empty list."""
    assert orchestrator.search("python", limit=-5) == []


def test_search_empty_query_empty_index(orchestrator):
    """search with an empty query returns an empty list."""
    assert orchestrator.search("") == []


def test_search_whitespace_query_empty_index(orchestrator):
    """search with a whitespace-only query returns an empty list."""
    assert orchestrator.search("   ") == []
