"""CLI interface for personal-index."""

from __future__ import annotations

import json
import os
from pathlib import Path

import click

from personal_index.content_filter import ContentFilter, FilterConfig
from personal_index.crawler import Crawler, CrawlerConfig
from personal_index.interest_store import InterestStore
from personal_index.models import Interest, InterestType
from personal_index.scheduler import ScheduleStore, Scheduler
from personal_index.search_index import SearchIndex


DEFAULT_DATA_DIR = os.path.expanduser("~/.personal-index")


def get_data_dir() -> str:
    """Get the data directory path."""
    return os.environ.get("PERSONAL_INDEX_DATA_DIR", DEFAULT_DATA_DIR)


def get_interest_store() -> InterestStore:
    """Get the default interest store."""
    return InterestStore(storage_path=os.path.join(get_data_dir(), "interests.json"))


def get_search_index() -> SearchIndex:
    """Get the default search index."""
    return SearchIndex(index_path=os.path.join(get_data_dir(), "index.json"))


def get_schedule_store() -> ScheduleStore:
    """Get the default schedule store."""
    return ScheduleStore(path=os.path.join(get_data_dir(), "schedules.json"))


@click.group()
@click.version_option(version="0.1.0", prog_name="personal-index")
def cli():
    """personal-index: A personal web search engine.

    Define your interests and the system scans, filters, and indexes the web for you.
    """
    pass


# ── Interest commands ──────────────────────────────────────────────

@cli.group()
def interests():
    """Manage your tracked interests."""
    pass


@interests.command()
@click.option("--name", "-n", required=True, help="Name for this interest")
@click.option(
    "--type",
    "-t",
    "interest_type",
    type=click.Choice(["keyword", "topic", "url_pattern"], case_sensitive=False),
    default="keyword",
    help="Type of interest",
)
@click.option("--value", "-v", required=True, help="Value (keyword, topic terms, or regex)")
@click.option(
    "--priority", "-p", type=int, default=5, help="Priority 1-10 (default: 5)"
)
def add(name, interest_type, value, priority):
    """Add a new interest to track."""
    store = get_interest_store()
    if store.get(name):
        click.echo(f"Error: Interest '{name}' already exists.", err=True)
        raise SystemExit(1)

    interest = Interest(
        name=name,
        interest_type=InterestType(interest_type),
        value=value,
        priority=max(1, min(10, priority)),
    )
    store.add(interest)
    click.echo(f"Added interest: {name} ({interest_type}) = {value}")


@interests.command()
@click.option("--name", "-n", required=True, help="Name of interest to remove")
def remove(name):
    """Remove an interest."""
    store = get_interest_store()
    if store.remove(name):
        click.echo(f"Removed interest: {name}")
    else:
        click.echo(f"Error: Interest '{name}' not found.", err=True)
        raise SystemExit(1)


@interests.command("list")
@click.option("--enabled-only", "-e", is_flag=True, help="Show only enabled interests")
def list_interests(enabled_only):
    """List all configured interests."""
    store = get_interest_store()
    interests_list = store.list_all(enabled_only=enabled_only)

    if not interests_list:
        click.echo("No interests configured.")
        return

    click.echo(f"{'Name':<20} {'Type':<12} {'Value':<30} {'Pri':<5} {'Enabled':<8}")
    click.echo("-" * 75)
    for interest in interests_list:
        click.echo(
            f"{interest.name:<20} "
            f"{interest.interest_type.value:<12} "
            f"{interest.value:<30} "
            f"{interest.priority:<5} "
            f"{'✓' if interest.enabled else '✗':<8}"
        )


@interests.command()
@click.option("--name", "-n", required=True, help="Name of interest to toggle")
def toggle(name):
    """Toggle an interest on/off."""
    store = get_interest_store()
    result = store.toggle(name)
    if result:
        status = "enabled" if result.enabled else "disabled"
        click.echo(f"Interest '{name}' is now {status}")
    else:
        click.echo(f"Error: Interest '{name}' not found.", err=True)
        raise SystemExit(1)


@interests.command()
@click.option("--name", "-n", required=True, help="Name of interest")
@click.option("--priority", "-p", type=int, required=True, help="New priority 1-10")
def priority(name, priority):
    """Update the priority of an interest."""
    store = get_interest_store()
    result = store.update_priority(name, priority)
    if result:
        click.echo(f"Updated priority for '{name}' to {result.priority}")
    else:
        click.echo(f"Error: Interest '{name}' not found.", err=True)
        raise SystemExit(1)


