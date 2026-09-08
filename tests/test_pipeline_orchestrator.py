"""Integration tests for PipelineOrchestrator - full pipeline verification.

Tests the complete crawl→extract→filter→score→tag→index→search pipeline
using local files (no network required).
"""

from __future__ import annotations

import os

from personal_index.config.pipeline_config import PipelineConfig
from personal_index.pipeline_orchestrator import PipelineOrchestrator, PipelineResult


class TestPipelineOrchestratorInit:
    """Test PipelineOrchestrator initialization."""

    def test_default_init(self, tmp_path):
        data_dir = str(tmp_path / "data")
        orch = PipelineOrchestrator(data_dir=data_dir)
        assert orch.data_dir == data_dir
        assert orch.interest_store is not None
        assert orch.tag_store is not None
        assert orch.search_index is not None
        orch.close()

    def test_init_creates_directories(self, tmp_path):
        data_dir = str(tmp_path / "data")
        PipelineOrchestrator(data_dir=data_dir)
        assert os.path.isdir(os.path.join(data_dir, "cache"))
        assert os.path.isdir(os.path.join(data_dir, "archive"))
        assert os.path.isdir(os.path.join(data_dir, "backups"))

    def test_init_with_custom_config(self, tmp_path):
        data_dir = str(tmp_path / "data")
        config = PipelineConfig(min_content_length=50, max_pages=50)
        orch = PipelineOrchestrator(data_dir=data_dir, config=config)
        assert orch.config.min_content_length == 50
        orch.close()


class TestPipelineFromFileImport:
    """Test pipeline with local file imports."""

    def _create_test_files(self, tmp_path):
        """Create test content files."""
        docs = tmp_path / "docs"
        docs.mkdir()

        (docs / "python_intro.txt").write_text(
            "Python is a versatile programming language used for web development, "
            "data science, and automation. It features clean syntax and a large "
            "standard library. Python supports multiple programming paradigms "
            "including procedural, object-oriented, and functional programming."
        )

        (docs / "javascript_guide.txt").write_text(
            "JavaScript is the language of the web. It powers interactive "
            "websites and modern web applications. Node.js extends JavaScript "
            "to server-side development. JavaScript frameworks like React and "
            "Vue.js enable building complex user interfaces."
        )

        (docs / "short.txt").write_text(
            "Too short"
        )

        (docs / "devops.txt").write_text(
            "DevOps practices include continuous integration, continuous deployment, "
            "infrastructure as code, and monitoring. Tools like Docker, Kubernetes, "
            "and Jenkins automate the software delivery pipeline. DevOps culture "
            "promotes collaboration between development and operations teams."
        )

        return docs

    def test_run_from_files_basic(self, tmp_path):
        """Test basic file import pipeline."""
        data_dir = str(tmp_path / "data")
        docs = self._create_test_files(tmp_path)

        orch = PipelineOrchestrator(data_dir=data_dir)
        files = [str(f) for f in docs.glob("*.txt")]
        result = orch.run_from_files(files)

        assert result.success is True
        assert result.stats.pages_crawled > 0
        assert result.stats.pages_indexed > 0
        orch.close()

    def test_run_from_files_filters_short_content(self, tmp_path):
        """Test that short content is filtered out."""
        data_dir = str(tmp_path / "data")
        docs = self._create_test_files(tmp_path)

        config = PipelineConfig(min_content_length=100)
        orch = PipelineOrchestrator(data_dir=data_dir, config=config)
        files = [str(f) for f in docs.glob("*.txt")]
        result = orch.run_from_files(files)

        # short.txt should be filtered out
        assert result.stats.pages_filtered_out >= 1
        orch.close()

    def test_run_from_files_with_interests(self, tmp_path):
        """Test pipeline scoring with configured interests."""
        data_dir = str(tmp_path / "data")
        docs = self._create_test_files(tmp_path)

        orch = PipelineOrchestrator(data_dir=data_dir)

        # Add interests before running
        from personal_index.models import Interest
        orch.interest_store.add(Interest(
            name="programming",
            keywords=["python", "javascript", "programming"],
        ))

        files = [str(f) for f in docs.glob("*.txt")]
        result = orch.run_from_files(files)

        assert result.success is True
        assert result.stats.pages_scored > 0
        orch.close()

    def test_run_from_files_tags_pages(self, tmp_path):
        """Test that pages get tagged during pipeline."""
        data_dir = str(tmp_path / "data")
        docs = self._create_test_files(tmp_path)

        orch = PipelineOrchestrator(data_dir=data_dir)
        files = [str(f) for f in docs.glob("*.txt")]
        result = orch.run_from_files(files)

        assert result.stats.tags_applied > 0
        orch.close()

    def test_run_from_files_empty_list(self, tmp_path):
        """Test pipeline with no files."""
        data_dir = str(tmp_path / "data")
        orch = PipelineOrchestrator(data_dir=data_dir)
        result = orch.run_from_files([])

        assert result.success is True
        assert result.stats.pages_crawled == 0
        assert result.stats.pages_indexed == 0
        orch.close()

    def test_run_from_files_nonexistent(self, tmp_path):
        """Test pipeline with nonexistent files."""
        data_dir = str(tmp_path / "data")
        orch = PipelineOrchestrator(data_dir=data_dir)
        result = orch.run_from_files(["/nonexistent/file.txt"])

        assert result.success is True
        assert result.stats.pages_crawled == 0
        orch.close()


