"""Stats and status CLI commands for personal-index."""

from __future__ import annotations

import json
import os

import click

from personal_index.index import SearchIndex
from personal_index.interests import InterestStore
from personal_index.tags import TagStore


@click.command("stats")
@click.option("--format", "fmt", default="text", type=click.Choice(["text", "json"]),
              help="Output format")
@click.option("--data-dir", default=None, help="Data directory")
@click.pass_context
def stats(ctx, fmt, data_dir):
    """Show index statistics.

    Displays statistics about the current index including page counts,
    tag counts, and interest counts.

    Examples:
        personal-index stats
        personal-index stats --format json
    """
    dd = data_dir or ctx.obj.get("data_dir", ".personal_index")

    search_index = SearchIndex(db_path=os.path.join(dd, "search_index.json"))
    tag_store = TagStore(store_path=os.path.join(dd, "tags.json"))
    interest_store = InterestStore(store_path=os.path.join(dd, "interests.json"))

    data = {
        "indexed_pages": search_index.get_page_count(),
        "total_tags": len(tag_store.list_tags()),
        "tagged_pages": len(tag_store._page_tags),
        "total_interests": len(interest_store.list_all()),
        "data_dir": dd,
    }

    if fmt == "json":
        click.echo(json.dumps(data, indent=2))
    else:
        click.echo("Index Statistics")
        click.echo("=" * 40)
        click.echo(f"Data directory:  {data['data_dir']}")
        click.echo(f"Indexed pages:   {data['indexed_pages']}")
        click.echo(f"Total tags:      {data['total_tags']}")
        click.echo(f"Tagged pages:    {data['tagged_pages']}")
        click.echo(f"Total interests: {data['total_interests']}")
