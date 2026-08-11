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


@main.command()
@click.option("--data-dir", default=None, help="Data directory")
@click.option("--config", default=None, help="Config file path")
@click.pass_context
def init(ctx, data_dir, config):
    """Initialize a new personal-index project.

    Creates the data directory and a default configuration file.

    Examples:
        personal-index init
        personal-index init --data-dir ~/my-index
    """
    dd = data_dir or ctx.obj.get("data_dir", ".personal_index")
    os.makedirs(dd, exist_ok=True)

    config_path = config or "config.yaml"
    if not os.path.exists(config_path):
        default_config = {
            "data_dir": dd,
            "crawler": {
                "max_depth": 3,
                "politeness_delay": 1.0,
                "rate_limit": 10,
                "timeout": 30,
                "max_pages": 100,
            },
            "pipeline": {
                "enabled": True,
                "min_score_threshold": 0.0,
                "min_content_length": 100,
            },
            "scheduler": {
                "enabled": False,
                "interval_hours": 24,
            },
        }
        with open(config_path, "w") as f:
            yaml.dump(default_config, f, default_flow_style=False)
        click.echo(f"Created {config_path}")
    else:
        click.echo(f"Config file already exists at {config_path}")

    # Create data directory structure
    for subdir in ["cache", "archive", "backups"]:
        os.makedirs(os.path.join(dd, subdir), exist_ok=True)

    click.echo(f"Initialized personal-index in {dd}")
    click.echo("Next steps:")
    click.echo("  1. Add interests: personal-index interests add mytopic -k keyword1 -k keyword2")
    click.echo("  2. Run pipeline: personal-index pipeline https://example.com")
    click.echo("  3. Search: personal-index search 'query'")


@main.command()
@click.argument("url", required=False)
@click.option("-d", "--depth", default=3, type=int, help="Max crawl depth")
@click.option("--data-dir", default=None, help="Data directory")
@click.option("--timeout", default=30, type=int, help="Request timeout in seconds")
@click.option("--delay", default=1.0, type=float, help="Delay between requests")
@click.option("--max-pages", default=100, type=int, help="Maximum pages to crawl")
@click.pass_context
def crawl(ctx, url, depth, data_dir, timeout, delay, max_pages):
    """Crawl a URL and its linked pages.

    Crawls the given URL and follows links up to the specified depth.
    Results are stored in the data directory for later processing.

    Examples:
        personal-index crawl https://example.com
        personal-index crawl https://example.com -d 2 --max-pages 50
    """
    dd = data_dir or ctx.obj.get("data_dir", ".personal_index")

    if not url:
        click.echo("Error: URL is required for crawl command.", err=True)
        click.echo("Usage: personal-index crawl <URL>", err=True)
        sys.exit(1)

    from personal_index.crawler.main import Crawler, CrawlerConfig
    from personal_index.interests import InterestStore

    interest_store = InterestStore(store_path=os.path.join(dd, "interests.json"))
    config = CrawlerConfig(
        max_depth=depth,
        delay=delay,
        timeout=timeout,
        max_pages=max_pages,
    )

    click.echo(f"Crawling {url} (depth={depth}, max_pages={max_pages})...")
    crawler = Crawler(config=config, interest_store=interest_store)
    try:
        pages = crawler.crawl([url], max_depth=depth)
        click.echo(f"Crawled {len(pages)} pages")

        # Save crawled pages
        pages_path = os.path.join(dd, "crawled_pages.json")
        pages_data = []
        for page in pages:
            pages_data.append({
                "url": page.url,
                "title": page.title,
                "content": page.content,
                "matched_interests": page.matched_interests or [],
            })
        with open(pages_path, "w") as f:
            json.dump(pages_data, f, indent=2)
        click.echo(f"Saved to {pages_path}")
    except (OSError, ValueError) as e:
        click.echo(f"Crawl error: {e}", err=True)
        sys.exit(1)
    finally:
        crawler.close()


