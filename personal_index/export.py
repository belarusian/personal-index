"""Export indexed data to various formats."""

from __future__ import annotations

import csv
import io
import json
from dataclasses import asdict
from typing import Dict, List, Optional

from personal_index.index import SearchIndex
from personal_index.models import IndexedPage, SearchResult


def export_to_json(
    index: SearchIndex,
    include_content: bool = True,
    indent: int = 2,
) -> str:
    """Export all indexed pages to JSON string."""
    pages = index.list_pages()
    data = {
        "total_pages": len(pages),
        "pages": [],
    }
    for page in pages:
        page_dict = asdict(page)
        if not include_content:
            page_dict.pop("content", None)
        data["pages"].append(page_dict)
    return json.dumps(data, indent=indent, default=str)


def export_to_csv(
    index: SearchIndex,
    include_content: bool = False,
) -> str:
    """Export indexed pages to CSV string."""
    pages = index.list_pages()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["url", "title", "score", "indexed_at", "content"])
    for page in pages:
        row = [
            page.url,
            page.title,
            page.score,
            page.indexed_at,
            page.content if include_content else "",
        ]
        writer.writerow(row)
    return output.getvalue()


def export_search_results_to_json(
    results: List[SearchResult], indent: int = 2
) -> str:
    """Export search results to JSON string."""
    data = {
        "total_results": len(results),
        "results": [],
    }
    for r in results:
        data["results"].append({
            "url": r.url,
            "title": r.title,
            "snippet": r.snippet,
            "relevance_score": r.relevance_score,
        })
    return json.dumps(data, indent=indent)


def export_search_results_to_csv(results: List[SearchResult]) -> str:
    """Export search results to CSV string."""
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["url", "title", "snippet", "relevance_score"])
    for r in results:
        writer.writerow([r.url, r.title, r.snippet, r.relevance_score])
    return output.getvalue()


def export_to_markdown(
    index: SearchIndex,
    include_content: bool = False,
) -> str:
    """Export indexed pages to Markdown format."""
    pages = index.list_pages()
    lines = ["# Indexed Pages", f"\n**Total pages:** {len(pages)}\n"]
    for page in pages:
        lines.append(f"## {page.title}")
        lines.append(f"- **URL:** {page.url}")
        lines.append(f"- **Score:** {page.score}")
        lines.append(f"- **Indexed:** {page.indexed_at}")
        if include_content and page.content:
            lines.append(f"\n{page.content[:500]}")
        lines.append("")
    return "\n".join(lines)


def export_to_markdown_results(results: List[SearchResult]) -> str:
    """Export search results to Markdown format."""
    lines = ["# Search Results", f"\n**Total results:** {len(results)}\n"]
    for i, r in enumerate(results, 1):
        lines.append(f"## {i}. {r.title}")
        lines.append(f"- **URL:** {r.url}")
        lines.append(f"- **Score:** {r.relevance_score:.2f}")
        if r.snippet:
            lines.append(f"\n> {r.snippet[:200]}")
        lines.append("")
    return "\n".join(lines)
