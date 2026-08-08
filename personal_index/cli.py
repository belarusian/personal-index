"""CLI interface for personal-index.

Provides command-line commands for managing interests, running crawls,
searching, and viewing results.
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path
from typing import Optional

import click

from personal_index.models import CrawlConfig, Interest
from personal_index.storage import InterestStore, PageStore
from personal_index.filter import ContentFilter
from personal_index.crawler import WebCrawler
from personal_index.search import SearchIndex
from personal_index.scheduler import CrawlScheduler

logger = logging.getLogger(__name__)


@click.group()
@click.version_option(version="0.1.0", prog_name="personal-index")
@click.option("--data-dir", default="~/.personal-index", help="Data directory path")
@click.option("--verbose", "-v", is_flag=True, help="Enable verbose output")
@click.pass_context
def cli(ctx, data_dir, verbose):
    """personal-index: A personal web search engine.

    Define your interests and let the system scan, filter,
    and index the web for you.
    """
    ctx.ensure_object(dict)
    ctx.obj["data_dir"] = str(Path(data_dir).expanduser())

    if verbose:
        logging.basicConfig(level=logging.DEBUG, format="%(levelname)s: %(message)s")
    else:
        logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")


@cli.group()
def interest():
    """Manage tracked interests."""
    pass


@interest.command()
@click.option("--topic", "-t", required=True, help="Topic name")
@click.option("--keywords", "-k", default="", help="Comma-separated keywords")
@click.option("--url-patterns", "-u", default="", help="Comma-separated URL patterns")
@click.pass_context
def add(ctx, topic, keywords, url_patterns):
    """Add a new interest to track."""
    store = InterestStore(ctx.obj["data_dir"])

    kw_list = [k.strip() for k in keywords.split(",") if k.strip()]
    url_list = [u.strip() for u in url_patterns.split(",") if u.strip()]

    interest = Interest(
        topic=topic,
        keywords=kw_list,
        url_patterns=url_list,
    )

    try:
        store.add_interest(interest)
        click.echo(f"Added interest: {topic}")
        if kw_list:
            click.echo(f"  Keywords: {', '.join(kw_list)}")
        if url_list:
            click.echo(f"  URL patterns: {', '.join(url_list)}")
    except ValueError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@interest.command("list")
@click.option("--enabled-only", is_flag=True, help="Show only enabled interests")
@click.pass_context
def list_interests(ctx, enabled_only):
    """List all tracked interests."""
    store = InterestStore(ctx.obj["data_dir"])
    interests = store.list_interests(enabled_only=enabled_only)

    if not interests:
        click.echo("No interests configured.")
        return

    click.echo(f"{'Topic':<25} {'Keywords':<30} {'URL Patterns':<25} {'Status'}")
    click.echo("-" * 100)
    for interest in interests:
        kw = ", ".join(interest.keywords[:3])
        if len(interest.keywords) > 3:
            kw += f" (+{len(interest.keywords) - 3})"
        urls = ", ".join(interest.url_patterns[:2])
        if len(interest.url_patterns) > 2:
            urls += f" (+{len(interest.url_patterns) - 2})"
        status = "enabled" if interest.enabled else "disabled"
        click.echo(f"{interest.topic:<25} {kw:<30} {urls:<25} {status}")


@interest.command()
@click.option("--topic", "-t", required=True, help="Topic name to remove")
@click.pass_context
def remove(ctx, topic):
    """Remove a tracked interest."""
    store = InterestStore(ctx.obj["data_dir"])
    if store.remove_interest(topic):
        click.echo(f"Removed interest: {topic}")
    else:
        click.echo(f"Interest not found: {topic}", err=True)
        sys.exit(1)


@interest.command()
@click.option("--topic", "-t", required=True, help="Topic name to toggle")
@click.pass_context
def toggle(ctx, topic):
    """Toggle an interest's enabled/disabled status."""
    store = InterestStore(ctx.obj["data_dir"])
    result = store.toggle_interest(topic)
    if result:
        status = "enabled" if result.enabled else "disabled"
        click.echo(f"Toggled '{topic}' -> {status}")
    else:
        click.echo(f"Interest not found: {topic}", err=True)
        sys.exit(1)