# ── Crawl commands ─────────────────────────────────────────────────

@cli.command()
@click.argument("seed-urls", nargs=-1, required=True)
@click.option(
    "--depth", "-d", type=int, default=3,
    help="Maximum crawl depth (default: 3)",
)
@click.option(
    "--max-pages", "-m", type=int, default=100,
    help="Maximum pages to crawl (default: 100)",
)
@click.option(
    "--delay", type=float, default=1.0,
    help="Delay between requests to same domain in seconds (default: 1.0)",
)
@click.option(
    "--timeout", type=int, default=10,
    help="Request timeout in seconds (default: 10)",
)
@click.option(
    "--domain", multiple=True,
    help="Restrict crawling to these domains (can be repeated)",
)
@click.option(
    "--dry-run", is_flag=True,
    help="Show what would be crawled without actually crawling",
)
def crawl(seed_urls, depth, max_pages, delay, timeout, domain, dry_run):
    """Crawl the web starting from seed URLs."""
    store = get_interest_store()
    index = get_search_index()

    if not store.list_all(enabled_only=True):
        click.echo("Warning: No enabled interests configured. All pages will be indexed.")

    config = CrawlerConfig(
        max_depth=depth,
        max_pages=max_pages,
        delay=delay,
        timeout=timeout,
        allowed_domains=list(domain),
    )

    crawler = Crawler(config=config, interest_store=store)

    if dry_run:
        click.echo(f"Would crawl from {len(seed_urls)} seed URL(s):")
        for url in seed_urls:
            click.echo(f"  {url}")
        click.echo(f"Max depth: {depth}, Max pages: {max_pages}, Delay: {delay}s")
        return

    click.echo(f"Crawling from {len(seed_urls)} seed URL(s)...")
    click.echo(f"Max depth: {depth}, Max pages: {max_pages}, Delay: {delay}s")

    pages = crawler.crawl(list(seed_urls))

    # Filter and index
    filter_config = FilterConfig(
        require_interest_match=len(store.list_all(enabled_only=True)) > 0,
    )
    content_filter = ContentFilter(config=filter_config, interest_store=store)
    filtered = content_filter.filter_pages(pages)

    for page in filtered:
        index.add(page)

    click.echo(f"\nCrawled: {crawler.pages_crawled} pages")
    click.echo(f"Matched interests: {len(filtered)} pages")
    click.echo(f"Total indexed: {index.count()} pages")


# ── Search commands ────────────────────────────────────────────────

@cli.command()
@click.argument("query")
@click.option(
    "--limit", "-l", type=int, default=10,
    help="Maximum results to show (default: 10)",
)
@click.option(
    "--show-content", "-c", is_flag=True,
    help="Show content snippet with results",
)
def search(query, limit, show_content):
    """Search the local index."""
    index = get_search_index()

    if index.count() == 0:
        click.echo("Index is empty. Run 'personal-index crawl' first.")
        return

    results = index.search(query, limit=limit)

    if not results:
        click.echo(f"No results found for: {query}")
        return

    click.echo(f"\nSearch results for: {query} ({len(results)} found)\n")
    click.echo("-" * 80)

    for i, (url, score) in enumerate(results, 1):
        page = index.get(url)
        if page:
            click.echo(f"\n[{i}] {page.title or 'Untitled'}")
            click.echo(f"    URL: {url}")
            click.echo(f"    Score: {score:.2f}")
            if page.matched_interests:
                click.echo(f"    Interests: {', '.join(page.matched_interests)}")
            if show_content and page.content:
                snippet = page.content[:200].replace("\n", " ")
                click.echo(f"    Content: {snippet}...")
            click.echo("-" * 80)


# ── Schedule commands ──────────────────────────────────────────────

@cli.group()
def schedule():
    """Manage scheduled crawling jobs."""
    pass


@schedule.command()
@click.option("--name", "-n", required=True, help="Name for this schedule")
@click.option("--url", "-u", "urls", multiple=True, required=True,
              help="Seed URL to crawl (can be repeated)")
