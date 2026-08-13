"""Top command for showing highest-scored indexed pages."""

from __future__ import annotations

import json
import os

import click

from personal_index.index import SearchIndex


@click.command("top")
@click.option("--limit", "-l", default=10, type=int, help="Number of top pages to show")
@click.option("--format", "fmt", default="text", type=click.Choice(["text", "json"]),
              help="Output format")
@click.option("--data-dir", default=None, help="Data directory")
@click.pass_context
def top_pages(ctx, limit, fmt, data_dir):
    """Show the highest-scored indexed pages."""
    dd = data_dir or ctx.obj.get("data_dir", ".personal_index")
    index = SearchIndex(db_path=os.path.join(dd, "search_index.json"))
    pages = index.list_pages()[:limit]
    if not pages:
        click.echo("No indexed pages found. Run 'personal-index pipeline' first.")
        return
    if fmt == "json":
        click.echo(json.dumps(_to_json(pages), indent=2))
    else:
        _print_text(pages)

def _to_json(pages: list) -> dict:
    """Convert pages to JSON-serializable dict."""
    return {
        "top_pages": [
            {"rank": i + 1, "url": p.url, "title": p.title,
             "score": p.score, "crawled_at": p.crawled_at, "tags": []}
            for i, p in enumerate(pages)
        ],
        "total": len(pages),
    }

def _print_text(pages: list) -> None:
    """Print pages in text format."""
    click.echo(f"\nTop {len(pages)} pages by score:")
    click.echo("=" * 60)
    for i, p in enumerate(pages, 1):
        click.echo(f"\n{i}. {p.title}")
        click.echo(f"   Score: {p.score:.4f}")
        click.echo(f"   URL:   {p.url}")
        click.echo(f"   Date:  {p.crawled_at or 'N/A'}")