class TestPipelineSearch:
    """Test search after pipeline execution."""

    def test_search_after_import(self, tmp_path):
        """Test that search works after pipeline import."""
        data_dir = str(tmp_path / "data")
        docs = tmp_path / "docs"
        docs.mkdir()
        (docs / "article.txt").write_text(
            "Python programming language for web development and data science."
        )

        orch = PipelineOrchestrator(data_dir=data_dir)
        files = [str(docs / "article.txt")]
        orch.run_from_files(files)

        results = orch.search("python")
        assert len(results) >= 1
        orch.close()

    def test_search_no_results(self, tmp_path):
        """Test search with no matching results."""
        data_dir = str(tmp_path / "data")
        docs = tmp_path / "docs"
        docs.mkdir()
        (docs / "article.txt").write_text(
            "Python programming language for web development."
        )

        orch = PipelineOrchestrator(data_dir=data_dir)
        files = [str(docs / "article.txt")]
        orch.run_from_files(files)

        results = orch.search("quantum physics")
        assert len(results) == 0
        orch.close()

    def test_search_persists_across_instances(self, tmp_path):
        """Test that search index persists between orchestrator instances."""
        data_dir = str(tmp_path / "data")
        docs = tmp_path / "docs"
        docs.mkdir()
        (docs / "article.txt").write_text(
            "Python programming language for web development."
        )

        # First instance: import
        orch1 = PipelineOrchestrator(data_dir=data_dir)
        orch1.run_from_files([str(docs / "article.txt")])
        orch1.close()

        # Second instance: search
        orch2 = PipelineOrchestrator(data_dir=data_dir)
        results = orch2.search("python")
        assert len(results) >= 1
        orch2.close()


class TestPipelineResult:
    """Test PipelineResult data class."""

    def test_result_summary(self):
        from personal_index.models import PipelineStats
        result = PipelineResult(stats=PipelineStats(
            pages_crawled=10,
            pages_extracted=10,
            pages_passed_filter=8,
            pages_scored=8,
            pages_tagged=8,
            pages_indexed=8,
            tags_applied=24,
            elapsed_seconds=1.5,
        ))
        summary = result.summary()
        assert "Pipeline Result" in summary
        assert "Pages crawled:    10" in summary
        assert "Pages indexed:    8" in summary

    def test_result_with_errors(self):
        result = PipelineResult(success=False, errors=["test error"])
        assert result.success is False
        assert len(result.errors) == 1


class TestPipelineProgressCallback:
    """Test progress callback integration."""

    def test_progress_callback_called(self, tmp_path):
        """Test that progress callback receives updates."""
        data_dir = str(tmp_path / "data")
        docs = tmp_path / "docs"
        docs.mkdir()
        (docs / "article.txt").write_text(
            "Python programming language for web development and data science. "
            "This is a longer article with enough content to pass the filter. "
            "It covers various topics including programming, development, and more."
        )

        callbacks = []

        def callback(stage, current, total):
            callbacks.append((stage, current, total))

        orch = PipelineOrchestrator(data_dir=data_dir, progress_callback=callback)
        orch.run_from_files([str(docs / "article.txt")])
        orch.close()

        assert len(callbacks) > 0
        stages = [c[0] for c in callbacks]
        assert "read" in stages or "filter" in stages


