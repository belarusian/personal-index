"""Local search index with full-text search and relevance scoring."""

import math
import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from collections import Counter


@dataclass
class Document:
    """A document stored in the search index."""
    url: str
    title: str = ""
    content: str = ""
    metadata: Dict = field(default_factory=dict)

    @property
    def searchable_text(self) -> str:
        """Return combined searchable text from title and content."""
        return f"{self.title} {self.content}"


@dataclass
class SearchResult:
    """A single search result with relevance score."""
    document: Document
    score: float
    matched_terms: List[str] = field(default_factory=list)


class SearchIndex:
    """Full-text search index with TF-IDF relevance scoring."""

    def __init__(self):
        self.documents: Dict[str, Document] = {}  # url -> Document
        self.inverted_index: Dict[str, set] = {}  # term -> set of urls
        self.doc_lengths: Dict[str, float] = {}  # url -> number of terms
        self.term_doc_freq: Dict[str, int] = {}  # term -> number of docs containing it
        self.term_counts: Dict[str, Dict[str, int]] = {}  # url -> {term: count}
        self._num_docs = 0

    @staticmethod
    def tokenize(text: str) -> List[str]:
        """Tokenize text into lowercase terms."""
        if not text:
            return []
        text = text.lower()
        # Remove HTML-like tags
        text = re.sub(r'<[^>]+>', ' ', text)
        # Split on non-alphanumeric characters
        tokens = re.findall(r'[a-z0-9]+', text)
        # Filter out very short tokens
        return [t for t in tokens if len(t) >= 2]

    def add_document(self, doc: Document) -> None:
        """Add a document to the index."""
        if doc.url in self.documents:
            self.remove_document(doc.url)

        self.documents[doc.url] = doc
        tokens = self.tokenize(doc.searchable_text)
        self.doc_lengths[doc.url] = len(tokens)

        # Store term counts per document
        self.term_counts[doc.url] = Counter(tokens)

        # Update inverted index and term frequencies
        unique_tokens = set(tokens)
        for token in unique_tokens:
            if token not in self.inverted_index:
                self.inverted_index[token] = set()
            self.inverted_index[token].add(doc.url)
            self.term_doc_freq[token] = len(self.inverted_index[token])

        self._num_docs += 1

    def remove_document(self, url: str) -> None:
        """Remove a document from the index."""
        if url not in self.documents:
            return

        doc = self.documents.pop(url)
        tokens = set(self.tokenize(doc.searchable_text))
        del self.doc_lengths[url]
        self.term_counts.pop(url, None)

        for token in tokens:
            if token in self.inverted_index:
                self.inverted_index[token].discard(url)
                if not self.inverted_index[token]:
                    del self.inverted_index[token]
                else:
                    self.term_doc_freq[token] = len(self.inverted_index[token])

        self._num_docs = max(0, self._num_docs - 1)

    def _tf(self, term: str, url: str) -> float:
        """Calculate term frequency for a term in a document using raw count."""
        counts = self.term_counts.get(url, {})
        return counts.get(term, 0)

    def _idf(self, term: str) -> float:
        """Calculate inverse document frequency for a term."""
        if self._num_docs == 0:
            return 0.0
        doc_freq = self.term_doc_freq.get(term, 0)
        if doc_freq == 0:
            return 0.0
        return math.log(1 + self._num_docs / doc_freq)

    def search(self, query: str, limit: int = 20) -> List[SearchResult]:
        """Search the index and return results sorted by relevance."""
        query_terms = self.tokenize(query)
        if not query_terms:
            return []

        scores: Dict[str, float] = {}
        matched: Dict[str, List[str]] = {}

        for term in query_terms:
            urls = self.inverted_index.get(term, set())
            for url in urls:
                tf = self._tf(term, url)
                idf = self._idf(term)
                score = tf * idf
                scores[url] = scores.get(url, 0.0) + score
                if url not in matched:
                    matched[url] = []
                matched[url].append(term)

        # Normalize scores by document length to prevent bias toward long docs
        results = []
        for url, score in scores.items():
            doc_len = self.doc_lengths.get(url, 1)
            normalized = score / math.log(1 + doc_len) if doc_len > 1 else score
            results.append(SearchResult(
                document=self.documents[url],
                score=normalized,
                matched_terms=matched.get(url, []),
            ))

        results.sort(key=lambda r: r.score, reverse=True)
        return results[:limit]

    def get_document(self, url: str) -> Optional[Document]:
        """Get a document by URL."""
        return self.documents.get(url)

    def get_stats(self) -> Dict:
        """Return index statistics."""
        return {
            "total_documents": self._num_docs,
            "total_terms": len(self.inverted_index),
            "total_urls_indexed": len(self.documents),
        }

    def clear(self) -> None:
        """Clear the entire index."""
        self.documents.clear()
        self.inverted_index.clear()
        self.doc_lengths.clear()
        self.term_doc_freq.clear()
        self.term_counts.clear()
        self._num_docs = 0
