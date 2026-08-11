"""Search CLI command for personal-index."""

from __future__ import annotations

import os
import sys

import click

from personal_index.index import SearchIndex
from personal_index.tags import TagStore


@click.command("search")
@click.argument("query")
@click.option("--limit", "-n", default=20, type=int, help="Max results to show")
@click.option("--data-dir", default=None, help="Data directory")
@click.option("--tag", "-t", multiple=True, help="Filter by tag")
@click.option("--sort", default="score", type=click.Choice(["score", "date", "relevance"]),
              help="Sort results by field")
@click.option("--highlight", is_flag=True, help="Highlight matching terms")
@click.pass_context
def search(ctx, query, limit, data_dir, tag, sort, highlight):
    """Search the indexed content.

    Searches through all indexed pages and returns matching results
    sorted by relevance score.

    Examples:
        personal-index search "python tutorial"
        personal-index search "machine learning" -n 10
        personal-index search "web development" --tag tutorial --tag python
    """
    dd = data_dir or ctx.obj.get("data_dir", ".personal_index")
    index = SearchIndex(db_path=os.path.join(dd, "search_index.json"))
    tag_store = TagStore(store_path=os.path.join(dd, "tags.json"))

    if not query:
        click.echo("Error: Search query is required.", err=True)
        sys.exit(1)

    results = index.search(query, limit=limit)

    # Filter by tags if specified
    if tag:
        tag_set = set(tag)
        filtered = []
        for r in results:
            page_tags = tag_store.get_tags_for_page(r.url)
            if page_tags and tag_set & set(page_tags):
                filtered.append(r)
        results = filtered

    # Apply sorting
    if sort == "date":
        results.sort(key=lambda r: r.url, reverse=True)
    elif sort == "relevance":
        results.sort(key=lambda r: r.relevance_score, reverse=True)
    # "score" is default from index.search()

    if not results:
        click.echo(f"No results found for '{query}'")
        return

    click.echo(f"\nFound {len(results)} result(s) for '{query}':\n")
    click.echo("-" * 70)

    for i, result in enumerate(results, 1):
        click.echo(f"\n{i}. {result.title or 'Untitled'}")
        click.echo(f"   URL: {result.url}")
        click.echo(f"   Score: {result.relevance_score:.3f}")
        if result.snippet:
            click.echo(f"   {result.snippet}")
        page_tags = tag_store.get_tags_for_page(result.url)
        if page_tags:
            click.echo(f"   Tags: {', '.join(page_tags)}")

    click.echo(f"\n{'-' * 70}")