@main.command()
@click.argument("query")
@click.option("--limit", "-n", default=20, type=int, help="Max results")
@click.option("--tag", default=None, help="Filter by tag")
@click.option("--data-dir", default=None, help="Data directory")
@click.option("--format", "-f", "fmt", type=click.Choice(["text", "json", "csv"]), default="text", help="Output format")
@click.pass_context
def search(ctx, query, limit, tag, data_dir, fmt):
    """Search the indexed content.

    Searches through all indexed pages for the given query.
    Results are ranked by relevance score.

    Examples:
        personal-index search "python tutorial"
        personal-index search "javascript" --limit 10
        personal-index search "web development" --tag tutorial
    """
    dd = data_dir or ctx.obj.get("data_dir", ".personal_index")
    idx = get_search_index(dd)
    tag_store = get_tag_store(dd)

    if idx.get_page_count() == 0:
        click.echo("No indexed content found. Run 'personal-index pipeline' first.")
        return

    results = idx.search(query, limit=limit)

    # Apply tag filter if specified
    if tag:
        tagged_urls = tag_store.get_pages_for_tag(tag)
        results = [r for r in results if r.url in tagged_urls]

    # Output results
    if fmt == "json":
        data = {
            "results": [
                {
                    "url": r.url,
                    "title": r.title,
                    "snippet": r.snippet,
                    "relevance_score": r.relevance_score,
                }
                for r in results
            ],
            "total": len(results),
        }
        click.echo(json.dumps(data, indent=2))
    elif fmt == "csv":
        import csv as _csv
        import io as _io
        output = _io.StringIO()
        writer = _csv.writer(output)
        writer.writerow(["rank", "title", "url", "score", "snippet"])
        for i, r in enumerate(results, 1):
            writer.writerow([i, r.title, r.url, f"{r.relevance_score:.4f}", r.snippet[:200]])
        click.echo(output.getvalue().strip())
    else:
        if not results:
            click.echo(f"No results found for '{query}'")
            return

        click.echo(f"\nSearch results for '{query}' ({len(results)} found):")
        click.echo("-" * 60)

        for i, result in enumerate(results, 1):
            click.echo(f"\n{i}. {result.title}")
            click.echo(f"   {result.url}")
            click.echo(f"   Score: {result.relevance_score:.4f}")
            if result.snippet:
                click.echo(f"   {result.snippet[:200]}")


# Interest management commands
@main.group()
@click.pass_context
def interests(ctx):
    """Manage your content interests.

    Define topics and keywords you want to track.

    Examples:
        personal-index interests add programming -k python -k javascript
        personal-index interests list
        personal-index interests remove programming
    """


@interests.command("add")
@click.option("-n", "--name", required=True, help="Interest name")
@click.option("-k", "--keyword", "keywords", multiple=True, help="Keywords to track")
@click.option("-p", "--priority", default=5, type=int, help="Priority (1-10)")
@click.option("--data-dir", default=None, help="Data directory")
@click.pass_context
def interests_add(ctx, name, keywords, priority, data_dir):
    """Add a new interest to track."""
    dd = data_dir or ctx.obj.get("data_dir", ".personal_index")
    store = get_interest_store(dd)

    from personal_index.models import Interest
    interest = Interest(
        name=name,
        keywords=list(keywords),
        priority=priority,
    )
    store.add(interest)

    click.echo(f"Added interest: {name}")


@interests.command("list")
@click.option("--data-dir", default=None, help="Data directory")
@click.pass_context
def interests_list(ctx, data_dir):
    """List all tracked interests."""
    dd = data_dir or ctx.obj.get("data_dir", ".personal_index")
    store = get_interest_store(dd)

    all_interests = store.list_all()
    if not all_interests:
        click.echo("No interests configured. Add one with 'personal-index interests add'")
        return

    click.echo(f"Interests ({len(all_interests)}):")
    for interest in all_interests:
        kws = ", ".join(interest.keywords) if interest.keywords else "(none)"
        click.echo(f"  {interest.name}: priority={interest.priority}, keywords=[{kws}]")


