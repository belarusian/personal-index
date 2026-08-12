"""Tests for individual pipeline stages and their interactions."""

from __future__ import annotations

from personal_index.config.pipeline_config import PipelineConfig
from personal_index.content_filter import ContentFilter, FilterConfig
from personal_index.models import CrawledPage, Interest
from personal_index.pipeline_runner import PipelineRunner


class TestExtractStage:
    """Test the extraction stage of the pipeline."""

    def test_extract_plain_text(self, tmp_path):
        """Test extracting from plain text files."""
        runner = PipelineRunner(data_dir=str(tmp_path / "data"))
        file = tmp_path / "article.txt"
        file.write_text("Python is a great programming language.")
        page = runner._read_file(str(file))
        assert page is not None
        assert "python" in page.content.lower()
        runner.close()

    def test_extract_html(self, tmp_path):
        """Test extracting from HTML files."""
        runner = PipelineRunner(data_dir=str(tmp_path / "data"))
        file = tmp_path / "page.html"
        file.write_text(
            "<html><head><title>Test Page</title></head>"
            "<body><h1>Hello World</h1><p>Some content here.</p></body></html>"
        )
        page = runner._read_file(str(file))
        assert page is not None
        assert "hello world" in page.title.lower() or "hello world" in page.content.lower()
        runner.close()

    def test_extract_markdown(self, tmp_path):
        """Test extracting from markdown files."""
        runner = PipelineRunner(data_dir=str(tmp_path / "data"))
        file = tmp_path / "readme.md"
        file.write_text("# Python Tutorial\n\nThis is a guide about Python programming.")
        page = runner._read_file(str(file))
        assert page is not None
        assert "python" in page.content.lower() or "python" in page.title.lower()
        runner.close()

    def test_extract_empty_file(self, tmp_path):
        """Test extracting from empty files."""
        runner = PipelineRunner(data_dir=str(tmp_path / "data"))
        file = tmp_path / "empty.txt"
        file.write_text("")
        page = runner._read_file(str(file))
        # Empty file returns None
        assert page is None
        runner.close()

    def test_extract_binary_file(self, tmp_path):
        """Test that binary files are handled gracefully."""
        runner = PipelineRunner(data_dir=str(tmp_path / "data"))
        file = tmp_path / "image.bin"
        file.write_bytes(bytes(range(256)) * 100)
        page = runner._read_file(str(file))
        # Should not crash
        assert page is not None
        runner.close()


class TestFilterStage:
    """Test the filtering stage of the pipeline."""

    def test_filter_min_content_length(self, tmp_path):
        """Test filtering by minimum content length."""
        cfg = PipelineConfig(min_content_length=50)
        runner = PipelineRunner(data_dir=str(tmp_path / "data"), pipeline_config=cfg)

        short_page = CrawledPage(
            url="https://example.com/short",
            title="Short",
            content="Hi.",
        )
        long_page = CrawledPage(
            url="https://example.com/long",
            title="Long",
            content="This is a much longer piece of content that should pass the filter.",
        )

        assert not runner._filter.should_include(short_page)
        assert runner._filter.should_include(long_page)
        runner.close()

    def test_filter_min_title_length(self, tmp_path):
        """Test filtering by minimum title length."""
        filter_cfg = FilterConfig(min_title_length=5, min_content_length=10)
        f = ContentFilter(config=filter_cfg)

        short_title = CrawledPage(
            url="https://example.com/page",
            title="Hi",
            content="Some content here that is long enough.",
        )
        long_title = CrawledPage(
            url="https://example.com/page2",
            title="A Valid Title",
            content="Some content here that is long enough.",
        )

        assert not f.should_include(short_title)
        assert f.should_include(long_title)

    def test_filter_blocked_domains(self, tmp_path):
        """Test filtering by blocked domains."""
        filter_cfg = FilterConfig(blocked_domains=["spam.com"], min_content_length=10)
        f = ContentFilter(config=filter_cfg)

        blocked = CrawledPage(
            url="https://spam.com/page",
            title="Spam",
            content="This content is from a blocked domain.",
        )
        allowed = CrawledPage(
            url="https://example.com/page",
            title="Good",
            content="This content is from an allowed domain.",
        )

        assert not f.should_include(blocked)
        assert f.should_include(allowed)


