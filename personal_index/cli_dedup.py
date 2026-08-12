"""CLI command for content deduplication."""

from __future__ import annotations

import click

from personal_index.content_dedup import ContentDeduplicator


@click.command("dedup")
@click.option("--data-dir", default=None, help="Data directory")
@click.option("--method", "-m", default="all",
              type=click.Choice(["hash", "url", "similarity", "all"]),
              help="Deduplication method")
@click.option("--similarity-threshold", type=float, default=0.9,
              help="Similarity threshold (0.0-1.0)")
@click.option("--dry-run", is_flag=True, help="Show duplicates without removing")
@click.pass_context
def dedup(ctx, data_dir, method, similarity_threshold, dry_run):
    """Find and remove duplicate content.

    Analyzes indexed content for duplicates using hash matching,
    URL normalization, or similarity scoring.

    Examples:
        personal-index dedup
        personal-index dedup --method hash
        personal-index dedup --method similarity --similarity-threshold 0.8
        personal-index dedup --dry-run
    """
    dd = data_dir or ctx.obj.get("data_dir", ".personal_index")

    # Load indexed content
    from personal_index.index import SearchIndex
    idx_path = f"{dd}/search_index.json"
    idx = SearchIndex(db_path=idx_path)

    pages = idx.list_pages()
    if not pages:
        click.echo("No indexed content found.")
        return

    # Build items for dedup
    items = []
    for page in pages:
        items.append({
            "url": page.url,
            "title": page.title,
            "content": page.content or "",
        })

    dedup = ContentDeduplicator(similarity_threshold=similarity_threshold)

    if method == "hash":
        result = dedup.dedup_by_hash(items)
    elif method == "url":
        result = dedup.dedup_by_url(items)
    elif method == "similarity":
        result = dedup.dedup_by_similarity(items)
    else:
        result = dedup.dedup_all(items)

    click.echo(result.summary())
    click.echo()

    if result.duplicate_groups:
        click.echo("Duplicate Groups:")
        click.echo("-" * 40)
        for group in result.duplicate_groups:
            click.echo(f"\n  Representative: {group.representative}")
            click.echo(f"  Method: {group.dedup_method}")
            click.echo(f"  Score: {group.similarity_score:.2f}")
            for dup in group.duplicates:
                click.echo(f"    Duplicate: {dup}")

        if not dry_run:
            click.echo(f"\nRemoving {result.removed_count} duplicates...")
            # Remove duplicates from index
            urls_to_remove = set()
            for group in result.duplicate_groups:
                urls_to_remove.update(group.duplicates)

            removed = 0
            for url in urls_to_remove:
                if idx.remove_page(url):
                    removed += 1
            idx._save()
            click.echo(f"Removed {removed} duplicate pages.")
        else:
            click.echo("\n(Dry run - no changes made)")
    else:
        click.echo("No duplicates found!")
