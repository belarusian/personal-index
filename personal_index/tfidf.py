"""TF-IDF scoring for document relevance ranking."""

from __future__ import annotations

import math
from collections import Counter

from personal_index.text_utils import tokenize


class TfidfScorer:
    """Compute TF-IDF scores for documents and queries."""

    def __init__(self):
        self._doc_freq: dict[str, int] = {}
        self._doc_count: int = 0
        self._doc_terms: dict[int, Counter] = {}
        self._next_id: int = 0

    def add_document(self, text: str) -> int:
        """Add a document to the corpus. Returns document ID."""
        doc_id = self._next_id
        self._next_id += 1
        tokens = tokenize(text, remove_stopwords=True)
        self._doc_terms[doc_id] = Counter(tokens)
        self._doc_count += 1
        unique_tokens = set(tokens)
        for token in unique_tokens:
            self._doc_freq[token] = self._doc_freq.get(token, 0) + 1
        return doc_id

    def remove_document(self, doc_id: int) -> bool:
        """Remove a document from the corpus."""
        if doc_id not in self._doc_terms:
            return False
        removed_tokens = set(self._doc_terms[doc_id].keys())
        del self._doc_terms[doc_id]
        self._doc_count -= 1
        for token in removed_tokens:
            self._doc_freq[token] -= 1
            if self._doc_freq[token] <= 0:
                del self._doc_freq[token]
        return True

    def compute_tfidf(self, doc_id: int) -> dict[str, float]:
        """Compute TF-IDF scores for a document."""
        if doc_id not in self._doc_terms:
            return {}
        if self._doc_count == 0:
            return {}
        terms = self._doc_terms[doc_id]
        total_terms = sum(terms.values())
        if total_terms == 0:
            return {}
        scores: dict[str, float] = {}
        for term, count in terms.items():
            tf = count / total_terms
            idf = math.log((1 + self._doc_count) / (1 + self._doc_freq.get(term, 0))) + 1
            scores[term] = tf * idf
        return scores

    def score_query(self, query: str, doc_id: int) -> float:
        """Score a document against a query using TF-IDF dot product."""
        query_tokens = tokenize(query, remove_stopwords=True)
        if not query_tokens or doc_id not in self._doc_terms:
            return 0.0
        doc_tfidf = self.compute_tfidf(doc_id)
        query_counter = Counter(query_tokens)
        query_total = sum(query_counter.values())
        if query_total == 0:
            return 0.0
        score = 0.0
        for term, count in query_counter.items():
            if term in doc_tfidf:
                query_tf = count / query_total
                score += query_tf * doc_tfidf[term]
        return score

    def rank_documents(self, query: str, limit: int = 10) -> list[tuple[int, float]]:
        """Rank all documents by relevance to query."""
        scores: list[tuple[int, float]] = []
        for doc_id in self._doc_terms:
            score = self.score_query(query, doc_id)
            if score > 0:
                scores.append((doc_id, score))
        scores.sort(key=lambda x: x[1], reverse=True)
        return scores[:limit]

    @property
    def document_count(self) -> int:
        """Return number of documents in corpus."""
        return self._doc_count

    @property
    def vocabulary_size(self) -> int:
        """Return size of vocabulary."""
        return len(self._doc_freq)

    def get_top_terms(self, doc_id: int, n: int = 10) -> list[tuple[str, float]]:
        """Get top N terms by TF-IDF score for a document."""
        scores = self.compute_tfidf(doc_id)
        return sorted(scores.items(), key=lambda x: x[1], reverse=True)[:n]

    def clear(self) -> None:
        """Clear the corpus."""
        self._doc_freq.clear()
        self._doc_count = 0
        self._doc_terms.clear()
        self._next_id = 0
