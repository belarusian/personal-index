"""Adversarial deep tests for personal_index.content_summarizer.

Contract source: docs/content-summarizer.md + module docstrings (the
"code is the truth" section). Pins the documented guard/short-text/scoring
paths, the ratio formula, the first-sentence x2.5 / last-sentence x1.1
boosts, document-order preservation, and the standalone-utility nature of
summarize_page.

DEFECT (QA-15): the negative-slice "top N" leak class (QA-1/QA-2/QA-3/QA-4/
QA-5) has a NEW public site missed by QA-5's 9-site sweep:
``summarize(text, max_sentences=-1)`` returns ``sentences[:-1]`` (all-but-last)
instead of ``[]``. The ``0`` guard is correct (returns ``[]``); the negative
bound is not. Pinned xfail-strict below.
"""

from __future__ import annotations

import subprocess
import sys

import pytest

from personal_index.content_summarizer import (
    STOPWORDS,
    SummaryResult,
    _build_summary_result,
    _no_op_result,
    _score_and_select,
    _score_sentence,
    _split_sentences,
    _tokenize,
    _word_frequency,
    summarize,
    summarize_page,
)

# A 6-sentence document, each sentence a distinct repeated keyword so the
# scoring path is deterministic. len > 50 (min_length default).
TEXT = (
    "Alpha alpha alpha. Beta beta beta. Gamma gamma gamma. "
    "Delta delta delta. Epsilon epsilon epsilon. Zeta zeta zeta."
)


# ---------------------------------------------------------------------------
# _split_sentences
# ---------------------------------------------------------------------------
def test_split_sentences_empty():
    assert _split_sentences("") == []


def test_split_sentences_whitespace_only():
    assert _split_sentences("   \n\t  ") == []


def test_split_sentences_normalizes_whitespace():
    assert _split_sentences("A.   B.    C.") == ["A.", "B.", "C."]


def test_split_sentences_requires_uppercase_after_punct():
    # lowercase continuation is NOT a sentence boundary per the regex
    assert _split_sentences("a. b. c.") == ["a. b. c."]


def test_split_sentences_exclamation_and_question():
    assert _split_sentences("Hi! How? Fine.") == ["Hi!", "How?", "Fine."]


def test_split_sentences_unicode_no_crash():
    out = _split_sentences("Привет мир. Как дела? Хорошо.")
    assert isinstance(out, list)
    assert all(isinstance(s, str) for s in out)


def test_split_sentences_drops_empty_fragments():
    # trailing punctuation with nothing after
    assert _split_sentences("One. Two.") == ["One.", "Two."]


# ---------------------------------------------------------------------------
# _tokenize
# ---------------------------------------------------------------------------
def test_tokenize_empty():
    assert _tokenize("") == []


def test_tokenize_all_punctuation():
    assert _tokenize("!!! ??? ...") == []


def test_tokenize_lowercases_and_splits():
    assert _tokenize("Hello, World!") == ["hello", "world"]


def test_tokenize_keeps_digit_runs():
    assert _tokenize("abc 123 def") == ["abc", "123", "def"]


def test_tokenize_apostrophe_is_separator():
    assert _tokenize("don't stop") == ["don", "t", "stop"]


def test_tokenize_unicode_no_crash():
    out = _tokenize("héllo wörld")
    assert isinstance(out, list)
    assert all(isinstance(t, str) for t in out)


# ---------------------------------------------------------------------------
# _word_frequency
# ---------------------------------------------------------------------------
def test_word_frequency_skips_stopwords():
    freq = _word_frequency("the cat and the dog")
    assert "the" not in freq
    assert "and" not in freq
    assert freq["cat"] == 1
    assert freq["dog"] == 1


def test_word_frequency_skips_short_tokens():
    # len <= 2 skipped
    freq = _word_frequency("ab cd efg")
    assert "ab" not in freq
    assert "cd" not in freq
    assert freq["efg"] == 1


def test_word_frequency_counts():
    freq = _word_frequency("cat cat cat dog")
    assert freq["cat"] == 3
    assert freq["dog"] == 1


def test_word_frequency_empty():
    assert _word_frequency("") == {}


# ---------------------------------------------------------------------------
# _score_sentence
# ---------------------------------------------------------------------------
def test_score_sentence_no_tokens_is_zero():
    assert _score_sentence("!!! ???", {}) == 0.0


def test_score_sentence_is_mean_not_sum():
    # two tokens each freq 2 -> mean 2.0, not sum 4.0
    assert _score_sentence("cat dog", {"cat": 2, "dog": 2}) == 2.0


def test_score_sentence_unknown_words_zero():
    assert _score_sentence("zebra", {"cat": 5}) == 0.0


# ---------------------------------------------------------------------------
# _score_and_select
# ---------------------------------------------------------------------------
def test_select_preserves_document_order():
    sentences = ["Alpha alpha.", "Beta beta.", "Gamma gamma.", "Delta delta."]
    freq = _word_frequency(" ".join(sentences))
    # max_sentences=2 -> picks top 2 by score but returns in original order
    sel = _score_and_select(sentences, freq, 2)
    assert len(sel) == 2
    # returned order must be a subsequence of the input order
    idx = [sentences.index(s) for s in sel]
    assert idx == sorted(idx)