@interests.command("remove")
@click.argument("name")
@click.option("--data-dir", default=None, help="Data directory")
@click.pass_context
def interests_remove(ctx, name, data_dir):
    """Remove an interest."""
    dd = data_dir or ctx.obj.get("data_dir", ".personal_index")
    store = get_interest_store(dd)

    if store.remove(name):
        click.echo(f"Removed interest '{name}'")
    else:
        click.echo(f"Interest '{name}' not found", err=True)
        sys.exit(1)


# Tag management commands
@main.group()
@click.pass_context
def tags(ctx):
    """Manage content tags.

    Tag indexed content for easier filtering and organization.

    Examples:
        personal-index tags add important https://example.com/page
        personal-index tags list
        personal-index tags remove important https://example.com/page
    """


@tags.command("add")
@click.argument("tag_name")
@click.argument("url")
@click.option("--data-dir", default=None, help="Data directory")
@click.pass_context
def tags_add(ctx, tag_name, url, data_dir):
    """Add a tag to a page."""
    dd = data_dir or ctx.obj.get("data_dir", ".personal_index")
    store = get_tag_store(dd)
    store.add_tag_to_page(url, tag_name)
    click.echo(f"Added tag '{tag_name}' to {url}")


@tags.command("list")
@click.option("--data-dir", default=None, help="Data directory")
@click.pass_context
def tags_list(ctx, data_dir):
    """List all tags."""
    dd = data_dir or ctx.obj.get("data_dir", ".personal_index")
    store = get_tag_store(dd)

    tag_names = store.list_tags()
    if not tag_names:
        click.echo("No tags found.")
        return

    click.echo(f"Tags ({len(tag_names)}):")
    for tag in sorted(tag_names):
        pages = store.get_pages_for_tag(tag)
        click.echo(f"  {tag}: {len(pages)} page(s)")


@tags.command("remove")
@click.argument("tag_name")
@click.argument("url")
@click.option("--data-dir", default=None, help="Data directory")
@click.pass_context
def tags_remove(ctx, tag_name, url, data_dir):
    """Remove a tag from a page."""
    dd = data_dir or ctx.obj.get("data_dir", ".personal_index")
    store = get_tag_store(dd)
    store.remove_tag_from_page(url, tag_name)
    click.echo(f"Removed tag '{tag_name}' from {url}")


# Import command - use 'import_' to avoid Python keyword conflict
@main.command("import")
@click.argument("source", required=True)
@click.option("-r", "--recursive", is_flag=True, help="Recursively import directories")
@click.option("--data-dir", default=None, help="Data directory")
@click.pass_context
def import_(ctx, source, recursive, data_dir):
    """Import content from files or directories.

    Supports text files, HTML files, and JSON files.
    Imported content is automatically scored, tagged, and indexed.

    Examples:
        personal-index import article.txt
        personal-index import ./articles/ --recursive
    """
    dd = data_dir or ctx.obj.get("data_dir", ".personal_index")
    idx = get_search_index(dd)
    tag_store = get_tag_store(dd)
    interest_store = get_interest_store(dd)

    from personal_index.content_filter import ContentFilter, FilterConfig
    from personal_index.content_scoring import ContentScorer, ScoreWeights
    from personal_index.models import CrawledPage

    scorer = ContentScorer(weights=ScoreWeights())
    content_filter = ContentFilter(config=FilterConfig(min_content_length=10))

    def _import_single_file(filepath: str) -> int:
        """Import a single file through the full pipeline."""
        try:
            with open(filepath, "r", errors="replace") as f:
                content = f.read()

            page = CrawledPage(
                url=filepath,
                title=os.path.basename(filepath),
                content=content,
            )

            # Filter
            if not content_filter.should_include(page):
                click.echo(f"  Filtered out: {filepath}")
                return 0

            # Score
            word_count = len(content.split())
            keyword_matches = 0
            total_keywords = 0
            matched_interests = []
            for interest in interest_store.list_all():
                for kw in interest.keywords:
                    total_keywords += 1
                    if kw.lower() in content.lower():
                        keyword_matches += 1
                        matched_interests.append(interest.name)
            score_result = scorer.score(
                keyword_matches=keyword_matches,
                total_keywords=max(total_keywords, 1),
                word_count=word_count,
                domain_authority=0.5,
            )
            score = score_result.total if hasattr(score_result, "total") else 0.0
            page.relevance_score = score
            page.matched_interests = matched_interests

            # Tag
            for interest_name in set(matched_interests):
                tag_store.add_tag_to_page(filepath, interest_name)

            # Index
            idx.add_page(page)
            click.echo(f"  Imported: {filepath} (score={score:.4f})")
            return 1
        except (OSError, ValueError) as e:
            click.echo(f"  Error importing {filepath}: {e}")
            return 0

    if os.path.isdir(source):
        if recursive:
            import pathlib
            files = list(pathlib.Path(source).rglob("*"))
            files = [f for f in files if f.is_file()]
        else:
            import pathlib
            files = list(pathlib.Path(source).iterdir())
            files = [f for f in files if f.is_file()]

        click.echo(f"Importing {len(files)} files from {source}...")
        total = 0
        for f in files:
            total += _import_single_file(str(f))
        click.echo(f"Imported {total}/{len(files)} files")
    else:
        total = _import_single_file(source)
        if total > 0:
            click.echo(f"Import complete: {total} file(s) processed")
        else:
            click.echo("Import failed: no files were processed")


