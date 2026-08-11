"""Verify CLI command for personal-index pipeline validation."""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

import click

from personal_index.config.pipeline_config import PipelineConfig
from personal_index.content_filter import ContentFilter, FilterConfig
from personal_index.content_scoring import ContentScorer, ScoreWeights
from personal_index.index import SearchIndex
from personal_index.interests import InterestStore
from personal_index.models import CrawledPage, Interest
from personal_index.tags import TagStore


@click.command("verify")
@click.option("--data-dir", default=None, help="Data directory")
@click.option("--quick", "-q", is_flag=True, help="Quick verification (skip full pipeline test)")
@click.pass_context
def verify(ctx, data_dir, quick):
    """Verify that the personal-index pipeline works end-to-end.

    Runs a self-test that creates temporary content and processes it
    through all pipeline stages to verify everything is working.

    Examples:
        personal-index verify
        personal-index verify --quick
    """
    dd = data_dir or ctx.obj.get("data_dir", ".personal_index")
    os.makedirs(dd, exist_ok=True)

    click.echo("Verifying personal-index pipeline...")
    click.echo("=" * 50)

    errors = []
    checks_passed = 0
    checks_total = 0

    def check(name: str, condition: bool, detail: str = "") -> None:
        nonlocal checks_passed, checks_total
        checks_total += 1
        if condition:
            checks_passed += 1
            click.echo(f"  ✓ {name}")
        else:
            errors.append(f"✗ {name}: {detail}")
            click.echo(f"  ✗ {name}: {detail}")

    # Check 1: Data directory writable
    test_file = os.path.join(dd, ".verify_test")
    try:
        with open(test_file, "w") as f:
            f.write("test")
        os.remove(test_file)
        check("Data directory is writable", True)
    except OSError as e:
        check("Data directory is writable", False, str(e))

    # Check 2: Interest store works
    try:
        interest_store = InterestStore(store_path=os.path.join(dd, "verify_interests.json"))
        interest_store.add(Interest(name="verify_test", keywords=["verify"]))
        interests = interest_store.list_all()
        check("Interest store works", len(interests) > 0, "Could not store interests")
        interest_store._interests.clear()
        interest_store._save()
    except Exception as e:
        check("Interest store works", False, str(e))

    # Check 3: Tag store works
    try:
        tag_store = TagStore(store_path=os.path.join(dd, "verify_tags.json"))
        tag_store.add_tag_to_page("http://test.com", "verify")
        tags = tag_store.get_tags_for_page("http://test.com")
        check("Tag store works", "verify" in tags, "Could not store tags")
        tag_store._page_tags.clear()
        tag_store._save()
    except Exception as e:
        check("Tag store works", False, str(e))

    # Check 4: Search index works
    try:
        search_index = SearchIndex(db_path=os.path.join(dd, "verify_index.json"))
        test_page = CrawledPage(
            url="http://verify.test/page1",
            title="Verify Test Page",
            content="This is a verification test page for the pipeline.",
        )
        search_index.add_page(test_page)
        results = search_index.search("verification")
        check("Search index works", len(results) > 0, "Could not search index")
        search_index.remove_page("http://verify.test/page1")
        search_index._save()
    except Exception as e:
        check("Search index works", False, str(e))

    # Check 5: Content filter works
    try:
        content_filter = ContentFilter(config=FilterConfig(min_content_length=10))
        test_page = CrawledPage(
            url="http://test.com",
            title="Test",
            content="This is test content for verification.",
        )
        included = content_filter.should_include(test_page)
        check("Content filter works", included, "Filter rejected valid content")
    except Exception as e:
        check("Content filter works", False, str(e))

    # Check 6: Content scorer works
    try:
        scorer = ContentScorer(weights=ScoreWeights())
        score = scorer.score(
            keyword_matches=1,
            total_keywords=2,
            word_count=10,
            domain_authority=0.5,
        )
        check("Content scorer works", score.total >= 0, "Scorer returned invalid score")
    except Exception as e:
        check("Content scorer works", False, str(e))

    # Full pipeline test (skip with --quick)
    if not quick:
        click.echo("\nRunning full pipeline self-test...")
        try:
            test_data_dir = os.path.join(dd, ".verify_pipeline")
            os.makedirs(test_data_dir, exist_ok=True)

            # Create test file
            test_file_path = os.path.join(test_data_dir, "test_article.txt")
            with open(test_file_path, "w") as f:
                f.write(
                    "Python is a versatile programming language used for web development, "
                    "data science, and machine learning. Python has a clean and readable syntax "
                    "that makes it popular among beginners and experts alike."
                )

            # Run mini pipeline
            mini_interest_store = InterestStore(store_path=os.path.join(test_data_dir, "interests.json"))
            mini_interest_store.add(Interest(name="python", keywords=["python", "programming"]))

            mini_tag_store = TagStore(store_path=os.path.join(test_data_dir, "tags.json"))
            mini_search_index = SearchIndex(db_path=os.path.join(test_data_dir, "search_index.json"))
            mini_filter = ContentFilter(
                config=FilterConfig(min_content_length=10),
                interest_store=mini_interest_store,
            )
            mini_scorer = ContentScorer(weights=ScoreWeights())

            # Process
            with open(test_file_path, "r") as f:
                content = f.read()
            page = CrawledPage(
                url=test_file_path,
                title="Python Overview",
                content=content,
            )

            # Filter
            if not mini_filter.should_include(page):
                check("Full pipeline: filter stage", False, "Content was filtered out")
            else:
                # Score
                score = mini_scorer.score(
                    keyword_matches=2,
                    total_keywords=2,
                    word_count=len(content.split()),
                    domain_authority=0.5,
                )
                page.relevance_score = score.total

                # Tag
                mini_tag_store.add_tag_to_page(page.url, "python")
                mini_tag_store.add_tag_to_page(page.url, "programming")

                # Index
                mini_search_index.add_page(page)

                # Search
                results = mini_search_index.search("python")

                check("Full pipeline: all stages", len(results) > 0,
                      "Pipeline did not produce searchable results")

            # Cleanup
            import shutil
            shutil.rmtree(test_data_dir, ignore_errors=True)

        except Exception as e:
            check("Full pipeline: all stages", False, str(e))

    # Cleanup verify files
    for f in ["verify_interests.json", "verify_tags.json", "verify_index.json"]:
        path = os.path.join(dd, f)
        if os.path.exists(path):
            os.remove(path)

    # Summary
    click.echo(f"\n{'=' * 50}")
    click.echo(f"Results: {checks_passed}/{checks_total} checks passed")

    if errors:
        click.echo(f"\nFailed checks ({len(errors)}):")
        for error in errors:
            click.echo(f"  {error}")
        sys.exit(1)
    else:
        click.echo("\n✓ All checks passed! Your pipeline is working correctly.")
