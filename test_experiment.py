"""Comprehensive tests for experiment_test module."""

import pytest
from experiment_test import slugify, truncate, word_count


# ─── slugify tests ───────────────────────────────────────────────

class TestSlugify:
    def test_simple_sentence(self):
        assert slugify("Hello World") == "hello-world"

    def test_with_special_characters(self):
        assert slugify("Hello, World!") == "hello-world"

    def test_with_numbers_and_dots(self):
        assert slugify("Python 3.10") == "python-3-10"

    def test_leading_trailing_whitespace(self):
        assert slugify("  Hello World  ") == "hello-world"

    def test_multiple_spaces(self):
        assert slugify("Hello   World") == "hello-world"

    def test_mixed_case(self):
        assert slugify("Hello WORLD") == "hello-world"

    def test_empty_string(self):
        assert slugify("") == ""

    def test_only_special_characters(self):
        assert slugify("!@#$%") == ""

    def test_underscores(self):
        assert slugify("hello_world") == "hello-world"

    def test_already_slugified(self):
        assert slugify("hello-world") == "hello-world"

    def test_unicode_characters_stripped(self):
        assert slugify("Café résumé") == "caf-rsum"

    def test_consecutive_hyphens(self):
        assert slugify("hello---world") == "hello-world"

    def test_single_word(self):
        assert slugify("Hello") == "hello"

    def test_with_apostrophes(self):
        assert slugify("It's a test") == "its-a-test"

    def test_with_tabs_and_newlines(self):
        assert slugify("Hello\t\nWorld") == "hello-world"


# ─── truncate tests ──────────────────────────────────────────────

class TestTruncate:
    def test_no_truncation_needed(self):
        assert truncate("Hello", 10) == "Hello"

    def test_exact_length(self):
        assert truncate("Hello", 5) == "Hello"

    def test_basic_truncation(self):
        # "Hello, World!" has 13 chars, max_length=8, suffix="..." (3 chars)
        # So we take 8 - 3 = 5 chars from text + suffix = "Hello..."
        assert truncate("Hello, World!", 8) == "Hello..."

    def test_custom_suffix(self):
        # max_length=8, suffix=">>" (2 chars), so 8 - 2 = 6 chars from text
        assert truncate("Hello, World!", 8, suffix=">>") == "Hello,>>"

    def test_suffix_longer_than_max_length(self):
        assert truncate("Hello", 2, suffix="...") == ".."

    def test_empty_string(self):
        assert truncate("", 5) == ""

    def test_max_length_zero(self):
        assert truncate("Hello", 0) == ""

    def test_max_length_equals_suffix_length(self):
        assert truncate("Hello World", 3, suffix="...") == "..."

    def test_unicode_truncation(self):
        # "Hello 世界" is 7 chars, max_length=8, no truncation needed
        assert truncate("Hello 世界", 8) == "Hello 世界"

    def test_no_truncation_when_text_shorter(self):
        assert truncate("Hi", 100) == "Hi"

    def test_truncation_with_spaces(self):
        # "Hello World" is 11 chars, max_length=10, suffix="..." (3 chars)
        # So we take 10 - 3 = 7 chars from text + suffix = "Hello W..."
        assert truncate("Hello World", 10) == "Hello W..."

    def test_custom_suffix_longer(self):
        # max_length=10, suffix="[truncated]" (11 chars)
        # suffix is longer than max_length, so return suffix[:10]
        assert truncate("Hello World", 10, suffix="[truncated]") == "[truncated"


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

    def test_multiple_spaces(self):
        assert word_count("Hello   world") == 2

    def test_leading_trailing_whitespace(self):
        assert word_count("  Hello world  ") == 2

    def test_tabs_and_newlines(self):
        assert word_count("Hello\t\nworld") == 2

    def test_sentence_with_punctuation(self):
        assert word_count("Hello, world!") == 2

    def test_long_sentence(self):
        assert word_count("The quick brown fox jumps over the lazy dog") == 9

    def test_numbers_as_words(self):
        assert word_count("I have 3 cats") == 4

    def test_mixed_whitespace(self):
        assert word_count("a  b\tc\nd") == 4

    def test_single_space(self):
        assert word_count(" ") == 0

    def test_newline_only(self):
        assert word_count("\n") == 0

    def test_unicode_words(self):
        assert word_count("Hello 世界") == 2

    def test_hyphenated_word(self):
        assert word_count("well-known") == 1
