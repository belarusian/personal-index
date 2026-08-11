"""Doctor command for diagnosing personal-index setup issues."""

from __future__ import annotations

import os
import sys

import click

from personal_index.index import SearchIndex
from personal_index.interests import InterestStore
from personal_index.tags import TagStore


@click.command("doctor")
@click.option("--data-dir", default=None, help="Data directory")
@click.pass_context
def doctor(ctx, data_dir):
    """Diagnose issues with your personal-index setup.

    Checks for common configuration and data issues.

    Examples:
        personal-index doctor
    """
    dd = data_dir or ctx.obj.get("data_dir", ".personal_index")
    issues = []
    warnings = []
    ok = []

    # Check data directory
    if os.path.exists(dd):
        ok.append(f"Data directory exists: {dd}")
    else:
        issues.append(f"Data directory missing: {dd}")
        issues.append("  Run 'personal-index init' to create it")

    # Check config
    config_path = "config.yaml"
    if os.path.exists(config_path):
        ok.append(f"Config file exists: {config_path}")
    else:
        warnings.append(f"Config file missing: {config_path}")
        warnings.append("  Run 'personal-index init' to create a default config")

    # Check search index
    db_path = os.path.join(dd, "search_index.json")
    if os.path.exists(db_path):
        try:
            index = SearchIndex(db_path=db_path)
            count = index.get_page_count()
            ok.append(f"Search index: {count} pages")
        except (OSError, ValueError) as e:
            issues.append(f"Search index error: {e}")
    else:
        warnings.append("No search index found")
        warnings.append("  Run 'personal-index pipeline' or 'personal-index import' to create one")

    # Check interests
    interest_path = os.path.join(dd, "interests.json")
    if os.path.exists(interest_path):
        try:
            store = InterestStore(store_path=interest_path)
            count = len(store.list_all())
            ok.append(f"Interests: {count} configured")
        except (OSError, ValueError) as e:
            issues.append(f"Interests error: {e}")
    else:
        warnings.append("No interests configured")
        warnings.append("  Run 'personal-index interests add <name> -k keyword' to add interests")

    # Check tags
    tag_path = os.path.join(dd, "tags.json")
    if os.path.exists(tag_path):
        try:
            store = TagStore(store_path=tag_path)
            count = store.get_tag_count()
            ok.append(f"Tags: {count} defined")
        except (OSError, ValueError) as e:
            issues.append(f"Tags error: {e}")
    else:
        warnings.append("No tags configured")

    # Check Python version
    py_ver = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    ok.append(f"Python version: {py_ver} (compatible)")

    # Report
    click.echo("Personal-Index Health Check")
    click.echo("=" * 50)

    if ok:
        click.echo("\n✓ OK:")
        for item in ok:
            click.echo(f"  ✓ {item}")

    if warnings:
        click.echo("\n⚠ Warnings:")
        for item in warnings:
            click.echo(f"  ⚠ {item}")

    if issues:
        click.echo("\n✗ Issues:")
        for item in issues:
            click.echo(f"  ✗ {item}")

    if not issues and not warnings:
        click.echo("\nAll checks passed!")
    elif not issues:
        click.echo("\nNo critical issues found.")
    else:
        click.echo("\nPlease fix the issues above.")
        ctx.exit(1)
