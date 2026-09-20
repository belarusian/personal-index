"""Adversarial deep tests for personal_index.text_utils.

Cycle 328 - VALIDATOR probe.

Covers all 15 public functions with edge cases:
  - None / empty / whitespace / unicode / duplicate / out-of-range inputs
  - Truncation / normalization invariants
  - Idempotence
  - Negative-slice guard (CONTRACTS.md binding rule)
  - Divisor guard (CONTRACTS.md binding rule, read_time_minutes wpm)
  - At least one end-to-end CLI run
"""

from __future__ import annotations

import subprocess
import sys

import pytest

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


# ── normalize_whitespace ──────────────────────────────────────────────────


class TestNormalizeWhitespace:
    def test_empty_string(self):
        assert normalize_whitespace("") == ""

    def test_none_returns_empty(self):
        assert normalize_whitespace(None) == ""  # type: ignore[arg-type]

    def test_whitespace_only(self):
        assert normalize_whitespace("   \t\n  ") == ""

    def test_single_space(self):
        assert normalize_whitespace("a b") == "a b"

    def test_multiple_spaces_collapsed(self):
        assert normalize_whitespace("a   b    c") == "a b c"

    def test_leading_trailing_stripped(self):
        assert normalize_whitespace("  hello  ") == "hello"

    def test_newlines_collapsed(self):
        assert normalize_whitespace("a\nb\nc") == "a b c"

    def test_tabs_collapsed(self):
        assert normalize_whitespace("a\tb\tc") == "a b c"

    def test_unicode_whitespace(self):
        # NBSP, em-space, ideographic space
        assert normalize_whitespace("a\u00a0b\u2003c\u3000d") == "a b c d"

    def test_idempotence(self):
        text = "  hello   world  "
        once = normalize_whitespace(text)
        twice = normalize_whitespace(once)
        assert once == twice

    def test_mixed_whitespace(self):
        assert normalize_whitespace("a \t\n b") == "a b"


# ── remove_html_tags ──────────────────────────────────────────────────────


class TestRemoveHtmlTags:
    def test_empty_string(self):
        assert remove_html_tags("") == ""

    def test_none_returns_empty(self):
        assert remove_html_tags(None) == ""  # type: ignore[arg-type]

    def test_plain_text_unchanged(self):
        assert remove_html_tags("hello world") == "hello world"

    def test_simple_tag_stripped(self):
        assert remove_html_tags("<b>bold</b>") == "bold"

    def test_nested_tags(self):
        assert remove_html_tags("<div><p>text</p></div>") == "text"

    def test_script_content_removed(self):
        assert remove_html_tags("<script>var x=1;</script>hello") == "hello"

    def test_style_content_removed(self):
        assert remove_html_tags("<style>.a{color:red}</style>hello") == "hello"

    def test_html_entities_decoded(self):
        assert remove_html_tags("a&nbsp;b&amp;c") == "a b&c"

    def test_lt_gt_entities(self):
        assert remove_html_tags("&lt;tag&gt;") == "<tag>"

    def test_quot_entities(self):
        assert remove_html_tags("&quot;hello&quot;") == '"hello"'

    def test_apos_entity(self):
        assert remove_html_tags("it&#39;s") == "it's"

    def test_mixed_tags_and_entities(self):
        result = remove_html_tags("<p>Hello &amp; welcome</p>")
        assert result == "Hello & welcome"

    def test_unchanged_plain_text_idempotent(self):
        text = "plain text no tags"
        once = remove_html_tags(text)
        twice = remove_html_tags(once)
        assert once == twice

    def test_unicode_content_preserved(self):
        assert remove_html_tags("<p>héllo wörld</p>") == "héllo wörld"


# ── truncate_text ─────────────────────────────────────────────────────────


