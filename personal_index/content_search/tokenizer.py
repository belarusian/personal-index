"""Text tokenizer for search indexing."""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass
class Tokenizer:
    """Tokenizes text into searchable terms.

    Attributes:
        min_token_length: Minimum length of a token to include.
        max_token_length: Maximum length of a token to include.
        stopwords: Set of words to exclude from tokens.
    """

    min_token_length: int = 2
    max_token_length: int = 100
    stopwords: set[str] | None = None

    def __post_init__(self) -> None:
        if self.stopwords is None:
            self.stopwords = {
                "the", "a", "an", "is", "are", "was", "were",
                "in", "on", "at", "to", "for", "of", "and",
                "or", "but", "not", "with", "by", "from",
            }

    def tokenize(self, text: str) -> list[str]:
        """Tokenize text into a list of terms.

        Args:
            text: Input text to tokenize.

        Returns:
            List of lowercase tokens.
        """
        if not text:
            return []

        # Extract words
        words = re.findall(r"[a-zA-Z0-9]+", text.lower())

        # Filter tokens
        tokens = [
            w for w in words
            if self.min_token_length <= len(w) <= self.max_token_length
            and w not in self.stopwords
        ]

        return tokens

    def tokenize_with_positions(self, text: str) -> list[tuple[str, int]]:
        """Tokenize text and return tokens with their positions.

        Args:
            text: Input text to tokenize.

        Returns:
            List of (token, position) tuples.
        """
        if not text:
            return []

        words = re.findall(r"[a-zA-Z0-9]+", text.lower())
        result: list[tuple[str, int]] = []
        for i, word in enumerate(words):
            if (self.min_token_length <= len(word) <= self.max_token_length
                    and word not in self.stopwords):
                result.append((word, i))
        return result
