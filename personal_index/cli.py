"""CLI entry point for personal-index.

Provides commands for crawling, indexing, searching, and managing
a personal web content index.

Usage:
    personal-index init
    personal-index crawl https://example.com
    personal-index pipeline https://example.com
    personal-index search "python tutorial"
    personal-index export --format markdown
"""

from __future__ import annotations

import json
import os
import shutil
import sys

import click
import yaml

from personal_index.index import SearchIndex
from personal_index.tags import TagStore


def get_search_index(data_dir: str) -> SearchIndex:
    """Get or create a search index for the given data directory."""
    db_path = os.path.join(data_dir, "search_index.json")
    return SearchIndex(db_path=db_path)


def get_tag_store(data_dir: str) -> TagStore:
    """Get or create a tag store for the given data directory."""
    store_path = os.path.join(data_dir, "tags.json")
    return TagStore(store_path=store_path)


def get_interest_store(data_dir: str):
    """Get or create an interest store for the given data directory."""
    from personal_index.interests import InterestStore
    store_path = os.path.join(data_dir, "interests.json")
    return InterestStore(store_path=store_path)


def load_config(data_dir: str) -> dict:
    """Load configuration from config.yaml."""
    config_path = "config.yaml"
    if os.path.exists(config_path):
        with open(config_path, "r") as f:
            return yaml.safe_load(f) or {}
    return {}


@click.group(cls=click.Group, invoke_without_command=True)
@click.option("--data-dir", default=None, help="Data directory")
@click.option("--verbose", "-v", is_flag=True, help="Enable verbose output")
@click.version_option(version="0.1.0", prog_name="personal-index")
@click.pass_context
def main(ctx, data_dir, verbose):
    """Personal Index - Crawl, filter, score, tag, and search the web.

    A personal web search engine that scans, filters, and indexes
    the web based on your interests.

    Quick start:
        personal-index init
        personal-index interests add programming --keywords "python,javascript,web"
        personal-index pipeline https://example.com
        personal-index search "python"
    """
    ctx.ensure_object(dict)
    ctx.obj["data_dir"] = data_dir or ".personal_index"
    ctx.obj["verbose"] = verbose



@main.command()
@click.option("--data-dir", default=None, help="Data directory")
@click.pass_context
def stats(ctx, data_dir):
    """Show statistics about your personal-index.

    Displays counts of indexed pages, interests, tags, and storage usage.

    Examples:
        personal-index stats
    """
    dd = data_dir or ctx.obj.get("data_dir", ".personal_index")
    idx = get_search_index(dd)
    tag_store = get_tag_store(dd)
    interest_store = get_interest_store(dd)

    page_count = idx.get_page_count()
    tag_count = tag_store.get_tag_count()
    interests = interest_store.list_all()
    interest_count = len(interests)

    # Calculate storage size
    total_size = 0
    if os.path.exists(dd):
        for dirpath, dirnames, filenames in os.walk(dd):
            for fn in filenames:
                fp = os.path.join(dirpath, fn)
                try:
                    total_size += os.path.getsize(fp)
                except OSError:
                    pass

    click.echo("Personal Index Statistics")
    click.echo("=" * 40)
    click.echo("  Indexed pages:  {}".format(page_count))
    click.echo("  Interests:      {}".format(interest_count))
    click.echo("  Tags:           {}".format(tag_count))
    click.echo("  Tagged pages:   {}".format(tag_store.get_tagged_page_count()))

    if interests:
        click.echo("")
        click.echo("Interests:")
        for interest in interests:
            click.echo("  - {}: {}".format(interest.name, ", ".join(interest.keywords[:5])))

    if total_size > 0:
        if total_size < 1024 * 1024:
            size_str = "{:.1f} KB".format(total_size / 1024)
        else:
            size_str = "{:.1f} MB".format(total_size / (1024 * 1024))
        click.echo("")
        click.echo("Storage: {}".format(size_str))


# Doctor command
@main.command()
@click.option("--data-dir", default=None, help="Data directory")
@click.pass_context
def doctor(ctx, data_dir):
    """Diagnose issues with your personal-index setup.

    Checks configuration, data directory, and component health.

    Examples:
        personal-index doctor
    """
    dd = data_dir or ctx.obj.get("data_dir", ".personal_index")
    issues = []
    warnings = []

    # Check data directory
    if not os.path.exists(dd):
        issues.append(f"Data directory '{dd}' does not exist. Run 'personal-index init'.")
    else:
        # Check subdirectories
        for subdir in ["cache", "archive", "backups"]:
            if not os.path.exists(os.path.join(dd, subdir)):
                warnings.append(f"Missing subdirectory: {subdir}")

    # Check config
    if not os.path.exists("config.yaml"):
        warnings.append("No config.yaml found. Run 'personal-index init' for defaults.")

    # Check index
    idx = get_search_index(dd)
    if idx.get_page_count() == 0:
        warnings.append("Index is empty. Run 'personal-index pipeline' to add content.")

    # Check interests
    interest_store = get_interest_store(dd)
    if not interest_store.list_all():
        warnings.append("No interests configured. Add interests for better scoring.")

    # Check tag store
    tag_store = get_tag_store(dd)

    click.echo("Personal Index Health Check")
    click.echo("=" * 40)

    if issues:
        click.echo(f"\n✗ Issues ({len(issues)}):")
        for issue in issues:
            click.echo(f"  - {issue}")
    else:
        click.echo("\n✓ No critical issues found")

    if warnings:
        click.echo(f"\n⚠ Warnings ({len(warnings)}):")
        for warning in warnings:
            click.echo(f"  - {warning}")

    click.echo(f"\nIndex: {idx.get_page_count()} pages")
    click.echo(f"Tags: {tag_store.get_tag_count()}")
    click.echo(f"Interests: {len(interest_store.list_all())}")

    if issues:
        sys.exit(1)


if __name__ == "__main__":
    main()
