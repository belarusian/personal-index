"""Search index for personal-index.

Provides full-text search with relevance scoring using Whoosh.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Optional

from whoosh import index
from whoosh.analysis import StemmingAnalyzer
from whoosh.fields import ID, TEXT, Schema
from whoosh.qparser import QueryParser
from whoosh.searching import Results

from personal_index.models import CrawledPage, SearchResult

logger = logging.getLogger(__name__)


class SearchIndex:
    """Full-text search index backed by Whoosh."""

    # Schema definition for the search index
    SCHEMA = Schema(
        id=ID(stored=True, unique=True),
        url=ID(stored=True),
        title=TEXT(
            stored=True,
            analyzer=StemmingAnalyzer(),
            field_boost=2.0,
        ),
        content=TEXT(stored=True, analyzer=StemmingAnalyzer()),
        meta_description=TEXT(stored=True, analyzer=StemmingAnalyzer()),
        matched_interests=TEXT(stored=True, field_boost=1.5),
        word_count=ID(stored=True),
        depth=ID(stored=True),
    )

    def __init__(self, index_dir: str = "~/.personal-index/index"):
        self.index_dir = Path(index_dir).expanduser()
        self.index_dir.mkdir(parents=True, exist_ok=True)
        self._ix = self._open_or_create_index()

    def _open_or_create_index(self) -> index.Index:
        """Open existing index or create a new one."""
        if index.exists_in(str(self.index_dir)):
            return index.open_dir(str(self.index_dir))
        return index.create_in(str(self.index_dir), self.SCHEMA)

    def add_document(self, page: CrawledPage) -> None:
        """Add a crawled page to the search index."""
        writer = self._ix.writer()
        writer.add_document(
            id=page.id,
            url=page.url,
            title=page.title,
            content=page.content,
            meta_description=page.meta_description,
            matched_interests=" ".join(page.matched_interests),
            word_count=str(page.word_count),
            depth=str(page.depth),
        )
        writer.commit()
        logger.debug(f"Indexed page: {page.url}")

    def remove_document(self, page_id: str) -> bool:
        """Remove a page from the search index."""
        with self._ix.searcher() as searcher:
            results = searcher.search(
                QueryParser("id", schema=self._ix.schema).parse(page_id)
            )
            if len(results) == 0:
                return False

        writer = self._ix.writer()
        writer.delete_by_term("id", page_id)
        writer.commit()
        return True

    def search(
        self,
        query: str,
        limit: int = 20,
        interest_filter: Optional[str] = None,
    ) -> list[SearchResult]:
        """Search the index and return ranked results.

        Args:
            query: Search query string.
            limit: Maximum number of results to return.
            interest_filter: Optional interest topic to filter by.

        Returns:
            List of SearchResult objects ranked by relevance.
        """
        with self._ix.searcher() as searcher:
            parser = QueryParser(
                "content",
                schema=self._ix.schema,
                termclass=None,
            )
            # Build query from multiple fields
            q = parser.parse(query)

            # Apply interest filter if specified
            if interest_filter:
                from whoosh.query import And, Term
                interest_q = Term("matched_interests", interest_filter)
                q = And([q, interest_q])

            results: Results = searcher.search(
                q,
                limit=limit,
                sortedby="score",
            )

            return self._convert_results(results)

    def _convert_results(self, results: Results) -> list[SearchResult]:
        """Convert Whoosh results to SearchResult objects."""
        search_results = []
        for hit in results:
            page = CrawledPage(
                url=hit["url"],
                title=hit["title"],
                content=hit["content"],
                meta_description=hit["meta_description"],
                word_count=int(hit["word_count"]) if hit["word_count"] else 0,
                depth=int(hit["depth"]) if hit["depth"] else 0,
                matched_interests=hit["matched_interests"].split() if hit["matched_interests"] else [],
            )
            search_results.append(SearchResult(
                page=page,
                score=hit.score,
                matched_interest=hit["matched_interests"].split()[0] if hit["matched_interests"] else None,
            ))
        return search_results

    def search_with_highlights(
        self,
        query: str,
        limit: int = 20,
        fragment_size: int = 200,
    ) -> list[SearchResult]:
        """Search with highlighted matching fragments.

        Args:
            query: Search query string.
            limit: Maximum number of results.
            fragment_size: Size of highlighted text fragments.

        Returns:
            List of SearchResult with highlighted text fragments.
        """
        with self._ix.searcher() as searcher:
            parser = QueryParser(
                "content",
                schema=self._ix.schema,
            )
            q = parser.parse(query)
            results: Results = searcher.search(q, limit=limit)

            search_results = []
            for hit in results:
                page = CrawledPage(
                    url=hit["url"],
                    title=hit["title"],
                    content=hit["content"],
                    meta_description=hit["meta_description"],
                    matched_interests=hit["matched_interests"].split() if hit["matched_interests"] else [],
                )

                # Generate highlights
                highlights = []
                try:
                    fragmenter = searcher.fragmenter("content")
                    highlighter = searcher.highlighter("content", fragmenter)
                    fragment = highlighter.highlight(hit["content"], q)
                    if fragment:
                        highlights.append(fragment)
                except Exception:
                    pass

                search_results.append(SearchResult(
                    page=page,
                    score=hit.score,
                    highlights=highlights,
                ))

            return search_results

    def get_document_count(self) -> int:
        """Get the number of documents in the index."""
        with self._ix.searcher() as searcher:
            return searcher.doc_count_all()

    def optimize(self) -> None:
        """Optimize the index for better search performance."""
        self._ix.optimize()

    def clear(self) -> None:
        """Remove all documents from the index."""
        writer = self._ix.writer()
        writer.delete_everything()
        writer.commit()
        logger.info("Search index cleared")

    def rebuild(self, pages: list[CrawledPage]) -> None:
        """Rebuild the entire index from a list of pages."""
        self.clear()
        for page in pages:
            self.add_document(page)
        self.optimize()
        logger.info(f"Index rebuilt with {len(pages)} documents")