class TestTruncateText:
    def test_empty_string(self):
        assert truncate_text("") == ""

    def test_none_returns_empty(self):
        assert truncate_text(None) == ""  # type: ignore[arg-type]

    def test_short_text_unchanged(self):
        assert truncate_text("hello", 10) == "hello"

    def test_exact_length_unchanged(self):
        assert truncate_text("hello", 5) == "hello"

    def test_truncation_appends_suffix(self):
        result = truncate_text("hello world", 5)
        assert result.endswith("...")
        assert len(result) <= 5 + 3  # max_length + suffix

    def test_word_boundary_preferred(self):
        # "hello world" truncated at 8: "hello wo" -> last_space at 5 > 4.8
        # so cut at space: "hello..."
        result = truncate_text("hello world", 8)
        assert result == "hello..."

    def test_no_word_boundary_hard_cut(self):
        # "helloworld" truncated at 5: no space, hard cut
        result = truncate_text("helloworld", 5)
        assert result == "hello..."

    def test_custom_suffix(self):
        result = truncate_text("hello world", 5, suffix="[...]")
        assert result.endswith("[...]")

    @pytest.mark.xfail(
        strict=True,
        reason="QA-60: truncate_text negative max_length leaks negative-slice semantics",
    )
    def test_negative_max_length_negative_slice_leak(self):
        """CONTRACTS.md negative-slice guard: max_length < 0 must yield the
        same result as max_length == 0 (the zero bound).

        With max_length=0: text[:0] = '', result = '...' (just suffix).
        With max_length=-5: text[:-5] is a NEGATIVE SLICE (all-but-last-5),
        which leaks Python negative-slice semantics.
        """
        text = "hello world this is a test"
        zero_result = truncate_text(text, 0)
        neg_result = truncate_text(text, -5)
        assert neg_result == zero_result, (
            f"Negative max_length=-5 leaked negative-slice semantics: "
            f"got {neg_result!r}, expected {zero_result!r} (same as max_length=0)"
        )

    @pytest.mark.xfail(
        strict=True,
        reason="QA-60: truncate_text negative max_length leaks negative-slice semantics",
    )
    def test_negative_max_length_small_text(self):
        """Even for short text, negative max_length must match zero bound."""
        text = "short"
        zero_result = truncate_text(text, 0)
        neg_result = truncate_text(text, -1)
        assert neg_result == zero_result

    def test_truncation_stable_when_no_truncation_needed(self):
        # If text is already short enough, truncation is a no-op (idempotent)
        text = "short"
        once = truncate_text(text, 100)
        twice = truncate_text(once, 100)
        assert once == twice == text


# ── extract_sentences ─────────────────────────────────────────────────────


class TestExtractSentences:
    def test_empty_string(self):
        assert extract_sentences("") == []

    def test_none_returns_empty(self):
        assert extract_sentences(None) == []  # type: ignore[arg-type]

    def test_single_sentence(self):
        assert extract_sentences("Hello world.") == ["Hello world."]

    def test_multiple_sentences(self):
        result = extract_sentences("First one. Second two! Third three?")
        assert len(result) == 3

    def test_min_length_filters_short(self):
        result = extract_sentences("Hi. Hello there. How are you doing today?")
        # "Hi." is 3 chars < 10, filtered out
        assert "Hi." not in result

    def test_no_punctuation_single_chunk(self):
        result = extract_sentences("no punctuation here at all")
        assert len(result) == 1

    def test_multiple_sentences_with_min_length(self):
        result = extract_sentences("This is the first sentence. This is the second one. This is the third one.")
        assert len(result) == 3

    def test_whitespace_only(self):
        assert extract_sentences("   ") == []

    def test_idempotence(self):
        text = "One two three. Four five six. Seven eight nine."
        once = extract_sentences(text)
        # Re-extracting from joined sentences should be stable
        joined = " ".join(once)
        twice = extract_sentences(joined)
        assert once == twice


# ── extract_paragraphs ────────────────────────────────────────────────────


class TestExtractParagraphs:
    def test_empty_string(self):
        assert extract_paragraphs("") == []

    def test_none_returns_empty(self):
        assert extract_paragraphs(None) == []  # type: ignore[arg-type]

    def test_single_paragraph(self):
        text = "This is a single paragraph with enough words to pass."
        result = extract_paragraphs(text)
        assert len(result) == 1

    def test_multiple_paragraphs(self):
        text = (
            "First paragraph with enough words to pass the minimum.\n\n"
            "Second paragraph also has enough words to pass."
        )
        result = extract_paragraphs(text)
        assert len(result) == 2

    def test_min_length_filters_short(self):
        text = "Short.\n\nThis is a long enough paragraph to pass the filter."
        result = extract_paragraphs(text, min_length=20)
        assert len(result) == 1
        assert result[0].startswith("This is a long")

    def test_no_double_newline_single_chunk(self):
        text = "Just one line with enough words to pass the minimum length."
        result = extract_paragraphs(text)
        assert len(result) == 1

    def test_whitespace_only(self):
        assert extract_paragraphs("   \n\n   ") == []

    def test_idempotence(self):
        text = (
            "First paragraph with enough words to pass the minimum length.\n\n"
            "Second paragraph also has enough words to pass the minimum."
        )
        once = extract_paragraphs(text)
        joined = "\n\n".join(once)
        twice = extract_paragraphs(joined)
        assert once == twice


