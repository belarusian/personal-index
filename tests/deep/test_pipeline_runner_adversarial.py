"""Adversarial deep tests for personal_index.pipeline_runner (cycle 207).

pipeline_runner is a never-probed, reachable (cli.py `pipeline`) module with NO
dedicated docs page, so its docstrings are the contract. The contracts under
attack:

- PipelineStats.summary(): a well-formed, human-readable multi-line summary
  that never crashes on negative / huge / unicode field values.
- PipelineRunner.add_page_directly(page): returns False for empty /
  whitespace / below-min-content / below-min-title pages and for pages whose
  score is below min_score_threshold; returns True for a well-formed page.
- PipelineRunner.run_from_files(paths): reads local files into the pipeline;
  a missing file / directory / empty file is recorded as an error, not a
  crash; a real text/HTML file flows through all six stages.
- PipelineRunner.run(seed_urls, stages=...): an empty seed list and an
  unknown stage name degrade gracefully (no stage runs, no crash).
- progress_callback: both 2-arg and 3-arg signatures are honored.
- End-to-end CLI: `python3 -m personal_index pipeline --import-file ...`.

All tests are regression armor (no defects found this cycle).
"""

from __future__ import annotations

import os
import subprocess
import sys

import pytest

from personal_index.config.pipeline_config import PipelineConfig
from personal_index.models import CrawledPage
from personal_index.pipeline_runner import PipelineRunner, PipelineStats

# A content string comfortably above the default min_content_length (10) and
# a title above the default min_title_length (3).
_GOOD_CONTENT = (
    "This is a long enough content string for the pipeline to process "
    "properly with plenty of words to clear the minimum length gate."
)
_GOOD_TITLE = "Hello World"


def _page(url: str = "http://x/c", title: str = _GOOD_TITLE,
          content: str = _GOOD_CONTENT) -> CrawledPage:
    return CrawledPage(url=url, title=title, content=content)


@pytest.fixture
def runner(tmp_path):
    r = PipelineRunner(data_dir=str(tmp_path / "dd"))
    yield r
    r.close()


# ---------------------------------------------------------------------------
# PipelineStats.summary
# ---------------------------------------------------------------------------

def test_summary_default_is_well_formed():
    s = PipelineStats()
    out = s.summary()
    assert out.startswith("Pipeline Summary")
    for label in ("Crawled:", "Extracted:", "Filtered in:", "Filtered out:",
                  "Scored:", "Tagged:", "Tags applied:", "Indexed:",
                  "Errors:", "Time:"):
        assert label in out
    # 12 lines: header + rule + 10 stat lines
    assert len(out.splitlines()) == 12


def test_summary_reflects_field_values():
    s = PipelineStats()
    s.pages_crawled = 7
    s.pages_indexed = 3
    s.errors = ["e1", "e2"]
    s.elapsed_seconds = 1.5
    out = s.summary()
    assert "Crawled:      7" in out
    assert "Indexed:      3" in out
    assert "Errors:       2" in out
    assert "Time:         1.5s" in out


def test_summary_negative_counter_does_not_crash():
    s = PipelineStats()
    s.pages_crawled = -5
    out = s.summary()
    assert "Crawled:      -5" in out


def test_summary_huge_elapsed_formats_to_one_decimal():
    s = PipelineStats()
    s.elapsed_seconds = 12345.678
    out = s.summary()
    assert "Time:         12345.7s" in out


def test_summary_unicode_errors_do_not_crash():
    s = PipelineStats()
    s.errors = ["ünïcödé 错误", "emoji 🚀"]
    out = s.summary()
    assert "Errors:       2" in out


# ---------------------------------------------------------------------------
# PipelineRunner construction
# ---------------------------------------------------------------------------

def test_construct_creates_data_dirs(tmp_path):
    dd = tmp_path / "dd"
    PipelineRunner(data_dir=str(dd))
    assert (dd / "cache").is_dir()
    assert (dd / "archive").is_dir()
    assert (dd / "backups").is_dir()


def test_construct_default_config(tmp_path):
    r = PipelineRunner(data_dir=str(tmp_path / "dd"))
    assert r.pipeline_config.min_content_length == 10
    assert r.pipeline_config.min_score_threshold == 0.0
    r.close()


