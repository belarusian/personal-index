"""CLI interface for personal-index."""

import json
import logging
import sys
from pathlib import Path
from typing import Optional

import click

from personal_index.config import AppConfig, Interest
from personal_index.index import SearchIndex
from personal_index.crawler import Crawler
from personal_index.filter import ContentFilter
from personal_index.scheduler import CrawlScheduler

logger = logging.getLogger(__name__)


@click.group()
@click.version_option(version="0.1.0", prog_name="personal-index")
@click.option("--config-dir", type=click.Path(), default=None, help="Configuration directory")
@click.option("--verbose", is_flag=True, help="Enable verbose output")
@click.pass_context
def main(ctx, config_dir, verbose):
    """personal-index: A personal web search engine."""
    ctx.ensure_object(dict)
    if verbose:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.WARNING)

    if config_dir:
        config = AppConfig(config_dir=Path(config_dir))
    else:
        config = AppConfig()
    config.ensure_dirs()

    # Load existing config if it exists
    config_file = config._config_file()
    if config_file.exists():
        loaded = AppConfig.load(config_file)
        config.interests = loaded.interests
        config.crawler = loaded.crawler
        config.schedule = loaded.schedule

    ctx.obj["config"] = config
    ctx.obj["index"] = SearchIndex(index_dir=config.index_dir)
    ctx.obj["filter"] = ContentFilter(interests=config.interests)


@main.group()
def interest():
    """Manage search interests."""
    pass


@interest.command("add")
@click.option("--topic", required=True, help="Topic name")
@click.option("--keywords", default="", help="Comma-separated keywords")
@click.option("--url-pattern", "url_patterns", multiple=True, help="URL pattern to match")
@click.option("--priority", default=5, type=int, help="Priority (1-10)")
@click.pass_context
def add_interest(ctx, topic, keywords, url_patterns, priority):
    """Add a new interest to track."""
    config = ctx.obj["config"]
    kw_list = [k.strip() for k in keywords.split(",") if k.strip()] if keywords else []
    patterns = [p.strip() for p in url_patterns]

    # Check for duplicate
    for existing in config.interests:
        if existing.topic.lower() == topic.lower():
            click.echo(f"Interest '{topic}' already exists. Use 'interest update' to modify.")
            return

    interest = Interest(
        topic=topic,
        keywords=kw_list,
        url_patterns=patterns,
        priority=priority,
    )
    config.interests.append(interest)
    config.save()
    ctx.obj["filter"].add_interest(interest)
    click.echo(f"Added interest: {topic}")
    if kw_list:
        click.echo(f"  Keywords: {', '.join(kw_list)}")
    if patterns:
        click.echo(f"  URL patterns: {', '.join(patterns)}")
    click.echo(f"  Priority: {priority}")


@interest.command("list")
@click.pass_context
def list_interests(ctx):
    """List all configured interests."""
    config = ctx.obj["config"]
    if not config.interests:
        click.echo("No interests configured. Use 'interest add' to add one.")
        return

    click.echo(f"\n{'Topic':<20} {'Keywords':<30} {'Priority':<10} {'Enabled':<8}")
    click.echo("-" * 68)
    for interest in config.interests:
        kws = ", ".join(interest.keywords[:3])
        if len(interest.keywords) > 3:
            kws += "..."
        click.echo(
            f"{interest.topic:<20} {kws:<30} {interest.priority:<10} "
            f"{'Yes' if interest.enabled else 'No':<8}"
        )
    click.echo(f"\nTotal: {len(config.interests)} interests")


@interest.command("remove")
@click.option("--topic", required=True, help="Topic name to remove")
@click.pass_context
def remove_interest(ctx, topic):
    """Remove an interest."""
    config = ctx.obj["config"]
    for i, interest in enumerate(config.interests):
        if interest.topic.lower() == topic.lower():
            config.interests.pop(i)
            config.save()
            ctx.obj["filter"].remove_interest(topic)
            click.echo(f"Removed interest: {topic}")
            return
    click.echo(f"Interest '{topic}' not found.")