def test_select_first_sentence_boost():
    # A single high-frequency sentence that is NOT first should still let the
    # first sentence win when its 2.5x boost dominates.
    sentences = ["Alpha alpha alpha alpha.", "Beta beta."]
    freq = {"alpha": 4, "beta": 2}
    sel = _score_and_select(sentences, freq, 1)
    assert sel == ["Alpha alpha alpha alpha."]


def test_select_zero_returns_empty():
    sentences = ["A a a.", "B b b.", "C c c."]
    freq = _word_frequency(" ".join(sentences))
    assert _score_and_select(sentences, freq, 0) == []


def test_select_more_than_available():
    sentences = ["A a a.", "B b b."]
    freq = _word_frequency(" ".join(sentences))
    sel = _score_and_select(sentences, freq, 10)
    assert len(sel) == 2


# ---------------------------------------------------------------------------
# _build_summary_result / _no_op_result
# ---------------------------------------------------------------------------
def test_build_result_ratio_formula():
    r = _build_summary_result("one two three four", ["one two"])
    assert r.ratio == r.word_count_summary / max(r.word_count_original, 1)
    assert r.word_count_original == 4
    assert r.word_count_summary == 2
    assert r.ratio == 0.5


def test_build_result_ratio_guard_zero_original():
    # original_text empty -> max(0,1)=1, ratio = summary_words/1
    r = _build_summary_result("", ["a b"])
    assert r.word_count_original == 0
    assert r.ratio == 2.0  # 2 / max(0,1)


def test_no_op_result_empty():
    r = _no_op_result("")
    assert r.summary == ""
    assert r.sentences == []
    assert r.ratio == 1.0
    assert r.word_count_original == 0
    assert r.word_count_summary == 0


def test_no_op_result_nonempty():
    r = _no_op_result("hello world")
    assert r.summary == "hello world"
    assert r.sentences == ["hello world"]
    assert r.ratio == 1.0
    assert r.word_count_original == 2
    assert r.word_count_summary == 2


def test_summary_result_str_is_summary():
    r = SummaryResult("o", "the summary", ["the summary"], 1.0, 1, 3)
    assert str(r) == "the summary"


# ---------------------------------------------------------------------------
# summarize - guard path
# ---------------------------------------------------------------------------
def test_summarize_empty_guard():
    r = summarize("")
    assert r.summary == ""
    assert r.sentences == []
    assert r.ratio == 1.0


def test_summarize_whitespace_guard():
    r = summarize("   ")
    # "   " is truthy but len < 50 -> guard path, summary == text
    assert r.summary == "   "
    assert r.ratio == 1.0


def test_summarize_short_text_guard():
    r = summarize("short text")
    assert r.summary == "short text"
    assert r.ratio == 1.0
    assert r.sentences == ["short text"]


def test_summarize_min_length_boundary():
    # exactly min_length chars -> NOT guard (len < min_length is False)
    text = "x" * 50
    r = summarize(text, min_length=50)
    # 50 x's -> one "sentence" (no punctuation) -> short-text path
    assert r.word_count_original == 1


def test_summarize_just_below_min_length_guard():
    text = "x" * 49
    r = summarize(text, min_length=50)
    assert r.summary == text
    assert r.ratio == 1.0


# ---------------------------------------------------------------------------
# summarize - short-text path (all sentences kept)
# ---------------------------------------------------------------------------
def test_summarize_short_text_keeps_all():
    # 3 sentences (53 chars >= min_length 50), <= max_sentences(3)
    # -> all kept, no scoring
    text = "Alpha alpha alpha. Beta beta beta. Gamma gamma gamma."
    r = summarize(text)
    assert len(r.sentences) == 3
    assert r.sentences == ["Alpha alpha alpha.", "Beta beta beta.", "Gamma gamma gamma."]


def test_summarize_short_text_order_preserved():
    text = "Alpha alpha alpha. Beta beta beta. Gamma gamma gamma."
    r = summarize(text, max_sentences=3)
    assert r.sentences[0] == "Alpha alpha alpha."
    assert r.sentences[2] == "Gamma gamma gamma."


# ---------------------------------------------------------------------------
# summarize - scoring path
# ---------------------------------------------------------------------------
def test_summarize_scoring_selects_max_sentences():
    r = summarize(TEXT, max_sentences=3)
    assert len(r.sentences) == 3


def test_summarize_scoring_order_preserved():
    r = summarize(TEXT, max_sentences=3)
    idx = [TEXT.index(s) for s in r.sentences]
    assert idx == sorted(idx)


def test_summarize_scoring_ratio_in_range():
    r = summarize(TEXT, max_sentences=2)
    assert 0.0 <= r.ratio <= 1.0


