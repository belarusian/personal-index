"""Export indexed data to various formats."""

from __future__ import annotations

import csv
import io
import json
import time
from typing import List, Optional

from personal_index.index import SearchIndex, IndexedPage
from personal_index.models import SearchResult


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
        page_dict = page.to_dict()
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


class JSONExporter:
    """Export indexed data to JSON format."""

    def __init__(self, indent: int = 2):
        self.indent = indent

    def export_entries(self, entries: list[dict], filepath: str) -> str:
        """Export entries to a JSON file."""
        data = {
            "exported_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "total_entries": len(entries),
            "entries": entries,
        }
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=self.indent, ensure_ascii=False, default=str)
        return filepath

    def export_entry(self, entry: dict) -> str:
        """Serialize a single entry to JSON string."""
        return json.dumps(entry, indent=self.indent, ensure_ascii=False, default=str)

    def export_batch(self, entries: list[dict], batch_size: int = 100) -> list[str]:
        """Export entries in batches, returning JSON strings."""
        batches = []
        for i in range(0, len(entries), batch_size):
            batch = entries[i : i + batch_size]
            data = {
                "batch_index": i // batch_size,
                "count": len(batch),
                "entries": batch,
            }
            batches.append(json.dumps(data, indent=self.indent, ensure_ascii=False, default=str))
        return batches
