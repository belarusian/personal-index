"""Status CLI command for personal-index."""

from __future__ import annotations

import os

import click

from personal_index.index import SearchIndex
from personal_index.interests import InterestStore
from personal_index.tags import TagStore


@click.command("status")
@click.option("--data-dir", default=None, help="Data directory")
@click.pass_context
def status(ctx, data_dir):
    """Show the current status of your personal-index.

    Displays statistics about indexed pages, tags, interests, and
    storage usage.

    Examples:
        personal-index status
    """
    dd = data_dir or ctx.obj.get("data_dir", ".personal_index")

    if not os.path.exists(dd):
        click.echo("No personal-index found. Run 'personal-index init' first.")
        return

    # Load components
    search_index = SearchIndex(db_path=os.path.join(dd, "search_index.json"))
    tag_store = TagStore(store_path=os.path.join(dd, "tags.json"))
    interest_store = InterestStore(store_path=os.path.join(dd, "interests.json"))

    # Calculate stats
    page_count = search_index.get_page_count()
    tag_count = tag_store.get_tag_count()
    tagged_pages = tag_store.get_tagged_page_count()
    interest_count = len(interest_store.list_all())
    enabled_interests = len(interest_store.get_enabled())

    # Calculate storage
    total_size = 0
    for root, dirs, files in os.walk(dd):
        for f in files:
            fp = os.path.join(root, f)
            try:
                total_size += os.path.getsize(fp)
            except OSError:
                pass

    # Format size
    if total_size < 1024:
        size_str = f"{total_size} B"
    elif total_size < 1024 * 1024:
        size_str = f"{total_size / 1024:.1f} KB"
    else:
        size_str = f"{total_size / (1024 * 1024):.1f} MB"

    click.echo("Personal Index Status")
    click.echo("=" * 40)
    click.echo(f"  Data directory: {dd}")
    click.echo(f"  Storage used:   {size_str}")
    click.echo("")
    click.echo("Index:")
    click.echo(f"  Pages indexed:  {page_count}")
    click.echo("")
    click.echo("Tags:")
    click.echo(f"  Unique tags:    {tag_count}")
    click.echo(f"  Tagged pages:   {tagged_pages}")
    click.echo("")
    click.echo("Interests:")
    click.echo(f"  Total:          {interest_count}")
    click.echo(f"  Enabled:        {enabled_interests}")

    if interest_count > 0:
        click.echo("")
        click.echo("Interest list:")
        for interest in interest_store.list_all():
            status = "enabled" if interest.enabled else "disabled"
            click.echo(f"  - {interest.name} ({status})")
