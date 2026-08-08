"""Comprehensive tests for experiment_test utility functions."""

import pytest
from experiment_test import slugify, truncate, word_count


# ─── slugify tests ───────────────────────────────────────────────

class TestSlugify:
    def test_basic_slugification(self):
        assert slugify("Hello World") == "hello-world"

    def test_with_special_characters(self):
        assert slugify("Hello, World!") == "hello-world"

    def test_with_numbers(self):
        # Dots are stripped by slugify, so "3.10" becomes "310"
        assert slugify("Python 3.10 is great") == "python-310-is-great"

    def test_leading_trailing_whitespace(self):
        assert slugify("  Hello World  ") == "hello-world"

    def test_multiple_spaces(self):
        assert slugify("Hello    World") == "hello-world"

    def test_mixed_case(self):
        assert slugify("HeLLo WoRLd") == "hello-world"

    def test_already_slug(self):
        assert slugify("hello-world") == "hello-world"

    def test_empty_string(self):
        assert slugify("") == ""

    def test_only_special_characters(self):
        assert slugify("!@#$%^&*()") == ""

    def test_only_whitespace(self):
        assert slugify("   ") == ""

    def test_underscores_converted(self):
        assert slugify("hello_world") == "hello-world"

    def test_consecutive_hyphens_removed(self):
        assert slugify("hello---world") == "hello-world"

    def test_unicode_letters_preserved(self):
        # Python's \w includes unicode word characters, so accented chars stay
        assert slugify("café résumé") == "café-résumé"

    def test_leading_trailing_hyphens_removed(self):
        assert slugify("-hello-world-") == "hello-world"

    def test_single_word(self):
        assert slugify("Hello") == "hello"

    def test_with_apostrophes(self):
        assert slugify("It's a test") == "its-a-test"


# ─── truncate tests ──────────────────────────────────────────────

class TestTruncate:
    def test_no_truncation_needed(self):
        assert truncate("Hello", 10) == "Hello"

    def test_exact_length(self):
        assert truncate("Hello", 5) == "Hello"

    def test_basic_truncation(self):
        assert truncate("Hello, World!", 8) == "Hello..."

    def test_custom_suffix(self):
        # max_length=8, suffix=">>" -> text[:6] + ">>" = "Hello,>>" (8 chars)
        assert truncate("Hello, World!", 8, suffix=">>") == "Hello,>>"

    def test_empty_string(self):
        assert truncate("", 5) == ""

    def test_max_length_equals_suffix_length(self):
        assert truncate("Hello, World!", 3) == "..."

    def test_max_length_less_than_suffix_raises(self):
        with pytest.raises(ValueError, match="must be at least"):
            truncate("Hello", 2)

    def test_custom_suffix_too_long_raises(self):
        with pytest.raises(ValueError, match="must be at least"):
            truncate("Hello", 5, suffix="...too long")

    def test_truncation_at_word_boundary(self):
        # max_length=10, suffix="..." -> text[:7] + "..." = "Hello W..." (10 chars)
        assert truncate("Hello World", 10) == "Hello W..."

    def test_very_long_text(self):
        result = truncate("a" * 1000, 10)
        assert result == "a" * 7 + "..."
        assert len(result) == 10

    def test_single_char_suffix(self):
        assert truncate("Hello World", 6, suffix="~") == "Hello~"

    def test_no_suffix(self):
        assert truncate("Hello World", 5, suffix="") == "Hello"

    def test_unicode_text(self):
        assert truncate("こんにちは世界", 5) == "こん..."


# ─── word_count tests ────────────────────────────────────────────

class TestWordCount:
    def test_simple_sentence(self):
        assert word_count("Hello world") == 2

    def test_single_word(self):
        assert word_count("Hello") == 1

    def test_empty_string(self):
        assert word_count("") == 0

    def test_only_whitespace(self):
        assert word_count("   ") == 0

    def test_multiple_spaces_between_words(self):
        assert word_count("Hello   world") == 2

    def test_leading_trailing_whitespace(self):
        assert word_count("  Hello world  ") == 2

    def test_newlines_and_tabs(self):
        assert word_count("Hello\nworld\tfoo") == 3

    def test_punctuation_attached_to_words(self):
        assert word_count("Hello, world!") == 2

    def test_numbers_as_words(self):
        assert word_count("I have 3 cats") == 4

    def test_mixed_whitespace(self):
        assert word_count("  One  two   three  ") == 3

    def test_hyphenated_word(self):
        assert word_count("well-known") == 1

    def test_long_sentence(self):
        sentence = "The quick brown fox jumps over the lazy dog"
        assert word_count(sentence) == 9

    def test_tabs_only(self):
        assert word_count("\t\t\t") == 0

    def test_newlines_only(self):
        assert word_count("\n\n\n") == 0