@cli.command()
@click.option("--seed-urls", "-s", default="", help="Comma-separated seed URLs")
@click.option("--depth", "-d", default=2, help="Maximum crawl depth")
@click.option("--max-pages", "-m", default=100, help="Maximum pages to crawl")
@click.option("--rate-limit", "-r", default=1.0, help="Seconds between requests")
@click.option("--timeout", default=10, help="Request timeout in seconds")
@click.option("--allowed-domains", default="", help="Comma-separated allowed domains")
@click.option("--blocked-domains", default="", help="Comma-separated blocked domains")
@click.pass_context
def crawl(ctx, seed_urls, depth, max_pages, rate_limit, timeout, allowed_domains, blocked_domains):
    """Run a web crawl based on configured interests."""
    data_dir = ctx.obj["data_dir"]

    # Load interests
    interest_store = InterestStore(data_dir)
    interests = interest_store.list_interests(enabled_only=True)

    if not interests:
        click.echo("No enabled interests configured. Use 'personal-index interest add' first.")
        sys.exit(1)

    # Build seed URLs from interests
    urls = [u.strip() for u in seed_urls.split(",") if u.strip()]
    if not urls:
        # Use URL patterns as seed URLs
        for interest in interests:
            for pattern in interest.url_patterns:
                if pattern.startswith("http"):
                    urls.append(pattern)
                else:
                    urls.append(f"https://{pattern}")

    if not urls:
        click.echo("No seed URLs provided and no URL patterns in interests.")
        click.echo("Provide --seed-urls or add URL patterns to your interests.")
        sys.exit(1)

    # Configure crawler
    config = CrawlConfig(
        max_depth=depth,
        max_pages=max_pages,
        rate_limit=rate_limit,
        timeout=timeout,
        allowed_domains=[d.strip() for d in allowed_domains.split(",") if d.strip()],
        blocked_domains=[d.strip() for d in blocked_domains.split(",") if d.strip()],
    )

    content_filter = ContentFilter(interests)
    page_store = PageStore(data_dir)
    search_index = SearchIndex(index_dir=f"{data_dir}/index")

    crawler = WebCrawler(config=config, content_filter=content_filter)

    click.echo(f"Starting crawl with {len(urls)} seed URL(s)...")
    click.echo(f"Depth: {depth}, Max pages: {max_pages}, Rate limit: {rate_limit}s")

    stats = crawler.crawl(urls)

    click.echo(f"\nCrawl complete:")
    click.echo(f"  Pages crawled: {stats.pages_crawled}")
    click.echo(f"  Pages filtered: {stats.pages_filtered}")
    click.echo(f"  Pages stored: {stats.pages_stored}")
    click.echo(f"  Errors: {stats.errors}")
    if stats.duration:
        click.echo(f"  Duration: {stats.duration:.1f}s")


@cli.command()
@click.argument("query")
@click.option("--limit", "-l", default=10, help="Maximum results to show")
@click.option("--interest", "-i", default=None, help="Filter by interest topic")
@click.pass_context
def search(ctx, query, limit, interest):
    """Search the local index."""
    data_dir = ctx.obj["data_dir"]
    search_index = SearchIndex(index_dir=f"{data_dir}/index")

    results = search_index.search(query, limit=limit, interest_filter=interest)

    if not results:
        click.echo(f"No results found for: {query}")
        return

    click.echo(f"\nSearch results for '{query}' ({len(results)} found):")
    click.echo("=" * 80)

    for i, result in enumerate(results, 1):
        page = result.page
        click.echo(f"\n[{i}] {page.title or 'Untitled'}")
        click.echo(f"    URL: {page.url}")
        click.echo(f"    Score: {result.score:.4f}")
        if page.meta_description:
            click.echo(f"    Description: {page.meta_description[:120]}")
        if page.matched_interests:
            click.echo(f"    Interests: {', '.join(page.matched_interests)}")


@cli.command()
@click.argument("query")
@click.option("--limit", "-l", default=10, help="Maximum results to show")
@click.option("--fragment-size", "-f", default=200, help="Highlight fragment size")
@click.pass_context
def results(ctx, query, limit, fragment_size):
    """Search and display results with highlighted matches."""
    data_dir = ctx.obj["data_dir"]
    search_index = SearchIndex(index_dir=f"{data_dir}/index")

    search_results = search_index.search_with_highlights(
        query, limit=limit, fragment_size=fragment_size
    )

    if not search_results:
        click.echo(f"No results found for: {query}")
        return

    click.echo(f"\nResults for '{query}' ({len(search_results)} found):")
    click.echo("=" * 80)

    for i, result in enumerate(search_results, 1):
        page = result.page
        click.echo(f"\n[{i}] {page.title or 'Untitled'}")
        click.echo(f"    URL: {page.url}")
        click.echo(f"    Score: {result.score:.4f}")
        if result.highlights:
            for highlight in result.highlights[:2]:
                click.echo(f"    Match: ...{highlight}...")
        if page.matched_interests:
            click.echo(f"    Interests: {', '.join(page.matched_interests)}")


@cli.group()
def schedule():
    """Manage crawl schedules."""
    pass


@schedule.command()
@click.option("--topic", "-t", required=True, help="Topic to schedule")
@click.option("--interval", "-i", default=24, help="Interval in hours")
@click.pass_context
def add_schedule(ctx, topic, interval):
    """Add a periodic crawl schedule."""
    scheduler = CrawlScheduler(ctx.obj["data_dir"])
    scheduler.add_schedule(topic, interval_hours=float(interval))
    click.echo(f"Added schedule for '{topic}' every {interval}h")


