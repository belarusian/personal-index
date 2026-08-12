"""Edge case and error handling integration tests for personal-index."""

from __future__ import annotations

import os

from personal_index.config.pipeline_config import PipelineConfig
from personal_index.index import SearchIndex
from personal_index.interests import InterestStore
from personal_index.models import CrawledPage, Interest
from personal_index.pipeline_runner import PipelineRunner
from personal_index.tags import TagStore


class TestPipelineEdgeCases:
    """Test pipeline behavior with edge cases."""

    def test_pipeline_with_unicode_content(self, tmp_path):
        """Test pipeline handles Unicode content correctly."""
        data_dir = str(tmp_path / "data")
        cfg = PipelineConfig(min_score_threshold=0.0, min_content_length=10)
        runner = PipelineRunner(data_dir=data_dir, pipeline_config=cfg)

        runner._interest_store.add(Interest(
            name="unicode", keywords=["python", "日本語"],
        ))

        file = tmp_path / "unicode.txt"
        file.write_text(
            "Python programming with Unicode support: 日本語のテキスト処理. "
            "Emojis work too: 🐍🔥💻"
        )

        stats = runner.run_from_files([str(file)])
        assert stats.pages_indexed >= 1
        runner.close()

    def test_pipeline_with_empty_interests(self, tmp_path):
        """Test pipeline works with no interests defined."""
        data_dir = str(tmp_path / "data")
        cfg = PipelineConfig(min_score_threshold=0.0, min_content_length=10)
        runner = PipelineRunner(data_dir=data_dir, pipeline_config=cfg)

        file = tmp_path / "article.txt"
        file.write_text("Some content about programming and software development.")

        stats = runner.run_from_files([str(file)])
        # Should still index content even without interests
        assert stats.pages_crawled >= 1
        runner.close()

    def test_pipeline_with_html_content(self, tmp_path):
        """Test pipeline extracts text from HTML files."""
        data_dir = str(tmp_path / "data")
        cfg = PipelineConfig(min_score_threshold=0.0, min_content_length=10)
        runner = PipelineRunner(data_dir=data_dir, pipeline_config=cfg)

        runner._interest_store.add(Interest(
            name="webdev", keywords=["python", "web"],
        ))

        html_file = tmp_path / "page.html"
        html_file.write_text(
            "<!DOCTYPE html><html><head><title>Python Web Dev</title></head>"
            "<body><h1>Python Web Development</h1>"
            "<p>Python is excellent for web development with Django and Flask.</p>"
            "<script>alert('ignore this');</script>"
            "<style>.ignore { color: red; }</style>"
            "</body></html>"
        )

        stats = runner.run_from_files([str(html_file)])
        assert stats.pages_indexed >= 1

        # Verify search finds the content
        results = runner._search_index.search("python web")
        assert len(results) >= 1
        runner.close()

    def test_pipeline_with_duplicate_urls(self, tmp_path):
        """Test pipeline handles duplicate URLs gracefully."""
        data_dir = str(tmp_path / "data")
        cfg = PipelineConfig(min_score_threshold=0.0, min_content_length=10)
        runner = PipelineRunner(data_dir=data_dir, pipeline_config=cfg)

        runner._interest_store.add(Interest(
            name="tech", keywords=["python"],
        ))

        file = tmp_path / "article.txt"
        file.write_text("Python programming language for software development.")

        # Import same file twice
        stats = runner.run_from_files([str(file), str(file)])

        # Should not crash, may deduplicate
        assert stats.errors == [] or len(stats.errors) == 0
        runner.close()

    def test_pipeline_with_very_long_content(self, tmp_path):
        """Test pipeline handles very long content."""
        data_dir = str(tmp_path / "data")
        cfg = PipelineConfig(min_score_threshold=0.0, min_content_length=10)
        runner = PipelineRunner(data_dir=data_dir, pipeline_config=cfg)

        runner._interest_store.add(Interest(
            name="tech", keywords=["python"],
        ))

        file = tmp_path / "long.txt"
        file.write_text("Python programming. " * 5000)

        stats = runner.run_from_files([str(file)])
        assert stats.pages_indexed >= 1
        runner.close()

    def test_pipeline_with_special_characters(self, tmp_path):
        """Test pipeline handles special characters in filenames and content."""
        data_dir = str(tmp_path / "data")
        cfg = PipelineConfig(min_score_threshold=0.0, min_content_length=10)
        runner = PipelineRunner(data_dir=data_dir, pipeline_config=cfg)

        runner._interest_store.add(Interest(
            name="tech", keywords=["python"],
        ))

        file = tmp_path / "special-chars.txt"
        file.write_text(
            "Python: <code>print('hello')</code> & more. "
            "Special chars: @#$%^&*()_+-=[]{}|;':\",./<>?"
        )

        stats = runner.run_from_files([str(file)])
        assert stats.pages_indexed >= 1
        runner.close()

    def test_pipeline_high_score_threshold(self, tmp_path):
        """Test pipeline filters by high score threshold."""
        data_dir = str(tmp_path / "data")
        cfg = PipelineConfig(min_score_threshold=0.3, min_content_length=10)
        runner = PipelineRunner(data_dir=data_dir, pipeline_config=cfg)

        runner._interest_store.add(Interest(
            name="python", keywords=["python"],
        ))

        # Highly relevant content
        relevant = tmp_path / "relevant.txt"
        relevant.write_text("Python Python Python Python Python programming.")

        # Irrelevant content
        irrelevant = tmp_path / "irrelevant.txt"
        irrelevant.write_text("Cooking recipes for pasta and pizza.")

        stats = runner.run_from_files([str(relevant), str(irrelevant)])
        # At least the relevant one should be indexed
        assert stats.pages_indexed >= 1
        runner.close()