def test_summarize_max_sentences_zero():
    r = summarize(TEXT, max_sentences=0)
    assert r.sentences == []
    assert r.summary == ""
    assert r.word_count_summary == 0


def test_summarize_idempotence():
    # summarizing the same text twice gives identical results
    a = summarize(TEXT, max_sentences=3)
    b = summarize(TEXT, max_sentences=3)
    assert a.sentences == b.sentences
    assert a.ratio == b.ratio


def test_summarize_unicode_no_crash():
    text = "Привет мир. Как дела? Хорошо сегодня. Погода отличная. Мы рады."
    r = summarize(text)
    assert isinstance(r, SummaryResult)


def test_summarize_all_stopwords_scoring():
    # text long enough to pass guard but all stopwords -> freq empty -> all
    # sentences score 0 -> still returns max_sentences (ties broken by sort).
    # Uppercase after punct so _split_sentences yields 3 sentences.
    text = "The the the the the. And and and and and. Of of of of of of."
    r = summarize(text, max_sentences=2)
    assert len(r.sentences) == 2


# ---------------------------------------------------------------------------
# DEFECT: negative-slice "top N" leak (QA-15)
# ---------------------------------------------------------------------------
@pytest.mark.xfail(
    strict=True,
    reason="QA-15: summarize(max_sentences=-1) leaks sentences[:-1] instead of []",
)
def test_summarize_max_sentences_negative_returns_empty():
    # Contract (negative-slice "top N" class, QA-1..QA-5): a negative bound
    # must yield an empty list, matching the 0 guard.
    r = summarize(TEXT, max_sentences=-1)
    assert r.sentences == []


@pytest.mark.xfail(
    strict=True,
    reason="QA-15: summarize(max_sentences=-5) leaks sentences[:-5] instead of []",
)
def test_summarize_max_sentences_more_negative_returns_empty():
    r = summarize(TEXT, max_sentences=-5)
    assert r.sentences == []


# ---------------------------------------------------------------------------
# summarize_page
# ---------------------------------------------------------------------------
def test_summarize_page_empty_content_guard():
    r = summarize_page("My Title", "")
    assert r.original_text == "My Title"
    assert r.summary == ""
    assert r.sentences == []
    assert r.ratio == 0.0
    assert r.word_count_original == len(_tokenize("My Title"))
    assert r.word_count_summary == 0


def test_summarize_page_whitespace_content_normal_path():
    # " " is truthy -> normal path; combined = "T. " + " " = "T.  " (two
    # spaces). That is < min_length -> guard inside summarize, so summary ==
    # combined and ratio == 1.0.
    r = summarize_page("T", " ")
    assert r.original_text == "T.  "
    assert r.summary == "T.  "
    assert r.ratio == 1.0


def test_summarize_page_normal_combines_title():
    # content long enough to pass guard
    content = "Alpha alpha alpha. Beta beta beta. Gamma gamma gamma."
    r = summarize_page("MyTitle", content)
    # original_text is the combined string, not the raw title
    assert r.original_text == f"MyTitle. {content}"


def test_summarize_page_normal_matches_summarize():
    content = "Alpha alpha alpha. Beta beta beta. Gamma gamma gamma."
    r = summarize_page("MyTitle", content, max_sentences=2)
    direct = summarize(f"MyTitle. {content}", max_sentences=2)
    assert r.sentences == direct.sentences
    assert r.ratio == direct.ratio


def test_summarize_page_short_content_guard():
    # content truthy but combined < min_length -> summarize guard path
    r = summarize_page("T", "hi")
    # combined = "T. hi" (5 chars) < 50 -> guard, summary == combined
    assert r.summary == "T. hi"
    assert r.ratio == 1.0


def test_summarize_page_unicode_no_crash():
    r = summarize_page("Заголовок", "Привет мир. Как дела? Хорошо.")
    assert isinstance(r, SummaryResult)


def test_summarize_page_idempotence():
    content = "Alpha alpha alpha. Beta beta beta. Gamma gamma gamma."
    a = summarize_page("T", content, max_sentences=2)
    b = summarize_page("T", content, max_sentences=2)
    assert a.sentences == b.sentences


# ---------------------------------------------------------------------------
# STOPWORDS sanity
# ---------------------------------------------------------------------------
def test_stopwords_is_frozenset_of_str():
    assert isinstance(STOPWORDS, frozenset)
    assert all(isinstance(w, str) for w in STOPWORDS)
    assert "the" in STOPWORDS


# ---------------------------------------------------------------------------
# End-to-end CLI run (summarizer is a standalone utility, not wired to the
# CLI per docs; the e2e run proves the installed CLI still boots and the
# package imports cleanly alongside the summarizer module).
# ---------------------------------------------------------------------------
def test_cli_boots_and_summarizer_importable():
    proc = subprocess.run(
        [sys.executable, "-m", "personal_index.cli", "--help"],
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert proc.returncode == 0
    assert "Personal Index" in proc.stdout
    # summarizer importable in the same interpreter
    import personal_index.content_summarizer as cs  # noqa: F401
    assert callable(cs.summarize)
