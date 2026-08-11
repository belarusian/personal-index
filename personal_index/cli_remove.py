"""Remove command for deleting indexed pages."""

from __future__ import annotations

import os

import click

from personal_index.index import SearchIndex
from personal_index.tags import TagStore


@click.command("remove")
@click.argument("url")
@click.option("--data-dir", default=None, help="Data directory")
@click.pass_context
def remove_page(ctx, url, data_dir):
    """Remove a page from the index by URL.

    Examples:
        personal-index remove https://example.com/page
    """
    dd = data_dir or ctx.obj.get("data_dir", ".personal_index")

    db_path = os.path.join(dd, "search_index.json")
    index = SearchIndex(db_path=db_path)

    if index.remove_page(url):
        # Also remove from tag store
        tag_store = TagStore(store_path=os.path.join(dd, "tags.json"))
        tag_store.remove_page(url)
        click.echo(f"Removed {url} from index")
    else:
        click.echo(f"Page not found: {url}")
        ctx.exit(1)
