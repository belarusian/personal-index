"""Comprehensive tests for experiment_test utility functions."""

from experiment_test import slugify, truncate, word_count


# ─── slugify tests ───────────────────────────────────────────────

class TestSlugify:
    def test_basic_slugification(self):
        assert slugify("Hello World") == "hello-world"

    def test_lowercase_conversion(self):
        assert slugify("HELLO WORLD") == "hello-world"

    def test_remove_special_characters(self):
        assert slugify("Hello, World!") == "hello-world"

    def test_multiple_spaces(self):
        assert slugify("  Multiple   Spaces  ") == "multiple-spaces"

    def test_leading_trailing_spaces(self):
        assert slugify("  Hello World  ") == "hello-world"

    def test_underscores_to_hyphens(self):
        assert slugify("hello_world") == "hello-world"

    def test_numbers_preserved(self):
        assert slugify("Test 123") == "test-123"

    def test_empty_string(self):
        assert slugify("") == ""

    def test_only_special_characters(self):
        assert slugify("!@#$%") == ""

    def test_mixed_special_chars_and_spaces(self):
        assert slugify("Hello,  World!  How are you?") == "hello-world-how-are-you"

    def test_single_word(self):
        assert slugify("Hello") == "hello"

    def test_already_slug(self):
        assert slugify("hello-world") == "hello-world"

    def test_consecutive_hyphens(self):
        assert slugify("hello---world") == "hello-world"

    def test_unicode_letters(self):
        # Non-ASCII letters are kept as-is (they are \w in Python re)
        result = slugify("café résumé")
        assert "café" in result or "cafe" in result


# ─── truncate tests ──────────────────────────────────────────────

class TestTruncate:
    def test_no_truncation_needed(self):
        assert truncate("Hello", 10) == "Hello"

    def test_exact_length(self):
        assert truncate("Hello", 5) == "Hello"

    def test_basic_truncation(self):
        # max_length=8, suffix="..." (3 chars) → text[:5] + "..." = "Hello..."
        assert truncate("Hello, World!", 8) == "Hello..."

    def test_custom_suffix(self):
        # max_length=8, suffix="~" (1 char) → text[:7] + "~" = "Hello, ~"
        assert truncate("Hello, World!", 8, suffix="~") == "Hello, ~"

    def test_max_length_less_than_suffix(self):
        assert truncate("Hello, World!", 2, suffix="...") == ".."

    def test_max_length_equal_to_suffix(self):
        assert truncate("Hello, World!", 3, suffix="...") == "..."

    def test_empty_string(self):
        assert truncate("", 5) == ""

    def test_truncation_at_boundary(self):
        assert truncate("abcdef", 5, suffix="..") == "abc.."

    def test_no_truncation_when_equal(self):
        assert truncate("abc", 3) == "abc"

    def test_single_char_suffix(self):
        assert truncate("Hello World", 6, suffix="*") == "Hello*"

    def test_long_suffix(self):
        assert truncate("Hi", 10, suffix="...") == "Hi"

    def test_truncate_with_unicode(self):
        result = truncate("Hello 世界", 7, suffix="...")
        assert result.endswith("...")
        assert len(result) <= 7


# ─── word_count tests ────────────────────────────────────────────

class TestWordCount:
    def test_simple_words(self):
        assert word_count("Hello world") == 2

    def test_single_word(self):
        assert word_count("Hello") == 1

    def test_multiple_spaces(self):
        # "Multiple" and "spaces" = 2 words
        assert word_count("  Multiple   spaces  ") == 2

    def test_empty_string(self):
        assert word_count("") == 0

    def test_only_spaces(self):
        assert word_count("   ") == 0

    def test_newlines_and_tabs(self):
        assert word_count("Hello\nWorld\tFoo") == 3

    def test_punctuation_attached(self):
        assert word_count("Hello, world!") == 2

    def test_numbers_as_words(self):
        assert word_count("1 2 3") == 3

    def test_mixed_content(self):
        assert word_count("The quick brown fox jumps over the lazy dog") == 9

    def test_single_space(self):
        assert word_count(" ") == 0

    def test_none_input(self):
        assert word_count(None) == 0