class TestScoreStage:
    """Test the scoring stage of the pipeline."""

    def test_score_with_interests(self, tmp_path):
        """Test scoring with interest matching."""
        runner = PipelineRunner(data_dir=str(tmp_path / "data"))

        runner._interest_store.add(Interest(
            name="python", keywords=["python", "programming"],
        ))

        page = CrawledPage(
            url="https://example.com/page",
            title="Python Tutorial",
            content="Python programming language for software development.",
        )

        score = runner._scorer.score_page(page, runner._interest_store)
        assert score.total > 0
        runner.close()

    def test_score_without_interests(self, tmp_path):
        """Test scoring without any interests."""
        runner = PipelineRunner(data_dir=str(tmp_path / "data"))

        page = CrawledPage(
            url="https://example.com/page",
            title="Random Page",
            content="Some random content here.",
        )

        score = runner._scorer.score_page(page, runner._interest_store)
        # Should still produce a score (possibly 0)
        assert score.total >= 0
        runner.close()

    def test_score_higher_for_more_matches(self, tmp_path):
        """Test that more keyword matches produce higher scores."""
        runner = PipelineRunner(data_dir=str(tmp_path / "data"))

        runner._interest_store.add(Interest(
            name="tech", keywords=["python", "code", "programming"],
        ))

        low_match = CrawledPage(
            url="https://example.com/low",
            title="Low Match",
            content="This has python once.",
        )
        high_match = CrawledPage(
            url="https://example.com/high",
            title="High Match",
            content="Python code programming python code programming python.",
        )

        low_score = runner._scorer.score_page(low_match, runner._interest_store)
        high_score = runner._scorer.score_page(high_match, runner._interest_store)
        assert high_score.total >= low_score.total
        runner.close()


class TestTagStage:
    """Test the tagging stage of the pipeline."""

    def test_tag_from_interests(self, tmp_path):
        """Test that tags are generated from matched interests."""
        runner = PipelineRunner(data_dir=str(tmp_path / "data"))

        runner._interest_store.add(Interest(
            name="python", keywords=["python"],
        ))
        runner._interest_store.add(Interest(
            name="web", keywords=["web"],
        ))

        page = CrawledPage(
            url="https://example.com/page",
            title="Python Web Dev",
            content="Python web development tutorial.",
        )

        tags, _ = runner._auto_tag_page(page)
        assert len(tags) >= 1
        runner.close()

    def test_tag_no_matches(self, tmp_path):
        """Test tagging when no interests match."""
        runner = PipelineRunner(data_dir=str(tmp_path / "data"))

        runner._interest_store.add(Interest(
            name="python", keywords=["python"],
        ))

        page = CrawledPage(
            url="https://example.com/page",
            title="Cooking",
            content="How to make pasta.",
        )

        tags, _ = runner._auto_tag_page(page)
        # May still get some tags from keywords
        assert isinstance(tags, list)
        runner.close()


class TestIndexStage:
    """Test the indexing stage of the pipeline."""

    def test_index_add_page(self, tmp_path):
        """Test adding a page to the index."""
        runner = PipelineRunner(data_dir=str(tmp_path / "data"))

        page = CrawledPage(
            url="https://example.com/page",
            title="Test Page",
            content="Python programming tutorial.",
        )

        runner._search_index.add_page(page)
        assert runner._search_index.get_page_count() >= 1
        runner.close()

    def test_index_search_after_add(self, tmp_path):
        """Test searching after adding pages."""
        runner = PipelineRunner(data_dir=str(tmp_path / "data"))

        runner._search_index.add_page(CrawledPage(
            url="https://example.com/page1",
            title="Python Tutorial",
            content="Python programming language.",
        ))
        runner._search_index.add_page(CrawledPage(
            url="https://example.com/page2",
            title="JavaScript Guide",
            content="JavaScript programming language.",
        ))

        results = runner._search_index.search("python")
        assert len(results) >= 1
        assert any("python" in r.url.lower() or "python" in r.title.lower()
                   for r in results)
        runner.close()

    def test_index_persistence(self, tmp_path):
        """Test that index persists to disk."""
        data_dir = str(tmp_path / "data")

        # First runner
        runner1 = PipelineRunner(data_dir=data_dir)
        runner1._search_index.add_page(CrawledPage(
            url="https://example.com/page",
            title="Persistent Page",
            content="This page should persist.",
        ))
        runner1.close()

        # Second runner should see the page
        runner2 = PipelineRunner(data_dir=data_dir)
        assert runner2._search_index.get_page_count() >= 1
        page = runner2._search_index.get_page("https://example.com/page")
        assert page is not None
        runner2.close()
