"""CLI command for content deduplication."""

from __future__ import annotations

import click

from personal_index.content_dedup import ContentDeduplicator
from personal_index.index import SearchIndex


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

    pages, idx = _load_indexed_content(dd)
    if not pages:
        click.echo("No indexed content found.")
        return

    items = _build_dedup_items(pages)
    result = _dispatch_dedup(items, method, similarity_threshold)

    _display_result(result)

    if result.duplicate_groups:
        _display_duplicate_groups(result)
        if not dry_run:
            _remove_duplicates(idx, result)
        else:
            click.echo("\n(Dry run - no changes made)")
    else:
        click.echo("No duplicates found!")


def _load_indexed_content(data_dir: str):
    """Load indexed pages from the search index.

    Returns:
        Tuple of (pages list, SearchIndex instance).
    """
    idx_path = f"{data_dir}/search_index.json"
    idx = SearchIndex(db_path=idx_path)
    pages = idx.list_pages()
    return pages, idx


def _build_dedup_items(pages):
    """Build dedup input items from indexed pages.

    Returns:
        List of dicts with url, title, and content keys.
    """
    items = []
    for page in pages:
        items.append({
            "url": page.url,
            "title": page.title,
            "content": page.content or "",
        })
    return items


def _dispatch_dedup(items, method: str, similarity_threshold: float):
    """Run the appropriate dedup method and return the result.

    Args:
        items: List of page dicts to deduplicate.
        method: One of 'hash', 'url', 'similarity', 'all'.
        similarity_threshold: Threshold for similarity-based dedup.

    Returns:
        DedupResult from ContentDeduplicator.
    """
    dedup = ContentDeduplicator(similarity_threshold=similarity_threshold)

    if method == "hash":
        return dedup.dedup_by_hash(items)
    elif method == "url":
        return dedup.dedup_by_url(items)
    elif method == "similarity":
        return dedup.dedup_by_similarity(items)
    else:
        return dedup.dedup_all(items)


def _display_result(result):
    """Display the dedup summary to the user."""
    click.echo(result.summary())
    click.echo()


def _display_duplicate_groups(result):
    """Display detailed duplicate group information."""
    click.echo("Duplicate Groups:")
    click.echo("-" * 40)
    for group in result.duplicate_groups:
        click.echo(f"\n  Representative: {group.representative}")
        click.echo(f"  Method: {group.dedup_method}")
        click.echo(f"  Score: {group.similarity_score:.2f}")
        for dup in group.duplicates:
            click.echo(f"    Duplicate: {dup}")


def _remove_duplicates(idx, result):
    """Remove duplicate pages from the index and persist."""
    click.echo(f"\nRemoving {result.removed_count} duplicates...")
    urls_to_remove = set()
    for group in result.duplicate_groups:
        urls_to_remove.update(group.duplicates)

    removed = 0
    for url in urls_to_remove:
        if idx.remove_page(url):
            removed += 1
    idx._save()
    click.echo(f"Removed {removed} duplicate pages.")
