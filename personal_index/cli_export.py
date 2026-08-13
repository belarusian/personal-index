"""Export CLI command for personal-index."""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone

import click

from personal_index.index import SearchIndex
from personal_index.tags import TagStore


@click.command("export")
@click.option("--format", "fmt", default="markdown",
              type=click.Choice(["markdown", "json", "csv", "html"]),
              help="Export format")
@click.option("--output", "-o", default=None, help="Output file path")
@click.option("--data-dir", default=None, help="Data directory")
@click.option("--tag", "-t", multiple=True, help="Filter by tag")
@click.option("--query", "-q", default=None, help="Search query to filter results")
@click.option("--limit", "-n", default=0, type=int, help="Max pages to export (0=all)")
@click.pass_context
def export_cmd(ctx, fmt, output, data_dir, tag, query, limit):
    """Export indexed content in various formats.

    Exports all indexed pages (or a filtered subset) in the specified
    format. Supports markdown, JSON, CSV, and HTML output.

    Examples:
        personal-index export --format markdown
        personal-index export --format json -o results.json
        personal-index export --format csv --tag tutorial
        personal-index export --format html --query "python"
    """
    dd = data_dir or ctx.obj.get("data_dir", ".personal_index")
    index = SearchIndex(db_path=os.path.join(dd, "search_index.json"))
    tag_store = TagStore(store_path=os.path.join(dd, "tags.json"))

    pages = _load_pages(index, tag_store, query, tag, limit)

    if not pages:
        click.echo("No pages to export.")
        return

    output_text = _dispatch_format(fmt, pages, tag_store)

    if output:
        with open(output, "w", encoding="utf-8") as f:
            f.write(output_text)
        click.echo(f"Exported {len(pages)} pages to {output}")
    else:
        click.echo(output_text)


def _load_pages(index, tag_store, query, tag, limit):
    """Load and filter pages from the index.

    Args:
        index: The SearchIndex instance.
        tag_store: The TagStore instance.
        query: Optional search query to filter results.
        tag: Tuple of tag names to filter by.
        limit: Maximum number of pages to return (0 = all).

    Returns:
        List of filtered and limited pages.
    """
    pages = index.list_pages()

    # Filter by query
    if query:
        results = index.search(query, limit=max(len(pages), 1000))
        result_urls = {r.url for r in results}
        pages = [p for p in pages if p.url in result_urls]

    # Filter by tags
    if tag:
        tag_set = set(tag)
        filtered = []
        for p in pages:
            page_tags = tag_store.get_tags_for_page(p.url)
            if page_tags and tag_set & set(page_tags):
                filtered.append(p)
        pages = filtered

    # Apply limit
    if limit > 0:
        pages = pages[:limit]

    return pages


def _dispatch_format(fmt, pages, tag_store):
    """Dispatch to the appropriate format exporter.

    Args:
        fmt: The export format string (markdown, json, csv, html).
        pages: List of pages to export.
        tag_store: The TagStore instance for tag lookups.

    Returns:
        The formatted output string.
    """
    dispatch = {
        "markdown": _export_markdown,
        "json": _export_json,
        "csv": _export_csv,
        "html": _export_html,
    }
    exporter = dispatch.get(fmt, _export_markdown)
    return exporter(pages, tag_store)


def _tag_names(tags):
    """Extract tag names from a list of tags (handles Tag objects and strings)."""
    names = []
    for t in tags:
        if hasattr(t, "name"):
            names.append(t.name)
        else:
            names.append(str(t))
    return names


def _export_markdown(pages, tag_store):
    """Export pages as markdown."""
    lines = ["# Personal Index Export", "",
             f"Exported: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}",
             f"Total pages: {len(pages)}", ""]

    for page in pages:
        lines.append(f"## {page.title or 'Untitled'}")
        lines.append(f"- **URL**: {page.url}")
        score = getattr(page, 'score', 0) or getattr(page, 'relevance_score', 0)
        lines.append(f"- **Score**: {score:.3f}")
        tags = tag_store.get_tags_for_page(page.url)
        if tags:
            tag_names = _tag_names(tags)
            lines.append(f"- **Tags**: {', '.join(sorted(tag_names))}")
        content = getattr(page, 'content', '') or ''
        if content:
            snippet = content[:300]
            if len(content) > 300:
                snippet += "..."
            lines.append(f"\n{snippet}")
        lines.append("")

    return "\n".join(lines)


def _export_json(pages, tag_store):
    """Export pages as JSON."""
    data = []
    for page in pages:
        tags = tag_store.get_tags_for_page(page.url)
        tag_names = _tag_names(tags)
        entry = {
            "url": page.url,
            "title": page.title or "",
            "score": getattr(page, 'score', 0) or getattr(page, 'relevance_score', 0),
            "content_length": getattr(page, 'content_length', len(page.content or '')),
            "tags": list(tag_names),
            "crawled_at": getattr(page, 'crawled_at', ''),
        }
        data.append(entry)
    return json.dumps(data, indent=2, default=str)


def _export_csv(pages, tag_store):
    """Export pages as CSV."""
    lines = ["url,title,score,tags,content_length"]
    for page in pages:
        title = (page.title or "").replace('"', '""')
        tags = tag_store.get_tags_for_page(page.url)
        tag_names = _tag_names(tags)
        tags_str = ";".join(sorted(tag_names))
        score = getattr(page, 'score', 0) or getattr(page, 'relevance_score', 0)
        content_len = getattr(page, 'content_length', len(page.content or ''))
        lines.append(f'"{page.url}","{title}",{score:.3f},"{tags_str}",{content_len}')
    return "\n".join(lines)


def _export_html(pages, tag_store):
    """Export pages as HTML."""
    lines = [
        "<!DOCTYPE html>",
        "<html><head><title>Personal Index Export</title>",
        ("<style>body{font-family:sans-serif;margin:2em;} table{border-collapse:collapse;} "
        "th,td{border:1px solid #ddd;padding:8px;text-align:left;} th{background:#f5f5f5;}</style>"),
        "</head><body>",
        "<h1>Personal Index Export</h1>",
        (f"<p>Exported: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')} "
        f"| Total pages: {len(pages)}</p>"),
        "<table><tr><th>Title</th><th>URL</th><th>Score</th><th>Tags</th></tr>",
    ]
    for page in pages:
        title = (page.title or "Untitled").replace("<", "&lt;").replace(">", "&gt;")
        score = getattr(page, 'score', 0) or getattr(page, 'relevance_score', 0)
        tags = tag_store.get_tags_for_page(page.url)
        tag_names = _tag_names(tags)
        tags_str = ", ".join(sorted(tag_names))
        lines.append(f'<tr><td>{title}</td><td><a href="{page.url}">{page.url}</a></td>'
                     f'<td>{score:.3f}</td><td>{tags_str}</td></tr>')
    lines.append("</table></body></html>")
    return "\n".join(lines)