# ── word_frequency ────────────────────────────────────────────────────────


class TestWordFrequency:
    def test_empty_string(self):
        assert word_frequency("") == {}

    def test_none_returns_empty(self):
        assert word_frequency(None) == {}  # type: ignore[arg-type]

    def test_basic_counting(self):
        result = word_frequency("hello hello world")
        assert result["hello"] == 2
        assert result["world"] == 1

    def test_min_freq_filters(self):
        result = word_frequency("a a b", min_freq=2)
        assert "a" in result
        assert "b" not in result

    def test_stop_words_excluded(self):
        result = word_frequency("the cat the dog", stop_words={"the"})
        assert "the" not in result
        assert "cat" in result
        assert "dog" in result

    def test_case_insensitive(self):
        result = word_frequency("Hello hello HELLO")
        assert result["hello"] == 3

    def test_negative_min_freq_same_as_zero(self):
        """Negative min_freq is out-of-range; must yield same as min_freq=0."""
        text = "a a b c"
        zero_result = word_frequency(text, min_freq=0)
        neg_result = word_frequency(text, min_freq=-1)
        assert neg_result == zero_result

    def test_unicode_words_ignored(self):
        # \b[a-zA-Z]+\b only matches ASCII letters
        result = word_frequency("héllo wörld")
        assert "hello" not in result  # é is not [a-zA-Z]
        assert "world" not in result  # ö is not [a-zA-Z]

    def test_idempotence(self):
        text = "the cat sat on the mat"
        once = word_frequency(text)
        # Re-running on the same text should give the same result
        twice = word_frequency(text)
        assert once == twice


# ── extract_keywords ──────────────────────────────────────────────────────


class TestExtractKeywords:
    def test_empty_string(self):
        assert extract_keywords("") == []

    def test_none_returns_empty(self):
        assert extract_keywords(None) == []  # type: ignore[arg-type]

    def test_top_n_zero_returns_empty(self):
        assert extract_keywords("hello hello world", top_n=0) == []

    def test_top_n_negative_returns_empty(self):
        """CONTRACTS.md negative-slice guard: top_n < 0 must return []."""
        assert extract_keywords("hello hello world", top_n=-1) == []

    def test_top_n_limits_results(self):
        text = "a a b b c c d d"
        result = extract_keywords(text, top_n=2, min_freq=2)
        assert len(result) <= 2

    def test_sorted_by_frequency_desc(self):
        text = "a a a b b c"
        result = extract_keywords(text, top_n=3, min_freq=1)
        freqs = [f for _, f in result]
        assert freqs == sorted(freqs, reverse=True)

    def test_min_freq_threshold(self):
        text = "a a a b c"
        result = extract_keywords(text, top_n=10, min_freq=2)
        words = {w for w, _ in result}
        assert "a" in words
        # b and c appear once, below min_freq=2, but may be included
        # to fill top_n slots

    def test_idempotence(self):
        text = "the quick brown fox jumps over the lazy dog"
        once = extract_keywords(text, top_n=5)
        twice = extract_keywords(text, top_n=5)
        assert once == twice


# ── levenshtein_distance ──────────────────────────────────────────────────


class TestLevenshteinDistance:
    def test_identical_strings(self):
        assert levenshtein_distance("hello", "hello") == 0

    def test_empty_vs_nonempty(self):
        assert levenshtein_distance("", "abc") == 3

    def test_both_empty(self):
        assert levenshtein_distance("", "") == 0

    def test_single_insertion(self):
        assert levenshtein_distance("abc", "ab") == 1

    def test_single_deletion(self):
        assert levenshtein_distance("ab", "abc") == 1

    def test_single_substitution(self):
        assert levenshtein_distance("abc", "axc") == 1

    def test_symmetry(self):
        assert levenshtein_distance("kitten", "sitting") == levenshtein_distance("sitting", "kitten")

    def test_known_distance(self):
        assert levenshtein_distance("kitten", "sitting") == 3

    def test_unicode(self):
        assert levenshtein_distance("héllo", "héllo") == 0
        assert levenshtein_distance("héllo", "hello") == 1

    def test_long_strings(self):
        s1 = "a" * 100
        s2 = "b" * 100
        assert levenshtein_distance(s1, s2) == 100