# Status command
@main.command()
@click.option("--data-dir", default=None, help="Data directory")
@click.pass_context
def status(ctx, data_dir):
    """Show the current status of the index.

    Displays statistics about indexed content, tags, and interests.

    Examples:
        personal-index status
    """
    dd = data_dir or ctx.obj.get("data_dir", ".personal_index")
    idx = get_search_index(dd)
    tag_store = get_tag_store(dd)
    interest_store = get_interest_store(dd)

    click.echo("Personal Index Status")
    click.echo("=" * 40)
    click.echo(f"Data directory: {dd}")
    click.echo(f"Indexed pages: {idx.get_page_count()}")
    click.echo(f"Tags: {tag_store.get_tag_count()}")
    click.echo(f"Interests: {len(interest_store.list_all())}")

    # Show top pages by score
    pages = idx.list_pages()
    if pages:
        click.echo("\nTop pages by score:")
        for page in pages[:5]:
            click.echo(f"  {page.title} ({page.url}) - score: {page.score:.4f}")


# Reset command
@main.command()
@click.option("--data-dir", default=None, help="Data directory")
@click.pass_context
def reset(ctx, data_dir):
    """Reset the index, clearing all data.

    WARNING: This deletes all indexed content, tags, and cached data.
    Your config.yaml and interests are preserved.

    Examples:
        personal-index reset
    """
    dd = data_dir or ctx.obj.get("data_dir", ".personal_index")

    files_to_remove = [
        os.path.join(dd, "search_index.json"),
        os.path.join(dd, "tags.json"),
        os.path.join(dd, "crawled_pages.json"),
    ]

    dirs_to_remove = [
        os.path.join(dd, "cache"),
        os.path.join(dd, "archive"),
    ]

    for f in files_to_remove:
        if os.path.exists(f):
            os.remove(f)
            click.echo(f"Removed {f}")

    for d in dirs_to_remove:
        if os.path.exists(d):
            shutil.rmtree(d)
            click.echo(f"Removed {d}")

    click.echo("Index reset complete.")


