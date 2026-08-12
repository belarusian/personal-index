"""CLI command for content recommendations."""

from __future__ import annotations

import click

from personal_index.content_recommender import ContentItem, Recommender


@click.command("recommend")
@click.argument("query", required=False)
@click.option("--top-n", "-n", default=5, help="Number of recommendations")
@click.option("--data-dir", default=None, help="Data directory")
@click.option("--keyword-weight", default=0.6, help="Keyword overlap weight")
@click.option("--tag-weight", default=0.3, help="Tag similarity weight")
@click.option("--score-weight", default=0.1, help="Score weight")
@click.pass_context
def recommend(
    ctx,
    query,
    top_n,
    data_dir,
    keyword_weight,
    tag_weight,
    score_weight,
):
    """Get content recommendations based on a query or seed content.

    Analyzes indexed content and recommends related pages based on
    keyword overlap, tag similarity, and content scores.

    Examples:
        personal-index recommend "python tutorial"
        personal-index recommend "python tutorial" --top-n 10
        personal-index recommend "python" --keyword-weight 0.8
    """
    dd = data_dir or ctx.obj.get("data_dir", ".personal_index")

    # Load indexed content
    from personal_index.index import SearchIndex
    idx_path = f"{dd}/search_index.json"
    idx = SearchIndex(db_path=idx_path)

    # Load tags
    from personal_index.tags import TagStore
    tag_path = f"{dd}/tags.json"
    tag_store = TagStore(store_path=tag_path)

    # Build recommender
    recommender = Recommender(min_score=0.0)

    # Add indexed pages to recommender
    pages = idx.list_pages()
    for page in pages:
        page_tags = list(tag_store.get_tags_for_url(page.url))
        item = ContentItem(
            url=page.url,
            title=page.title,
            content=page.content or "",
            keywords=getattr(page, "keywords", []) or [],
            tags=page_tags,
            score=page.score,
        )
        recommender.add_item(item)

    if not recommender.item_count:
        click.echo("No indexed content found. Run 'personal-index pipeline' first.")
        return

    if query:
        # Search by keywords
        recs = recommender.recommend_for_keywords(
            query.split(),
            top_n=top_n,
        )
    else:
        # Recommend top content by score
        recs = recommender.recommend_for_keywords(
            [],
            top_n=top_n,
        )

    if not recs:
        click.echo("No recommendations found.")
        return

    click.echo(f"Top {top_n} Recommendations:")
    click.echo("=" * 50)
    for i, rec in enumerate(recs, 1):
        click.echo(f"\n{i}. {rec.title}")
        click.echo(f"   URL: {rec.url}")
        click.echo(f"   Score: {rec.score:.3f}")
        click.echo(f"   Reason: {rec.reason}")
