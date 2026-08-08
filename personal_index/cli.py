"""
CLI interface for personal-index.

Provides commands to add interests, run crawls, search, and view results.
"""

import sys
from typing import Optional

import click

from personal_index.config import AppConfig, ConfigManager, CrawlerConfig, ScheduleConfig
from personal_index.interests import Interest, InterestStore
from personal_index.filter import ContentFilter
from personal_index.index import SearchIndex, IndexedPage
from personal_index.crawler import WebCrawler
from personal_index.scheduler import Scheduler, ScheduledJob


def get_config_manager() -> ConfigManager:
    """Get the configuration manager."""
    return ConfigManager()


def get_interest_store() -> InterestStore:
    """Get the interest store."""
    return InterestStore()


def get_search_index() -> SearchIndex:
    """Get the search index."""
    return SearchIndex()


def get_crawler() -> WebCrawler:
    """Get a configured crawler."""
    config_mgr = get_config_manager()
    config = config_mgr.config
    interest_store = get_interest_store()
    filter = ContentFilter(interest_store)
    search_index = get_search_index()
    return WebCrawler(
        config=config.crawler,
        content_filter=filter,
        search_index=search_index,
    )


@click.group()
@click.version_option(version="0.1.0", prog_name="personal-index")
def main():
    """personal-index: A personal web search engine.

    Define your interests and let the system scan, filter,
    and index the web for you.
    """
    pass


# ── Interest Commands ──────────────────────────────────────────────

@main.group()
def interests():
    """Manage your interests (topics, keywords, URL patterns)."""
    pass


@interests.command("add")
@click.option("--name", "-n", required=True, help="Name for this interest.")
@click.option("--keyword", "-k", multiple=True, help="Keywords to track.")
@click.option("--topic", "-t", multiple=True, help="Topics to track.")
@click.option("--url-pattern", "-u", multiple=True, help="URL regex patterns to match.")
@click.option("--priority", "-p", type=int, default=1, help="Priority (1-5).")
def add_interest(name, keyword, topic, url_pattern, priority):
    """Add a new interest to track."""
    store = get_interest_store()
    interest = Interest(
        name=name,
        keywords=list(keyword),
        topics=list(topic),
        url_patterns=list(url_pattern),
        priority=priority,
    )
    store.add(interest)
    click.echo(f"✓ Added interest '{name}'")
    if keyword:
        click.echo(f"  Keywords: {', '.join(keyword)}")
    if topic:
        click.echo(f"  Topics: {', '.join(topic)}")
    if url_pattern:
        click.echo(f"  URL patterns: {', '.join(url_pattern)}")
    click.echo(f"  Priority: {priority}")


@interests.command("list")
def list_interests():
    """List all configured interests."""
    store = get_interest_store()
    all_interests = store.list_all()
    if not all_interests:
        click.echo("No interests configured. Use 'personal-index interests add' to add one.")
        return

    for interest in all_interests:
        status = "enabled" if interest.enabled else "disabled"
        click.echo(f"  [{status}] {interest.name} (priority: {interest.priority})")
        if interest.keywords:
            click.echo(f"    Keywords: {', '.join(interest.keywords)}")
        if interest.topics:
            click.echo(f"    Topics: {', '.join(interest.topics)}")
        if interest.url_patterns:
            click.echo(f"    URL patterns: {', '.join(interest.url_patterns)}")
        click.echo()


@interests.command("remove")
@click.argument("name")
def remove_interest(name):
    """Remove an interest by name."""
    store = get_interest_store()
    if store.remove(name):
        click.echo(f"✓ Removed interest '{name}'")
    else:
        click.echo(f"✗ Interest '{name}' not found")
        sys.exit(1)


@interests.command("toggle")
@click.argument("name")
def toggle_interest(name):
    """Toggle an interest's enabled/disabled state."""
    store = get_interest_store()
    result = store.toggle(name)
    if result:
        status = "enabled" if result.enabled else "disabled"
        click.echo(f"✓ Interest '{name}' is now {status}")
    else:
        click.echo(f"✗ Interest '{name}' not found")
        sys.exit(1)


# ── Crawl Commands ─────────────────────────────────────────────────

@main.group()
def crawl():
    """Crawl and index web pages."""
    pass