@interest.command("enable")
@click.option("--topic", required=True, help="Topic name to enable")
@click.pass_context
def enable_interest(ctx, topic):
    """Enable an interest."""
    config = ctx.obj["config"]
    for interest in config.interests:
        if interest.topic.lower() == topic.lower():
            interest.enabled = True
            config.save()
            click.echo(f"Enabled interest: {topic}")
            return
    click.echo(f"Interest '{topic}' not found.")


@interest.command("disable")
@click.option("--topic", required=True, help="Topic name to disable")
@click.pass_context
def disable_interest(ctx, topic):
    """Disable an interest."""
    config = ctx.obj["config"]
    for interest in config.interests:
        if interest.topic.lower() == topic.lower():
            interest.enabled = False
            config.save()
            click.echo(f"Disabled interest: {topic}")
            return
    click.echo(f"Interest '{topic}' not found.")


@main.command("crawl")
@click.option("--seed", "seeds", multiple=True, required=True, help="Seed URL to crawl")
@click.option("--depth", default=3, type=int, help="Maximum crawl depth")
@click.option("--rate-limit", default=1.0, type=float, help="Requests per second")
@click.option("--max-pages", default=100, type=int, help="Max pages per domain")
@click.pass_context
def crawl(ctx, seeds, depth, rate_limit, max_pages):
    """Crawl URLs and index matching content."""
    config = ctx.obj["config"]
    index = ctx.obj["index"]
    content_filter = ctx.obj["filter"]

    # Update crawler config
    config.crawler.max_depth = depth
    config.crawler.rate_limit = rate_limit
    config.crawler.max_pages_per_domain = max_pages

    crawler = Crawler(config=config.crawler)
    interests = [i for i in config.interests if i.enabled]

    click.echo(f"Starting crawl with {len(seeds)} seed URL(s)...")
    click.echo(f"Max depth: {depth}, Rate limit: {rate_limit}/s")
    click.echo(f"Interests: {len(interests)} enabled")
    click.echo()

    results = crawler.crawl(list(seeds), interests=interests)

    # Index successful results
    indexed = 0
    for result in results:
        if result.success and result.content:
            filter_result = content_filter.filter_content(result.content)
            if filter_result.passed:
                index.add_document(result.content, interest_topics=filter_result.matched_interests)
                indexed += 1
                click.echo(f"  [indexed] {result.url} (score: {filter_result.relevance_score})")
            else:
                click.echo(f"  [filtered] {result.url}")
        elif result.success:
            click.echo(f"  [skipped] {result.url}")
        else:
            click.echo(f"  [error] {result.url} - {result.error}")

    index.save()
    stats = crawler.get_stats()
    click.echo()
    click.echo(f"Crawl complete:")
    click.echo(f"  Total crawled: {stats['total_crawled']}")
    click.echo(f"  Successful: {stats['successful']}")
    click.echo(f"  Failed: {stats['failed']}")
    click.echo(f"  Indexed: {indexed}")
    click.echo(f"  Index size: {index.get_document_count()} documents")


@main.command("search")
@click.argument("query")
@click.option("--limit", default=10, type=int, help="Maximum results")
@click.pass_context
def search(ctx, query, limit):
    """Search the local index."""
    index = ctx.obj["index"]

    if index.get_document_count() == 0:
        click.echo("Index is empty. Run 'crawl' first to index some content.")
        return

    results = index.search(query, limit=limit)

    if not results:
        click.echo(f"No results found for: {query}")
        return

    click.echo(f"\nSearch results for: {query}")
    click.echo(f"Found {len(results)} result(s)\n")

    for i, result in enumerate(results, 1):
        click.echo(f"  {i}. {result.title}")
        click.echo(f"     URL: {result.url}")
        click.echo(f"     Score: {result.score}")
        if result.snippet:
            click.echo(f"     {result.snippet[:200]}")
        if result.matched_terms:
            click.echo(f"     Terms: {', '.join(result.matched_terms)}")
        click.echo()


