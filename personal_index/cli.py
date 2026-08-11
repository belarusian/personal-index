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

from personal_index.cli_clear import clear as clear_cmd
from personal_index.cli_doctor import doctor as doctor_cmd
from personal_index.cli_list import list_pages as list_cmd
from personal_index.cli_remove import remove_page as remove_cmd
from personal_index.cli_stats import stats as stats_cmd
from personal_index.cli_status import status as status_cmd
from personal_index.cli_top import top_pages as top_cmd
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


@main.group()
@click.pass_context
def config(ctx):
    """Manage configuration settings.

    View and modify crawler, filter, and scheduler settings.

    Examples:
        personal-index config show
        personal-index config set-crawler --max-depth 5
    """


@config.command("show")
@click.option("--data-dir", default=None, help="Data directory")
@click.pass_context
def config_show(ctx, data_dir):
    """Show current configuration."""
    config_path = "config.yaml"
    if os.path.exists(config_path):
        with open(config_path, "r") as f:
            data = yaml.safe_load(f) or {}
        click.echo("Current configuration:")
        click.echo(yaml.dump(data, default_flow_style=False))
    else:
        click.echo("No config file found. Run 'personal-index init' first.")


@config.command("set-crawler")
@click.option("--max-depth", type=int, help="Set max crawl depth")
@click.option("--data-dir", default=None, help="Data directory")
@click.pass_context
def config_set_crawler(ctx, max_depth, data_dir):
    """Set crawler configuration."""
    config_path = "config.yaml"
    if not os.path.exists(config_path):
        click.echo("No config file found. Run 'personal-index init' first.", err=True)
        sys.exit(1)
    with open(config_path, "r") as f:
        data = yaml.safe_load(f) or {}
    if max_depth is not None:
        data.setdefault("crawler", {})["max_depth"] = max_depth
    with open(config_path, "w") as f:
        yaml.dump(data, f, default_flow_style=False)
    click.echo("Crawler configuration updated.")


@config.command("set-schedule")
@click.option("--interval", type=int, help="Set schedule interval in hours")
@click.option("--data-dir", default=None, help="Data directory")
@click.pass_context
def config_set_schedule(ctx, interval, data_dir):
    """Set scheduler configuration."""
    config_path = "config.yaml"
    if not os.path.exists(config_path):
        click.echo("No config file found. Run 'personal-index init' first.", err=True)
        sys.exit(1)
    with open(config_path, "r") as f:
        data = yaml.safe_load(f) or {}
    if interval is not None:
        data.setdefault("scheduler", {})["interval_hours"] = interval
    with open(config_path, "w") as f:
        yaml.dump(data, f, default_flow_style=False)
    click.echo("Scheduler configuration updated.")


# Schedule management commands
@main.group()
@click.pass_context
def schedule(ctx):
    """Manage scheduled crawl jobs.

    Schedule regular crawls of your favorite sites.

    Examples:
        personal-index schedule add daily --url https://example.com --interval 24
        personal-index schedule list
        personal-index schedule remove daily
    """


@schedule.command("add")
@click.option("-n", "--name", required=True, help="Job name")
@click.option("--url", "-u", required=True, help="URL to crawl")
@click.option("--interval", "-i", default=24, type=int, help="Interval in hours")
@click.option("--depth", "-d", default=2, type=int, help="Crawl depth")
@click.option("--max-pages", "-m", default=50, type=int, help="Max pages per run")
@click.option("--data-dir", default=None, help="Data directory")
@click.pass_context
def schedule_add(ctx, name, url, interval, depth, max_pages, data_dir):
    """Add a new scheduled crawl job."""
    dd = data_dir or ctx.obj.get("data_dir", ".personal_index")
    from personal_index.scheduler import ScheduleConfig, ScheduleEntry, ScheduleStore

    store_path = os.path.join(dd, "schedules.json")
    store = ScheduleStore(path=store_path)

    config = ScheduleConfig(
        interval_hours=interval,
        seed_urls=[url],
        max_pages_per_run=max_pages,
        crawl_depth=depth,
    )
    entry = ScheduleEntry(name=name, config=config)
    store.add(entry)
    click.echo(f"Added scheduled job '{name}'")


@schedule.command("list")
@click.option("--data-dir", default=None, help="Data directory")
@click.pass_context
def schedule_list(ctx, data_dir):
    """List all scheduled crawl jobs."""
    dd = data_dir or ctx.obj.get("data_dir", ".personal_index")
    from personal_index.scheduler import ScheduleStore

    store_path = os.path.join(dd, "schedules.json")
    store = ScheduleStore(path=store_path)
    entries = store.list_all()

    if not entries:
        click.echo("No scheduled jobs configured.")
        return

    click.echo(f"Scheduled jobs ({len(entries)}):")
    for entry in entries:
        click.echo(f"  {entry.name}: every {entry.config.interval_hours}h, "
                    f"urls={', '.join(entry.config.seed_urls)}, "
                    f"runs={entry.run_count}")


@schedule.command("remove")
@click.argument("name")
@click.option("--data-dir", default=None, help="Data directory")
@click.pass_context
def schedule_remove(ctx, name, data_dir):
    """Remove a scheduled crawl job."""
    dd = data_dir or ctx.obj.get("data_dir", ".personal_index")
    from personal_index.scheduler import ScheduleStore

    store_path = os.path.join(dd, "schedules.json")
    store = ScheduleStore(path=store_path)

    if store.remove(name):
        click.echo(f"Removed scheduled job '{name}'")
    else:
        click.echo(f"Scheduled job '{name}' not found", err=True)
        sys.exit(1)


# Import pipeline command
from personal_index.cli_pipeline import pipeline
from personal_index.cli_pipeline_unified import run_pipeline
from personal_index.cli_verify import verify
from personal_index.cli_watch import watch
from personal_index.cli_interests import interests as interests_cmd
from personal_index.cli_tags import tags as tags_cmd
from personal_index.cli_import import import_cmd
from personal_index.cli_export import export_cmd
from personal_index.cli_schedule import schedule as schedule_cmd

main.add_command(pipeline)
main.add_command(run_pipeline)
main.add_command(verify)
main.add_command(watch)
main.add_command(interests_cmd)
main.add_command(tags_cmd)
main.add_command(import_cmd)
main.add_command(export_cmd)
main.add_command(schedule_cmd)

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
        warnings.append("No config.yaml found. Run 'personal-index init' to create one.")

    # Check index
    idx = get_search_index(dd)
    if idx.get_page_count() == 0:
        warnings.append("No pages indexed. Run 'personal-index pipeline' to index content.")

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


main.add_command(stats_cmd)
main.add_command(list_cmd)
main.add_command(remove_cmd)
main.add_command(clear_cmd)
main.add_command(top_cmd)
main.add_command(doctor_cmd)
main.add_command(status_cmd)


if __name__ == "__main__":
    main()