# ── similarity_ratio ──────────────────────────────────────────────────────


class TestSimilarityRatio:
    def test_identical_strings(self):
        assert similarity_ratio("hello", "hello") == 1.0

    def test_both_empty(self):
        assert similarity_ratio("", "") == 1.0

    def test_one_empty(self):
        assert similarity_ratio("", "abc") == 0.0

    def test_completely_different(self):
        assert similarity_ratio("abc", "xyz") == 0.0

    def test_range_0_to_1(self):
        for s1 in ["", "a", "hello", "hello world"]:
            for s2 in ["", "b", "hello", "completely different"]:
                r = similarity_ratio(s1, s2)
                assert 0.0 <= r <= 1.0, f"similarity_ratio({s1!r}, {s2!r}) = {r} out of range"

    def test_symmetry(self):
        assert similarity_ratio("kitten", "sitting") == similarity_ratio("sitting", "kitten")

    def test_none_inputs(self):
        # None is falsy; both None -> 1.0, one None -> 0.0
        assert similarity_ratio(None, None) == 1.0  # type: ignore[arg-type]
        assert similarity_ratio(None, "abc") == 0.0  # type: ignore[arg-type]
        assert similarity_ratio("abc", None) == 0.0  # type: ignore[arg-type]


# ── slugify ───────────────────────────────────────────────────────────────


class TestSlugify:
    def test_empty_string(self):
        assert slugify("") == ""

    def test_none_returns_empty(self):
        assert slugify(None) == ""  # type: ignore[arg-type]

    def test_basic_lowercase(self):
        assert slugify("Hello World") == "hello-world"

    def test_special_chars_replaced(self):
        assert slugify("Hello, World!") == "hello-world"

    def test_unicode_normalized(self):
        # NFKD decomposition: é -> e
        assert slugify("héllo") == "hello"

    def test_multiple_spaces_collapsed(self):
        assert slugify("hello   world") == "hello-world"

    def test_leading_trailing_hyphens_stripped(self):
        assert slugify("  hello  ") == "hello"

    def test_only_special_chars(self):
        assert slugify("!!!") == ""

    def test_mixed_case_and_numbers(self):
        assert slugify("Hello World 123") == "hello-world-123"

    def test_idempotence(self):
        text = "Hello World"
        once = slugify(text)
        twice = slugify(once)
        assert once == twice


# ── highlight_text ────────────────────────────────────────────────────────


class TestHighlightText:
    def test_empty_text(self):
        assert highlight_text("", ["term"]) == ""

    def test_none_text_returns_none(self):
        assert highlight_text(None, ["term"]) is None  # type: ignore[arg-type]

    def test_empty_terms(self):
        assert highlight_text("hello", []) == "hello"

    def test_no_match(self):
        assert highlight_text("hello", ["world"]) == "hello"

    def test_single_term(self):
        result = highlight_text("hello world", ["world"])
        assert result == "hello <mark>world</mark>"

    def test_case_insensitive(self):
        # highlight_text uses the term's case (from term_map), not the matched text's case
        result = highlight_text("Hello World", ["hello"])
        assert result == "<mark>hello</mark> World"

    def test_multiple_terms(self):
        result = highlight_text("hello world foo", ["hello", "foo"])
        assert "<mark>hello</mark>" in result
        assert "<mark>foo</mark>" in result

    def test_custom_tag(self):
        result = highlight_text("hello", ["hello"], tag="b")
        assert result == "<b>hello</b>"

    def test_term_not_rematched_inside_marker(self):
        """Longest-first matching: shorter terms must not re-match inside
        markers inserted for longer terms."""
        result = highlight_text("hello world", ["hello", "hello world"])
        # "hello world" is longer, matched first
        assert result == "<mark>hello world</mark>"

    def test_empty_term_in_list_ignored(self):
        result = highlight_text("hello", ["", "hello"])
        assert result == "<mark>hello</mark>"

    def test_idempotence_on_no_match(self):
        text = "no matches here"
        once = highlight_text(text, ["xyz"])
        twice = highlight_text(once, ["xyz"])
        assert once == twice


# ── count_words ───────────────────────────────────────────────────────────