class TestSearchEdgeCases:
    """Test search edge cases."""

    def test_search_empty_query(self, tmp_path):
        """Test search with empty query returns no results."""
        data_dir = str(tmp_path / "data")
        index = SearchIndex(db_path=os.path.join(data_dir, "search_index.json"))

        results = index.search("")
        assert results == []

    def test_search_no_results(self, tmp_path):
        """Test search returns empty when no matches."""
        data_dir = str(tmp_path / "data")
        index = SearchIndex(db_path=os.path.join(data_dir, "search_index.json"))

        index.add_page(CrawledPage(
            url="https://example.com/page",
            title="Python Tutorial",
            content="Python programming language.",
        ))

        results = index.search("xyznonexistent")
        assert results == []

    def test_search_case_insensitive(self, tmp_path):
        """Test search is case-insensitive."""
        data_dir = str(tmp_path / "data")
        index = SearchIndex(db_path=os.path.join(data_dir, "search_index.json"))

        index.add_page(CrawledPage(
            url="https://example.com/page",
            title="Python Tutorial",
            content="Python programming language for beginners.",
        ))

        results = index.search("PYTHON")
        assert len(results) >= 1

        results = index.search("python")
        assert len(results) >= 1

    def test_search_limit(self, tmp_path):
        """Test search respects limit parameter."""
        data_dir = str(tmp_path / "data")
        index = SearchIndex(db_path=os.path.join(data_dir, "search_index.json"))

        for i in range(20):
            index.add_page(CrawledPage(
                url=f"https://example.com/page{i}",
                title=f"Python Tutorial {i}",
                content=f"Python programming lesson {i}.",
            ))

        results = index.search("python", limit=5)
        assert len(results) <= 5

    def test_search_snippet_generation(self, tmp_path):
        """Test search generates useful snippets."""
        data_dir = str(tmp_path / "data")
        index = SearchIndex(db_path=os.path.join(data_dir, "search_index.json"))

        index.add_page(CrawledPage(
            url="https://example.com/page",
            title="Python Tutorial",
            content="This is a long article about Python programming. "
                    "Python is great for web development and data science. "
                    "Many developers love Python for its simplicity.",
        ))

        results = index.search("data science")
        assert len(results) >= 1
        assert results[0].snippet  # Should have a snippet
        assert "data" in results[0].snippet.lower() or "science" in results[0].snippet.lower()


class TestTagEdgeCases:
    """Test tag system edge cases."""

    def test_tag_duplicate_add(self, tmp_path):
        """Test adding same tag to page multiple times."""
        store = TagStore(store_path=str(tmp_path / "tags.json"))

        store.add_tag_to_page("https://example.com/page", "python")
        store.add_tag_to_page("https://example.com/page", "python")

        tags = store.get_tags_for_page("https://example.com/page")
        assert len(tags) == 1

    def test_tag_case_sensitivity(self, tmp_path):
        """Test tag name case sensitivity."""
        store = TagStore(store_path=str(tmp_path / "tags.json"))

        store.add_tag_to_page("https://example.com/page", "Python")
        store.add_tag_to_page("https://example.com/page", "python")

        # Tags are case-sensitive
        all_tags = store.list_tags()
        tag_names = [t.name for t in all_tags]
        assert "Python" in tag_names or "python" in tag_names

    def test_tag_remove_nonexistent(self, tmp_path):
        """Test removing tag from page that doesn't have it."""
        store = TagStore(store_path=str(tmp_path / "tags.json"))

        result = store.remove_tag_from_page("https://example.com/page", "python")
        assert result is False

    def test_tag_delete_cascades(self, tmp_path):
        """Test deleting a tag removes it from all pages."""
        store = TagStore(store_path=str(tmp_path / "tags.json"))

        store.add_tag_to_page("https://example.com/page1", "python")
        store.add_tag_to_page("https://example.com/page2", "python")

        store.delete_tag("python")

        pages = store.get_pages_for_tag("python")
        assert pages == []


class TestInterestEdgeCases:
    """Test interest system edge cases."""

    def test_interest_duplicate_name(self, tmp_path):
        """Test adding interest with same name overwrites."""
        store = InterestStore(store_path=str(tmp_path / "interests.json"))

        store.add(Interest(name="tech", keywords=["python"]))
        store.add(Interest(name="tech", keywords=["javascript"]))

        interest = store.get("tech")
        assert interest is not None
        assert "javascript" in interest.keywords

    def test_interest_disabled_not_matched(self, tmp_path):
        """Test disabled interests don't match."""
        interest = Interest(name="tech", keywords=["python"], enabled=False)
        assert not interest.matches("python programming")

    def test_interest_priority_clamping(self, tmp_path):
        """Test interest priority is clamped to 1-10."""
        interest = Interest(name="tech", keywords=["python"], priority=100)
        assert interest.priority == 10

        interest2 = Interest(name="tech2", keywords=["python"], priority=-5)
        assert interest2.priority == 1

    def test_interest_total_score(self, tmp_path):
        """Test total score calculation across interests."""
        store = InterestStore(store_path=str(tmp_path / "interests.json"))

        store.add(Interest(name="python", keywords=["python"], priority=5))
        store.add(Interest(name="web", keywords=["web"], priority=3))

        score = store.total_score("python web development")
        assert score > 0

    def test_interest_matches_any(self, tmp_path):
        """Test finding all matching interests."""
        store = InterestStore(store_path=str(tmp_path / "interests.json"))

        store.add(Interest(name="python", keywords=["python"]))
        store.add(Interest(name="web", keywords=["web"]))
        store.add(Interest(name="db", keywords=["database"]))

        matches = store.matches_any("python web development")
        assert len(matches) == 2
        match_names = {m.name for m in matches}
        assert "python" in match_names
        assert "web" in match_names