class TestPipelineStageMethods:
    """Test extracted stage methods and _run_stage helper."""

    def _create_test_file(self, tmp_path, name, content):
        f = tmp_path / name
        f.write_text(content)
        return str(f)

    def test_stage_read_returns_pages(self, tmp_path):
        data_dir = str(tmp_path / "data")
        docs = tmp_path / "docs"
        docs.mkdir()
        fpath = self._create_test_file(docs, "test.txt", "Hello world content here")

        orch = PipelineOrchestrator(data_dir=data_dir)
        pages = orch._stage_read([fpath])
        assert len(pages) == 1
        assert pages[0].title == "test.txt"
        orch.close()

    def test_stage_read_skips_bad_files(self, tmp_path):
        data_dir = str(tmp_path / "data")
        orch = PipelineOrchestrator(data_dir=data_dir)
        pages = orch._stage_read(["/nonexistent/file.txt"])
        assert pages == []
        orch.close()

    def test_stage_methods_are_the_live_path(self, tmp_path):
        """The live stage path (filter->score->tag->index) drives the counters.

        Pins the live-path behavior (the stage counters reflect the
        _run_*_stage/_apply_* path) AND the guard (drop) path (a file that
        fails the content filter increments pages_filtered_out). A regression
        that re-introduces a dead or alternate _stage_* implementation would
        break these counters.
        """
        data_dir = str(tmp_path / "data")
        docs = tmp_path / "docs"
        docs.mkdir()

        # Two long files pass the content filter (>= 100 chars).
        (docs / "long_a.txt").write_text(
            "Python is a versatile programming language used for web development, "
            "data science, and automation. It features clean syntax and a large "
            "standard library that supports many programming paradigms."
        )
        (docs / "long_b.txt").write_text(
            "JavaScript is the language of the web. It powers interactive "
            "websites and modern web applications, and Node.js extends it to "
            "server-side development for building complex user interfaces."
        )
        # One short file fails the content filter (guard / drop path).
        (docs / "short.txt").write_text("Too short")

        orch = PipelineOrchestrator(data_dir=data_dir)
        files = [
            str(docs / "long_a.txt"),
            str(docs / "long_b.txt"),
            str(docs / "short.txt"),
        ]
        result = orch.run_from_files(files)

        assert result.success is True
        # Live path: the two long pages flow through filter->score->tag->index.
        assert result.stats.pages_passed_filter == 2
        assert result.stats.pages_scored == 2
        assert result.stats.pages_tagged == 2
        assert result.stats.pages_indexed == 2
        # Guard (drop) path: the short page is filtered out.
        assert result.stats.pages_filtered_out == 1
        orch.close()

    def test_tag_index_counters_single_source(self, tmp_path):
        """pages_tagged / pages_indexed are each written by ONE site.

        Pins the single-source contract (ARCH-9): the authoritative value
        is the len(out) overwrite in _run_tag_stage/_run_index_stage, and
        the redundant per-page += 1 in _apply_tag/_apply_index is gone.
        Normal path: every page that passes the filter reaches the tag and
        index stages, so pages_tagged == pages_indexed ==
        pages_passed_filter. Guard (drop) path: a page that fails the
        content filter is excluded from all three counters and counted in
        pages_filtered_out, keeping the counters mutually consistent.
        """
        data_dir = str(tmp_path / "data")
        docs = tmp_path / "docs"
        docs.mkdir()

        # Three long files pass the content filter (>= 10 chars default).
        (docs / "a.txt").write_text(
            "Python is a versatile programming language used for web "
            "development, data science, and automation with clean syntax."
        )
        (docs / "b.txt").write_text(
            "JavaScript powers interactive websites and modern web "
            "applications, and Node.js extends it to server-side code."
        )
        (docs / "c.txt").write_text(
            "DevOps practices include continuous integration, deployment, "
            "infrastructure as code, and monitoring for delivery."
        )
        # One short file fails the content filter (guard / drop path).
        (docs / "short.txt").write_text("Too short")

        orch = PipelineOrchestrator(data_dir=data_dir)
        files = [
            str(docs / "a.txt"),
            str(docs / "b.txt"),
            str(docs / "c.txt"),
            str(docs / "short.txt"),
        ]
        result = orch.run_from_files(files)

        assert result.success is True
        # Normal path: the three long pages reach tag and index stages.
        assert result.stats.pages_passed_filter == 3
        assert result.stats.pages_tagged == 3
        assert result.stats.pages_indexed == 3
        # Single-source consistency: tag/index counters equal the filter
        # pass count (no divergent second write inflating them).
        assert result.stats.pages_tagged == result.stats.pages_passed_filter
        assert result.stats.pages_indexed == result.stats.pages_passed_filter
        # Guard (drop) path: the short page is excluded from tag/index and
        # counted in pages_filtered_out; the counters stay consistent.
        assert result.stats.pages_filtered_out == 1
        assert (
            result.stats.pages_passed_filter
            + result.stats.pages_filtered_out
            == len(files)
        )
        orch.close()

    def test_run_stage_includes_matching(self, tmp_path):
        data_dir = str(tmp_path / "data")
        orch = PipelineOrchestrator(data_dir=data_dir)

        from personal_index.models import CrawledPage
        pages = [
            CrawledPage(url=f"http://example.com/{i}", title=f"Page {i}",
                        content=f"Content {i}", word_count=3)
            for i in range(3)
        ]
        # Include only even-indexed pages
        result = orch._run_stage(
            pages,
            lambda page: int(page.url.split("/")[-1]) % 2 == 0,
            "test",
        )
        assert len(result) == 2  # pages 0 and 2
        orch.close()

    def test_run_stage_empty_input(self, tmp_path):
        data_dir = str(tmp_path / "data")
        orch = PipelineOrchestrator(data_dir=data_dir)
        result = orch._run_stage([], lambda p: True, "test")
        assert result == []
        orch.close()

    def test_run_stage_progress_callback(self, tmp_path):
        data_dir = str(tmp_path / "data")
        callbacks = []

        def cb(stage, current, total):
            callbacks.append((stage, current, total))

        orch = PipelineOrchestrator(data_dir=data_dir, progress_callback=cb)

        from personal_index.models import CrawledPage
        pages = [
            CrawledPage(url=f"http://example.com/{i}", title=f"Page {i}",
                        content=f"Content {i}", word_count=3)
            for i in range(3)
        ]
        orch._run_stage(pages, lambda p: True, "my_stage")

        assert len(callbacks) > 0
        stages = [c[0] for c in callbacks]
        assert "my_stage" in stages
        orch.close()