@schedule.command("list")
@click.pass_context
def list_schedules(ctx):
    """List all crawl schedules."""
    scheduler = CrawlScheduler(ctx.obj["data_dir"])
    schedules = scheduler.list_schedules()

    if not schedules:
        click.echo("No schedules configured.")
        return

    click.echo(f"{'Topic':<25} {'Interval':<15} {'Last Run':<25} {'Next Run':<25} {'Status'}")
    click.echo("-" * 105)
    for sched in schedules:
        last = sched.last_run.strftime("%Y-%m-%d %H:%M") if sched.last_run else "Never"
        next_run = sched.next_run.strftime("%Y-%m-%d %H:%M") if sched.next_run else "N/A"
        status = "enabled" if sched.enabled else "disabled"
        click.echo(f"{sched.topic:<25} {sched.interval_hours:<15} {last:<25} {next_run:<25} {status}")


@schedule.command()
@click.option("--topic", "-t", required=True, help="Topic to remove schedule for")
@click.pass_context
def remove_schedule(ctx, topic):
    """Remove a crawl schedule."""
    scheduler = CrawlScheduler(ctx.obj["data_dir"])
    if scheduler.remove_schedule(topic):
        click.echo(f"Removed schedule for '{topic}'")
    else:
        click.echo(f"No schedule found for '{topic}'", err=True)
        sys.exit(1)


@schedule.command()
@click.option("--topic", "-t", required=True, help="Topic to run now")
@click.pass_context
def run_now(ctx, topic):
    """Manually trigger a scheduled crawl."""
    scheduler = CrawlScheduler(ctx.obj["data_dir"])
    interest_store = InterestStore(ctx.obj["data_dir"])
    page_store = PageStore(ctx.obj["data_dir"])
    search_index = SearchIndex(index_dir=f"{ctx.obj['data_dir']}/index")

    def crawl_callback(schedule):
        interests = interest_store.list_interests(enabled_only=True)
        content_filter = ContentFilter(interests)

        urls = []
        for interest in interests:
            if interest.topic == schedule.topic:
                for pattern in interest.url_patterns:
                    if pattern.startswith("http"):
                        urls.append(pattern)
                    else:
                        urls.append(f"https://{pattern}")

        if not urls:
            return CrawlConfig.__class__.__dict__  # empty stats

        config = schedule.config or CrawlConfig()
        crawler = WebCrawler(config=config, content_filter=content_filter)
        stats = crawler.crawl(urls)

        # Store and index crawled pages
        for page in crawler.get_visited_urls():
            pass  # Pages are processed during crawl

        return stats

    scheduler.set_crawl_callback(crawl_callback)
    job = scheduler.run_now(topic)

    if job:
        click.echo(f"Job started: {job.job_id}")
        click.echo(f"Status: {job.status}")
        if job.pages_crawled:
            click.echo(f"Pages crawled: {job.pages_crawled}")
            click.echo(f"Pages stored: {job.pages_stored}")
            click.echo(f"Errors: {job.errors}")
    else:
        click.echo(f"No schedule found for '{topic}'", err=True)
        sys.exit(1)


@schedule.command("jobs")
@click.option("--limit", "-l", default=10, help="Number of recent jobs to show")
@click.pass_context
def list_jobs(ctx, limit):
    """List recent crawl jobs."""
    scheduler = CrawlScheduler(ctx.obj["data_dir"])
    jobs = scheduler.list_jobs(limit=limit)

    if not jobs:
        click.echo("No jobs found.")
        return

    click.echo(f"{'Job ID':<40} {'Topic':<20} {'Status':<12} {'Pages':<10} {'Errors'}")
    click.echo("-" * 90)
    for job in jobs:
        click.echo(
            f"{job.job_id:<40} {job.topic:<20} {job.status:<12} "
            f"{job.pages_crawled:<10} {job.errors}"
        )


@cli.command()
@click.pass_context
def status(ctx):
    """Show system status."""
    data_dir = ctx.obj["data_dir"]

    interest_store = InterestStore(data_dir)
    page_store = PageStore(data_dir)
    search_index = SearchIndex(index_dir=f"{data_dir}/index")
    scheduler = CrawlScheduler(data_dir)

    interests = interest_store.list_interests()
    enabled_interests = [i for i in interests if i.enabled]

    click.echo("Personal Index Status")
    click.echo("=" * 40)
    click.echo(f"Data directory: {data_dir}")
    click.echo(f"Interests: {len(interests)} total, {len(enabled_interests)} enabled")
    click.echo(f"Stored pages: {page_store.count_pages()}")
    click.echo(f"Indexed documents: {search_index.get_document_count()}")
    click.echo(f"Schedules: {len(scheduler.list_schedules())}")
