"""Local search index with full-text search and relevance scoring."""

import json
import math
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from personal_index.content import ExtractedContent, tokenize, remove_stopwords, compute_tf


@dataclass
class DocumentEntry:
    """A document entry in the search index."""

    url: str
    title: str = ""
    text: str = ""
    meta_description: str = ""
    keywords: List[str] = field(default_factory=list)
    token_count: int = 0
    indexed_at: str = ""
    interest_topics: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "url": self.url,
            "title": self.title,
            "text": self.text,
            "meta_description": self.meta_description,
            "keywords": self.keywords,
            "token_count": self.token_count,
            "indexed_at": self.indexed_at,
            "interest_topics": self.interest_topics,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "DocumentEntry":
        return cls(**data)


@dataclass
class SearchResult:
    """A single search result with relevance score."""

    url: str
    title: str
    snippet: str = ""
    score: float = 0.0
    matched_terms: List[str] = field(default_factory=list)
    interest_topics: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "url": self.url,
            "title": self.title,
            "snippet": self.snippet,
            "score": self.score,
            "matched_terms": self.matched_terms,
            "interest_topics": self.interest_topics,
        }


class SearchIndex:
    """Inverted index for full-text search with relevance scoring."""

    def __init__(self, index_dir: Optional[Path] = None):
        self.index_dir = index_dir or Path("index")
        self.index_dir.mkdir(parents=True, exist_ok=True)
        self.inverted_index: Dict[str, Dict[str, float]] = {}
        self.documents: Dict[str, DocumentEntry] = {}
        self._load()

    def _index_path(self) -> Path:
        return self.index_dir / "inverted_index.json"

    def _docs_path(self) -> Path:
        return self.index_dir / "documents.json"

    def _load(self) -> None:
        """Load index from disk."""
        if self._index_path().exists():
            with open(self._index_path()) as f:
                self.inverted_index = json.load(f)
        if self._docs_path().exists():
            with open(self._docs_path()) as f:
                docs_data = json.load(f)
                self.documents = {
                    url: DocumentEntry.from_dict(d) for url, d in docs_data.items()
                }

    def save(self) -> None:
        """Save index to disk."""
        with open(self._index_path(), "w") as f:
            json.dump(self.inverted_index, f)
        with open(self._docs_path(), "w") as f:
            json.dump(
                {url: doc.to_dict() for url, doc in self.documents.items()}, f
            )

    def add_document(self, content: ExtractedContent, interest_topics: List[str] = None) -> None:
        """Add a document to the index."""
        if interest_topics is None:
            interest_topics = []

        searchable_text = content.get_searchable_text()
        tokens = tokenize(searchable_text)
        tokens = remove_stopwords(tokens)
        tf = compute_tf(tokens)

        # Store document
        entry = DocumentEntry(
            url=content.url,
            title=content.title,
            text=content.text[:5000],  # Limit stored text
            meta_description=content.meta_description,
            keywords=content.get_keywords(),
            token_count=len(tokens),
            indexed_at=content.fetched_at,
            interest_topics=interest_topics,
        )
        self.documents[content.url] = entry

        # Update inverted index
        doc_id = content.url
        for token, freq in tf.items():
            if token not in self.inverted_index:
                self.inverted_index[token] = {}
            self.inverted_index[token][doc_id] = freq

    def remove_document(self, url: str) -> bool:
        """Remove a document from the index."""
        if url not in self.documents:
            return False

        entry = self.documents[url]
        searchable_text = entry.title + " " + entry.meta_description + " " + entry.text
        tokens = tokenize(searchable_text)
        tokens = remove_stopwords(tokens)

        for token in set(tokens):
            if token in self.inverted_index:
                self.inverted_index[token].pop(url, None)
                if not self.inverted_index[token]:
                    del self.inverted_index[token]

        del self.documents[url]
        return True

    def _compute_idf(self, term: str) -> float:
        """Compute IDF for a term with smoothing."""
        num_docs = len(self.documents)
        num_containing = len(self.inverted_index.get(term, {}))
        # Smoothed IDF to avoid zero scores
        return math.log(1 + (num_docs / (1 + num_containing))) + 0.1

    def search(
        self,
        query: str,
        limit: int = 20,
        boost_interests: bool = True,
    ) -> List[SearchResult]:
        """Search the index and return ranked results."""
        query_tokens = tokenize(query)
        query_tokens = remove_stopwords(query_tokens)

        if not query_tokens:
            return []

        # Find matching documents
        scores: Dict[str, float] = {}
        matched_terms: Dict[str, set] = {}

        for token in query_tokens:
            if token in self.inverted_index:
                idf = self._compute_idf(token)
                for doc_id, tf in self.inverted_index[token].items():
                    if doc_id not in scores:
                        scores[doc_id] = 0.0
                        matched_terms[doc_id] = set()
                    scores[doc_id] += tf * idf
                    matched_terms[doc_id].add(token)

        # Boost documents matching interest topics
        if boost_interests:
            query_lower = query.lower()
            for doc_id in scores:
                if doc_id in self.documents:
                    entry = self.documents[doc_id]
                    for topic in entry.interest_topics:
                        if topic.lower() in query_lower:
                            scores[doc_id] *= 1.5

        # Title boost
        for doc_id in scores:
            if doc_id in self.documents:
                entry = self.documents[doc_id]
                title_tokens = set(tokenize(entry.title))
                query_set = set(query_tokens)
                title_overlap = title_tokens & query_set
                if title_overlap:
                    scores[doc_id] *= (1 + 0.5 * len(title_overlap))

        # Sort by score
        ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)

        results = []
        for doc_id, score in ranked[:limit]:
            if doc_id in self.documents:
                entry = self.documents[doc_id]
                snippet = self._generate_snippet(entry, query_tokens)
                result = SearchResult(
                    url=doc_id,
                    title=entry.title,
                    snippet=snippet,
                    score=round(score, 4),
                    matched_terms=list(matched_terms.get(doc_id, set())),
                    interest_topics=entry.interest_topics,
                )
                results.append(result)

        return results

    def _generate_snippet(self, entry: DocumentEntry, query_tokens: List[str]) -> str:
        """Generate a text snippet around matched terms."""
        text = entry.text
        if not text:
            return entry.meta_description or ""

        # Find first occurrence of any query term
        best_pos = 0
        for token in query_tokens:
            pos = text.lower().find(token)
            if pos != -1 and pos < best_pos or best_pos == 0:
                best_pos = pos

        # Extract snippet around the match
        start = max(0, best_pos - 50)
        end = min(len(text), best_pos + 150)
        snippet = text[start:end].strip()
        if start > 0:
            snippet = "..." + snippet
        if end < len(text):
            snippet += "..."
        return snippet

    def get_document(self, url: str) -> Optional[DocumentEntry]:
        """Get a document by URL."""
        return self.documents.get(url)

    def get_document_count(self) -> int:
        """Get total number of indexed documents."""
        return len(self.documents)

    def get_term_count(self) -> int:
        """Get total number of unique terms in the index."""
        return len(self.inverted_index)

    def clear(self) -> None:
        """Clear the entire index."""
        self.inverted_index = {}
        self.documents = {}
        self.save()

    def get_urls(self) -> List[str]:
        """Get all indexed URLs."""
        return list(self.documents.keys())

    def get_stats(self) -> dict:
        """Get index statistics."""
        return {
            "document_count": len(self.documents),
            "term_count": len(self.inverted_index),
            "index_dir": str(self.index_dir),
        }
