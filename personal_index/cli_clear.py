"""Clear command for resetting the index."""

from __future__ import annotations

import os

import click

from personal_index.index import SearchIndex
from personal_index.tags import TagStore
from personal_index.interests import InterestStore


@click.command("clear")
@click.option("--index/--no-index", default=True, help="Clear search index")
@click.option("--tags/--no-tags", default=True, help="Clear tags")
@click.option("--interests/--no-interests", default=False, help="Clear interests")
@click.option("--data-dir", default=None, help="Data directory")
@click.pass_context
def clear(ctx, index, tags, interests, data_dir):
    """Clear index data.

    Removes indexed pages, tags, and optionally interests.

    Examples:
        personal-index clear
        personal-index clear --index --tags --no-interests
    """
    dd = data_dir or ctx.obj.get("data_dir", ".personal_index")

    if index:
        db_path = os.path.join(dd, "search_index.json")
        idx = SearchIndex(db_path=db_path)
        idx.clear()
        click.echo("Cleared search index")

    if tags:
        tag_store = TagStore(store_path=os.path.join(dd, "tags.json"))
        tag_store.clear()
        click.echo("Cleared tags")

    if interests:
        interest_store = InterestStore(store_path=os.path.join(dd, "interests.json"))
        interest_store.clear()
        click.echo("Cleared interests")

    click.echo("Done.")
