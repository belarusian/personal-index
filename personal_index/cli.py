"""CLI interface for personal-index."""

from __future__ import annotations

import click
import os

from personal_index.index import SearchIndex
from personal_index.interests import InterestStore
from personal_index.models import Interest
from personal_index.scheduler import Scheduler, ScheduleStore


def get_interest_store() -> InterestStore:
    """Get an InterestStore with default path."""
    data_dir = ".personal_index"
    os.makedirs(data_dir, exist_ok=True)
    return InterestStore(store_path=os.path.join(data_dir, "interests.json"))


@click.group()
@click.version_option(version="0.1.0")
def main():
    """personal-index - Track and index content matching your interests."""


@main.group()
def interests():
    """Manage tracked interests."""


@interests.command("add")
@click.option("-n", "--name", required=True, help="Interest name")
@click.option("-k", "--keyword", multiple=True, help="Keywords to track")
@click.option("-u", "--url-pattern", multiple=True, help="URL patterns to match")
@click.option("-p", "--priority", default=5, type=int, help="Priority (1-10)")
def add_interest(name, keyword, url_pattern, priority):
    """Add a new interest to track."""
    store = get_interest_store()
    interest = Interest(
        name=name,
        keywords=list(keyword),
        url_patterns=list(url_pattern),
        priority=priority,
    )
    store.add(interest)
    click.echo(f"Added interest: {name}")


@interests.command("list")
def list_interests():
    """List all tracked interests."""
    store = get_interest_store()
    all_interests = store.list_all()
    if not all_interests:
        click.echo("No interests configured.")
        return
    for interest in all_interests:
        status = "enabled" if interest.enabled else "disabled"
        click.echo(f"  {interest.name} [{status}] priority={interest.priority}")
        if interest.keywords:
            click.echo(f"    keywords: {', '.join(interest.keywords)}")


@interests.command("remove")
@click.argument("name")
def remove_interest(name):
    """Remove an interest by name."""
    store = get_interest_store()
    if store.remove(name):
        click.echo(f"Removed interest: {name}")
    else:
        click.echo(f"Interest not found: {name}", err=True)
        raise SystemExit(1)


@interests.command("toggle")
@click.argument("name")
def toggle_interest(name):
    """Toggle an interest on/off."""
    store = get_interest_store()
    interest = store.toggle(name)
    if interest:
        status = "enabled" if interest.enabled else "disabled"
        click.echo(f"Interest '{name}' is now {status}")
    else:
        click.echo(f"Interest not found: {name}", err=True)
        raise SystemExit(1)


@main.command("search")
@click.argument("query")
@click.option("-l", "--limit", default=10, type=int, help="Max results")
def search(query, limit):
    """Search indexed pages."""
    index = SearchIndex()
    results = index.search(query, limit=limit)
    if not results:
        click.echo("No results found.")
        return
    for i, result in enumerate(results, 1):
        click.echo(f"\n{i}. {result.title}")
        click.echo(f"   {result.url}")
        click.echo(f"   Score: {result.relevance_score:.2f}")
        if result.snippet:
            click.echo(f"   {result.snippet[:200]}")


@main.command("crawl")
@click.argument("url")
@click.option("-d", "--depth", default=3, type=int, help="Max crawl depth")
def crawl(url, depth):
    """Crawl a URL and index matching content."""
    from personal_index.crawler import Crawler, CrawlerConfig
    interest_store = get_interest_store()
    config = CrawlerConfig(max_depth=depth)
    crawler = Crawler(config=config, interest_store=interest_store)
    pages = crawler.crawl([url], max_depth=depth)
    click.echo(f"Crawled {len(pages)} pages")
    crawler.close()


@main.group()
def index():
    """Manage the search index."""


@index.command("count")
def index_count():
    """Show number of indexed pages."""
    idx = SearchIndex()
    count = idx.get_page_count()
    click.echo(f"Indexed pages: {count}")


@index.command("list")
def index_list():
    """List indexed pages."""
    idx = SearchIndex()
    pages = idx.list_pages()
    if not pages:
        click.echo("No pages indexed.")
        return
    for page in pages:
        click.echo(f"  {page.url} - {page.title}")


@index.command("clear")
def index_clear():
    """Clear the search index."""
    click.confirm("Are you sure you want to clear the index?", abort=True)
    idx = SearchIndex()
    idx.clear()
    click.echo("Index cleared.")


@main.group()
def schedule():
    """Manage scheduled crawling jobs."""


@schedule.command("add")
@click.option("-n", "--name", required=True, help="Job name")
@click.option("-u", "--url", required=True, help="URL to crawl")
@click.option("-i", "--interval", default=24, type=int, help="Interval in hours")
def add_schedule(name, url, interval):
    """Add a scheduled crawl job."""
    interest_store = get_interest_store()
    search_index = SearchIndex()
    schedule_store = ScheduleStore(path=".personal_index/schedules.json")
    scheduler = Scheduler(
        interest_store=interest_store,
        search_index=search_index,
        schedule_store=schedule_store,
    )
    scheduler.add_job(name=name, seed_urls=[url], interval_hours=interval)
    click.echo(f"Added scheduled job: {name}")


