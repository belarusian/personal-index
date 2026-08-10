"""Search index module for personal-index."""

from __future__ import annotations

import json
import re
from collections import defaultdict
from pathlib import Path

from personal_index.models import Page, SearchResult


class SearchIndex:
    """Full-text search index with TF-IDF-like scoring."""

    def __init__(self, index_dir: str | Path | None = None):
        self.index_dir = Path(index_dir) if index_dir else None
        self._documents: dict[str, Page] = {}
        self._inverted_index: dict[str, set[str]] = defaultdict(set)
        self._term_freq: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
        self._doc_lengths: dict[str, int] = {}

    @property
    def num_documents(self) -> int:
        """Number of documents in the index."""
        return len(self._documents)

    @property
    def num_terms(self) -> int:
        """Number of unique terms in the inverted index."""
        return len(self._inverted_index)

    def _tokenize(self, text: str) -> list[str]:
        """Tokenize text into lowercase words."""
        if not text:
            return []
        return re.findall(r'[a-z0-9]+(?:-[a-z0-9]+)*', text.lower())

    def add_page(self, page: Page):
        """Add a page to the index."""
        self._documents[page.id] = page
        text = f"{page.title} {page.content}"
        tokens = self._tokenize(text)
        self._doc_lengths[page.id] = len(tokens)
        for token in tokens:
            self._inverted_index[token].add(page.id)
            self._term_freq[token][page.id] += 1

    def remove_page(self, page_id: str) -> bool:
        """Remove a page from the index."""
        if page_id not in self._documents:
            return False
        page = self._documents.pop(page_id)
        text = f"{page.title} {page.content}"
        tokens = self._tokenize(text)
        for token in tokens:
            self._inverted_index[token].discard(page_id)
            if page_id in self._term_freq[token]:
                del self._term_freq[token][page_id]
            if not self._inverted_index[token]:
                del self._inverted_index[token]
                if token in self._term_freq:
                    del self._term_freq[token]
        self._doc_lengths.pop(page_id, None)
        return True

    def search(
        self,
        query: str,
        limit: int = 10,
        min_score: float = 0.0,
        interest_filter: list[str] | None = None,
    ) -> list[SearchResult]:
        """Search the index for a query."""
        if not query.strip():
            return []
        query_tokens = self._tokenize(query)
        if not query_tokens:
            return []

        # Find candidate documents
        candidate_ids: set[str] = set()
        for token in query_tokens:
            candidate_ids.update(self._inverted_index.get(token, set()))

        # Score each candidate
        scores: dict[str, float] = defaultdict(float)
        matched_terms: dict[str, set[str]] = defaultdict(set)
        for doc_id in candidate_ids:
            if doc_id not in self._documents:
                continue
            page = self._documents[doc_id]

            # Apply interest filter
            if interest_filter:
                page_interests = {i.lower() for i in page.matched_interests}
                if not any(fi.lower() in page_interests for fi in interest_filter):
                    continue

            doc_len = max(self._doc_lengths.get(doc_id, 1), 1)
            for token in query_tokens:
                tf = self._term_freq.get(token, {}).get(doc_id, 0)
                if tf > 0:
                    # TF-IDF-like scoring
                    idf = len(self._documents) / max(
                        len(self._inverted_index.get(token, set())), 1
                    )
                    score = (tf / doc_len) * idf
                    # Title bonus
                    if token in self._tokenize(page.title):
                        score *= 2.0
                    scores[doc_id] += score
                    matched_terms[doc_id].add(token)

        # Build results
        results = []
        for doc_id, score in sorted(scores.items(), key=lambda x: -x[1]):
            if score < min_score:
                continue
            page = self._documents[doc_id]
            snippet = self._generate_snippet(page.content, query_tokens)
            results.append(SearchResult(
                page=page,
                score=score,
                matched_terms=list(matched_terms.get(doc_id, set())),
                snippet=snippet,
            ))
            if len(results) >= limit:
                break
        return results

    def _generate_snippet(self, text: str, query_tokens: list[str]) -> str:
        """Generate a snippet highlighting query terms."""
        if not text:
            return ""
        text_lower = text.lower()
        for token in query_tokens:
            idx = text_lower.find(token)
            if idx != -1:
                start = max(0, idx - 50)
                end = min(len(text), idx + len(token) + 100)
                snippet = text[start:end].strip()
                if start > 0:
                    snippet = "..." + snippet
                if end < len(text):
                    snippet += "..."
                return snippet
        # Fallback: first 150 chars
        return text[:150] + ("..." if len(text) > 150 else "")

    def get_page(self, page_id: str) -> Page | None:
        """Get a page by ID."""
        return self._documents.get(page_id)

    def get_all_pages(self) -> list[Page]:
        """Get all indexed pages."""
        return list(self._documents.values())

    def clear(self):
        """Clear the entire index."""
        self._documents.clear()
        self._inverted_index.clear()
        self._term_freq.clear()
        self._doc_lengths.clear()

    def save(self):
        """Save index to disk."""
        if not self.index_dir:
            return
        self.index_dir.mkdir(parents=True, exist_ok=True)
        # Save documents
        docs_data = {pid: p.to_dict() for pid, p in self._documents.items()}
        with open(self.index_dir / "documents.json", "w") as f:
            json.dump(docs_data, f)
        # Save inverted index
        inv_data = {t: list(docs) for t, docs in self._inverted_index.items()}
        with open(self.index_dir / "inverted_index.json", "w") as f:
            json.dump(inv_data, f)
        # Save term freq
        tf_data = {t: dict(freqs) for t, freqs in self._term_freq.items()}
        with open(self.index_dir / "term_freq.json", "w") as f:
            json.dump(tf_data, f)
        # Save doc lengths
        with open(self.index_dir / "doc_lengths.json", "w") as f:
            json.dump(self._doc_lengths, f)

    def load(self):
        """Load index from disk."""
        if not self.index_dir:
            return
        # Load documents
        docs_path = self.index_dir / "documents.json"
        if docs_path.exists():
            with open(docs_path) as f:
                docs_data = json.load(f)
            for pid, data in docs_data.items():
                self._documents[pid] = Page.from_dict(data)
        # Load inverted index
        inv_path = self.index_dir / "inverted_index.json"
        if inv_path.exists():
            with open(inv_path) as f:
                inv_data = json.load(f)
            self._inverted_index = {t: set(docs) for t, docs in inv_data.items()}
        # Load term freq
        tf_path = self.index_dir / "term_freq.json"
        if tf_path.exists():
            with open(tf_path) as f:
                tf_data = json.load(f)
            self._term_freq = {
                t: defaultdict(int, freqs) for t, freqs in tf_data.items()
            }
        # Load doc lengths
        dl_path = self.index_dir / "doc_lengths.json"
        if dl_path.exists():
            with open(dl_path) as f:
                self._doc_lengths = json.load(f)