# Validate command
@main.command()
@click.option("--data-dir", default=None, help="Data directory")
@click.pass_context
def validate(ctx, data_dir):
    """Validate the index data integrity.

    Checks for corrupted data files and consistency issues.

    Examples:
        personal-index validate
    """
    dd = data_dir or ctx.obj.get("data_dir", ".personal_index")
    idx = get_search_index(dd)
    tag_store = get_tag_store(dd)

    errors = []
    warnings = []

    # Check index consistency
    indexed_urls = set(idx._pages.keys())
    indexed_words = set(idx._word_index.keys())

    # Check for orphaned tags
    all_tagged_urls = set(tag_store._page_tags.keys())
    orphaned = all_tagged_urls - indexed_urls
    if orphaned:
        warnings.append(f"{len(orphaned)} tagged URLs not in index (orphaned tags)")

    # Check for missing tags
    if indexed_urls and not all_tagged_urls:
        warnings.append("No tags found for indexed pages")

    # Check index file
    if idx.db_path and os.path.exists(idx.db_path):
        try:
            with open(idx.db_path) as f:
                json.load(f)
        except json.JSONDecodeError:
            errors.append("Corrupted search index file")

    # Check tag file
    if tag_store.store_path and os.path.exists(tag_store.store_path):
        try:
            with open(tag_store.store_path) as f:
                json.load(f)
        except json.JSONDecodeError:
            errors.append("Corrupted tags file")

    click.echo("Validation Results")
    click.echo("=" * 40)
    click.echo(f"Indexed pages: {len(indexed_urls)}")
    click.echo(f"Indexed words: {len(indexed_words)}")
    click.echo(f"Tags: {tag_store.get_tag_count()}")
    click.echo(f"Tagged pages: {len(all_tagged_urls)}")

    if errors:
        click.echo(f"\nErrors ({len(errors)}):")
        for e in errors:
            click.echo(f"  ✗ {e}")
    else:
        click.echo("\n✓ No errors found")

    if warnings:
        click.echo(f"\nWarnings ({len(warnings)}):")
        for w in warnings:
            click.echo(f"  ⚠ {w}")

    if errors:
        sys.exit(1)


# Reindex command
@main.command()
@click.option("--data-dir", default=None, help="Data directory")
@click.pass_context
def reindex(ctx, data_dir):
    """Rebuild the search index from existing crawled pages.

    Useful after updating interests or scoring weights.

    Examples:
        personal-index reindex
    """
    dd = data_dir or ctx.obj.get("data_dir", ".personal_index")
    idx = get_search_index(dd)
    tag_store = get_tag_store(dd)
    interest_store = get_interest_store(dd)

    from personal_index.content_filter import ContentFilter, FilterConfig
    from personal_index.content_scoring import ContentScorer, ScoreWeights

    scorer = ContentScorer(weights=ScoreWeights())
    content_filter = ContentFilter(config=FilterConfig(min_content_length=10))

    # Clear existing index
    idx.clear()
    tag_store.clear()

    # Re-process all existing pages
    pages_path = os.path.join(dd, "crawled_pages.json")
    if not os.path.exists(pages_path):
        click.echo("No crawled pages found. Run 'personal-index pipeline' first.")
        return

    with open(pages_path, "r") as f:
        pages_data = json.load(f)

    from personal_index.models import CrawledPage

    reindexed = 0
    for pd in pages_data:
        page = CrawledPage(
            url=pd["url"],
            title=pd.get("title", ""),
            content=pd.get("content", ""),
        )

        if not content_filter.should_include(page):
            continue

        word_count = len((page.content or "").split())
        keyword_matches = 0
        total_keywords = 0
        matched_interests = []
        for interest in interest_store.list_all():
            for kw in interest.keywords:
                total_keywords += 1
                if kw.lower() in (page.content or "").lower():
                    keyword_matches += 1
                    matched_interests.append(interest.name)
        score_result = scorer.score(
            keyword_matches=keyword_matches,
            total_keywords=max(total_keywords, 1),
            word_count=word_count,
            domain_authority=0.5,
        )
        score = score_result.total if hasattr(score_result, "total") else 0.0
        page.relevance_score = score
        page.matched_interests = matched_interests

        for interest_name in set(matched_interests):
            tag_store.add_tag_to_page(page.url, interest_name)

        idx.add_page(page)
        reindexed += 1

    click.echo(f"Reindexed {reindexed} pages")


