"""List command for browsing indexed content."""

from __future__ import annotations

import csv
import io
import json
import os

import click

from personal_index.index import SearchIndex
from personal_index.tags import TagStore


@click.command("list")
@click.option("--limit", "-l", default=50, type=int, help="Maximum results to show")
@click.option("--tag", default=None, help="Filter by tag")
@click.option("--sort", default="score", type=click.Choice(["score", "date", "title"]),
              help="Sort order")
@click.option("--format", "fmt", default="text", type=click.Choice(["text", "json", "csv"]),
              help="Output format")
@click.option("--data-dir", default=None, help="Data directory")
@click.pass_context
def list_pages(ctx, limit, tag, sort, fmt, data_dir):
    """List indexed pages.

    Shows all indexed pages with their scores and metadata.

    Examples:
        personal-index list
        personal-index list --limit 10 --sort date
        personal-index list --tag tutorial --format json
    """
    dd = data_dir or ctx.obj.get("data_dir", ".personal_index")

    db_path = os.path.join(dd, "search_index.json")
    index = SearchIndex(db_path=db_path)

    pages = index.list_pages()

    # Apply tag filter
    if tag:
        tag_store = TagStore(store_path=os.path.join(dd, "tags.json"))
        tagged_urls = tag_store.get_pages_for_tag(tag)
        pages = [p for p in pages if p.url in tagged_urls]

    # Sort
    if sort == "date":
        pages.sort(key=lambda p: p.crawled_at or "", reverse=True)
    elif sort == "title":
        pages.sort(key=lambda p: p.title.lower())
    else:
        pages.sort(key=lambda p: p.score, reverse=True)

    pages = pages[:limit]

    if fmt == "json":
        _output_json(pages)
    elif fmt == "csv":
        _output_csv(pages)
    else:
        _output_text(pages)


def _output_text(pages):
    if not pages:
        click.echo("No indexed pages found.")
        return
    click.echo(f"\nIndexed pages ({len(pages)}):")
    click.echo("-" * 70)
    for i, p in enumerate(pages, 1):
        click.echo(f"\n{i}. {p.title}")
        click.echo(f"   URL:   {p.url}")
        click.echo(f"   Score: {p.score:.4f}")
        click.echo(f"   Date:  {p.crawled_at or 'N/A'}")


def _output_json(pages):
    data = {
        "pages": [
            {
                "url": p.url,
                "title": p.title,
                "score": p.score,
                "crawled_at": p.crawled_at,
                "content_length": p.content_length,
            }
            for p in pages
        ],
        "total": len(pages),
    }
    click.echo(json.dumps(data, indent=2))


def _output_csv(pages):
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["rank", "title", "url", "score", "crawled_at", "content_length"])
    for i, p in enumerate(pages, 1):
        writer.writerow([i, p.title, p.url, f"{p.score:.4f}", p.crawled_at or "", p.content_length])
    click.echo(output.getvalue().strip())
