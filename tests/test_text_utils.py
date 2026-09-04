"""Tests for text_utils module."""

from __future__ import annotations

from personal_index.text_utils import (
    count_characters,
    count_words,
    extract_keywords,
    extract_paragraphs,
    extract_sentences,
    highlight_text,
    levenshtein_distance,
    normalize_whitespace,
    read_time_minutes,
    remove_html_tags,
    similarity_ratio,
    slugify,
    tokenize,
    truncate_text,
    word_frequency,
)


class TestNormalizeWhitespace:
    def test_collapse_spaces(self):
        assert normalize_whitespace("hello   world") == "hello world"

    def test_collapse_tabs_newlines(self):
        assert normalize_whitespace("hello\t\nworld") == "hello world"

    def test_strip_leading_trailing(self):
        assert normalize_whitespace("  hello  ") == "hello"

    def test_empty_string(self):
        assert normalize_whitespace("") == ""

    def test_none(self):
        assert normalize_whitespace(None) == ""  # type: ignore

    def test_single_word(self):
        assert normalize_whitespace("hello") == "hello"


class TestRemoveHtmlTags:
    def test_basic_tags(self):
        assert remove_html_tags("<p>Hello</p>") == "Hello"

    def test_nested_tags(self):
        assert remove_html_tags("<div><p>Hello <b>world</b></p></div>") == "Hello world"

    def test_script_removal(self):
        result = remove_html_tags("<p>Text</p><script>alert('xss')</script>")
        assert "alert" not in result
        assert "Text" in result

    def test_style_removal(self):
        result = remove_html_tags("<style>.x{color:red}</style><p>Text</p>")
        assert "color" not in result
        assert "Text" in result

    def test_html_entities(self):
        result = remove_html_tags("&nbsp;hello&nbsp;")
        assert "hello" in result

    def test_amp_entity(self):
        assert remove_html_tags("a&amp;b") == "a&b"

    def test_empty_html(self):
        assert remove_html_tags("") == ""

    def test_none_input(self):
        assert remove_html_tags(None) == ""  # type: ignore


class TestTruncateText:
    def test_no_truncation_needed(self):
        assert truncate_text("short", max_length=100) == "short"

    def test_truncation(self):
        result = truncate_text("hello world foo bar", max_length=10)
        assert len(result) <= 13
        assert result.endswith("...")

    def test_custom_suffix(self):
        result = truncate_text("hello world", max_length=5, suffix=">>")
        assert result.endswith(">>")

    def test_empty_string(self):
        assert truncate_text("", max_length=10) == ""

    def test_none_input(self):
        assert truncate_text(None, max_length=10) == ""  # type: ignore

    def test_long_unbroken_tail_cut_mid_word(self):
        # Pins the corrected docstring claim: a word boundary is preferred
        # only when a space exists after 60% of max_length. When the tail
        # is one long unbroken token, the cut lands mid-word (not on a
        # space), so "without breaking words" is NOT guaranteed.
        result = truncate_text("hello world " + "x" * 200, max_length=200)
        assert result.endswith("...")
        # The cut is mid-word: the pre-suffix text does not end on a space.
        assert not result[:-3].endswith(" ")
        # It ends inside the unbroken x-run.
        assert result[:-3].endswith("x")


class TestExtractSentences:
    def test_basic_sentences(self):
        text = "Hello world. This is a test. Final sentence!"
        sentences = extract_sentences(text)
        assert len(sentences) == 3

    def test_min_length_filter(self):
        text = "Hi. This is a longer sentence. Go."
        sentences = extract_sentences(text, min_length=10)
        assert len(sentences) == 1

    def test_empty_text(self):
        assert extract_sentences("") == []

    def test_no_punctuation(self):
        text = "This has no punctuation at all"
        sentences = extract_sentences(text)
        assert len(sentences) == 1


class TestExtractParagraphs:
    def test_basic_paragraphs(self):
        text = "First paragraph with enough words.\n\nSecond paragraph with more content here.\n\nThird paragraph is also long enough."
        paragraphs = extract_paragraphs(text)
        assert len(paragraphs) == 3

    def test_min_length_filter(self):
        text = "Short.\n\nThis is a much longer paragraph with more content."
        paragraphs = extract_paragraphs(text, min_length=20)
        assert len(paragraphs) == 1

    def test_empty_text(self):
        assert extract_paragraphs("") == []

    def test_single_paragraph(self):
        text = "This is a single paragraph with enough content."
        paragraphs = extract_paragraphs(text)
        assert len(paragraphs) == 1


class TestWordFrequency:
    def test_basic_frequency(self):
        freq = word_frequency("the cat sat on the mat")
        assert freq["the"] == 2
        assert freq["cat"] == 1

    def test_min_freq_filter(self):
        freq = word_frequency("the cat sat on the mat", min_freq=2)
        assert "cat" not in freq
        assert "the" in freq

    def test_stop_words(self):
        freq = word_frequency("the cat sat", stop_words={"the"})
        assert "the" not in freq
        assert "cat" in freq

    def test_empty_text(self):
        assert word_frequency("") == {}

    def test_case_insensitive(self):
        freq = word_frequency("Hello hello HELLO")
        assert freq["hello"] == 3


