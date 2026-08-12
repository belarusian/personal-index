"""Integration tests for content export functionality."""

from __future__ import annotations

import json

from personal_index.index import SearchIndex
from personal_index.models import CrawledPage


class TestExportIntegrationE2E:
    """Test content export with realistic scenarios."""

    def test_export_to_markdown(self, tmp_path):
        """Export index to markdown format."""
        index = SearchIndex(db_path=str(tmp_path / "index.json"))
        
        # Add some pages
        index.add_page(CrawledPage(
            url="https://example.com/page1",
            title="Page 1",
            content="Content for page one.",
        ))
        index.add_page(CrawledPage(
            url="https://example.com/page2",
            title="Page 2",
            content="Content for page two with more details.",
        ))
        
        # Export to markdown
        pages = index.list_pages()
        lines = ["# Exported Content", ""]
        for p in pages:
            lines.append(f"## {p.title}")
            lines.append(f"**URL:** {p.url}")
            if hasattr(p, 'score') and p.score:
                lines.append(f"**Score:** {p.score:.2f}")
            snippet = getattr(p, "snippet", "")
            if snippet:
                lines.append(snippet)
            lines.append("")
        
        content = "\n".join(lines)
        
        assert "# Exported Content" in content
        assert "Page 1" in content
        assert "Page 2" in content

    def test_export_to_json(self, tmp_path):
        """Export index to JSON format."""
        index = SearchIndex(db_path=str(tmp_path / "index.json"))
        
        # Add some pages
        index.add_page(CrawledPage(
            url="https://example.com/page1",
            title="Page 1",
            content="Content for page one.",
        ))
        index.add_page(CrawledPage(
            url="https://example.com/page2",
            title="Page 2",
            content="Content for page two.",
        ))
        
        # Export to JSON
        pages = index.list_pages()
        data = []
        for p in pages:
            item = {
                "title": p.title,
                "url": p.url,
                "snippet": getattr(p, 'snippet', ''),
                "score": getattr(p, 'score', 0),
            }
            data.append(item)
        
        json_content = json.dumps(data, indent=2)
        parsed = json.loads(json_content)
        
        assert len(parsed) == 2
        assert parsed[0]["title"] == "Page 1"

    def test_export_with_query_filter(self, tmp_path):
        """Export only content matching a query."""
        index = SearchIndex(db_path=str(tmp_path / "index.json"))
        
        # Add pages with different content
        index.add_page(CrawledPage(
            url="https://example.com/python",
            title="Python Guide",
            content="Python is a programming language.",
        ))
        index.add_page(CrawledPage(
            url="https://example.com/rust",
            title="Rust Guide",
            content="Rust is a systems programming language.",
        ))
        
        # Search for python
        results = index.search("python")
        assert len(results) == 1
        assert "Python" in results[0].title

    def test_export_limit(self, tmp_path):
        """Export respects limit parameter."""
        index = SearchIndex(db_path=str(tmp_path / "index.json"))
        
        # Add many pages
        for i in range(10):
            index.add_page(CrawledPage(
                url=f"https://example.com/page{i}",
                title=f"Page {i}",
                content=f"Content for page {i}.",
            ))
        
        # Export with limit
        results = index.search("*", limit=3)
        assert len(results) <= 3

    def test_export_empty_index(self, tmp_path):
        """Export from empty index."""
        index = SearchIndex(db_path=str(tmp_path / "index.json"))
        
        pages = index.list_pages()
        data = []
        for p in pages:
            data.append({
                "title": p.title,
                "url": p.url,
            })
        
        assert len(data) == 0

    def test_export_with_snippet(self, tmp_path):
        """Export includes snippets when available."""
        index = SearchIndex(db_path=str(tmp_path / "index.json"))
        
        index.add_page(CrawledPage(
            url="https://example.com/test",
            title="Test Page",
            content="This is a long piece of content that contains the word search in the middle.",
        ))
        
        results = index.search("search")
        assert len(results) == 1
        assert "search" in results[0].snippet.lower()

    def test_export_sorted_by_score(self, tmp_path):
        """Export sorts pages by score."""
        from personal_index.models import IndexedPage
        
        index = SearchIndex(db_path=str(tmp_path / "index.json"))
        
        # Add pages with different scores
        index.add_page(IndexedPage(
            url="https://example.com/low",
            title="Low Score",
            content="Low score page", score=0.3,
        ))
        index.add_page(IndexedPage(
            url="https://example.com/high",
            title="High Score",
            content="High score page", score=0.9,
        ))
        
        pages = index.list_pages()
        
        # Should be sorted by score descending
        assert pages[0].score >= pages[1].score

    def test_export_format_consistency(self, tmp_path):
        """Export formats are consistent."""
        index = SearchIndex(db_path=str(tmp_path / "index.json"))
        
        page = CrawledPage(
            url="https://example.com/test",
            title="Test Page",
            content="Test content.",
        )
        index.add_page(page)
        
        # Export as markdown
        pages = index.list_pages()
        md_lines = ["# Exported Content", ""]
        for p in pages:
            md_lines.append(f"## {p.title}")
            md_lines.append(f"**URL:** {p.url}")
        md_content = "\n".join(md_lines)
        
        # Export as JSON
        json_data = []
        for p in pages:
            json_data.append({
                "title": p.title,
                "url": p.url,
            })
        json_content = json.dumps(json_data, indent=2)
        
        # Both should have the same title and URL
        assert "Test Page" in md_content
        assert "Test Page" in json_content

    def test_export_large_index(self, tmp_path):
        """Export handles large index."""
        index = SearchIndex(db_path=str(tmp_path / "index.json"))
        
        # Add 100 pages
        for i in range(100):
            index.add_page(CrawledPage(
                url=f"https://example.com/page{i}",
                title=f"Page {i}",
                content=f"Content for page {i}.",
            ))
        
        # Export should work
        pages = index.list_pages()
        assert len(pages) == 100
        
        data = []
        for p in pages:
            data.append({
                "title": p.title,
                "url": p.url,
            })
        
        json_content = json.dumps(data)
        parsed = json.loads(json_content)
        assert len(parsed) == 100

    def test_export_preserves_metadata(self, tmp_path):
        """Export preserves page metadata."""
        from personal_index.models import IndexedPage
        
        index = SearchIndex(db_path=str(tmp_path / "index.json"))
        
        page = IndexedPage(
            url="https://example.com/test",
            title="Test Page",
            content="Content",
            score=0.8,
            crawled_at="2024-01-01T00:00:00Z",
            domain="example.com",
            status_code=200,
            content_length=100,
        )
        index.add_page(page)
        
        # Export
        pages = index.list_pages()
        data = []
        for p in pages:
            data.append({
                "title": p.title,
                "url": p.url,
                "score": p.score,
                "domain": p.domain,
            })
        
        assert data[0]["score"] == 0.8
        assert data[0]["domain"] == "example.com"
