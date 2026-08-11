"""Crawl CLI command for personal-index.

Provides the 'crawl' command that performs web crawling and saves
results to the data directory.
"""

from __future__ import annotations

import os
import sys

import click

from personal_index.crawler.main import Crawler, CrawlerConfig


@click.command("crawl")
@click.argument("urls", nargs=-1)
@click.option("--depth", "-d", default=3, type=int, help="Max crawl depth")
@click.option("--max-pages", "-m", default=100, type=int, help="Max pages to crawl")
@click.option("--delay", default=1.0, type=float, help="Delay between requests (seconds)")
@click.option("--timeout", "-t", default=30, type=int, help="Request timeout (seconds)")
@click.option("--data-dir", default=None, help="Data directory")
@click.option("--save", "-s", is_flag=True, help="Save crawled pages to data directory")
@click.pass_context
def crawl(ctx, urls, depth, max_pages, delay, timeout, data_dir, save):
    """Crawl web pages from the given URLs.

    Downloads and extracts content from web pages. Results can be
    saved to the data directory for later processing.

    Examples:
        personal-index crawl https://example.com
        personal-index crawl https://example.com -d 2 -m 50
        personal-index crawl https://example.com --save
    """
    if not urls:
        click.echo("Error: No URLs provided.", err=True)
        click.echo("Usage: personal-index crawl <url> [url ...]", err=True)
        sys.exit(1)

    dd = data_dir or ctx.obj.get("data_dir", ".personal_index")
    os.makedirs(dd, exist_ok=True)

    config = CrawlerConfig(
        max_depth=depth,
        max_pages=max_pages,
        delay=delay,
        timeout=timeout,
    )

    crawler = Crawler(config=config)

    try:
        click.echo(f"Crawling {len(urls)} URL(s) with depth={depth}, max_pages={max_pages}...")
        pages = crawler.crawl(list(urls))
        click.echo(f"\nCrawled {len(pages)} pages:")
        for page in pages[:20]:
            status = "OK" if page.status_code == 200 else f"HTTP {page.status_code}"
            click.echo(f"  [{status}] {page.url} ({len(page.content or '')} chars)")
        if len(pages) > 20:
            click.echo(f"  ... and {len(pages) - 20} more")

        if save:
            import json
            cache_path = os.path.join(dd, "crawl_cache.json")
            serializable = []
            for page in pages:
                d = {
                    "url": page.url,
                    "title": page.title,
                    "content": page.content,
                    "status_code": page.status_code,
                    "content_length": len(page.content or ""),
                }
                serializable.append(d)
            with open(cache_path, "w") as f:
                json.dump(serializable, f, indent=2)
            click.echo(f"\nSaved {len(pages)} pages to {cache_path}")

    except KeyboardInterrupt:
        click.echo("\nCrawl interrupted by user.")
        sys.exit(130)
    except (OSError, ValueError) as e:
        click.echo(f"\nCrawl failed: {e}", err=True)
        sys.exit(1)
