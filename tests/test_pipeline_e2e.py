"""End-to-end pipeline integration tests.

Tests the complete crawl → extract → filter → score → tag → index → search pipeline.
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

import pytest

from personal_index.content_extractor import ContentExtractor
from personal_index.content_filter import ContentFilter, FilterConfig
from personal_index.content_scoring import ContentScorer, ScoreWeights
from personal_index.index import SearchIndex
from personal_index.interests import InterestStore
from personal_index.models import (
    CrawledPage,
    Interest,
    PipelineStats,
)
from personal_index.pipeline import Pipeline, PipelineConfig
from personal_index.tags import TagStore


class TestPipelineConfig:
    """Test PipelineConfig dataclass."""

    def test_default_config(self):
        config = PipelineConfig()
        assert config.max_depth == 3
        assert config.max_pages == 100
        assert config.min_content_length == 100
        assert config.min_score_threshold == 0.0
        assert config.auto_tag is True

    def test_custom_config(self):
        config = PipelineConfig(
            max_depth=5,
            min_score_threshold=0.5,
            min_content_length=50,
        )
        assert config.max_depth == 5
        assert config.min_score_threshold == 0.5
        assert config.min_content_length == 50

    def test_step_enabled(self):
        config = PipelineConfig()
        assert config.is_step_enabled("crawl") is True
        assert config.is_step_enabled("extract") is True
        assert config.is_step_enabled("search") is True

    def test_step_disabled(self):
        config = PipelineConfig(enabled_steps=["extract", "index"])
        assert config.is_step_enabled("crawl") is False
        assert config.is_step_enabled("extract") is True
        assert config.is_step_enabled("index") is True

    def test_from_dict(self):
        data = {
            "max_depth": 5,
            "min_score_threshold": 0.3,
            "auto_tag": False,
        }
        config = PipelineConfig.from_dict(data)
        assert config.max_depth == 5
        assert config.min_score_threshold == 0.3
        assert config.auto_tag is False


class TestPipelineInit:
    """Test Pipeline initialization."""

    def test_pipeline_creates_dirs(self, tmp_path):
        data_dir = str(tmp_path / "data")
        pipe = Pipeline(data_dir=data_dir)
        assert os.path.isdir(data_dir)
        assert os.path.isdir(os.path.join(data_dir, "cache"))
        assert os.path.isdir(os.path.join(data_dir, "archive"))
        assert os.path.isdir(os.path.join(data_dir, "backups"))

    def test_pipeline_initializes_components(self, tmp_path):
        data_dir = str(tmp_path / "data")
        pipe = Pipeline(data_dir=data_dir)
        assert pipe.interest_store is not None
        assert pipe.tag_store is not None
        assert pipe.search_index is not None
        assert pipe.extractor is not None
        assert pipe.content_filter is not None
        assert pipe.scorer is not None

    def test_pipeline_loads_existing_interests(self, tmp_path):
        data_dir = str(tmp_path / "data")
        # Create interest store with data
        store = InterestStore(store_path=os.path.join(data_dir, "interests.json"))
        store.add(Interest(name="python", keywords=["python"]))

        # New pipeline should load it
        pipe = Pipeline(data_dir=data_dir)
        interests = pipe.interest_store.list_all()
        assert len(interests) == 1
        assert interests[0].name == "python"


class TestPipelineAddPageDirectly:
    """Test adding pages directly through the pipeline."""

    def _setup_pipeline(self, tmp_path, interests=None):
        data_dir = str(tmp_path / "data")
        config = PipelineConfig(
            min_score_threshold=0.0,
            min_content_length=10,
            require_interest_match=False,
        )
        pipe = Pipeline(data_dir=data_dir, config=config)
        if interests:
            for name, keywords in interests:
                pipe.interest_store.add(Interest(name=name, keywords=keywords))
        return pipe

    def test_add_page_directly(self, tmp_path):
        pipe = self._setup_pipeline(tmp_path, [("python", ["python"])])
        page = CrawledPage(
            url="https://example.com/python",
            title="Python Guide",
            content="Python is a great programming language for web development.",
        )
        result = pipe.add_page_directly(page)
        assert result is True
        assert pipe.search_index.get_page_count() == 1

    def test_add_page_filtered_out_short_content(self, tmp_path):
        pipe = self._setup_pipeline(tmp_path)
        page = CrawledPage(
            url="https://example.com/short",
            title="Hi",
            content="Short",
        )
        result = pipe.add_page_directly(page)
        assert result is False

    def test_add_page_empty_content(self, tmp_path):
        pipe = self._setup_pipeline(tmp_path)
        page = CrawledPage(
            url="https://example.com/empty",
            title="Empty",
            content="",
        )
        result = pipe.add_page_directly(page)
        assert result is False

    def test_add_page_with_auto_tags(self, tmp_path):
        pipe = self._setup_pipeline(tmp_path, [("python", ["python"])])
        page = CrawledPage(
            url="https://example.com/blog/python-tips",
            title="Python Tips",
            content="Python programming tips and tricks for web development.",
        )
        pipe.add_page_directly(page)
        tags = pipe.tag_store.get_tags_for_page("https://example.com/blog/python-tips")
        tag_names = [t.name for t in tags]
        assert "python" in tag_names
        assert "blog" in tag_names

    def test_add_multiple_pages(self, tmp_path):
        pipe = self._setup_pipeline(tmp_path, [("tech", ["programming"])])
        for i in range(5):
            page = CrawledPage(
                url=f"https://example.com/page{i}",
                title=f"Page {i}",
                content=f"This is programming content for page {i}.",
            )
            pipe.add_page_directly(page)
        assert pipe.search_index.get_page_count() == 5

    def test_add_page_scored_and_indexed(self, tmp_path):
        pipe = self._setup_pipeline(tmp_path, [("python", ["python"])])
        page = CrawledPage(
            url="https://example.com/page",
            title="Python Page",
            content="Python programming language guide.",
        )
        pipe.add_page_directly(page)
        indexed = pipe.search_index.get_page("https://example.com/page")
        assert indexed is not None
        assert indexed.score > 0


class TestPipelineSearch:
    """Test pipeline search functionality."""

    def _setup_with_pages(self, tmp_path, pages_data):
        data_dir = str(tmp_path / "data")
        config = PipelineConfig(
            min_score_threshold=0.0,
            min_content_length=10,
            require_interest_match=False,
        )
        pipe = Pipeline(data_dir=data_dir, config=config)
        pipe.interest_store.add(Interest(name="tech", keywords=["programming"]))

        for url, title, content in pages_data:
            page = CrawledPage(url=url, title=title, content=content)
            pipe.add_page_directly(page)
        return pipe

    def test_search_returns_results(self, tmp_path):
        pipe = self._setup_with_pages(tmp_path, [
            ("https://example.com/1", "Python", "Python programming language"),
            ("https://example.com/2", "Java", "Java programming language"),
        ])
        results = pipe.search("programming")
        assert len(results) == 2

    def test_search_filters_by_relevance(self, tmp_path):
        pipe = self._setup_with_pages(tmp_path, [
            ("https://example.com/1", "Python", "Python programming language"),
            ("https://example.com/2", "Cooking", "Cooking recipes for dinner"),
        ])
        results = pipe.search("python")
        assert len(results) >= 1
        # At least one result should contain python in title or content
        found = False
        for r in results:
            if "python" in r.title.lower() or "python" in (r.content or "").lower():
                found = True
                break
        assert found, f"No python results found in {[(r.url, r.title) for r in results]}"

    def test_search_with_tag_filter(self, tmp_path):
        pipe = self._setup_with_pages(tmp_path, [
            ("https://example.com/blog/post1", "Blog Post", "Python programming"),
            ("https://example.com/docs/api", "API Docs", "REST API documentation"),
        ])
        results = pipe.search("programming", tag="blog")
        # Should only return blog-tagged pages
        for r in results:
            assert "blog" in r.url.lower()

    def test_search_limit(self, tmp_path):
        pipe = self._setup_with_pages(tmp_path, [
            (f"https://example.com/{i}", f"Page {i}", f"Programming content {i}")
            for i in range(10)
        ])
        results = pipe.search("programming", limit=3)
        assert len(results) == 3

    def test_search_empty_index(self, tmp_path):
        data_dir = str(tmp_path / "data")
        pipe = Pipeline(data_dir=data_dir)
        results = pipe.search("anything")
        assert len(results) == 0

    def test_search_case_insensitive(self, tmp_path):
        pipe = self._setup_with_pages(tmp_path, [
            ("https://example.com/1", "Python", "Python programming"),
        ])
        for query in ["python", "Python", "PYTHON", "PyThOn"]:
            results = pipe.search(query)
            assert len(results) == 1, f"Failed for query: {query}"


class TestPipelineStats:
    """Test pipeline statistics."""

    def test_get_stats_empty(self, tmp_path):
        data_dir = str(tmp_path / "data")
        pipe = Pipeline(data_dir=data_dir)
        stats = pipe.get_stats()
        assert stats["indexed_pages"] == 0
        assert stats["total_interests"] == 0
        assert stats["total_tags"] == 0

    def test_get_stats_with_data(self, tmp_path):
        data_dir = str(tmp_path / "data")
        config = PipelineConfig(
            min_score_threshold=0.0,
            min_content_length=10,
            require_interest_match=False,
        )
        pipe = Pipeline(data_dir=data_dir, config=config)
        pipe.interest_store.add(Interest(name="python", keywords=["python"]))
        page = CrawledPage(
            url="https://example.com/blog/python",
            title="Python",
            content="Python programming language.",
        )
        pipe.add_page_directly(page)

        stats = pipe.get_stats()
        assert stats["indexed_pages"] == 1
        assert stats["total_interests"] == 1
        assert stats["total_tags"] > 0
        assert stats["tagged_pages"] == 1


class TestPipelinePersistence:
    """Test that pipeline data persists across instances."""

    def test_pipeline_data_persists(self, tmp_path):
        data_dir = str(tmp_path / "data")
        config = PipelineConfig(
            min_score_threshold=0.0,
            min_content_length=10,
            require_interest_match=False,
        )

        # First pipeline: add data
        pipe1 = Pipeline(data_dir=data_dir, config=config)
        pipe1.interest_store.add(Interest(name="python", keywords=["python"]))
        page = CrawledPage(
            url="https://example.com/page",
            title="Python Page",
            content="Python programming language.",
        )
        pipe1.add_page_directly(page)

        # Second pipeline: verify persistence
        pipe2 = Pipeline(data_dir=data_dir, config=config)
        assert pipe2.search_index.get_page_count() == 1
        assert len(pipe2.interest_store.list_all()) == 1
        results = pipe2.search("python")
        assert len(results) == 1

    def test_tags_persist_across_instances(self, tmp_path):
        data_dir = str(tmp_path / "data")
        config = PipelineConfig(
            min_score_threshold=0.0,
            min_content_length=10,
            require_interest_match=False,
        )

        pipe1 = Pipeline(data_dir=data_dir, config=config)
        pipe1.interest_store.add(Interest(name="python", keywords=["python"]))
        page = CrawledPage(
            url="https://example.com/blog/python",
            title="Python",
            content="Python programming.",
        )
        pipe1.add_page_directly(page)

        pipe2 = Pipeline(data_dir=data_dir, config=config)
        tags = pipe2.tag_store.get_tags_for_page("https://example.com/blog/python")
        tag_names = [t.name for t in tags]
        assert "python" in tag_names
        assert "blog" in tag_names


class TestPipelineWithFileImport:
    """Test pipeline with local file imports."""

    def test_import_and_index_file(self, tmp_path):
        data_dir = str(tmp_path / "data")
        config = PipelineConfig(
            min_score_threshold=0.0,
            min_content_length=10,
            require_interest_match=False,
            enabled_steps=["extract", "filter", "score", "tag", "index"],
        )
        pipe = Pipeline(data_dir=data_dir, config=config)
        pipe.interest_store.add(Interest(name="python", keywords=["python"]))

        # Create a test file
        test_file = tmp_path / "article.txt"
        test_file.write_text("Python is a great programming language for web development.")

        page = CrawledPage(
            url=f"file://{test_file}",
            title="article.txt",
            content=str(test_file.read_text()),
        )
        result = pipe.add_page_directly(page)
        assert result is True
        assert pipe.search_index.get_page_count() == 1

    def test_import_multiple_files(self, tmp_path):
        data_dir = str(tmp_path / "data")
        config = PipelineConfig(
            min_score_threshold=0.0,
            min_content_length=10,
            require_interest_match=False,
        )
        pipe = Pipeline(data_dir=data_dir, config=config)

        for i in range(3):
            test_file = tmp_path / f"file{i}.txt"
            test_file.write_text(f"This is content file number {i} about programming.")
            page = CrawledPage(
                url=f"file://{test_file}",
                title=f"file{i}.txt",
                content=str(test_file.read_text()),
            )
            pipe.add_page_directly(page)

        assert pipe.search_index.get_page_count() == 3


class TestFullPipelineWorkflow:
    """Test the complete end-to-end workflow."""

    def test_full_workflow_with_interests(self, tmp_path):
        """Test: init → add interests → import content → search → export."""
        data_dir = str(tmp_path / "data")
        config = PipelineConfig(
            min_score_threshold=0.0,
            min_content_length=10,
            require_interest_match=False,
        )
        pipe = Pipeline(data_dir=data_dir, config=config)

        # Step 1: Add interests
        pipe.interest_store.add(Interest(name="python", keywords=["python", "django"]))
        pipe.interest_store.add(Interest(name="javascript", keywords=["javascript", "node"]))

        # Step 2: Import content
        pages = [
            CrawledPage(
                url="https://example.com/python-guide",
                title="Python Guide",
                content="Python is a versatile programming language for web development with Django.",
            ),
            CrawledPage(
                url="https://example.com/js-tutorial",
                title="JS Tutorial",
                content="JavaScript and Node.js for building modern web applications.",
            ),
            CrawledPage(
                url="https://example.com/cooking",
                title="Cooking",
                content="How to cook pasta and make delicious Italian food.",
            ),
        ]
        for page in pages:
            pipe.add_page_directly(page)

        # Step 3: Verify indexing
        assert pipe.search_index.get_page_count() == 3

        # Step 4: Search
        python_results = pipe.search("python")
        assert len(python_results) >= 1

        js_results = pipe.search("javascript")
        assert len(js_results) >= 1

        # Step 5: Verify tags
        python_tags = pipe.tag_store.get_tags_for_page("https://example.com/python-guide")
        python_tag_names = [t.name for t in python_tags]
        assert "python" in python_tag_names

        # Step 6: Verify stats
        stats = pipe.get_stats()
        assert stats["indexed_pages"] == 3
        assert stats["total_interests"] == 2

    def test_pipeline_filters_low_quality(self, tmp_path):
        """Test that low-quality content is filtered out."""
        data_dir = str(tmp_path / "data")
        config = PipelineConfig(
            min_score_threshold=0.0,
            min_content_length=50,
            require_interest_match=False,
        )
        pipe = Pipeline(data_dir=data_dir, config=config)

        # Good content
        good_page = CrawledPage(
            url="https://example.com/good",
            title="Good Article",
            content="This is a well-written article with substantial content about programming.",
        )
        assert pipe.add_page_directly(good_page) is True

        # Short content
        short_page = CrawledPage(
            url="https://example.com/short",
            title="Hi",
            content="Short",
        )
        assert pipe.add_page_directly(short_page) is False

        assert pipe.search_index.get_page_count() == 1