# Export command
@main.command()
@click.option("--format", "-f", "fmt", type=click.Choice(["text", "json", "markdown", "csv"]), default="text", help="Export format")
@click.option("--output", "-o", default=None, help="Output file path")
@click.option("--data-dir", default=None, help="Data directory")
@click.pass_context
def export(ctx, fmt, output, data_dir):
    """Export indexed content.

    Exports all indexed pages in the specified format.

    Examples:
        personal-index export --format json
        personal-index export --format markdown -o results.md
    """
    dd = data_dir or ctx.obj.get("data_dir", ".personal_index")
    idx = get_search_index(dd)
    tag_store = get_tag_store(dd)

    pages = idx.list_pages()
    if not pages:
        click.echo("No indexed content to export.")
        return

    if fmt == "json":
        data = {
            "pages": [
                {
                    "url": p.url,
                    "title": p.title,
                    "content": p.content[:500] if p.content else "",
                    "score": p.score,
                    "tags": [t.name if hasattr(t, "name") else str(t) for t in tag_store.get_tags_for_page(p.url)],
                }
                for p in pages
            ],
            "total": len(pages),
        }
        output_text = json.dumps(data, indent=2)
    elif fmt == "markdown":
        lines = ["# Search Results", ""]
        for p in pages:
            tags = tag_store.get_tags_for_page(p.url)
            tag_names = [t.name if hasattr(t, "name") else str(t) for t in tags]
            tag_str = f" [{', '.join(tag_names)}]" if tag_names else ""
            lines.append(f"## {p.title}{tag_str}")
            lines.append(f"**URL:** {p.url}")
            lines.append(f"**Score:** {p.score:.4f}")
            if p.content:
                lines.append(f"\n{p.content[:500]}")
            lines.append("")
        output_text = "\n".join(lines)
    elif fmt == "csv":
        import csv
        import io
        buf = io.StringIO()
        writer = csv.writer(buf)
        writer.writerow(["url", "title", "score", "tags", "content_preview"])
        for p in pages:
            tags = tag_store.get_tags_for_page(p.url)
            tag_names = [t.name if hasattr(t, "name") else str(t) for t in tags]
            writer.writerow([
                p.url, p.title, f"{p.score:.4f}",
                ";".join(tag_names), (p.content or "")[:200]
            ])
        output_text = buf.getvalue()
    else:
        lines = [f"Indexed Pages ({len(pages)})", "=" * 40]
        for p in pages:
            tags = tag_store.get_tags_for_page(p.url)
            tag_names = [t.name if hasattr(t, "name") else str(t) for t in tags]
            tag_str = f" [{', '.join(tag_names)}]" if tag_names else ""
            lines.append(f"\n{p.title}{tag_str}")
            lines.append(f"  URL: {p.url}")
            lines.append(f"  Score: {p.score:.4f}")
        output_text = "\n".join(lines)

    if output:
        with open(output, "w") as f:
            f.write(output_text)
        click.echo(f"Exported to {output}")
    else:
        click.echo(output_text)


# Config management commands
@main.group()
@click.pass_context
def config(ctx):
    """Manage configuration settings.

    Examples:
        personal-index config show
        personal-index config set-crawler --max-depth 5
        personal-index config set-schedule --interval 12
    """


@config.command("show")
@click.option("--data-dir", default=None, help="Data directory")
@click.pass_context
def config_show(ctx, data_dir):
    """Show current configuration."""
    dd = data_dir or ctx.obj.get("data_dir", ".personal_index")
    config_path = "config.yaml"
    if os.path.exists(config_path):
        with open(config_path, "r") as f:
            data = yaml.safe_load(f) or {}
        click.echo("Current configuration:")
        click.echo(f"  Data dir: {data.get('data_dir', dd)}")
        crawler = data.get("crawler", {})
        click.echo(f"  Max depth: {crawler.get('max_depth', 3)}")
        click.echo(f"  Politeness delay: {crawler.get('politeness_delay', 1.0)}s")
        click.echo(f"  Rate limit: {crawler.get('rate_limit', 10)}/s")
        scheduler = data.get("scheduler", {})
        click.echo(f"  Scheduler enabled: {scheduler.get('enabled', False)}")
        click.echo(f"  Interval: {scheduler.get('interval_hours', 24)}h")
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

main.add_command(pipeline)

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
        warnings.append("No config.yaml found. Run 'personal-index init' for defaults.")

    # Check index
    idx = get_search_index(dd)
    if idx.get_page_count() == 0:
        warnings.append("Index is empty. Run 'personal-index pipeline' to add content.")

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
