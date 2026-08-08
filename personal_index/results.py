"""Search results formatting and export."""

from __future__ import annotations

import csv
import io
import json
from dataclasses import dataclass, field
from typing import List

from personal_index.search_index import SearchIndex


@dataclass
class SearchResult:
    """A formatted search result."""

    rank: int = 0
    url: str = ""
    title: str = ""
    score: float = 0.0
    snippet: str = ""
    matched_interests: List[str] = field(default_factory=list)
    meta_description: str = ""


class ResultsFormatter:
    """Formats search results for display."""

    def __init__(self, max_snippet_length: int = 200):
        self.max_snippet_length = max_snippet_length

    def format_result(self, result: SearchResult) -> str:
        """Format a single search result."""
        lines = [
            f"[{result.rank}] {result.title}",
            f"    URL: {result.url}",
            f"    Score: {result.score:.2f}",
        ]
        if result.snippet:
            lines.append(f"    {result.snippet}")
        if result.matched_interests:
            lines.append(
                f"    Interests: {', '.join(result.matched_interests)}"
            )
        if result.meta_description:
            lines.append(f"    {result.meta_description}")
        return "\n".join(lines)

    def format_results(self, results: List[SearchResult]) -> str:
        """Format multiple search results."""
        if not results:
            return "No results found."
        lines = []
        for result in results:
            lines.append(self.format_result(result))
            lines.append("-" * 60)
        return "\n".join(lines)

    def create_snippet(
        self, text: str, query: str, max_length: int = 200
    ) -> str:
        """Create a snippet highlighting the query."""
        if not text:
            return ""
        query_lower = query.lower()
        idx = text.lower().find(query_lower)
        if idx == -1:
            return text[: max_length + 50]
        start = max(0, idx - 50)
        end = min(len(text), idx + len(query) + max_length)
        snippet = text[start:end]
        if start > 0:
            snippet = "..." + snippet
        if end < len(text):
            snippet = snippet + "..."
        return snippet


class ResultsExporter:
    """Export search results to various formats."""

    @staticmethod
    def to_json(results: List[SearchResult]) -> str:
        """Export results as JSON."""
        data = [
            {
                "rank": r.rank,
                "url": r.url,
                "title": r.title,
                "score": r.score,
                "snippet": r.snippet,
                "interests": r.matched_interests,
            }
            for r in results
        ]
        return json.dumps(data, indent=2)

    @staticmethod
    def to_csv(results: List[SearchResult]) -> str:
        """Export results as CSV."""
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow([
            "rank", "url", "title", "score", "snippet", "interests"
        ])
        for r in results:
            writer.writerow([
                r.rank, r.url, r.title, r.score, r.snippet,
                ";".join(r.matched_interests),
            ])
        return output.getvalue()

    @staticmethod
    def to_markdown(results: List[SearchResult]) -> str:
        """Export results as Markdown."""
        lines = []
        for r in results:
            lines.append(f"## {r.rank}. {r.title}")
            lines.append(f"**URL**: {r.url}")
            lines.append(f"**Score**: {r.score:.2f}")
            if r.snippet:
                lines.append(f"{r.snippet}")
            if r.matched_interests:
                lines.append(
                    f"**Interests**: {', '.join(r.matched_interests)}"
                )
            lines.append("")
        return "\n".join(lines)


def search_and_format(
    index: SearchIndex,
    query: str,
    limit: int = 10,
    show_snippets: bool = False,
) -> List[SearchResult]:
    """Search index and format results."""
    raw_results = index.search(query, limit=limit)
    formatter = ResultsFormatter()
    results = []
    for rank, (url, score) in enumerate(raw_results, 1):
        page = index.get(url)
        if page is None:
            continue
        snippet = ""
        if show_snippets:
            snippet = formatter.create_snippet(page.content, query)
        results.append(SearchResult(
            rank=rank,
            url=url,
            title=page.title,
            score=score,
            snippet=snippet,
            matched_interests=page.matched_interests,
            meta_description=page.meta_description,
        ))
    return results
