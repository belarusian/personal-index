"""Search CLI commands for personal-index."""

from __future__ import annotations

import json
import os
import sys

import click

from personal_index.index import SearchIndex
from personal_index.tags import TagStore


@click.command("search")
@click.argument("query")
@click.option("--limit", "-l", default=20, type=int, help="Maximum results to return")
@click.option("--tag", default=None, help="Filter results by tag")
@click.option("--format", "fmt", default="text", type=click.Choice(["text", "json", "csv"]),
              help="Output format")
@click.option("--data-dir", default=None, help="Data directory")
@click.pass_context
def search(ctx, query, limit, tag, fmt, data_dir):
    """Search the indexed content.

    Performs full-text search across all indexed pages.

    Examples:
        personal-index search "python tutorial"
        personal-index search "web development" --limit 10
        personal-index search "api" --tag documentation
        personal-index search "rust" --format json
    """
    dd = data_dir or ctx.obj.get("data_dir", ".personal_index")

    db_path = os.path.join(dd, "search_index.json")
    index = SearchIndex(db_path=db_path)

    if index.get_page_count() == 0:
        click.echo("No indexed content found. Run 'personal-index pipeline' first.")
        return

    results = index.search(query, limit=limit)

    # Apply tag filter if specified
    if tag:
        tag_store = TagStore(store_path=os.path.join(dd, "tags.json"))
        tagged_urls = tag_store.get_pages_for_tag(tag)
        results = [r for r in results if r.url in tagged_urls]

    # Output results
    if fmt == "json":
        _output_json(results)
    elif fmt == "csv":
        _output_csv(results)
    else:
        _output_text(results, query)


def _output_text(results, query):
    """Output search results in text format."""
    if not results:
        click.echo(f"No results found for '{query}'")
        return

    click.echo(f"\nSearch results for '{query}' ({len(results)} found):")
    click.echo("-" * 60)

    for i, result in enumerate(results, 1):
        click.echo(f"\n{i}. {result.title}")
        click.echo(f"   {result.url}")
        click.echo(f"   Score: {result.relevance_score:.4f}")
        if result.snippet:
            click.echo(f"   {result.snippet[:200]}")


def _output_json(results):
    """Output search results in JSON format."""
    data = {
        "results": [
            {
                "url": r.url,
                "title": r.title,
                "snippet": r.snippet,
                "relevance_score": r.relevance_score,
            }
            for r in results
        ],
        "total": len(results),
    }
    click.echo(json.dumps(data, indent=2))


def _output_csv(results):
    """Output search results in CSV format."""
    import csv
    import io

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["rank", "title", "url", "score", "snippet"])
    for i, r in enumerate(results, 1):
        writer.writerow([i, r.title, r.url, f"{r.relevance_score:.4f}", r.snippet[:200]])
    click.echo(output.getvalue().strip())