class TestExecuteStages:
    """Test the extracted _execute_stages shared core."""

    def test_execute_stages_processes_pages(self, tmp_path):
        from personal_index.models import CrawledPage
        from personal_index.pipeline_orchestrator import PipelineResult

        data_dir = str(tmp_path / "data")
        orch = PipelineOrchestrator(data_dir=data_dir)

        pages = [
            CrawledPage(
                url="http://example.com/1",
                title="Test Page",
                content="This is some content that should pass the filter with enough words",
                word_count=14,
            )
        ]
        result = PipelineResult()
        import time
        start_time = time.time()

        orch._execute_stages(pages, result, start_time)

        assert result.stats.pages_extracted == 1
        assert result.stats.pages_passed_filter >= 0
        assert result.stats.pages_scored >= 0
        assert result.stats.pages_tagged >= 0
        assert result.stats.pages_indexed >= 0
        assert result.stats.elapsed_seconds >= 0
        orch.close()

    def test_execute_stages_filters_short_content(self, tmp_path):
        from personal_index.models import CrawledPage
        from personal_index.pipeline_orchestrator import PipelineResult

        data_dir = str(tmp_path / "data")
        config = PipelineConfig(min_content_length=100)
        orch = PipelineOrchestrator(data_dir=data_dir, config=config)

        pages = [
            CrawledPage(
                url="http://example.com/1",
                title="Short",
                content="Too short",
                word_count=2,
            )
        ]
        result = PipelineResult()
        import time
        start_time = time.time()

        orch._execute_stages(pages, result, start_time)

        assert result.stats.pages_extracted == 1
        assert result.stats.pages_filtered_out >= 1
        orch.close()

    def test_execute_stages_empty_pages(self, tmp_path):
        from personal_index.pipeline_orchestrator import PipelineResult

        data_dir = str(tmp_path / "data")
        orch = PipelineOrchestrator(data_dir=data_dir)

        result = PipelineResult()
        import time
        start_time = time.time()

        orch._execute_stages([], result, start_time)

        assert result.stats.pages_extracted == 0
        assert result.stats.pages_indexed == 0
        assert result.pages == []
        orch.close()

    def test_execute_stages_returns_result(self, tmp_path):
        from personal_index.pipeline_orchestrator import PipelineResult

        data_dir = str(tmp_path / "data")
        orch = PipelineOrchestrator(data_dir=data_dir)

        result = PipelineResult()
        import time
        start_time = time.time()

        returned = orch._execute_stages([], result, start_time)
        assert returned is result
        orch.close()


class TestPipelineOrchestratorDocstringClaim:
    """Pin the corrected docstring: pipeline stages are crawl→filter→score→tag→index.

    There is no separate 'extract' stage; pages_extracted mirrors pages_crawled.
    """

    def test_no_separate_extract_stage(self, tmp_path):
        """Normal path: pages_extracted equals pages_crawled (no extract stage)."""
        data_dir = str(tmp_path / "data")
        docs = tmp_path / "docs"
        docs.mkdir()
        (docs / "article.txt").write_text(
            "Python is a programming language used for web development, "
            "data science, and automation. It supports multiple paradigms "
            "including procedural, object-oriented, and functional programming."
        )
        orch = PipelineOrchestrator(data_dir=data_dir)
        files = [str(docs / "article.txt")]
        result = orch.run_from_files(files)
        assert result.success is True
        assert result.stats.pages_crawled == 1
        # Pin: no separate extract stage; extracted == crawled
        assert result.stats.pages_extracted == result.stats.pages_crawled
        orch.close()

    def test_empty_files_no_extract(self, tmp_path):
        """Guard path: empty file list yields zero extracted (no extract stage)."""
        data_dir = str(tmp_path / "data")
        orch = PipelineOrchestrator(data_dir=data_dir)
        result = orch.run_from_files([])
        assert result.success is True
        assert result.stats.pages_crawled == 0
        assert result.stats.pages_extracted == 0
        orch.close()
