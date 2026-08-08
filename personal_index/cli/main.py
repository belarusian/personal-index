"""CLI interface for Personal Index.

Provides commands for managing interests, running crawls, searching,
and viewing results.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import click

from personal_index.config import AppConfig, Interest


def _get_config(config_dir: Optional[str]) -> AppConfig:
    """Load config, optionally from a custom directory."""
    if config_dir:
        config = AppConfig.load(Path(config_dir) / "config.json")
        config.config_dir = Path(config_dir)
        config.index_dir = Path(config_dir) / "index"
    else:
        config = AppConfig.load()
    return config


@click.group()
@click.version_option(version="0.1.0", prog_name="personal-index")
def cli() -> None:
    """Personal Index - A personal web search engine.

    Define your interests and let the system scan, filter, and index the web for you.
    """
    pass


@cli.group()
def interest() -> None:
    """Manage tracked interests."""
    pass


@interest.command("add")
@click.option("--topic", "-t", required=True, help="Topic name for this interest.")
@click.option(
    "--keywords",
    "-k",
    multiple=True,
    help="Keywords to track (can be specified multiple times).",
)
@click.option(
    "--url-pattern",
    "-u",
    "url_patterns",
    multiple=True,
    help="URL patterns to match (can be specified multiple times).",
)
@click.option(
    "--priority",
    "-p",
    type=int,
    default=5,
    help="Priority level (1-10, default: 5).",
)
@click.option("--config-dir", type=click.Path(), default=None, help="Config directory.")
def interest_add(
    topic: str,
    keywords: tuple[str, ...],
    url_patterns: tuple[str, ...],
    priority: int,
    config_dir: Optional[str],
) -> None:
    """Add a new interest to track."""
    config = _get_config(config_dir)

    # Check for duplicate topic
    for existing in config.interests:
        if existing.topic.lower() == topic.lower():
            click.echo(f"Error: Interest '{topic}' already exists.")
            return

    new_interest = Interest(
        topic=topic,
        keywords=list(keywords),
        url_patterns=list(url_patterns),
        priority=priority,
    )
    config.interests.append(new_interest)
    config.save()

    click.echo(f"Added interest: {topic}")
    if keywords:
        click.echo(f"  Keywords: {', '.join(keywords)}")
    if url_patterns:
        click.echo(f"  URL patterns: {', '.join(url_patterns)}")
    click.echo(f"  Priority: {priority}")


@interest.command("list")
@click.option("--config-dir", type=click.Path(), default=None, help="Config directory.")
def interest_list(config_dir: Optional[str]) -> None:
    """List all tracked interests."""
    config = _get_config(config_dir)

    if not config.interests:
        click.echo("No interests configured. Use 'personal-index interest add' to add one.")
        return

    click.echo(f"Tracked interests ({len(config.interests)}):")
    click.echo("-" * 60)
    for i, interest in enumerate(config.interests, 1):
        status = "enabled" if interest.enabled else "disabled"
        click.echo(f"  {i}. [{status}] {interest.topic} (priority: {interest.priority})")
        if interest.keywords:
            click.echo(f"     Keywords: {', '.join(interest.keywords)}")
        if interest.url_patterns:
            click.echo(f"     URL patterns: {', '.join(interest.url_patterns)}")
        click.echo()


@interest.command("remove")
@click.option("--topic", "-t", required=True, help="Topic name to remove.")
@click.option("--config-dir", type=click.Path(), default=None, help="Config directory.")
def interest_remove(topic: str, config_dir: Optional[str]) -> None:
    """Remove a tracked interest."""
    config = _get_config(config_dir)

    original_len = len(config.interests)
    config.interests = [i for i in config.interests if i.topic.lower() != topic.lower()]

    if len(config.interests) == original_len:
        click.echo(f"Error: Interest '{topic}' not found.")
        return

    config.save()
    click.echo(f"Removed interest: {topic}")


@cli.command("crawl")
@click.option("--seed", "-s", multiple=True, required=True, help="Seed URL to start crawling.")
@click.option("--depth", "-d", type=int, default=None, help="Maximum crawl depth.")
@click.option(
    "--rate-limit", "-r", type=float, default=None, help="Seconds between requests per domain."
)
@click.option(
    "--max-pages", "-m", type=int, default=None, help="Max pages per domain."
)
@click.option("--config-dir", type=click.Path(), default=None, help="Config directory.")
def crawl(
    seed: tuple[str, ...],
    depth: Optional[int],
    rate_limit: Optional[float],
    max_pages: Optional[int],
    config_dir: Optional[str],
) -> None:
    """Run a web crawl from seed URLs."""
    from personal_index.crawler import WebCrawler
    from personal_index.filter import ContentFilter
    from personal_index.indexer import SearchIndex

    config = _get_config(config_dir)

    if depth is not None:
        config.crawler.max_depth = depth
    if rate_limit is not None:
        config.crawler.politeness_delay = rate_limit
    if max_pages is not None:
        config.crawler.max_pages_per_domain = max_pages

    content_filter = ContentFilter(config.interests)
    index = SearchIndex(index_dir=config.index_dir)
    index.load()

    click.echo(f"Starting crawl with {len(seed)} seed URL(s)...")
    click.echo(f"Max depth: {config.crawler.max_depth}")
    click.echo(f"Politeness delay: {config.crawler.politeness_delay}s")
    click.echo(f"Interests: {len(config.interests)} configured")
    click.echo()

    with WebCrawler(config=config, content_filter=content_filter) as crawler:
        pages = crawler.crawl(list(seed))

    # Index the pages
    for page in pages:
        index.add_page(page)

    index.save()

    click.echo(f"Crawl complete!")
    click.echo(f"  Pages indexed: {len(pages)}")
    click.echo(f"  Total in index: {index.num_documents}")
    stats = crawler.stats
    if stats:
        click.echo("  Statistics:")
        for key, value in stats.items():
            click.echo(f"    {key}: {value}")


@cli.command("search")
@click.argument("query")
@click.option("--limit", "-l", type=int, default=10, help="Max results to show.")
@click.option(
    "--interest", "-i", multiple=True, help="Filter by interest topic."
)
@click.option("--config-dir", type=click.Path(), default=None, help="Config directory.")
def search(
    query: str,
    limit: int,
    interest: tuple[str, ...],
    config_dir: Optional[str],
) -> None:
    """Search the local index."""
    from personal_index.indexer import SearchIndex

    config = _get_config(config_dir)

    index = SearchIndex(index_dir=config.index_dir)
    index.load()

    if index.num_documents == 0:
        click.echo("Index is empty. Run 'personal-index crawl' first.")
        return

    interest_filter = list(interest) if interest else None
    results = index.search(query, limit=limit, interest_filter=interest_filter)

    if not results:
        click.echo(f"No results found for: {query}")
        return

    click.echo(f"Search results for '{query}' ({len(results)} found):")
    click.echo("-" * 70)
    for i, result in enumerate(results, 1):
        click.echo(f"  {i}. [{result.score:.3f}] {result.page.title or result.page.url}")
        click.echo(f"     {result.page.url}")
        if result.page.meta_description:
            desc = result.page.meta_description[:120]
            click.echo(f"     {desc}...")
        if result.matched_interests:
            click.echo(f"     Interests: {', '.join(result.matched_interests)}")
        click.echo()


@cli.command("status")
@click.option("--config-dir", type=click.Path(), default=None, help="Config directory.")
def status(config_dir: Optional[str]) -> None:
    """Show index and configuration status."""
    from personal_index.indexer import SearchIndex

    config = _get_config(config_dir)

    index = SearchIndex(index_dir=config.index_dir)
    index.load()

    click.echo("Personal Index Status")
    click.echo("=" * 40)
    click.echo(f"  Interests: {len(config.interests)}")
    click.echo(f"  Indexed pages: {index.num_documents}")
    click.echo(f"  Unique terms: {index.num_terms}")
    click.echo(f"  Index dir: {config.index_dir}")
    click.echo(f"  Config dir: {config.config_dir}")
    click.echo()

    if config.interests:
        click.echo("Interests:")
        for interest in config.interests:
            click.echo(f"  - {interest.topic} (priority: {interest.priority})")


@cli.command("stats")
@click.option("--config-dir", type=click.Path(), default=None, help="Config directory.")
def stats(config_dir: Optional[str]) -> None:
    """Show detailed index statistics."""
    from personal_index.indexer import SearchIndex

    config = _get_config(config_dir)

    index = SearchIndex(index_dir=config.index_dir)
    index.load()

    click.echo("Index Statistics")
    click.echo("=" * 40)
    click.echo(f"  Total documents: {index.num_documents}")
    click.echo(f"  Unique terms: {index.num_terms}")

    pages = index.get_all_pages()
    if pages:
        interests_count: dict[str, int] = {}
        for page in pages:
            for interest in page.matched_interests:
                interests_count[interest] = interests_count.get(interest, 0) + 1

        if interests_count:
            click.echo("\n  Pages by interest:")
            for topic, count in sorted(interests_count.items(), key=lambda x: -x[1]):
                click.echo(f"    {topic}: {count}")


if __name__ == "__main__":
    cli()
