"""Verify CLI command for personal-index pipeline validation."""

from __future__ import annotations

import os
import sys

import click

from personal_index.content_filter import ContentFilter, FilterConfig
from personal_index.content_scoring import ContentScorer, ScoreWeights
from personal_index.index import SearchIndex
from personal_index.interests import InterestStore
from personal_index.models import CrawledPage, Interest
from personal_index.tags import TagStore


def _check_data_dir(data_dir: str) -> tuple[bool, str]:
    """Check that the data directory is writable.

    Returns:
        Tuple of (passed, message).
    """
    test_file = os.path.join(data_dir, ".verify_test")
    try:
        with open(test_file, "w") as f:
            f.write("test")
        os.remove(test_file)
        return True, ""
    except OSError as e:
        return False, str(e)


def _check_interest_store(data_dir: str) -> tuple[bool, str]:
    """Check that the interest store works.

    Returns:
        Tuple of (passed, message).
    """
    try:
        interest_store = InterestStore(store_path=os.path.join(data_dir, "verify_interests.json"))
        interest_store.add(Interest(name="verify_test", keywords=["verify"]))
        interests = interest_store.list_all()
        if len(interests) > 0:
            interest_store._interests.clear()
            interest_store._save()
            return True, ""
        return False, "Could not store interests"
    except (RuntimeError, OSError, ValueError) as e:
        return False, str(e)


def _check_tag_store(data_dir: str) -> tuple[bool, str]:
    """Check that the tag store works.

    Returns:
        Tuple of (passed, message).
    """
    try:
        tag_store = TagStore(store_path=os.path.join(data_dir, "verify_tags.json"))
        tag_store.add_tag_to_page("http://test.com", "verify")
        tags = tag_store.get_tags_for_page("http://test.com")
        if any(t.name == "verify" for t in tags):
            tag_store._page_tags.clear()
            tag_store._save()
            return True, ""
        return False, "Could not store tags"
    except (RuntimeError, OSError, ValueError) as e:
        return False, str(e)


def _check_search_index(data_dir: str) -> tuple[bool, str]:
    """Check that the search index works.

    Returns:
        Tuple of (passed, message).
    """
    try:
        search_index = SearchIndex(db_path=os.path.join(data_dir, "verify_index.json"))
        test_page = CrawledPage(
            url="http://verify.test/page1",
            title="Verify Test Page",
            content="This is a verification test page for the pipeline.",
        )
        search_index.add_page(test_page)
        results = search_index.search("verification")
        if len(results) > 0:
            search_index.remove_page("http://verify.test/page1")
            search_index._save()
            return True, ""
        return False, "Could not search index"
    except (RuntimeError, OSError, ValueError) as e:
        return False, str(e)


def _check_content_filter() -> tuple[bool, str]:
    """Check that the content filter works.

    Returns:
        Tuple of (passed, message).
    """
    try:
        content_filter = ContentFilter(config=FilterConfig(min_content_length=10))
        test_page = CrawledPage(
            url="http://test.com",
            title="Test",
            content="This is test content for verification.",
        )
        included = content_filter.should_include(test_page)
        if included:
            return True, ""
        return False, "Filter rejected valid content"
    except (RuntimeError, OSError, ValueError) as e:
        return False, str(e)


def _check_content_scorer() -> tuple[bool, str]:
    """Check that the content scorer works.

    Returns:
        Tuple of (passed, message).
    """
    try:
        scorer = ContentScorer(weights=ScoreWeights())
        score = scorer.score(
            keyword_matches=1,
            total_keywords=2,
            word_count=10,
            domain_authority=0.5,
        )
        if score.total > 0:
            return True, ""
        return False, "Scorer returned zero score"
    except (RuntimeError, OSError, ValueError) as e:
        return False, str(e)


def _create_test_content(data_dir: str) -> tuple[str, str]:
    """Create temporary directory and test file for pipeline verification.

    Args:
        data_dir: Base data directory.

    Returns:
        Tuple of (test_data_dir, test_file_path).
    """
    test_data_dir = os.path.join(data_dir, ".verify_pipeline")
    os.makedirs(test_data_dir, exist_ok=True)

    test_file_path = os.path.join(test_data_dir, "test_article.txt")
    with open(test_file_path, "w") as f:
        f.write(
            "Python is a versatile programming language used for web development, "
            "data science, and machine learning. Python has a clean and readable syntax "
            "that makes it popular among beginners and experts alike."
        )

    return test_data_dir, test_file_path


