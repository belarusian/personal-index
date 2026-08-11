"""Unified pipeline CLI command for personal-index.

Provides a single command that runs the complete pipeline:
crawl → extract → filter → score → tag → index → search
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import click

from personal_index.content_filter import ContentFilter, FilterConfig
from personal_index.content_scoring import ContentScorer, ScoreWeights
from personal_index.crawler.main import Crawler, CrawlerConfig
from personal_index.index import SearchIndex
from personal_index.interests import InterestStore
from personal_index.models import CrawledPage
from personal_index.tags import TagStore


@click.command("run-pipeline")
@click.argument("sources", nargs=-1)
@click.option("--import-file", "-i", "import_files", multiple=True,
              help="Import local files instead of crawling")
@click.option("--depth", "-d", default=3, type=int, help="Max crawl depth")
@click.option("--max-pages", "-m", default=100, type=int, help="Max pages to crawl")
@click.option("--min-score", default=0.0, type=float, help="Minimum score threshold")
@click.option("--min-content-length", "-l", default=10, type=int,
              help="Minimum content length to include")
@click.option("--data-dir", default=None, help="Data directory")
@click.option("--steps", "-s", default=None,
              help="Comma-separated steps: crawl,extract,filter,score,tag,index")
@click.option("--no-crawl", is_flag=True, help="Skip crawl stage")
@click.option("--no-filter", is_flag=True, help="Skip filter stage")
@click.option("--no-score", is_flag=True, help="Skip score stage")
@click.option("--no-tag", is_flag=True, help="Skip tag stage")
@click.option("--no-index", is_flag=True, help="Skip index stage")
@click.option("--recursive", "-r", is_flag=True, help="Recursively import directories")
@click.option("--dry-run", is_flag=True, help="Show what would happen without making changes")
@click.pass_context
def run_pipeline(ctx, sources, import_files, depth, max_pages, min_score,
                 min_content_length, data_dir, steps, no_crawl, no_filter,
                 no_score, no_tag, no_index, recursive, dry_run):
    """Run the full content pipeline end-to-end.

    Processes content through all stages: crawl → extract → filter →
    score → tag → index. Works with URLs (web crawling) or local files.

    Examples:
        # Crawl and index a website
        personal-index run-pipeline https://example.com

        # Import local files
        personal-index run-pipeline --import-file ./docs/*.md

        # Run specific stages only
        personal-index run-pipeline https://example.com --steps extract,filter,score

        # Dry run to see what would happen
        personal-index run-pipeline https://example.com --dry-run
    """
    dd = data_dir or ctx.obj.get("data_dir", ".personal_index")
    os.makedirs(dd, exist_ok=True)

    # Build enabled steps
    if steps:
        enabled_steps = [s.strip() for s in steps.split(",")]
    else:
        enabled_steps = ["crawl", "extract", "filter", "score", "tag", "index"]

    if no_crawl and "crawl" in enabled_steps:
        enabled_steps.remove("crawl")
    if no_filter and "filter" in enabled_steps:
        enabled_steps.remove("filter")
    if no_score and "score" in enabled_steps:
        enabled_steps.remove("score")
    if no_tag and "tag" in enabled_steps:
        enabled_steps.remove("tag")
    if no_index and "index" in enabled_steps:
        enabled_steps.remove("index")

    click.echo(f"Pipeline stages: {', '.join(enabled_steps)}")
    if dry_run:
        click.echo("[DRY RUN] No changes will be made")

    # Initialize components
    interest_store = InterestStore(store_path=os.path.join(dd, "interests.json"))
    tag_store = TagStore(store_path=os.path.join(dd, "tags.json"))
    search_index = SearchIndex(db_path=os.path.join(dd, "search_index.json"))
    content_filter = ContentFilter(
        config=FilterConfig(
            min_content_length=min_content_length,
            require_interest_match=False,
        ),
        interest_store=interest_store,
    )
    scorer = ContentScorer(weights=ScoreWeights())

    # Collect pages
    pages: list[CrawledPage] = []

    if "crawl" in enabled_steps:
        if not sources:
            click.echo("Error: URLs required when crawl stage is enabled.", err=True)
            sys.exit(1)
        click.echo(f"Crawling {len(sources)} URL(s)...")
        crawler = Crawler(
            config=CrawlerConfig(
                max_depth=depth,
                max_pages=max_pages,
                delay=0.5,
                timeout=30,
            ),
            interest_store=interest_store,
        )
        pages = crawler.crawl(list(sources))
        crawler.close()
        click.echo(f"Crawled {len(pages)} pages")
    elif import_files:
        # Import local files
        expanded_files = []
        for f in import_files:
            if os.path.isdir(f) and recursive:
                for root, dirs, files in os.walk(f):
                    for filename in files:
                        filepath = os.path.join(root, filename)
                        if filepath.endswith(('.txt', '.md', '.html', '.htm', '.json', '.xml', '.rst')):
                            expanded_files.append(filepath)
            else:
                expanded_files.append(f)
        click.echo(f"Importing {len(expanded_files)} file(s)...")
        for filepath in expanded_files:
            try:
                with open(filepath, "r", encoding="utf-8", errors="replace") as fh:
                    content = fh.read()
                page = CrawledPage(
                    url=filepath,
                    title=Path(filepath).stem,
                    content=content,
                )
                pages.append(page)
            except OSError as e:
                click.echo(f"  Warning: Could not read {filepath}: {e}", err=True)
        click.echo(f"Imported {len(pages)} pages")
    elif sources:
        # Treat sources as file paths if they look like files
        for source in sources:
            if os.path.isfile(source):
                try:
                    with open(source, "r", encoding="utf-8", errors="replace") as fh:
                        content = fh.read()
                    page = CrawledPage(
                        url=source,
                        title=Path(source).stem,
                        content=content,
                    )
                    pages.append(page)
                except OSError as e:
                    click.echo(f"  Warning: Could not read {source}: {e}", err=True)
        click.echo(f"Loaded {len(pages)} pages from files")
    else:
        click.echo("Error: No sources provided. Use URLs or --import-file.", err=True)
        sys.exit(1)

    if not pages:
        click.echo("No pages to process.")
        return

    # Stage: Extract
    if "extract" in enabled_steps:
        from personal_index.content_extractor import ContentExtractor
        extractor = ContentExtractor()
        extracted = 0
        for page in pages:
            if page.raw_html:
                ext = extractor.extract(page.raw_html)
                if ext.title:
                    page.title = ext.title
                if ext.text:
                    page.content = ext.text
                page.word_count = ext.word_count
                extracted += 1
        click.echo(f"Extracted content from {extracted} pages")

    # Stage: Filter
    if "filter" in enabled_steps:
        before = len(pages)
        pages = [p for p in pages if content_filter.should_include(p)]
        filtered_out = before - len(pages)
        click.echo(f"Filtered: {before} → {len(pages)} ({filtered_out} removed)")

    if not pages:
        click.echo("All pages filtered out. Nothing to index.")
        return

    # Stage: Score
    if "score" in enabled_steps:
        for page in pages:
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
                word_count=len((page.content or "").split()),
                domain_authority=0.5,
            )
            page.relevance_score = score_result.total
            page.matched_interests = list(set(matched_interests))
        click.echo(f"Scored {len(pages)} pages")

    # Stage: Tag
    if "tag" in enabled_steps:
        tags_applied = 0
        for page in pages:
            tags = set()
            url_lower = page.url.lower()
            content_lower = (page.content or "").lower()
            title_lower = (page.title or "").lower()
            combined = f"{title_lower} {content_lower}"

            # Auto-tags from URL
            if "blog" in url_lower:
                tags.add("blog")
            if "api" in url_lower:
                tags.add("api")
            if "docs" in url_lower or "documentation" in url_lower:
                tags.add("documentation")
            if "github" in url_lower:
                tags.add("github")

            # Auto-tags from content keywords
            common_tags = {
                "python": "python",
                "javascript": "javascript",
                "tutorial": "tutorial",
                "guide": "guide",
                "reference": "reference",
                "news": "news",
                "review": "review",
            }
            for keyword, tag_name in common_tags.items():
                if keyword in combined:
                    tags.add(tag_name)

            # Tags from matched interests
            if page.matched_interests:
                for mi in page.matched_interests:
                    tags.add(mi)

            for tag_name in tags:
                tag_store.add_tag_to_page(page.url, tag_name)
                tags_applied += 1
        click.echo(f"Applied {tags_applied} tags to {len(pages)} pages")

    # Stage: Index
    if "index" in enabled_steps:
        if dry_run:
            click.echo(f"[DRY RUN] Would index {len(pages)} pages")
        else:
            indexed = 0
            for page in pages:
                try:
                    search_index.add_page(page)
                    indexed += 1
                except (OSError, ValueError) as e:
                    click.echo(f"  Warning: Could not index {page.url}: {e}", err=True)
            click.echo(f"Indexed {indexed}/{len(pages)} pages")

    # Final summary
    click.echo("")
    click.echo("=" * 50)
    click.echo("Pipeline Complete")
    click.echo("=" * 50)
    click.echo(f"  Pages processed: {len(pages)}")
    click.echo(f"  Pages indexed:   {search_index.get_page_count()}")
    click.echo(f"  Total tags:      {tag_store.get_tag_count()}")
    click.echo(f"  Interests:       {len(interest_store.list_all())}")
    click.echo("=" * 50)

    # Save stores
    tag_store._save()
    interest_store._save()
    search_index._save()
