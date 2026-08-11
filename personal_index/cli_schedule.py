"""Schedule CLI command group for personal-index."""

from __future__ import annotations

import os
import sys

import click


@click.group("schedule")
@click.pass_context
def schedule(ctx):
    """Manage scheduled crawl jobs.

    Set up periodic crawling of websites to keep your index fresh.

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
    os.makedirs(dd, exist_ok=True)

    from personal_index.scheduler import ScheduleConfig, ScheduleEntry, ScheduleStore

    store_path = os.path.join(dd, "schedules.json")
    store = ScheduleStore(path=store_path)

    # Check if already exists
    existing = store.list_all()
    if any(e.name == name for e in existing):
        click.echo(f"Scheduled job '{name}' already exists.", err=True)
        sys.exit(1)

    config = ScheduleConfig(
        interval_hours=interval,
        seed_urls=[url],
        max_pages_per_run=max_pages,
        crawl_depth=depth,
    )
    entry = ScheduleEntry(name=name, config=config)
    store.add(entry)
    click.echo(f"Added scheduled job '{name}':")
    click.echo(f"  URL: {url}")
    click.echo(f"  Interval: every {interval} hours")
    click.echo(f"  Max depth: {depth}")
    click.echo(f"  Max pages: {max_pages}")


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
        click.echo("Add one: personal-index schedule add my-job --url https://example.com")
        return

    click.echo(f"Scheduled jobs ({len(entries)}):")
    click.echo("-" * 60)
    for entry in entries:
        last_run = entry.last_run or "never"
        next_run = entry.next_run or "unknown"
        click.echo(f"\n  {entry.name}")
        click.echo(f"    URLs: {', '.join(entry.config.seed_urls)}")
        click.echo(f"    Interval: every {entry.config.interval_hours} hours")
        click.echo(f"    Max pages: {entry.config.max_pages_per_run}")
        click.echo(f"    Runs: {entry.run_count}")
        click.echo(f"    Last run: {last_run}")
        click.echo(f"    Next run: {next_run}")


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
        click.echo(f"Scheduled job '{name}' not found.", err=True)
        sys.exit(1)


@schedule.command("run")
@click.argument("name")
@click.option("--data-dir", default=None, help="Data directory")
@click.pass_context
def schedule_run(ctx, name, data_dir):
    """Manually run a scheduled job now."""
    dd = data_dir or ctx.obj.get("data_dir", ".personal_index")
    from personal_index.scheduler import ScheduleStore

    store_path = os.path.join(dd, "schedules.json")
    store = ScheduleStore(path=store_path)

    entries = store.list_all()
    entry = next((e for e in entries if e.name == name), None)
    if not entry:
        click.echo(f"Scheduled job '{name}' not found.", err=True)
        sys.exit(1)

    click.echo(f"Running scheduled job '{name}'...")
    click.echo(f"  URLs: {', '.join(entry.config.seed_urls)}")

    from personal_index.pipeline_runner import PipelineConfig, PipelineRunner
    config = PipelineConfig(
        max_depth=entry.config.crawl_depth,
        max_pages=entry.config.max_pages_per_run,
    )
    runner = PipelineRunner(data_dir=dd, pipeline_config=config)
    try:
        stats = runner.run(entry.config.seed_urls)
        click.echo("\nJob complete:")
        click.echo(f"  Crawled: {stats.pages_crawled}")
        click.echo(f"  Indexed: {stats.pages_indexed}")
        click.echo(f"  Errors: {len(stats.errors)}")
    finally:
        runner.close()