def test_construct_custom_config(tmp_path):
    cfg = PipelineConfig(min_score_threshold=0.5, min_content_length=50)
    r = PipelineRunner(data_dir=str(tmp_path / "dd"), pipeline_config=cfg)
    assert r.pipeline_config.min_score_threshold == 0.5
    assert r.pipeline_config.min_content_length == 50
    r.close()


# ---------------------------------------------------------------------------
# add_page_directly
# ---------------------------------------------------------------------------

def test_add_page_directly_empty_content_returns_false(runner):
    assert runner.add_page_directly(_page(content="")) is False


def test_add_page_directly_whitespace_content_returns_false(runner):
    assert runner.add_page_directly(_page(content="   \t\n  ")) is False


def test_add_page_directly_short_content_returns_false(runner):
    # below default min_content_length (10)
    assert runner.add_page_directly(_page(content="tiny")) is False


def test_add_page_directly_short_title_returns_false(runner):
    # below default min_title_length (3)
    assert runner.add_page_directly(_page(title="Hi")) is False


def test_add_page_directly_three_char_title_returns_true(runner):
    assert runner.add_page_directly(_page(title="Hi!")) is True


def test_add_page_directly_good_page_returns_true(runner):
    assert runner.add_page_directly(_page()) is True


def test_add_page_directly_unicode_page_returns_true(runner):
    p = _page(url="http://x/u", title="Ünïcödé 标题",
              content=_GOOD_CONTENT + " ünïcödé 内容 here")
    assert runner.add_page_directly(p) is True


def test_add_page_directly_high_threshold_returns_false(tmp_path):
    cfg = PipelineConfig(min_score_threshold=0.99)
    r = PipelineRunner(data_dir=str(tmp_path / "dd"), pipeline_config=cfg)
    try:
        assert r.add_page_directly(_page()) is False
    finally:
        r.close()


def test_add_page_directly_duplicate_is_idempotent(runner):
    p = _page()
    assert runner.add_page_directly(p) is True
    assert runner.add_page_directly(p) is True
    # The search index holds the page exactly once (dedup by url).
    urls = [pg.url for pg in runner._search_index.list_pages()]
    assert urls.count("http://x/c") == 1


# ---------------------------------------------------------------------------
# run_from_files
# ---------------------------------------------------------------------------

def _write(path, text):
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(text)


def test_run_from_files_real_text_file(tmp_path):
    r = PipelineRunner(data_dir=str(tmp_path / "dd"))
    f = tmp_path / "note.txt"
    _write(f, _GOOD_CONTENT)
    st = r.run_from_files([str(f)])
    assert st.pages_crawled == 1
    assert st.pages_extracted == 1
    assert st.pages_filtered_in == 1
    assert st.pages_scored == 1
    assert st.pages_indexed == 1
    assert st.errors == []
    r.close()


def test_run_from_files_missing_file_records_error(tmp_path):
    r = PipelineRunner(data_dir=str(tmp_path / "dd"))
    st = r.run_from_files([str(tmp_path / "nope.txt")])
    assert st.pages_crawled == 0
    assert len(st.errors) == 1
    assert "File not found" in st.errors[0]
    r.close()


def test_run_from_files_empty_list(tmp_path):
    r = PipelineRunner(data_dir=str(tmp_path / "dd"))
    st = r.run_from_files([])
    assert st.pages_crawled == 0
    assert st.errors == []
    r.close()


def test_run_from_files_directory_records_error(tmp_path):
    r = PipelineRunner(data_dir=str(tmp_path / "dd"))
    st = r.run_from_files([str(tmp_path)])  # a directory, not a file
    assert st.pages_crawled == 0
    assert len(st.errors) == 1
    r.close()


def test_run_from_files_empty_file_records_error(tmp_path):
    r = PipelineRunner(data_dir=str(tmp_path / "dd"))
    f = tmp_path / "empty.txt"
    _write(f, "")
    st = r.run_from_files([str(f)])
    assert st.pages_crawled == 0
    assert len(st.errors) == 1
    r.close()


def test_run_from_files_whitespace_only_file_records_error(tmp_path):
    r = PipelineRunner(data_dir=str(tmp_path / "dd"))
    f = tmp_path / "ws.txt"
    _write(f, "   \t\n  ")
    st = r.run_from_files([str(f)])
    assert st.pages_crawled == 0
    assert len(st.errors) == 1
    r.close()