@crawl.command("run")
@click.argument("urls", nargs=-1, required=True)
@click.option("--depth", "-d", type=int, default=None, help="Max crawl depth.")
@click.option("--no-filter", is_flag=True, help="Index all pages regardless of interests.")
def crawl_run(urls, depth, no_filter):
    """Run a crawl from the given seed URLs."""
    import asyncio

    config_mgr = get_config_manager()
    config = config_mgr.config
    interest_store = get_interest_store()
    content_filter = ContentFilter(interest_store)
    search_index = get_search_index()

    crawler = WebCrawler(
        config=config.crawler,
        content_filter=None if no_filter else content_filter,
        search_index=search_index,
    )

    click.echo(f"Crawling {len(urls)} seed URL(s)..." + (f" (max depth: {depth})" if depth else ""))

    async def run():
        pages = await crawler.crawl(list(urls), max_depth=depth)
        return pages

    pages = asyncio.run(run())
    stats = crawler.stats

    click.echo(f"\n✓ Crawl complete!")
    click.echo(f"  Pages crawled: {stats['pages_crawled']}")
    click.echo(f"  Pages indexed: {stats['pages_indexed']}")
    click.echo(f"  Pages filtered: {stats['pages_filtered']}")
    click.echo(f"  Errors: {stats['errors']}")


@crawl.command("status")
def crawl_status():
    """Show crawl/index status."""
    search_index = get_search_index()
    count = search_index.get_page_count()
    click.echo(f"Indexed pages: {count}")


# ── Search Commands ────────────────────────────────────────────────

@main.command("search")
@click.argument("query")
@click.option("--limit", "-l", type=int, default=10, help="Max results to show.")
def search(query, limit):
    """Search the local index."""
    search_index = get_search_index()
    results = search_index.search(query, limit=limit)

    if not results:
        click.echo(f"No results found for '{query}'")
        return

    click.echo(f"\nSearch results for '{query}' ({len(results)} found):\n")
    for i, result in enumerate(results, 1):
        click.echo(f"  {i}. {result.title}")
        click.echo(f"     {result.url}")
        click.echo(f"     Score: {result.relevance_score:.2f}")
        if result.source_interest:
            click.echo(f"     Interest: {result.source_interest}")
        click.echo()


# ── Index Commands ─────────────────────────────────────────────────

@main.group()
def index():
    """Manage the search index."""
    pass


@index.command("list")
@click.option("--limit", "-l", type=int, default=20, help="Max pages to show.")
def index_list(limit):
    """List indexed pages."""
    search_index = get_search_index()
    pages = search_index.list_pages(limit=limit)

    if not pages:
        click.echo("No pages indexed yet.")
        return

    click.echo(f"\nIndexed pages ({len(pages)} shown):\n")
    for page in pages:
        click.echo(f"  {page.title}")
        click.echo(f"    {page.url}")
        click.echo(f"    Score: {page.score:.2f} | Words: {page.word_count}")
        click.echo()


@index.command("clear")
@click.confirmation_option(prompt="Are you sure you want to clear the entire index?")
def index_clear():
    """Clear the entire search index."""
    search_index = get_search_index()
    search_index.clear()
    click.echo("✓ Index cleared")


@index.command("count")
def index_count():
    """Show the number of indexed pages."""
    search_index = get_search_index()
    count = search_index.get_page_count()
    click.echo(f"Total indexed pages: {count}")


# ── Schedule Commands ──────────────────────────────────────────────

@main.group()
def schedule():
    """Manage scheduled crawling jobs."""
    pass


@schedule.command("add")
@click.option("--name", "-n", required=True, help="Name for this job.")
@click.option("--url", "-u", multiple=True, required=True, help="Seed URL(s) to crawl.")
@click.option("--interval", "-i", type=int, default=24, help="Interval in hours.")
def schedule_add(name, url, interval):
    """Add a scheduled crawling job."""
    scheduler = Scheduler()
    job = ScheduledJob(
        name=name,
        seed_urls=list(url),
        interval_hours=interval,
    )
    scheduler.add_job(job)
    click.echo(f"✓ Added scheduled job '{name}'")
    click.echo(f"  URLs: {', '.join(url)}")
    click.echo(f"  Interval: every {interval} hours")


@schedule.command("list")
def schedule_list():
    """List all scheduled jobs."""
    scheduler = Scheduler()
    jobs = scheduler.list_jobs()

    if not jobs:
        click.echo("No scheduled jobs configured.")
        return

    for job in jobs:
        status = "enabled" if job.enabled else "disabled"
        click.echo(f"  [{status}] {job.name}")
        click.echo(f"    URLs: {', '.join(job.seed_urls)}")
        click.echo(f"    Interval: every {job.interval_hours} hours")
        click.echo(f"    Runs: {job.run_count} | Last: {job.last_run or 'never'}")
        click.echo()


@schedule.command("remove")
@click.argument("name")
def schedule_remove(name):
    """Remove a scheduled job."""
    scheduler = Scheduler()
    if scheduler.remove_job(name):
        click.echo(f"✓ Removed job '{name}'")
    else:
        click.echo(f"✗ Job '{name}' not found")
        sys.exit(1)


