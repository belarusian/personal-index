"""Score CLI command for personal-index.

Provides the 'score' command that scores indexed content based
on configured interests and scoring weights.
"""

from __future__ import annotations

import os
import sys

import click

from personal_index.content_scoring import ContentScorer, ScoreWeights
from personal_index.index import SearchIndex
from personal_index.interests import InterestStore


@click.command("score")
@click.option("--data-dir", default=None, help="Data directory")
@click.option("--min-score", default=0.0, type=float, help="Minimum score threshold")
@click.option("--top", "-n", default=20, type=int, help="Number of top results to show")
@click.option("--recency", type=float, help="Recency weight (0.0-1.0)")
@click.option("--relevance", type=float, help="Relevance weight (0.0-1.0)")
@click.option("--quality", type=float, help="Quality weight (0.0-1.0)")
@click.pass_context
def score(ctx, data_dir, min_score, top, recency, relevance, quality):
    """Score and rank indexed content.

    Re-scores all indexed pages based on current interests and
    scoring weights. Useful for re-ranking after adding new interests.

    Examples:
        personal-index score
        personal-index score --min-score 0.5 --top 10
        personal-index score --relevance 0.5 --quality 0.3
    """
    dd = data_dir or ctx.obj.get("data_dir", ".personal_index")

    weights = ScoreWeights()
    if recency is not None:
        weights.recency = recency
    if relevance is not None:
        weights.relevance = relevance
    if quality is not None:
        weights.quality = quality

    scorer = ContentScorer(weights=weights)
    index = SearchIndex(db_path=os.path.join(dd, "search_index.json"))
    interest_store = InterestStore(store_path=os.path.join(dd, "interests.json"))

    pages = index.list_pages()
    if not pages:
        click.echo("No pages in index. Run 'personal-index pipeline' first.")
        return

    scored = []
    for page in pages:
        try:
            result = scorer.score_page(
                content=page.content,
                title=page.title,
                url=page.url,
                interest_store=interest_store,
            )
            if result.total >= min_score:
                scored.append((page, result))
        except Exception as e:
            click.echo(f"Error scoring {page.url}: {e}", err=True)

    scored.sort(key=lambda x: x[1].total, reverse=True)

    click.echo(f"Scored {len(scored)}/{len(pages)} pages (min_score={min_score}):")
    for page, result in scored[:top]:
        click.echo(f"  [{result.total:.2f}] {page.title}")
        click.echo(f"         {page.url}")
    if len(scored) > top:
        click.echo(f"  ... and {len(scored) - top} more")