def test_run_from_files_html_file(tmp_path):
    r = PipelineRunner(data_dir=str(tmp_path / "dd"))
    f = tmp_path / "page.html"
    _write(f, "<html><head><title>My Title</title></head><body><p>"
              + _GOOD_CONTENT + "</p></body></html>")
    st = r.run_from_files([str(f)])
    assert st.pages_crawled == 1
    assert st.pages_indexed == 1
    assert st.errors == []
    r.close()


def test_run_from_files_unicode_filename(tmp_path):
    r = PipelineRunner(data_dir=str(tmp_path / "dd"))
    f = tmp_path / "ünïcödé_文件.txt"
    _write(f, _GOOD_CONTENT)
    st = r.run_from_files([str(f)])
    assert st.pages_crawled == 1
    assert st.pages_indexed == 1
    r.close()


def test_run_from_files_mixed_good_and_missing(tmp_path):
    r = PipelineRunner(data_dir=str(tmp_path / "dd"))
    good = tmp_path / "good.txt"
    _write(good, _GOOD_CONTENT)
    st = r.run_from_files([str(good), str(tmp_path / "missing.txt")])
    assert st.pages_crawled == 1
    assert len(st.errors) == 1
    r.close()


# ---------------------------------------------------------------------------
# run()
# ---------------------------------------------------------------------------

def test_run_empty_seed_urls(tmp_path):
    r = PipelineRunner(data_dir=str(tmp_path / "dd"))
    st = r.run([])
    assert st.pages_crawled == 0
    assert st.errors == []
    r.close()


def test_run_unknown_stage_degrades_gracefully(tmp_path):
    r = PipelineRunner(data_dir=str(tmp_path / "dd"))
    st = r.run(["http://example.com"], stages={"bogus_stage"})
    # No known stage is in the set, so nothing runs and nothing crashes.
    assert st.pages_crawled == 0
    assert st.pages_indexed == 0
    assert st.errors == []
    r.close()


def test_run_index_only_stage_subset(tmp_path):
    r = PipelineRunner(data_dir=str(tmp_path / "dd"))
    st = r.run(["http://example.com"], stages={"index"})
    assert st.pages_crawled == 0
    assert st.pages_indexed == 0
    r.close()


# ---------------------------------------------------------------------------
# progress_callback
# ---------------------------------------------------------------------------

def test_progress_callback_two_arg(tmp_path):
    calls = []

    def cb(stage, count):
        calls.append((stage, count))

    r = PipelineRunner(data_dir=str(tmp_path / "dd"), progress_callback=cb)
    f = tmp_path / "note.txt"
    _write(f, _GOOD_CONTENT)
    r.run_from_files([str(f)])
    assert len(calls) > 0
    assert all(len(c) == 2 for c in calls)
    assert calls[0] == ("crawl", 0)
    r.close()


def test_progress_callback_three_arg(tmp_path):
    calls = []

    def cb(stage, count, total):
        calls.append((stage, count, total))

    r = PipelineRunner(data_dir=str(tmp_path / "dd"), progress_callback=cb)
    f = tmp_path / "note.txt"
    _write(f, _GOOD_CONTENT)
    r.run_from_files([str(f)])
    assert len(calls) > 0
    assert all(len(c) == 3 for c in calls)
    assert calls[0] == ("crawl", 0, 1)
    r.close()


def test_progress_callback_none_is_noop(tmp_path):
    r = PipelineRunner(data_dir=str(tmp_path / "dd"), progress_callback=None)
    f = tmp_path / "note.txt"
    _write(f, _GOOD_CONTENT)
    st = r.run_from_files([str(f)])
    assert st.pages_indexed == 1
    r.close()


# ---------------------------------------------------------------------------
# End-to-end CLI
# ---------------------------------------------------------------------------

def test_cli_pipeline_import_file_end_to_end(tmp_path):
    f = tmp_path / "note.txt"
    _write(f, _GOOD_CONTENT)
    dd = tmp_path / "dd"
    proc = subprocess.run(
        [sys.executable, "-m", "personal_index", "pipeline",
         "--import-file", str(f), "--data-dir", str(dd)],
        capture_output=True, text=True, cwd=os.getcwd(),
    )
    assert proc.returncode == 0, proc.stderr
    assert "Imported: 1 file(s)" in proc.stdout
    assert "Crawled:      1" in proc.stdout
    assert "Indexed:      1" in proc.stdout
    assert "Errors:       0" in proc.stdout