def _setup_mini_pipeline(test_data_dir: str) -> dict:
    """Create mini pipeline components for verification.

    Args:
        test_data_dir: Directory for temporary pipeline data.

    Returns:
        Dict with keys: interest_store, tag_store, search_index, filter, scorer.
    """
    interest_store = InterestStore(store_path=os.path.join(test_data_dir, "interests.json"))
    interest_store.add(Interest(name="python", keywords=["python", "programming"]))

    tag_store = TagStore(store_path=os.path.join(test_data_dir, "tags.json"))
    search_index = SearchIndex(db_path=os.path.join(test_data_dir, "search_index.json"))
    content_filter = ContentFilter(
        config=FilterConfig(min_content_length=10),
        interest_store=interest_store,
    )
    scorer = ContentScorer(weights=ScoreWeights())

    return {
        "interest_store": interest_store,
        "tag_store": tag_store,
        "search_index": search_index,
        "filter": content_filter,
        "scorer": scorer,
    }


def _check_full_pipeline(data_dir: str) -> tuple[bool, str]:
    """Run a full pipeline self-test.

    Creates temporary content and processes it through all pipeline stages
    to verify the complete pipeline works end-to-end.

    Args:
        data_dir: Base data directory.

    Returns:
        Tuple of (passed, message).
    """
    import shutil

    test_data_dir, test_file_path = _create_test_content(data_dir)

    try:
        components = _setup_mini_pipeline(test_data_dir)
        mini_tag_store = components["tag_store"]
        mini_search_index = components["search_index"]
        mini_filter = components["filter"]
        mini_scorer = components["scorer"]

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
            return False, "Content was filtered out"

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

        if len(results) > 0:
            return True, ""
        return False, "Pipeline did not produce searchable results"

    except (RuntimeError, OSError, ValueError) as e:
        return False, str(e)
    finally:
        shutil.rmtree(test_data_dir, ignore_errors=True)


def _build_summary(checks_passed: int, checks_total: int, errors: list[str]) -> None:
    """Build and display the verification summary report.

    Args:
        checks_passed: Number of checks that passed.
        checks_total: Total number of checks run.
        errors: List of error messages for failed checks.
    """
    click.echo(f"\n{'=' * 50}")
    click.echo(f"Results: {checks_passed}/{checks_total} checks passed")

    if errors:
        click.echo(f"\nFailed checks ({len(errors)}):")
        for error in errors:
            click.echo(f"  {error}")
        sys.exit(1)
    else:
        click.echo("\n✓ All checks passed! Your pipeline is working correctly.")


# Data-driven check definitions for the verify command
_VERIFY_CHECKS = [
    ("Data directory is writable", lambda dd: _check_data_dir(dd)),
    ("Interest store works", lambda dd: _check_interest_store(dd)),
    ("Tag store works", lambda dd: _check_tag_store(dd)),
    ("Search index works", lambda dd: _check_search_index(dd)),
    ("Content filter works", lambda dd: _check_content_filter()),
    ("Content scorer works", lambda dd: _check_content_scorer()),
]


def _run_checks(data_dir: str, quick: bool) -> tuple[int, int, list[str]]:
    """Run all verification checks.

    Args:
        data_dir: Data directory to verify.
        quick: If True, skip the full pipeline test.

    Returns:
        Tuple of (checks_passed, checks_total, errors).
    """
    errors: list[str] = []
    checks_passed = 0
    checks_total = 0

    for name, check_fn in _VERIFY_CHECKS:
        checks_total += 1
        passed, msg = check_fn(data_dir)
        if passed:
            checks_passed += 1
            click.echo(f"  ✓ {name}")
        else:
            errors.append(f"✗ {name}: {msg}")
            click.echo(f"  ✗ {name}: {msg}")

    # Full pipeline test (skip with --quick)
    if not quick:
        click.echo("\nRunning full pipeline self-test...")
        checks_total += 1
        passed, msg = _check_full_pipeline(data_dir)
        if passed:
            checks_passed += 1
            click.echo("  ✓ Full pipeline: all stages")
        else:
            errors.append(f"✗ Full pipeline: all stages: {msg}")
            click.echo(f"  ✗ Full pipeline: all stages: {msg}")

    return checks_passed, checks_total, errors


def _cleanup_verify_files(data_dir: str) -> None:
    """Remove temporary verify files from the data directory.

    Args:
        data_dir: Data directory to clean up.
    """
    for f in ["verify_interests.json", "verify_tags.json", "verify_index.json"]:
        path = os.path.join(data_dir, f)
        if os.path.exists(path):
            os.remove(path)


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

    checks_passed, checks_total, errors = _run_checks(dd, quick)

    _cleanup_verify_files(dd)

    _build_summary(checks_passed, checks_total, errors)