@schedule.command("run")
@click.argument("name")
def schedule_run(name):
    """Run a scheduled job immediately."""
    import asyncio

    config_mgr = get_config_manager()
    config = config_mgr.config
    interest_store = get_interest_store()
    content_filter = ContentFilter(interest_store)
    search_index = get_search_index()
    crawler = WebCrawler(
        config=config.crawler,
        content_filter=content_filter,
        search_index=search_index,
    )
    scheduler = Scheduler(crawler=crawler)

    click.echo(f"Running job '{name}'...")

    async def run():
        return await scheduler.run_job(name)

    result = asyncio.run(run())
    if "error" in result:
        click.echo(f"✗ Error: {result['error']}")
        sys.exit(1)
    else:
        click.echo(f"✓ Job completed: {result.get('pages_crawled', 0)} pages crawled")


@schedule.command("enable")
@click.option("--all", "enable_all", is_flag=True, help="Enable all jobs.")
@click.argument("name", required=False)
def schedule_enable(enable_all, name):
    """Enable a scheduled job."""
    scheduler = Scheduler()
    if enable_all:
        for job in scheduler.list_jobs():
            scheduler.enable_job(job.name)
        click.echo("✓ All jobs enabled")
    elif name:
        if scheduler.enable_job(name):
            click.echo(f"✓ Job '{name}' enabled")
        else:
            click.echo(f"✗ Job '{name}' not found")
            sys.exit(1)
    else:
        click.echo("Specify a job name or use --all")
        sys.exit(1)


@schedule.command("disable")
@click.option("--all", "disable_all", is_flag=True, help="Disable all jobs.")
@click.argument("name", required=False)
def schedule_disable(disable_all, name):
    """Disable a scheduled job."""
    scheduler = Scheduler()
    if disable_all:
        for job in scheduler.list_jobs():
            scheduler.disable_job(job.name)
        click.echo("✓ All jobs disabled")
    elif name:
        if scheduler.disable_job(name):
            click.echo(f"✓ Job '{name}' disabled")
        else:
            click.echo(f"✗ Job '{name}' not found")
            sys.exit(1)
    else:
        click.echo("Specify a job name or use --all")
        sys.exit(1)


# ── Config Commands ────────────────────────────────────────────────

@main.group()
def config():
    """Manage configuration."""
    pass


@config.command("show")
def config_show():
    """Show current configuration."""
    config_mgr = get_config_manager()
    config = config_mgr.config
    click.echo("Configuration:")
    click.echo(f"  Config dir: {config.config_dir}")
    click.echo(f"  Data dir: {config.data_dir}")
    click.echo(f"  Crawler:")
    click.echo(f"    Max depth: {config.crawler.max_depth}")
    click.echo(f"    Politeness delay: {config.crawler.politeness_delay}s")
    click.echo(f"    Max concurrent: {config.crawler.max_concurrent_requests}")
    click.echo(f"    Timeout: {config.crawler.request_timeout}s")
    click.echo(f"    Respect robots.txt: {config.crawler.respect_robots_txt}")
    click.echo(f"  Schedule:")
    click.echo(f"    Enabled: {config.schedule.enabled}")
    click.echo(f"    Interval: {config.schedule.interval_hours}h")


@config.command("set-crawler")
@click.option("--max-depth", type=int, help="Max crawl depth.")
@click.option("--politeness-delay", type=float, help="Delay between requests (seconds).")
@click.option("--max-concurrent", type=int, help="Max concurrent requests.")
@click.option("--timeout", type=int, help="Request timeout (seconds).")
@click.option("--user-agent", help="User agent string.")
def config_set_crawler(max_depth, politeness_delay, max_concurrent, timeout, user_agent):
    """Set crawler configuration."""
    config_mgr = get_config_manager()
    config = config_mgr.config

    if max_depth is not None:
        config.crawler.max_depth = max_depth
    if politeness_delay is not None:
        config.crawler.politeness_delay = politeness_delay
    if max_concurrent is not None:
        config.crawler.max_concurrent_requests = max_concurrent
    if timeout is not None:
        config.crawler.request_timeout = timeout
    if user_agent is not None:
        config.crawler.user_agent = user_agent

    config_mgr.save(config)
    click.echo("✓ Crawler configuration updated")


@config.command("set-schedule")
@click.option("--enable/--disable", default=None, help="Enable/disable scheduled crawling.")
@click.option("--interval", type=int, help="Interval in hours.")
@click.option("--max-pages", type=int, help="Max pages per run.")
def config_set_schedule(enable, interval, max_pages):
    """Set schedule configuration."""
    config_mgr = get_config_manager()
    config = config_mgr.config

    if enable is not None:
        config.schedule.enabled = enable
    if interval is not None:
        config.schedule.interval_hours = interval
    if max_pages is not None:
        config.schedule.max_pages_per_run = max_pages

    config_mgr.save(config)
    click.echo("✓ Schedule configuration updated")


if __name__ == "__main__":
    main()