class TestCountWords:
    def test_empty_string(self):
        assert count_words("") == 0

    def test_none_returns_zero(self):
        assert count_words(None) == 0  # type: ignore[arg-type]

    def test_single_word(self):
        assert count_words("hello") == 1

    def test_multiple_words(self):
        assert count_words("hello world foo") == 3

    def test_whitespace_only(self):
        assert count_words("   \t\n  ") == 0

    def test_multiple_spaces_between_words(self):
        assert count_words("hello   world") == 2

    def test_unicode_words(self):
        # split() splits on any whitespace
        assert count_words("héllo wörld") == 2


# ── count_characters ──────────────────────────────────────────────────────
# (already covered in test_text_utils.py, but re-verify key invariants)


class TestCountCharacters:
    def test_empty_string(self):
        assert count_characters("") == 0

    def test_none_returns_zero(self):
        assert count_characters(None) == 0  # type: ignore[arg-type]

    def test_include_spaces_true(self):
        assert count_characters("a b c") == 5

    def test_include_spaces_false(self):
        assert count_characters("a b c", include_spaces=False) == 3

    def test_unicode(self):
        assert count_characters("héllo") == 5
        assert count_characters("héllo", include_spaces=False) == 5


# ── read_time_minutes ─────────────────────────────────────────────────────


class TestReadTimeMinutes:
    def test_empty_text(self):
        assert read_time_minutes("") == 0

    def test_none_text(self):
        assert read_time_minutes(None) == 0  # type: ignore[arg-type]

    def test_wpm_zero_returns_zero(self):
        """CONTRACTS.md divisor guard: wpm <= 0 -> 0."""
        assert read_time_minutes("hello world", wpm=0) == 0

    def test_wpm_negative_returns_zero(self):
        """CONTRACTS.md divisor guard: wpm < 0 -> 0."""
        assert read_time_minutes("hello world", wpm=-1) == 0

    def test_normal_calculation(self):
        # 200 words at 200 wpm = 1 minute
        text = " ".join(["word"] * 200)
        assert read_time_minutes(text, wpm=200) == 1

    def test_ceiling_rounding(self):
        # 201 words at 200 wpm = ceil(201/200) = 2
        text = " ".join(["word"] * 201)
        assert read_time_minutes(text, wpm=200) == 2

    def test_exact_division(self):
        # 400 words at 200 wpm = 2
        text = " ".join(["word"] * 400)
        assert read_time_minutes(text, wpm=200) == 2

    def test_idempotence(self):
        text = " ".join(["word"] * 100)
        once = read_time_minutes(text, wpm=200)
        twice = read_time_minutes(text, wpm=200)
        assert once == twice


# ── tokenize ──────────────────────────────────────────────────────────────


class TestTokenize:
    def test_empty_string(self):
        assert tokenize("") == []

    def test_none_returns_empty(self):
        assert tokenize(None) == []  # type: ignore[arg-type]

    def test_basic_tokenization(self):
        assert tokenize("hello world") == ["hello", "world"]

    def test_lowercase_default(self):
        assert tokenize("Hello World") == ["hello", "world"]

    def test_no_lowercase(self):
        assert tokenize("Hello World", lowercase=False) == ["Hello", "World"]

    def test_stopwords_removed(self):
        result = tokenize("the cat and the dog", remove_stopwords=True)
        assert "the" not in result
        assert "and" not in result
        assert "cat" in result
        assert "dog" in result

    def test_stopwords_kept_by_default(self):
        result = tokenize("the cat and the dog")
        assert "the" in result
        assert "and" in result

    def test_numbers_tokenized(self):
        result = tokenize("hello 123 world")
        assert "123" in result

    def test_mixed_alphanumeric(self):
        result = tokenize("hello world123 foo-bar")
        assert "hello" in result
        assert "world123" in result
        assert "foo-bar" in result

    def test_idempotence(self):
        text = "the quick brown fox"
        once = tokenize(text)
        twice = tokenize(" ".join(once))
        assert once == twice


# ── End-to-end CLI run ────────────────────────────────────────────────────


class TestCliEndToEnd:
    def test_cli_help_runs(self):
        """End-to-end: the installed CLI must respond to --help."""
        result = subprocess.run(
            [sys.executable, "-m", "personal_index", "--help"],
            capture_output=True,
            text=True,
            timeout=30,
        )
        assert result.returncode == 0, f"CLI --help failed: {result.stderr}"
        assert "usage" in result.stdout.lower() or "usage" in result.stderr.lower()