@click.option(
    "--interval", "-i", type=int, default=24,
    help="Interval in hours between runs (default: 24)",
)
@click.option(
    "--max-pages", "-m", type=int, default=50,
    help="Max pages per run (default: 50)",
)
@click.option(
    "--depth", "-d", type=int, default=2,
    help="Crawl depth (default: 2)",
)
def add_schedule(name, urls, interval, max_pages, depth):
    """Add a new scheduled crawl."""
    store = get_interest_store()
    index = get_search_index()
    scheduler = Scheduler(
        interest_store=store,
        search_index=index,
        schedule_store=get_schedule_store(),
    )
    entry = scheduler.add_schedule(
        name=name,
        seed_urls=list(urls),
        interval_hours=interval,
        max_pages=max_pages,
        depth=depth,
    )
    click.echo(f"Added schedule: {name}")
    click.echo(f"  URLs: {', '.join(entry.config.seed_urls)}")
    click.echo(f"  Interval: every {interval} hours")
    click.echo(f"  Max pages: {max_pages}, Depth: {depth}")


@schedule.command("list")
def list_schedules():
    """List all scheduled crawls."""
    store = get_schedule_store()
    entries = store.list_all()

    if not entries:
        click.echo("No schedules configured.")
        return

    click.echo(f"{'Name':<20} {'Enabled':<10} {'Interval':<10} {'Runs':<6} {'Last Run':<20}")
    click.echo("-" * 66)
    for entry in entries:
        last = entry.last_run.strftime("%Y-%m-%d %H:%M") if entry.last_run else "never"
        click.echo(
            f"{entry.name:<20} "
            f"{'✓' if entry.config.enabled else '✗':<10} "
            f"{entry.config.interval_hours}h{'':<5} "
            f"{entry.run_count:<6} "
            f"{last:<20}"
        )


@schedule.command()
@click.option("--name", "-n", required=True, help="Name of schedule to remove")
def remove_schedule(name):
    """Remove a scheduled crawl."""
    store = get_schedule_store()
    if store.remove(name):
        click.echo(f"Removed schedule: {name}")
    else:
        click.echo(f"Error: Schedule '{name}' not found.", err=True)
        raise SystemExit(1)


@schedule.command()
@click.option("--name", "-n", required=True, help="Name of schedule to toggle")
def toggle_schedule(name):
    """Toggle a schedule on/off."""
    store = get_interest_store()
    index = get_search_index()
    scheduler = Scheduler(
        interest_store=store,
        search_index=index,
        schedule_store=get_schedule_store(),
    )
    entry = scheduler.toggle_schedule(name)
    if entry:
        status = "enabled" if entry.config.enabled else "disabled"
        click.echo(f"Schedule '{name}' is now {status}")
    else:
        click.echo(f"Error: Schedule '{name}' not found.", err=True)
        raise SystemExit(1)


@schedule.command()
@click.option("--name", "-n", required=True, help="Name of schedule to run")
def run(name):
    """Manually run a scheduled crawl."""
    store = get_interest_store()
    index = get_search_index()
    scheduler = Scheduler(
        interest_store=store,
        search_index=index,
        schedule_store=get_schedule_store(),
    )
    count = scheduler.run_schedule(name)
    click.echo(f"Schedule '{name}' completed: {count} pages indexed")


# ── Index commands ─────────────────────────────────────────────────

@cli.command()
def status():
    """Show index and interest status."""
    store = get_interest_store()
    index = get_search_index()
    schedule_store = get_schedule_store()

    click.echo("=== personal-index Status ===\n")
    click.echo(f"Data directory: {get_data_dir()}")
    click.echo(f"Interests: {len(store.list_all())} total, "
               f"{len(store.list_all(enabled_only=True))} enabled")
    click.echo(f"Indexed pages: {index.count()}")
    click.echo(f"Schedules: {len(schedule_store.list_all())}")


@cli.command()
@click.confirmation_option(prompt="Are you sure you want to clear the index?")
def clear():
    """Clear the search index."""
    index = get_search_index()
    index.clear()
    click.echo("Index cleared.")


@cli.command()
@click.option("--url", "-u", required=True, help="URL to remove from index")
def remove_url(url):
    """Remove a specific URL from the index."""
    index = get_search_index()
    if index.remove(url):
        click.echo(f"Removed: {url}")
    else:
        click.echo(f"URL not found in index: {url}")
        raise SystemExit(1)


# ── Stats commands ─────────────────────────────────────────────────

@cli.command()
def stats():
    """Show index and crawl statistics."""
    from personal_index.stats import StatsCollector

    store = get_interest_store()
    index = get_search_index()
    collector = StatsCollector(interest_store=store, search_index=index)
    click.echo(collector.format_index_stats())
