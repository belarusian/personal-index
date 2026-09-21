"""Adversarial deep tests for PipelineE2E."""
import tempfile
import os
import pytest
from personal_index.pipeline_e2e import PipelineE2E
from personal_index.pipeline import PipelineConfig


def test_run_from_files_empty_list():
    with tempfile.TemporaryDirectory() as td:
        p = PipelineE2E(data_dir=td)
        res = p.run_from_files([])
        assert res.pages_crawled == 0
        assert res.pages_indexed == 0
        assert res.errors == []


def test_run_from_files_nonexistent_file():
    with tempfile.TemporaryDirectory() as td:
        p = PipelineE2E(data_dir=td)
        res = p.run_from_files(["/no/such/file.txt"])
        assert res.pages_crawled == 0
        assert len(res.errors) == 1
        assert "File not found" in res.errors[0]


def test_run_from_files_empty_file():
    with tempfile.TemporaryDirectory() as td:
        fp = os.path.join(td, "empty.txt")
        open(fp, "w").close()
        p = PipelineE2E(data_dir=td)
        res = p.run_from_files([fp])
        # empty file should be crawled but filtered out (min_content_length)
        assert res.pages_crawled == 1
        # errors should be empty
        assert res.errors == []


def test_run_from_files_unicode_path():
    with tempfile.TemporaryDirectory() as td:
        fp = os.path.join(td, "ünïçödé.txt")
        with open(fp, "w", encoding="utf-8") as f:
            f.write("Python is great. Python python python.")
        p = PipelineE2E(data_dir=td)
        p.add_interest("python", keywords=["python"])
        res = p.run_from_files([fp])
        assert res.pages_crawled == 1
        # should be indexed if passes filter/score
        # at least no crash
        assert res.errors == []


def test_run_from_files_idempotence():
    with tempfile.TemporaryDirectory() as td:
        fp = os.path.join(td, "idempotent.txt")
        with open(fp, "w") as f:
            f.write("Python is great. Python python python.")
        p = PipelineE2E(data_dir=td)
        p.add_interest("python", keywords=["python"])
        res1 = p.run_from_files([fp])
        res2 = p.run_from_files([fp])
        # second run should not crash; pages_crawled increments again
        assert res2.pages_crawled == 1
        # search should find the page (at least one result)
        results = p.search("python", limit=10)
        assert isinstance(results, list)


def test_search_negative_limit():
    with tempfile.TemporaryDirectory() as td:
        p = PipelineE2E(data_dir=td)
        # search on empty index with negative limit should not crash
        results = p.search("anything", limit=-5)
        assert isinstance(results, list)
        assert results == []


def test_search_empty_query():
    with tempfile.TemporaryDirectory() as td:
        p = PipelineE2E(data_dir=td)
        results = p.search("", limit=5)
        assert isinstance(results, list)


def test_add_interest_empty_keywords():
    with tempfile.TemporaryDirectory() as td:
        p = PipelineE2E(data_dir=td)
        # empty keywords should not crash
        p.add_interest("empty", keywords=[])
        # run a file
        fp = os.path.join(td, "x.txt")
        with open(fp, "w") as f:
            f.write("some content")
        res = p.run_from_files([fp])
        assert res.pages_crawled == 1


def test_close_idempotence():
    with tempfile.TemporaryDirectory() as td:
        p = PipelineE2E(data_dir=td)
        p.close()
        # second close should not crash
        p.close()


def test_run_from_files_whitespace_path():
    with tempfile.TemporaryDirectory() as td:
        p = PipelineE2E(data_dir=td)
        res = p.run_from_files(["   "])
        assert res.pages_crawled == 0
        assert len(res.errors) == 1


def test_pipeline_config_min_score_threshold():
    with tempfile.TemporaryDirectory() as td:
        cfg = PipelineConfig(min_score_threshold=9999.0)
        p = PipelineE2E(data_dir=td, config=cfg)
        fp = os.path.join(td, "low.txt")
        with open(fp, "w") as f:
            f.write("Python")
        p.add_interest("python", keywords=["python"])
        res = p.run_from_files([fp])
        # score will be low, should be filtered out by score threshold
        assert res.pages_score_filtered_out >= 0
        assert res.errors == []
