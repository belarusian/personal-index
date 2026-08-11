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
@click.option("--no-snippet", is_flag=True, help="Don't show content snippets")
@click.option("--json", "as_json", is_flag=True, help="Output results as JSON")
@click.pass_context
def search(ctx, query, limit, data_dir, tag, sort, highlight, no_snippet, as_json):
    """Search the indexed content.

    Searches through all indexed pages and returns matching results
    sorted by relevance score.

    Examples:
        personal-index search "python tutorial"
        personal-index search "machine learning" -n 10
        personal-index search "web development" --tag tutorial --tag python
        personal-index search "api docs" --sort relevance
        personal-index search "python" --json
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
        results.sort(key=lambda r: getattr(r, 'crawled_at', r.url) or r.url, reverse=True)
    elif sort == "relevance":
        results.sort(key=lambda r: getattr(r, 'relevance_score', 0) or 0, reverse=True)
    # "score" is default from index.search()

    if as_json:
        import json
        output = []
        for r in results:
            entry = {
                "url": r.url,
                "title": getattr(r, 'title', ''),
                "score": getattr(r, 'relevance_score', 0) or getattr(r, 'score', 0),
                "snippet": getattr(r, 'snippet', ''),
                "tags": list(tag_store.get_tags_for_page(r.url)),
            }
            output.append(entry)
        click.echo(json.dumps(output, indent=2, default=str))
        return

    if not results:
        click.echo(f"No results found for '{query}'")
        return

    click.echo(f"\nFound {len(results)} result(s) for '{query}':\n")
    click.echo("-" * 70)

    for i, result in enumerate(results, 1):
        title = getattr(result, 'title', '') or 'Untitled'
        url = result.url
        score = getattr(result, 'relevance_score', 0) or getattr(result, 'score', 0)
        snippet = getattr(result, 'snippet', '')

        click.echo(f"\n{i}. {title}")
        click.echo(f"   URL: {url}")
        click.echo(f"   Score: {score:.3f}")
        if not no_snippet and snippet:
            # Truncate snippet if too long
            if len(snippet) > 200:
                snippet = snippet[:197] + "..."
            click.echo(f"   {snippet}")
        page_tags = tag_store.get_tags_for_page(result.url)
        if page_tags:
            click.echo(f"   Tags: {', '.join(sorted(t.name for t in page_tags))}")

    click.echo(f"\n{'-' * 70}")
