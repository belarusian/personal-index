"""Doctor CLI command for personal-index diagnostics."""

from __future__ import annotations

import os
import sys

import click


@click.command("doctor")
@click.option("--data-dir", default=None, help="Data directory")
@click.pass_context
def doctor(ctx, data_dir):
    """Diagnose issues with your personal-index setup.

    Checks configuration, data directory, component health, and
    provides actionable recommendations.

    Examples:
        personal-index doctor
        personal-index doctor --data-dir ~/custom-index
    """
    dd = data_dir or ctx.obj.get("data_dir", ".personal_index")
    issues = []
    warnings = []
    infos = []

    # Check data directory
    if not os.path.exists(dd):
        issues.append(f"Data directory '{dd}' does not exist. Run 'personal-index init'.")
    else:
        # Check subdirectories
        for subdir in ["cache", "archive", "backups"]:
            full_path = os.path.join(dd, subdir)
            if not os.path.exists(full_path):
                warnings.append(f"Missing subdirectory: {subdir}/ (will be created on next run)")

    # Check config
    config_found = False
    for config_name in ["config.yaml", "config.yml", "my-config.yaml"]:
        if os.path.exists(config_name):
            config_found = True
            infos.append(f"Config file found: {config_name}")
            break
    if not config_found:
        warnings.append("No config.yaml found. Run 'personal-index init' to create one.")

    # Check index
    index_path = os.path.join(dd, "search_index.json")
    if os.path.exists(index_path):
        try:
            from personal_index.index import SearchIndex
            idx = SearchIndex(db_path=index_path)
            page_count = idx.get_page_count()
            infos.append(f"Search index contains {page_count} pages")
            if page_count == 0:
                warnings.append("Index is empty. Run 'personal-index pipeline' to index content.")
        except (RuntimeError, OSError, ValueError) as e:
            issues.append(f"Search index is corrupted: {e}")
    else:
        infos.append("No search index yet (will be created on first pipeline run)")

    # Check interests
    interests_path = os.path.join(dd, "interests.json")
    if os.path.exists(interests_path):
        try:
            from personal_index.interests import InterestStore
            interest_store = InterestStore(store_path=interests_path)
            interests = interest_store.list_all()
            infos.append(f"Found {len(interests)} interest(s)")
            if not interests:
                warnings.append("No interests configured. Add interests for better scoring.")
        except (RuntimeError, OSError, ValueError) as e:
            issues.append(f"Interest store is corrupted: {e}")
    else:
        warnings.append("No interests configured. Add interests for better scoring.")

    # Check tag store
    tags_path = os.path.join(dd, "tags.json")
    if os.path.exists(tags_path):
        try:
            from personal_index.tags import TagStore
            tag_store = TagStore(store_path=tags_path)
            tag_count = tag_store.get_tag_count()
            infos.append(f"Found {tag_count} tag(s)")
        except (RuntimeError, OSError, ValueError) as e:
            issues.append(f"Tag store is corrupted: {e}")
    else:
        infos.append("No tags yet (will be created during pipeline run)")

    # Check Python dependencies
    missing_deps = []
    for dep in ["click", "yaml", "requests", "bs4"]:
        try:
            if dep == "yaml":
                __import__("yaml")
            elif dep == "bs4":
                __import__("bs4")
            else:
                __import__(dep)
        except ImportError:
            missing_deps.append(dep)

    if missing_deps:
        issues.append(f"Missing Python dependencies: {', '.join(missing_deps)}")
    else:
        infos.append("All required dependencies are installed")

    # Output report
    click.echo("Personal Index Health Check")
    click.echo("=" * 50)

    if issues:
        click.echo(f"\n✗ Issues ({len(issues)}):")
        for issue in issues:
            click.echo(f"  • {issue}")
    else:
        click.echo("\n✓ No critical issues found")

    if warnings:
        click.echo(f"\n⚠ Warnings ({len(warnings)}):")
        for warning in warnings:
            click.echo(f"  • {warning}")

    if infos:
        click.echo(f"\nℹ Info ({len(infos)}):")
        for info in infos:
            click.echo(f"  • {info}")

    click.echo(f"\n{'=' * 50}")

    if issues:
        click.echo("\nRecommendation: Fix the issues above before running the pipeline.")
        sys.exit(1)
    elif warnings:
        click.echo("\nYour setup is functional but could be improved.")