@schedule.command("list")
def list_schedule():
    """List scheduled jobs."""
    interest_store = get_interest_store()
    search_index = SearchIndex()
    schedule_store = ScheduleStore(path=".personal_index/schedules.json")
    scheduler = Scheduler(
        interest_store=interest_store,
        search_index=search_index,
        schedule_store=schedule_store,
    )
    jobs = scheduler.list_jobs()
    if not jobs:
        click.echo("No scheduled jobs.")
        return
    for job in jobs:
        urls = ', '.join(job.config.seed_urls) if job.config.seed_urls else 'none'
        click.echo(f"  {job.name}: {urls} (every {job.config.interval_hours}h)")


@schedule.command("remove")
@click.argument("name")
def remove_schedule(name):
    """Remove a scheduled job."""
    interest_store = get_interest_store()
    search_index = SearchIndex()
    schedule_store = ScheduleStore(path=".personal_index/schedules.json")
    scheduler = Scheduler(
        interest_store=interest_store,
        search_index=search_index,
        schedule_store=schedule_store,
    )
    if scheduler.remove_job(name):
        click.echo(f"Removed scheduled job: {name}")
    else:
        click.echo(f"Job not found: {name}", err=True)
        raise SystemExit(1)


@main.group()
def config():
    """Manage configuration."""


@config.command("show")
def config_show():
    """Show current configuration."""
    from personal_index.config.loader import load_config
    try:
        cfg = load_config("config.yaml")
    except Exception:
        # Fallback to defaults if config file doesn't exist
        from personal_index.models import AppConfig, CrawlConfig, SchedulerConfig, IndexConfig
        cfg = AppConfig(
            data_dir=".personal_index",
            crawl=CrawlConfig(),
            scheduler=SchedulerConfig(),
            index=IndexConfig(),
        )
    click.echo(f"Config dir: {cfg.config_dir or '~/.config/personal-index'}")
    click.echo(f"Data dir: {cfg.data_dir}")
    click.echo("\nCrawler:")
    click.echo(f"  Max depth: {cfg.crawl.max_depth}")
    click.echo(f"  Politeness delay: {cfg.crawl.politeness_delay}s")
    click.echo(f"  Rate limit: {cfg.crawl.rate_limit}")
    click.echo(f"  Timeout: {cfg.crawl.timeout}s")
    click.echo(f"  Respect robots.txt: {cfg.crawl.respect_robots_txt}")
    click.echo("\nSchedule:")
    click.echo(f"  Enabled: {cfg.scheduler.enabled}")
    click.echo(f"  Interval: {cfg.scheduler.interval_hours}h")


@config.command("set-crawler")
@click.option("--max-depth", type=int, help="Max crawl depth")
@click.option("--delay", type=float, help="Politeness delay")
@click.option("--concurrent", type=int, help="Max concurrent requests")
@click.option("--timeout", type=int, help="Request timeout")
def config_set_crawler(max_depth, delay, concurrent, timeout):
    """Set crawler configuration."""
    from personal_index.config.loader import load_config, save_config
    try:
        cfg = load_config("config.yaml")
    except Exception:
        from personal_index.models import AppConfig, CrawlConfig, SchedulerConfig, IndexConfig
        cfg = AppConfig(
            data_dir=".personal_index",
            crawl=CrawlConfig(),
            scheduler=SchedulerConfig(),
            index=IndexConfig(),
        )
    if max_depth is not None:
        cfg.crawl.max_depth = max_depth
    if delay is not None:
        cfg.crawl.politeness_delay = delay
    if concurrent is not None:
        cfg.crawl.rate_limit = concurrent
    if timeout is not None:
        cfg.crawl.timeout = timeout
    save_config(cfg, "config.yaml")
    click.echo("Crawler config updated.")


@config.command("set-schedule")
@click.option("--interval", type=int, help="Interval in hours")
@click.option("--enable", is_flag=True, help="Enable scheduling")
@click.option("--disable", is_flag=True, help="Disable scheduling")
def config_set_schedule(interval, enable, disable):
    """Set schedule configuration."""
    from personal_index.config.loader import load_config, save_config
    try:
        cfg = load_config("config.yaml")
    except Exception:
        from personal_index.models import AppConfig, CrawlConfig, SchedulerConfig, IndexConfig
        cfg = AppConfig(
            data_dir=".personal_index",
            crawl=CrawlConfig(),
            scheduler=SchedulerConfig(),
            index=IndexConfig(),
        )
    if interval is not None:
        cfg.scheduler.interval_hours = interval
    if enable:
        cfg.scheduler.enabled = True
    if disable:
        cfg.scheduler.enabled = False
    save_config(cfg, "config.yaml")
    click.echo("Schedule config updated.")


if __name__ == "__main__":
    main()
