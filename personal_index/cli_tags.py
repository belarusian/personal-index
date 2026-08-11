"""Tags CLI command group for personal-index."""

from __future__ import annotations

import os
import sys

import click

from personal_index.tags import TagStore


@click.group("tags")
@click.pass_context
def tags(ctx):
    """Manage tags for indexed pages.

    Tags help organize and categorize your indexed content.
    They can be used to filter search results.

    Examples:
        personal-index tags add important https://example.com/page
        personal-index tags list
        personal-index tags remove important https://example.com/page
    """


@tags.command("add")
@click.argument("tag_name")
@click.argument("url")
@click.option("--color", "-c", default="#3498db", help="Tag color (hex)")
@click.option("--description", "-d", default="", help="Tag description")
@click.option("--data-dir", default=None, help="Data directory")
@click.pass_context
def tags_add(ctx, tag_name, url, color, description, data_dir):
    """Add a tag to a page."""
    dd = data_dir or ctx.obj.get("data_dir", ".personal_index")
    store = TagStore(store_path=os.path.join(dd, "tags.json"))

    store.add_tag_to_page(url, tag_name)
    click.echo(f"Added tag '{tag_name}' to {url}")


@tags.command("list")
@click.option("--data-dir", default=None, help="Data directory")
@click.pass_context
def tags_list(ctx, data_dir):
    """List all tags and their page counts."""
    dd = data_dir or ctx.obj.get("data_dir", ".personal_index")
    store = TagStore(store_path=os.path.join(dd, "tags.json"))

    tags = store.list_tags()
    if not tags:
        click.echo("No tags configured.")
        return

    click.echo(f"Tags ({len(tags)}):")
    click.echo("-" * 50)
    for tag in sorted(tags, key=lambda t: t.name):
        pages = store.get_pages_for_tag(tag.name)
        desc = tag.description if tag else ""
        click.echo(f"\n  {tag.name} ({len(pages)} pages)")
        if desc:
            click.echo(f"    Description: {desc}")
        if len(pages) <= 5:
            for page_url in pages:
                click.echo(f"    - {page_url}")
        else:
            for page_url in pages[:5]:
                click.echo(f"    - {page_url}")
            click.echo(f"    ... and {len(pages) - 5} more")


@tags.command("remove")
@click.argument("tag_name")
@click.argument("url")
@click.option("--data-dir", default=None, help="Data directory")
@click.pass_context
def tags_remove(ctx, tag_name, url, data_dir):
    """Remove a tag from a page."""
    dd = data_dir or ctx.obj.get("data_dir", ".personal_index")
    store = TagStore(store_path=os.path.join(dd, "tags.json"))

    if store.remove_tag_from_page(url, tag_name):
        click.echo(f"Removed tag '{tag_name}' from {url}")
    else:
        click.echo(f"Tag '{tag_name}' not found on {url}", err=True)
        sys.exit(1)


@tags.command("delete")
@click.argument("tag_name")
@click.option("--data-dir", default=None, help="Data directory")
@click.pass_context
def tags_delete(ctx, tag_name, data_dir):
    """Delete a tag entirely (removes from all pages)."""
    dd = data_dir or ctx.obj.get("data_dir", ".personal_index")
    store = TagStore(store_path=os.path.join(dd, "tags.json"))

    pages = store.get_pages_for_tag(tag_name)
    if store.delete_tag(tag_name):
        click.echo(f"Deleted tag '{tag_name}' (was on {len(pages)} pages)")
    else:
        click.echo(f"Tag '{tag_name}' not found.", err=True)
        sys.exit(1)


@tags.command("pages")
@click.argument("tag_name")
@click.option("--data-dir", default=None, help="Data directory")
@click.pass_context
def tags_pages(ctx, tag_name, data_dir):
    """List all pages with a specific tag."""
    dd = data_dir or ctx.obj.get("data_dir", ".personal_index")
    store = TagStore(store_path=os.path.join(dd, "tags.json"))

    pages = store.get_pages_for_tag(tag_name)
    if not pages:
        click.echo(f"No pages tagged with '{tag_name}'.")
        return

    click.echo(f"Pages tagged with '{tag_name}' ({len(pages)}):")
    for i, page_url in enumerate(sorted(pages), 1):
        click.echo(f"  {i}. {page_url}")