@main.command("results")
@click.option("--limit", default=20, type=int, help="Maximum results to show")
@click.option("--format", "fmt", default="text", type=click.Choice(["text", "json"]), help="Output format")
@click.pass_context
def results(ctx, limit, fmt):
    """View indexed results."""
    index = ctx.obj["index"]

    if fmt == "json":
        docs = []
        for url in index.get_urls()[:limit]:
            doc = index.get_document(url)
            if doc:
                docs.append(doc.to_dict())
        click.echo(json.dumps(docs, indent=2))
    else:
        urls = index.get_urls()
        if not urls:
            click.echo("No indexed documents.")
            return

        click.echo(f"\nIndexed documents ({len(urls)} total, showing {min(limit, len(urls))}):\n")
        for i, url in enumerate(urls[:limit], 1):
            doc = index.get_document(url)
            if doc:
                click.echo(f"  {i}. {doc.title or url}")
                click.echo(f"     {url}")
                if doc.interest_topics:
                    click.echo(f"     Topics: {', '.join(doc.interest_topics)}")
                click.echo()


@main.command("stats")
@click.pass_context
def stats(ctx):
    """Show index and configuration statistics."""
    config = ctx.obj["config"]
    index = ctx.obj["index"]
    content_filter = ctx.obj["filter"]

    click.echo("\n=== Personal Index Statistics ===\n")
    click.echo(f"Configuration directory: {config.config_dir}")
    click.echo(f"Index directory: {config.index_dir}")
    click.echo()

    click.echo("Interests:")
    click.echo(f"  Total: {len(config.interests)}")
    click.echo(f"  Enabled: {sum(1 for i in config.interests if i.enabled)}")
    click.echo()

    click.echo("Index:")
    index_stats = index.get_stats()
    click.echo(f"  Documents: {index_stats['document_count']}")
    click.echo(f"  Unique terms: {index_stats['term_count']}")
    click.echo()

    click.echo("Content Filter:")
    filter_stats = content_filter.get_stats()
    click.echo(f"  Indexed keywords: {filter_stats['indexed_keywords']}")
    click.echo()


@main.command("clear")
@click.confirmation_option(prompt="Are you sure you want to clear the entire index?")
@click.pass_context
def clear(ctx):
    """Clear the entire search index."""
    index = ctx.obj["index"]
    index.clear()
    click.echo("Index cleared.")


@main.group()
def schedule():
    """Manage scheduled crawling."""
    pass


@schedule.command("add")
@click.option("--name", required=True, help="Schedule name")
@click.option("--interval", default=24, type=int, help="Interval in hours")
@click.option("--seed", "seeds", multiple=True, help="Seed URL")
@click.option("--topic", "topics", multiple=True, help="Topic to track")
@click.pass_context
def add_schedule(ctx, name, interval, seeds, topics):
    """Add a scheduled crawl task."""
    config = ctx.obj["config"]
    scheduler = CrawlScheduler(config=config)
    entry = scheduler.add_schedule(
        name=name,
        interval_hours=interval,
        seed_urls=list(seeds),
        topics=list(topics),
    )
    click.echo(f"Added schedule: {name}")
    click.echo(f"  Interval: every {interval} hours")
    if seeds:
        click.echo(f"  Seeds: {', '.join(seeds)}")
    if topics:
        click.echo(f"  Topics: {', '.join(topics)}")


@schedule.command("list")
@click.pass_context
def list_schedules(ctx):
    """List all scheduled tasks."""
    config = ctx.obj["config"]
    scheduler = CrawlScheduler(config=config)
    schedules = scheduler.list_schedules()
    if not schedules:
        click.echo("No scheduled tasks.")
        return
    for entry in schedules:
        click.echo(f"  {entry.name}: every {entry.interval_hours}h ({'enabled' if entry.enabled else 'disabled'})")


@schedule.command("start")
@click.pass_context
def start_schedule(ctx):
    """Start the scheduler."""
    config = ctx.obj["config"]
    scheduler = CrawlScheduler(config=config)

    def crawl_callback(entry):
        click.echo(f"Running scheduled crawl: {entry.name}")

    scheduler.set_crawl_callback(crawl_callback)
    scheduler.start()
    click.echo("Scheduler started. Press Ctrl+C to stop.")
    try:
        while scheduler.is_running():
            click.pause()
    except KeyboardInterrupt:
        scheduler.stop()
        click.echo("\nScheduler stopped.")


if __name__ == "__main__":
    main()
