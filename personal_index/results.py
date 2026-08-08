"""Results viewer and formatter for search results."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from personal_index.models import CrawledPage
from personal_index.search_index import SearchIndex


@dataclass
class SearchResult:
    """A formatted search result."""

    rank: int
    url: str
    title: str
    score: float
    snippet: str = ""
    matched_interests: list[str] = None
    meta_description: str = ""

    def __post_init__(self):
        if self.matched_interests is None:
            self.matched_interests = []


class ResultsFormatter:
    """Format search results for display."""

    def __init__(self, max_snippet_length: int = 200):
        self.max_snippet_length = max_snippet_length

    def format_result(self, result: SearchResult) -> str:
        """Format a single search result."""
        lines = []
        lines.append(f"[{result.rank}] {result.title}")
        lines.append(f"    URL: {result.url}")
        lines.append(f"    Score: {result.score:.2f}")
        if result.matched_interests:
            lines.append(f"    Interests: {', '.join(result.matched_interests)}")
        if result.snippet:
            lines.append(f"    {result.snippet}")
        if result.meta_description:
            lines.append(f"    Description: {result.meta_description}")
        return "\n".join(lines)

    def format_results(self, results: list[SearchResult], separator: str = "-" * 60) -> str:
        """Format multiple search results."""
        if not results:
            return "No results found."

        output_parts = []
        for result in results:
            output_parts.append(self.format_result(result))
            output_parts.append(separator)
        return "\n".join(output_parts)

    def create_snippet(self, text: str, query: str, max_length: int = 200) -> str:
        """Create a content snippet highlighting the query."""
        if not text:
            return ""

        text_lower = text.lower()
        query_lower = query.lower()
        pos = text_lower.find(query_lower)

        if pos == -1:
            return text[:max_length] + ("..." if len(text) > max_length else "")

        # Center snippet around the match
        start = max(0, pos - 50)
        end = min(len(text), pos + len(query) + max_length - 50)
        snippet = text[start:end]

        if start > 0:
            snippet = "..." + snippet
        if end < len(text):
            snippet = snippet + "..."

        return snippet


class ResultsExporter:
    """Export search results to various formats."""

    @staticmethod
    def to_json(results: list[SearchResult]) -> str:
        """Export results as JSON."""
        import json
        data = [
            {
                "rank": r.rank,
                "url": r.url,
                "title": r.title,
                "score": r.score,
                "snippet": r.snippet,
                "matched_interests": r.matched_interests,
                "meta_description": r.meta_description,
            }
            for r in results
        ]
        return json.dumps(data, indent=2)

    @staticmethod
    def to_csv(results: list[SearchResult]) -> str:
        """Export results as CSV."""
        import csv
        import io
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["rank", "url", "title", "score", "snippet", "interests"])
        for r in results:
            writer.writerow([
                r.rank,
                r.url,
                r.title,
                f"{r.score:.2f}",
                r.snippet,
                ";".join(r.matched_interests),
            ])
        return output.getvalue()

    @staticmethod
    def to_markdown(results: list[SearchResult]) -> str:
        """Export results as Markdown."""
        lines = []
        for r in results:
            lines.append(f"## {r.rank}. {r.title}")
            lines.append(f"- **URL**: {r.url}")
            lines.append(f"- **Score**: {r.score:.2f}")
            if r.matched_interests:
                lines.append(f"- **Interests**: {', '.join(r.matched_interests)}")
            if r.snippet:
                lines.append(f"- **Snippet**: {r.snippet}")
            lines.append("")
        return "\n".join(lines)


def search_and_format(
    index: SearchIndex,
    query: str,
    limit: int = 10,
    show_snippets: bool = False,
) -> list[SearchResult]:
    """Search the index and return formatted results."""
    raw_results = index.search(query, limit=limit)
    formatter = ResultsFormatter()
    results = []

    for rank, (url, score) in enumerate(raw_results, 1):
        page = index.get(url)
        if not page:
            continue

        snippet = ""
        if show_snippets:
            snippet = formatter.create_snippet(page.content, query)

        results.append(SearchResult(
            rank=rank,
            url=url,
            title=page.title or "Untitled",
            score=score,
            snippet=snippet,
            matched_interests=list(page.matched_interests),
            meta_description=page.meta_description,
        ))

    return results
