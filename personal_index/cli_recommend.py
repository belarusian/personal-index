"""CLI command for content recommendations."""

from __future__ import annotations

import click

from personal_index.content_recommender import ContentItem, Recommendation, Recommender


def _load_recommender(data_dir: str) -> tuple[Recommender, int]:
    from personal_index.index import SearchIndex
    from personal_index.tags import TagStore

    idx = SearchIndex(db_path=f"{data_dir}/search_index.json")
    tag_store = TagStore(store_path=f"{data_dir}/tags.json")
    recommender = Recommender(min_score=0.0)

    for page in idx.list_pages():
        page_tags = tag_store.get_tags_for_url(page.url)
        tag_names = [t.name if hasattr(t, 'name') else str(t) for t in page_tags]
        recommender.add_item(ContentItem(
            url=page.url,
            title=page.title,
            content=page.content or "",
            keywords=getattr(page, "keywords", []) or [],
            tags=tag_names,
            score=page.score,
        ))
    return recommender, recommender.item_count


def _print_recommendations(recs: list[Recommendation], top_n: int) -> None:
    click.echo(f"Top {top_n} Recommendations:")
    click.echo("=" * 50)
    for i, rec in enumerate(recs, 1):
        click.echo(f"\n{i}. {rec.title}")
        click.echo(f"   URL: {rec.url}")
        click.echo(f"   Score: {rec.score:.3f}")
        click.echo(f"   Reason: {rec.reason}")


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
    """Get content recommendations based on a query or seed content."""
    dd = data_dir or ctx.obj.get("data_dir", ".personal_index")
    recommender, count = _load_recommender(dd)

    if not count:
        click.echo("No indexed content found. Run 'personal-index pipeline' first.")
        return

    keywords = query.split() if query else []
    recs = recommender.recommend_for_keywords(keywords, top_n=top_n)

    if not recs:
        click.echo("No recommendations found.")
        return

    _print_recommendations(recs, top_n)
