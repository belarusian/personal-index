"""Comprehensive tests for experiment_test utility functions."""

import pytest
from experiment_test import slugify, truncate, word_count


# ─── slugify tests ───────────────────────────────────────────────

class TestSlugify:
    def test_basic_slugification(self):
        assert slugify("Hello World") == "hello-world"

    def test_lowercase_conversion(self):
        assert slugify("HELLO WORLD") == "hello-world"

    def test_special_characters_removed(self):
        assert slugify("Hello, World!") == "hello-world"

    def test_multiple_spaces(self):
        assert slugify("Hello   World") == "hello-world"

    def test_leading_trailing_spaces(self):
        assert slugify("  Hello World  ") == "hello-world"

    def test_numbers_preserved(self):
        assert slugify("Python 3.10") == "python-3-10"

    def test_underscores_become_hyphens(self):
        assert slugify("hello_world") == "hello-world"

    def test_consecutive_hyphens_collapsed(self):
        assert slugify("hello---world") == "hello-world"

    def test_empty_string(self):
        assert slugify("") == ""

    def test_only_special_chars(self):
        assert slugify("!@#$%") == ""

    def test_mixed_special_chars_and_spaces(self):
        assert slugify("  Hello,   World!  ") == "hello-world"

    def test_unicode_letters_preserved(self):
        # Unicode letters are kept as-is
        assert slugify("café résumé") == "café-résumé"

    def test_single_word(self):
        assert slugify("Hello") == "hello"

    def test_already_slug(self):
        assert slugify("hello-world") == "hello-world"

    def test_leading_trailing_hyphens_stripped(self):
        assert slugify("-hello-world-") == "hello-world"


# ─── truncate tests ──────────────────────────────────────────────

class TestTruncate:
    def test_no_truncation_needed(self):
        assert truncate("Hello", 100) == "Hello"

    def test_exact_length(self):
        assert truncate("Hello", 5) == "Hello"

    def test_basic_truncation(self):
        # "Hello, World!" (13 chars), max_length=8, suffix="..." (3 chars)
        # text[:5] + "..." = "Hello..."
        assert truncate("Hello, World!", 8) == "Hello..."

    def test_custom_suffix(self):
        # "Hello, World!" (13 chars), max_length=8, suffix="--" (2 chars)
        # text[:6] + "--" = "Hello,--"
        assert truncate("Hello, World!", 8, suffix="--") == "Hello,--"

    def test_suffix_longer_than_max_length(self):
        assert truncate("Hello", 2, suffix="...") == ".."

    def test_empty_string(self):
        assert truncate("", 10) == ""

    def test_max_length_zero(self):
        assert truncate("Hello", 0, suffix="...") == ""

    def test_truncation_with_spaces(self):
        # "Hello World" (11 chars), max_length=5, suffix="..." (3 chars)
        # text[:2] + "..." = "He..."
        assert truncate("Hello World", 5) == "He..."

    def test_suffix_included_in_length(self):
        # "Hello, World!" is exactly 13 chars, max_length=13 → no truncation
        result = truncate("Hello, World!", 13)
        assert result == "Hello, World!"
        assert len(result) == 13

    def test_very_long_text(self):
        long_text = "A" * 1000
        result = truncate(long_text, 20)
        assert len(result) == 20
        assert result.endswith("...")

    def test_custom_suffix_length(self):
        result = truncate("Hello, World!", 10, suffix="[truncated]")
        assert len(result) <= 10

    def test_no_truncation_when_equal(self):
        assert truncate("abc", 3) == "abc"


# ─── word_count tests ────────────────────────────────────────────

class TestWordCount:
    def test_simple_sentence(self):
        assert word_count("Hello world") == 2

    def test_single_word(self):
        assert word_count("Hello") == 1

    def test_multiple_spaces(self):
        assert word_count("Hello   world") == 2

    def test_leading_trailing_spaces(self):
        assert word_count("  Hello world  ") == 2

    def test_empty_string(self):
        assert word_count("") == 0

    def test_only_spaces(self):
        assert word_count("   ") == 0

    def test_newlines_and_tabs(self):
        assert word_count("Hello\nworld\tfoo") == 3

    def test_punctuation_attached_to_words(self):
        assert word_count("Hello, world!") == 2

    def test_long_sentence(self):
        assert word_count("The quick brown fox jumps over the lazy dog") == 9

    def test_numbers_as_words(self):
        assert word_count("I have 2 cats and 3 dogs") == 7

    def test_mixed_whitespace(self):
        assert word_count("One\ttwo\nthree  four") == 4

    def test_single_space(self):
        assert word_count(" ") == 0
