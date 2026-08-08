"""Comprehensive tests for experiment_test module."""

import pytest
from experiment_test import slugify, truncate, word_count


# ─── slugify tests ───────────────────────────────────────────────

class TestSlugify:
    def test_simple_lowercase(self):
        assert slugify("Hello World") == "hello-world"

    def test_already_lowercase(self):
        assert slugify("hello world") == "hello-world"

    def test_special_characters_removed(self):
        assert slugify("Hello, World!") == "hello-world"

    def test_multiple_spaces(self):
        assert slugify("Hello   World") == "hello-world"

    def test_leading_trailing_spaces(self):
        assert slugify("  Hello World  ") == "hello-world"

    def test_consecutive_special_chars(self):
        assert slugify("Hello---World") == "hello-world"

    def test_mixed_special_chars_and_spaces(self):
        assert slugify("Hello   ---   World") == "hello-world"

    def test_empty_string(self):
        assert slugify("") == ""

    def test_only_special_characters(self):
        assert slugify("!@#$%^&*()") == ""

    def test_only_spaces(self):
        assert slugify("   ") == ""

    def test_single_word(self):
        assert slugify("Hello") == "hello"

    def test_numbers_preserved(self):
        assert slugify("Hello World 123") == "hello-world-123"

    def test_underscores_become_hyphens(self):
        assert slugify("hello_world") == "hello-world"

    def test_unicode_characters_preserved(self):
        # Python's \w includes unicode letters, so accented chars are kept
        assert slugify("Café résumé") == "café-résumé"

    def test_mixed_case_with_numbers(self):
        assert slugify("Hello World 123 Test") == "hello-world-123-test"


# ─── truncate tests ──────────────────────────────────────────────

class TestTruncate:
    def test_no_truncation_needed(self):
        assert truncate("Hello", 10) == "Hello"

    def test_exact_length(self):
        assert truncate("Hello", 5) == "Hello"

    def test_basic_truncation(self):
        assert truncate("Hello World", 8) == "Hello..."

    def test_custom_suffix(self):
        assert truncate("Hello World", 8, suffix="~") == "Hello W~"

    def test_max_length_less_than_suffix(self):
        assert truncate("Hello World", 2) == ".."

    def test_max_length_equal_to_suffix(self):
        assert truncate("Hello World", 3) == "..."

    def test_empty_string(self):
        assert truncate("", 5) == ""

    def test_truncation_with_long_suffix(self):
        assert truncate("Hi", 10, suffix="[truncated]") == "Hi"

    def test_truncation_boundary(self):
        assert truncate("Hello World", 11) == "Hello World"

    def test_truncation_just_over_boundary(self):
        # "Hello World" is 11 chars, max_length=10, suffix="..." (3 chars)
        # Result: first (10-3)=7 chars + "..." = "Hello W..."
        assert truncate("Hello World", 10) == "Hello W..."

    def test_single_char_suffix(self):
        assert truncate("Hello World", 6, suffix="!") == "Hello!"

    def test_unicode_text(self):
        # "Hello 世界" is 8 characters, max_length=7, suffix="..." (3 chars)
        # Result: first (7-3)=4 chars + "..." = "Hell..."
        assert truncate("Hello 世界", 7) == "Hell..."

    def test_max_length_zero(self):
        assert truncate("Hello", 0) == ""


# ─── word_count tests ────────────────────────────────────────────

class TestWordCount:
    def test_simple_sentence(self):
        assert word_count("Hello World") == 2

    def test_single_word(self):
        assert word_count("Hello") == 1

    def test_empty_string(self):
        assert word_count("") == 0

    def test_only_spaces(self):
        assert word_count("   ") == 0

    def test_multiple_spaces_between_words(self):
        assert word_count("Hello   World") == 2

    def test_leading_trailing_spaces(self):
        assert word_count("  Hello World  ") == 2

    def test_newlines_and_tabs(self):
        assert word_count("Hello\nWorld\tTest") == 3

    def test_punctuation_attached_to_words(self):
        assert word_count("Hello, World!") == 2

    def test_numbers_as_words(self):
        assert word_count("I have 2 cats") == 4

    def test_mixed_whitespace(self):
        assert word_count("  Hello \t World \n Test  ") == 3

    def test_single_space(self):
        assert word_count(" ") == 0

    def test_long_sentence(self):
        assert word_count("The quick brown fox jumps over the lazy dog") == 9