class TestExtractKeywords:
    def test_basic_keywords(self):
        text = "python is great python programming python"
        keywords = extract_keywords(text, top_n=2, min_freq=2)
        assert len(keywords) == 2
        assert keywords[0][0] == "python"

    def test_empty_text(self):
        assert extract_keywords("") == []

    def test_top_n_limit(self):
        text = "a a b b c c d d e e"
        keywords = extract_keywords(text, top_n=3, min_freq=2)
        assert len(keywords) == 3


class TestLevenshteinDistance:
    def test_identical(self):
        assert levenshtein_distance("hello", "hello") == 0

    def test_completely_different(self):
        assert levenshtein_distance("abc", "xyz") == 3

    def test_empty_strings(self):
        assert levenshtein_distance("", "") == 0
        assert levenshtein_distance("abc", "") == 3
        assert levenshtein_distance("", "abc") == 3

    def test_single_edit(self):
        assert levenshtein_distance("cat", "bat") == 1

    def test_insertion(self):
        assert levenshtein_distance("cat", "cats") == 1


class TestSimilarityRatio:
    def test_identical(self):
        assert similarity_ratio("hello", "hello") == 1.0

    def test_completely_different(self):
        assert similarity_ratio("a", "b") == 0.0

    def test_empty_both(self):
        assert similarity_ratio("", "") == 1.0

    def test_one_empty(self):
        assert similarity_ratio("hello", "") == 0.0
        assert similarity_ratio("", "hello") == 0.0

    def test_similar(self):
        ratio = similarity_ratio("hello", "hallo")
        assert 0.5 < ratio < 1.0


class TestSlugify:
    def test_basic_slug(self):
        assert slugify("Hello World") == "hello-world"

    def test_special_characters(self):
        assert slugify("Hello, World!") == "hello-world"

    def test_unicode(self):
        result = slugify("café")
        assert "caf" in result

    def test_empty_string(self):
        assert slugify("") == ""

    def test_multiple_spaces(self):
        assert slugify("hello   world") == "hello-world"


class TestHighlightText:
    def test_basic_highlight(self):
        result = highlight_text("hello world", ["world"])
        assert "<mark>world</mark>" in result

    def test_case_insensitive(self):
        result = highlight_text("Hello World", ["hello"])
        assert "<mark>hello</mark>" in result

    def test_multiple_terms(self):
        result = highlight_text("hello world foo", ["hello", "foo"])
        assert "<mark>hello</mark>" in result
        assert "<mark>foo</mark>" in result

    def test_empty_terms(self):
        assert highlight_text("hello", []) == "hello"

    def test_empty_text(self):
        assert highlight_text("", ["hello"]) == ""

    def test_substring_terms(self):
        """Shorter terms must not be re-matched inside longer-term markers."""
        result = highlight_text("catalog cat", ["catalog", "cat"])
        assert result == "<mark>catalog</mark> <mark>cat</mark>"


class TestCountWords:
    def test_basic(self):
        assert count_words("hello world") == 2

    def test_empty(self):
        assert count_words("") == 0

    def test_none(self):
        assert count_words(None) == 0  # type: ignore


class TestCountCharacters:
    def test_with_spaces(self):
        assert count_characters("hello world") == 11

    def test_without_spaces(self):
        assert count_characters("hello world", include_spaces=False) == 10

    def test_empty(self):
        assert count_characters("") == 0


class TestReadTimeMinutes:
    def test_basic(self):
        text = "word " * 400
        assert read_time_minutes(text) == 2

    def test_short_text(self):
        assert read_time_minutes("hello") == 1

    def test_empty(self):
        assert read_time_minutes("") == 1

    def test_returns_int_type(self):
        # Regression: annotation is -> int; pin the runtime type.
        assert isinstance(read_time_minutes("word " * 400), int)
        assert type(read_time_minutes("hello")) is int
        assert type(read_time_minutes("")) is int


class TestTokenize:
    def test_single_letter_word_preserved(self):
        """Single-letter words must be preserved when remove_stopwords=False."""
        result = tokenize("I like cats", remove_stopwords=False)
        assert "i" in result
        assert result == ["i", "like", "cats"]

    def test_single_letter_word_filtered_with_stopwords(self):
        """Single-letter stopwords are filtered when remove_stopwords=True."""
        result = tokenize("I like cats", remove_stopwords=True)
        assert "i" not in result
        assert result == ["like", "cats"]

    def test_mixed_single_and_multi_letter(self):
        """Mix of single and multi-letter words all preserved."""
        result = tokenize("A B hello 42", remove_stopwords=False)
        assert result == ["a", "b", "hello", "42"]
