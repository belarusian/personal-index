"""Tests for content_nlp - NLP utilities for text analysis."""

from __future__ import annotations

import pytest
from personal_index.content_nlp import (
    NLPTokenizer,
    NLPLemma,
    NLPLemmatizer,
    NLPPOS,
    NLPPOSTagger,
    NLPStemmer,
    NLPStem,
    NLPTextStats,
    NLPTextAnalysisResult,
    NLPConfig,
)


class TestNLPTokenizer:
    def test_tokenize_basic(self):
        tokenizer = NLPTokenizer()
        tokens = tokenizer.tokenize("Hello world, this is a test.")
        assert len(tokens) > 0
        assert "hello" in tokens or "Hello" in tokens

    def test_tokenize_empty(self):
        tokenizer = NLPTokenizer()
        tokens = tokenizer.tokenize("")
        assert tokens == []

    def test_tokenize_punctuation(self):
        tokenizer = NLPTokenizer()
        tokens = tokenizer.tokenize("Hello, world! How are you?")
        assert any("hello" in t.lower() for t in tokens)
        assert any("world" in t.lower() for t in tokens)

    def test_tokenize_numbers(self):
        tokenizer = NLPTokenizer()
        tokens = tokenizer.tokenize("There are 42 items in 2024.")
        assert any("42" in t for t in tokens)

    def test_tokenize_with_stopword_removal(self):
        tokenizer = NLPTokenizer(remove_stopwords=True)
        tokens = tokenizer.tokenize("The quick brown fox jumps over the lazy dog")
        assert "the" not in tokens
        assert "quick" in tokens or "brown" in tokens

    def test_tokenize_lowercase(self):
        tokenizer = NLPTokenizer(lowercase=True)
        tokens = tokenizer.tokenize("Hello WORLD")
        assert all(t == t.lower() for t in tokens)

    def test_tokenize_preserve_case(self):
        tokenizer = NLPTokenizer(lowercase=False)
        tokens = tokenizer.tokenize("Hello WORLD")
        assert "Hello" in tokens or "WORLD" in tokens


class TestNLPLemmatizer:
    def test_lemmatize_basic(self):
        lemmatizer = NLPLemmatizer()
        result = lemmatizer.lemmatize("running")
        assert isinstance(result, str)

    def test_lemmatize_plural(self):
        lemmatizer = NLPLemmatizer()
        result = lemmatizer.lemmatize("cats")
        assert isinstance(result, str)

    def test_lemmatize_list(self):
        lemmatizer = NLPLemmatizer()
        results = lemmatizer.lemmatize_list(["running", "cats", "better"])
        assert len(results) == 3
        assert all(isinstance(r, str) for r in results)

    def test_lemmatize_empty(self):
        lemmatizer = NLPLemmatizer()
        result = lemmatizer.lemmatize("")
        assert result == ""

    def test_lemmatize_text(self):
        lemmatizer = NLPLemmatizer()
        result = lemmatizer.lemmatize_text("The cats are running quickly")
        assert isinstance(result, str)
        assert len(result) > 0


class TestNLPStemmer:
    def test_stem_basic(self):
        stemmer = NLPStemmer()
        result = stemmer.stem("running")
        assert isinstance(result, str)
        assert len(result) > 0

    def test_stem_list(self):
        stemmer = NLPStemmer()
        results = stemmer.stem_list(["running", "cats", "better"])
        assert len(results) == 3

    def test_stem_empty(self):
        stemmer = NLPStemmer()
        result = stemmer.stem("")
        assert result == ""

    def test_stem_text(self):
        stemmer = NLPStemmer()
        result = stemmer.stem_text("The cats are running quickly")
        assert isinstance(result, str)


class TestNLPPOSTagger:
    def test_tag_basic(self):
        tagger = NLPPOSTagger()
        result = tagger.tag("The cat runs")
        assert isinstance(result, list)
        assert len(result) > 0

    def test_tag_empty(self):
        tagger = NLPPOSTagger()
        result = tagger.tag("")
        assert result == []

    def test_tag_single_word(self):
        tagger = NLPPOSTagger()
        result = tagger.tag("cat")
        assert len(result) >= 1

    def test_get_pos_counts(self):
        tagger = NLPPOSTagger()
        counts = tagger.get_pos_counts("The cat runs quickly")
        assert isinstance(counts, dict)


class TestNLPTextStats:
    def test_compute_stats_basic(self):
        stats = NLPTextStats()
        result = stats.compute("Hello world. This is a test sentence.")
        assert isinstance(result, NLPTextAnalysisResult)
        assert result.word_count > 0
        assert result.char_count > 0

    def test_compute_stats_empty(self):
        stats = NLPTextStats()
        result = stats.compute("")
        assert result.word_count == 0
        assert result.char_count == 0

    def test_compute_stats_sentence_count(self):
        stats = NLPTextStats()
        result = stats.compute("First sentence. Second sentence! Third sentence?")
        assert result.sentence_count >= 2

    def test_compute_stats_avg_word_length(self):
        stats = NLPTextStats()
        result = stats.compute("The quick brown fox")
        assert result.avg_word_length > 0

    def test_compute_stats_readability(self):
        stats = NLPTextStats()
        result = stats.compute("The cat sat on the mat. It was a good day.")
        assert result.readability_score is not None

    def test_compute_stats_unique_words(self):
        stats = NLPTextStats()
        result = stats.compute("The cat the dog the bird")
        assert result.unique_word_count > 0

    def test_compute_stats_vocabulary_richness(self):
        stats = NLPTextStats()
        result = stats.compute("The cat the dog the bird the fish")
        assert 0 <= result.vocabulary_richness <= 1


class TestNLPTextAnalysisResult:
    def test_result_attributes(self):
        result = NLPTextAnalysisResult(
            word_count=10,
            char_count=50,
            sentence_count=2,
            avg_word_length=5.0,
            unique_word_count=8,
            vocabulary_richness=0.8,
            readability_score=60.0,
        )
        assert result.word_count == 10
        assert result.char_count == 50
        assert result.sentence_count == 2
        assert result.avg_word_length == 5.0
        assert result.unique_word_count == 8
        assert result.vocabulary_richness == 0.8
        assert result.readability_score == 60.0

    def test_result_defaults(self):
        result = NLPTextAnalysisResult()
        assert result.word_count == 0
        assert result.char_count == 0
        assert result.sentence_count == 0


class TestNLPConfig:
    def test_config_defaults(self):
        config = NLPConfig()
        assert config.lowercase is True
        assert config.remove_stopwords is True

    def test_config_custom(self):
        config = NLPConfig(lowercase=False, remove_stopwords=False)
        assert config.lowercase is False
        assert config.remove_stopwords is False
