"""Import CLI command for personal-index."""

from __future__ import annotations

import os
import sys
from pathlib import Path

import click

from personal_index.index import SearchIndex
from personal_index.interests import InterestStore
from personal_index.models import CrawledPage
from personal_index.tags import TagStore
from personal_index.content_filter import ContentFilter, FilterConfig
from personal_index.content_scoring import ContentScorer, ScoreWeights
from personal_index.content_extractor import ContentExtractor


SUPPORTED_EXTENSIONS = {
    '.txt', '.md', '.html', '.htm', '.json', '.xml', '.rst',
    '.adoc', '.org', '.tex', '.csv', '.log',
}


@click.command("import")
@click.argument("source")
@click.option("--recursive", "-r", is_flag=True, help="Recursively import directories")
@click.option("--data-dir", default=None, help="Data directory")
@click.option("--min-content-length", "-l", default=10, type=int,
              help="Minimum content length to include")
@click.option("--skip-filter", is_flag=True, help="Skip content filtering")
@click.option("--skip-score", is_flag=True, help="Skip scoring")
@click.option("--skip-tag", is_flag=True, help="Skip auto-tagging")
@click.option("--force", "-f", is_flag=True, help="Force re-import even if already indexed")
@click.pass_context
def import_cmd(ctx, source, recursive, data_dir, min_content_length,
               skip_filter, skip_score, skip_tag, force):
    """Import local files into the index.

    Imports text files, markdown, HTML, and other supported formats
    into the search index. Supports recursive directory imports.

    Supported formats: .txt, .md, .html, .htm, .json, .xml, .rst,
                       .adoc, .org, .tex, .csv, .log

    Examples:
        personal-index import ./article.txt
        personal-index import ./docs --recursive
        personal-index import ./content --recursive --min-content-length 50
    """
    dd = data_dir or ctx.obj.get("data_dir", ".personal_index")
    os.makedirs(dd, exist_ok=True)

    # Initialize components
    search_index = SearchIndex(db_path=os.path.join(dd, "search_index.json"))
    tag_store = TagStore(store_path=os.path.join(dd, "tags.json"))
    interest_store = InterestStore(store_path=os.path.join(dd, "interests.json"))
    content_filter = ContentFilter(
        config=FilterConfig(min_content_length=min_content_length),
        interest_store=interest_store,
    )
    scorer = ContentScorer(weights=ScoreWeights())
    extractor = ContentExtractor()

    # Collect files to import
    files_to_import = []
    if os.path.isfile(source):
        files_to_import.append(source)
    elif os.path.isdir(source):
        if recursive:
            for root, dirs, files in os.walk(source):
                for f in files:
                    fp = os.path.join(root, f)
                    if Path(fp).suffix.lower() in SUPPORTED_EXTENSIONS:
                        files_to_import.append(fp)
        else:
            for f in os.listdir(source):
                fp = os.path.join(source, f)
                if os.path.isfile(fp) and Path(fp).suffix.lower() in SUPPORTED_EXTENSIONS:
                    files_to_import.append(fp)
    else:
        click.echo(f"Error: '{source}' is not a file or directory.", err=True)
        sys.exit(1)

    if not files_to_import:
        click.echo(f"No supported files found in '{source}'.")
        click.echo(f"Supported extensions: {', '.join(sorted(SUPPORTED_EXTENSIONS))}")
        return

    click.echo(f"Importing {len(files_to_import)} file(s)...")

    imported = 0
    skipped = 0
    errors = 0

    for filepath in files_to_import:
        try:
            # Check if already indexed
            existing = search_index.get_page(filepath)
            if existing and not force:
                click.echo(f"  ⊘ {filepath} (already indexed)")
                skipped += 1
                continue

            # Read file content
            with open(filepath, "r", encoding="utf-8", errors="replace") as f:
                raw_content = f.read()

            # Extract content from HTML
            if filepath.endswith(('.html', '.htm')):
                extracted = extractor.extract(raw_content)
                title = extracted.title or Path(filepath).stem
                content = extracted.text or raw_content
            else:
                title = Path(filepath).stem
                content = raw_content

            page = CrawledPage(
                url=filepath,
                title=title,
                content=content,
                word_count=len(content.split()),
            )

            # Filter
            if not skip_filter and not content_filter.should_include(page):
                click.echo(f"  ✗ {filepath} (filtered out)")
                skipped += 1
                continue

            # Score
            if not skip_score:
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
                    word_count=page.word_count,
                    domain_authority=0.5,
                )
                page.relevance_score = score_result.total
                page.matched_interests = list(set(matched_interests))

            # Auto-tag
            if not skip_tag:
                tags = set()
                ext = Path(filepath).suffix.lower()
                if ext == '.md':
                    tags.add('markdown')
                elif ext in ('.html', '.htm'):
                    tags.add('html')
                elif ext == '.txt':
                    tags.add('text')

                # Content-based tags
                content_lower = content.lower()
                for keyword, tag_name in {
                    'python': 'python', 'javascript': 'javascript',
                    'tutorial': 'tutorial', 'guide': 'guide',
                    'reference': 'reference', 'api': 'api',
                }.items():
                    if keyword in content_lower:
                        tags.add(tag_name)

                for tag_name in tags:
                    tag_store.add_tag_to_page(filepath, tag_name)

            # Index
            search_index.add_page(page)
            click.echo(f"  ✓ {filepath}")
            imported += 1

        except OSError as e:
            click.echo(f"  ✗ {filepath}: {e}", err=True)
            errors += 1
        except Exception as e:
            click.echo(f"  ✗ {filepath}: {e}", err=True)
            errors += 1

    # Summary
    click.echo(f"\nImport complete:")
    click.echo(f"  Imported: {imported}")
    click.echo(f"  Skipped:  {skipped}")
    click.echo(f"  Errors:   {errors}")

    # Save
    tag_store._save()
    search_index._save()
