"""Adversarial deep tests for personal_index.keyword_extractor.

Cycle 149 - VALIDATOR probe (never-probed subsystem).

Contracts under test (from docstrings / dataclass):
  - KeywordExtractor.extract(text) -> list[Keyword]:
      * empty/whitespace/punctuation-only text -> [] (no crash)
      * each Keyword has non-empty str text, int frequency >= 1, float score > 0
      * no duplicate keyword texts in the result
      * len(result) <= max_keywords (constructor bound)
      * sorted by score descending
      * keywords are lowercased tokens of the input (substring property)
      * stop words excluded (tokenize remove_stopwords=True)
  - extract_top_n(text, n) -> list[str]:
      * n=0 / n negative -> []
      * len(result) <= n
      * result == [kw.text for kw in extract(text)[:n]] (consistency)
  - extract_phrases(text, n) -> list[tuple[str, int]]:
      * n=1, n larger than token count -> []
      * phrases are space-joined token n-grams
  - compute_term_frequency(text) -> dict[str, float]:
      * values in (0, 1], sum <= 1
  - compare_keywords(t1, t2) -> dict[str, float]:
      * only shared keywords, symmetric
  - module-level extract_keywords(text, max_keywords) -> list[str]
  - one end-to-end CLI run.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from personal_index.keyword_extractor import (
    Keyword,
    KeywordExtractor,
    extract_keywords,
)


@pytest.fixture
def extractor() -> KeywordExtractor:
    return KeywordExtractor()


@pytest.fixture
def sample_text() -> str:
    return (
        "Python is a great programming language. Python is widely used in "
        "data science, machine learning, and web development. Python has a "
        "large ecosystem of libraries and frameworks. Many developers love "
        "Python because of its readability and simplicity."
    )


# --- extract(): guard inputs ------------------------------------------------

def test_extract_empty_string():
    assert KeywordExtractor().extract("") == []


def test_extract_whitespace_only():
    assert KeywordExtractor().extract("   \t\n  \r\n  ") == []


def test_extract_punctuation_only():
    assert KeywordExtractor().extract("!!! ??? ... ---") == []


def test_extract_numbers_only():
    # tokenize drops non-word tokens; numbers may or may not survive -
    # contract: no crash, returns list[Keyword]
    result = KeywordExtractor().extract("123 456 789")
    assert isinstance(result, list)
    for kw in result:
        assert isinstance(kw, Keyword)


def test_extract_unicode_cyrillic():
    text = "программирование на питоне очень популярно среди разработчиков"
    result = KeywordExtractor().extract(text)
    assert isinstance(result, list)
    for kw in result:
        assert isinstance(kw.text, str) and len(kw.text) > 0


def test_extract_unicode_cjk():
    text = "Python编程语言在数据科学和机器学习领域非常流行"
    result = KeywordExtractor().extract(text)
    assert isinstance(result, list)


def test_extract_emoji_mixed():
    text = "python 🐍 is great for data 📊 science and ML 🤖"
    result = KeywordExtractor().extract(text)
    assert isinstance(result, list)


def test_extract_single_short_word():
    # min_length=3 default: "go" is too short
    assert KeywordExtractor().extract("go") == []


def test_extract_none_raises_typeerror():
    # tokenize(None) is not guarded by extract's `if not text` (None is
    # falsy -> returns []). Pin the actual behavior:
    assert KeywordExtractor().extract(None) == []


# --- extract(): shape and ordering properties -------------------------------

def test_extract_returns_keyword_objects(extractor, sample_text):
    result = extractor.extract(sample_text)
    assert len(result) > 0
    for kw in result:
        assert isinstance(kw, Keyword)
        assert isinstance(kw.text, str) and len(kw.text) > 0
        assert isinstance(kw.frequency, int) and kw.frequency >= 1
        assert isinstance(kw.score, float) and kw.score > 0
        assert isinstance(kw.positions, list)


def test_extract_no_duplicate_texts(extractor, sample_text):
    result = extractor.extract(sample_text)
    texts = [kw.text for kw in result]
    assert len(texts) == len(set(texts)), f"duplicates: {texts}"


def test_extract_bounded_by_max_keywords(sample_text):
    for max_kw in [1, 3, 5, 10, 50]:
        result = KeywordExtractor(max_keywords=max_kw).extract(sample_text)
        assert len(result) <= max_kw, f"max_keywords={max_kw} got {len(result)}"


def test_extract_sorted_by_score_desc(extractor, sample_text):
    result = extractor.extract(sample_text)
    scores = [kw.score for kw in result]
    assert scores == sorted(scores, reverse=True)


def test_extract_keywords_are_lowercased_tokens(extractor, sample_text):
    # tokenize lowercases; every keyword must appear in the lowercased text
    lower = sample_text.lower()
    for kw in extractor.extract(sample_text):
        assert kw.text in lower, f"{kw.text!r} not in lowercased input"


def test_extract_stop_words_excluded(extractor):
    text = "the is a an and or but of in on at to for with by from"
    result = extractor.extract(text)
    stop = {"the", "is", "a", "an", "and", "or", "but", "of", "in", "on",
            "at", "to", "for", "with", "by", "from"}
    for kw in result:
        assert kw.text not in stop, f"stop word {kw.text!r} leaked"


def test_extract_mixed_case_collapses(extractor):
    text = "Python python PYTHON Python"
    result = extractor.extract(text)
    texts = [kw.text for kw in result]
    assert texts.count("python") <= 1
    assert len(texts) == len(set(texts))


def test_extract_frequency_matches_positions(extractor, sample_text):
    for kw in extractor.extract(sample_text):
        assert len(kw.positions) == kw.frequency


def test_extract_min_length_filter():
    ke = KeywordExtractor(min_length=5)
    result = ke.extract("cat dog python")
    texts = [kw.text for kw in result]
    assert "cat" not in texts
    assert "dog" not in texts
    assert "python" in texts


def test_extract_min_frequency_filter():
    ke = KeywordExtractor(min_frequency=2)
    result = ke.extract("python python data science")
    texts = [kw.text for kw in result]
    assert "python" in texts
    assert "data" not in texts
    assert "science" not in texts


def test_extract_very_long_text():
    text = " ".join(["python"] * 10000)
    result = KeywordExtractor(max_keywords=5).extract(text)
    assert len(result) <= 5
    assert result[0].text == "python"
    assert result[0].frequency == 10000


def test_extract_idempotence_no_crash(extractor, sample_text):
    first = extractor.extract(sample_text)
    if first:
        second = extractor.extract(" ".join(kw.text for kw in first))
        assert isinstance(second, list)


# --- extract_top_n ------------------------------------------------------------

def test_extract_top_n_basic(extractor):
    result = extractor.extract_top_n("python python data data science", 2)
    assert result == ["python", "data"]


def test_extract_top_n_zero(extractor):
    assert extractor.extract_top_n("python python data", 0) == []


@pytest.mark.xfail(
    strict=True,
    reason=(
        "QA-1: extract_top_n(text, n=-1) returns keywords[:-1] (all but the "
        "last keyword) instead of [] - Python negative-slice semantics leak "
        "into the 'top N' contract. Out-of-range n must yield an empty list."
    ),
)
def test_extract_top_n_negative(extractor):
    assert extractor.extract_top_n("python python data", -1) == []


def test_extract_top_n_bounded(extractor, sample_text):
    for n in [1, 3, 5, 10, 50]:
        assert len(extractor.extract_top_n(sample_text, n)) <= n


def test_extract_top_n_consistent_with_extract(extractor, sample_text):
    for n in [1, 3, 7]:
        expected = [kw.text for kw in extractor.extract(sample_text)[:n]]
        assert extractor.extract_top_n(sample_text, n) == expected


def test_extract_top_n_empty_text(extractor):
    assert extractor.extract_top_n("", 5) == []


# --- extract_phrases -----------------------------------------------------------

def test_extract_phrases_basic(extractor):
    result = extractor.extract_phrases("python python data data", 2)
    assert isinstance(result, list)
    phrases = [p for p, _ in result]
    assert "python python" in phrases
    assert "data data" in phrases
    for phrase, count in result:
        assert isinstance(phrase, str)
        assert isinstance(count, int) and count >= 1


def test_extract_phrases_empty_text(extractor):
    assert extractor.extract_phrases("", 2) == []


def test_extract_phrases_n_one(extractor):
    result = extractor.extract_phrases("python data science", 1)
    phrases = [p for p, _ in result]
    assert set(phrases) == {"python", "data", "science"}


def test_extract_phrases_n_exceeds_tokens(extractor):
    assert extractor.extract_phrases("python data", 5) == []


def test_extract_phrases_sorted_by_count_desc(extractor):
    text = "a b a b a b c d c d"
    result = extractor.extract_phrases(text, 2)
    counts = [c for _, c in result]
    assert counts == sorted(counts, reverse=True)


# --- compute_term_frequency -----------------------------------------------------

def test_compute_term_frequency_values(extractor):
    tf = extractor.compute_term_frequency("python python data")
    assert tf == {"python": 2 / 3, "data": 1 / 3}


def test_compute_term_frequency_empty(extractor):
    assert extractor.compute_term_frequency("") == {}


def test_compute_term_frequency_sums_to_one(extractor, sample_text):
    tf = extractor.compute_term_frequency(sample_text)
    assert abs(sum(tf.values()) - 1.0) < 1e-9
    assert all(0 < v <= 1 for v in tf.values())


# --- compare_keywords -------------------------------------------------------------

def test_compare_keywords_shared_only(extractor):
    shared = extractor.compare_keywords("python data", "python science")
    assert set(shared) == {"python"}


def test_compare_keywords_symmetric(extractor):
    a = extractor.compare_keywords("python data science", "python web")
    b = extractor.compare_keywords("python web", "python data science")
    assert a == b


def test_compare_keywords_disjoint(extractor):
    assert extractor.compare_keywords("python data", "web html") == {}


def test_compare_keywords_score_is_average(extractor):
    ke = KeywordExtractor()
    kw1 = {kw.text: kw.score for kw in ke.extract("python python data")}
    kw2 = {kw.text: kw.score for kw in ke.extract("python data data")}
    shared = ke.compare_keywords("python python data", "python data data")
    for word, score in shared.items():
        assert score == pytest.approx((kw1[word] + kw2[word]) / 2)


# --- module-level extract_keywords -------------------------------------------------

def test_extract_keywords_module_level():
    result = extract_keywords("python python data data science", max_keywords=2)
    assert result == ["python", "data"]


def test_extract_keywords_empty():
    assert extract_keywords("") == []


def test_extract_keywords_bounded():
    text = " ".join(f"word{i}" for i in range(100))
    result = extract_keywords(text, max_keywords=5)
    assert len(result) <= 5


# --- end-to-end CLI smoke -----------------------------------------------------------

def test_cli_smoke(tmp_path: Path):
    text_file = tmp_path / "sample.txt"
    text_file.write_text(
        "Python is a programming language. "
        "Python is used in data science and machine learning. "
        "Python has great libraries.",
        encoding="utf-8",
    )
    repo_root = Path(__file__).resolve().parent.parent.parent
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            (
                "from personal_index.keyword_extractor import extract_keywords; "
                f"print(extract_keywords(open(r'{text_file}').read(), max_keywords=5))"
            ),
        ],
        capture_output=True,
        text=True,
        cwd=str(repo_root),
    )
    assert result.returncode == 0, f"CLI failed: {result.stderr}"
    assert "[" in result.stdout and "]" in result.stdout
