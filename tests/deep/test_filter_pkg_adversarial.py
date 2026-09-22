"""Adversarial deep tests for the personal_index.filter package.

The ``filter`` package (engine.py + matcher.py) is a never-probed subsystem:
it is imported only by its own ``__init__`` and by tests/test_filter*.py, NOT
by the live pipeline (which uses the separate personal_index.content_filter
module). It exposes three public classes:

  * ``ContentFilter``   (engine.py)  - URL/content/page filtering + text
                                       extraction, driven by a list of
                                       ``Interest`` objects.
  * ``ContentMatcher``  (matcher.py) - single-interest keyword/URL matching
                                       and relevance scoring.
  * ``InterestFilter``  (matcher.py) - multi-interest best-match selection.

These tests pin the documented/observable contracts against adversarial
inputs: empty/whitespace/unicode text, disabled interests, malformed regex
patterns (which must be suppressed, not raised), empty keyword/pattern lists,
out-of-range ``max_length`` (0 and negative) in ``extract_relevant_text``,
score accumulation and the ``relevance_score`` cap-at-priority invariant,
the ``filter_page`` Page-object vs URL-string duality, ``update_page``
mutation, and the ``InterestFilter`` best-by-score / sorted-by-priority
selection. A final end-to-end run exercises the installed CLI group's
documented empty-index guard path (the filter package has no dedicated CLI
command).

NOTE (benign, not a QA defect): ``ContentFilter.min_relevance_score`` is
stored but never referenced by any engine method, and no docs/** file
promises it is used (docs/content-filter.md describes the *other*
``content_filter.ContentFilter`` class). It is a dead parameter, not a
contract violation, so it is pinned only for its observable "stored" effect.
"""

from __future__ import annotations


from click.testing import CliRunner

from personal_index.cli import main
from personal_index.config.models import Interest, MatchMode
from personal_index.filter.engine import ContentFilter, FilterResult
from personal_index.filter.matcher import ContentMatcher, InterestFilter


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _interest(name="py", keywords=("python",), url_patterns=(), priority=5,
              enabled=True, mode=MatchMode.ANY):
    return Interest(
        name=name,
        keywords=list(keywords),
        url_patterns=list(url_patterns),
        priority=priority,
        enabled=enabled,
        match_mode=mode,
    )


class _Page:
    """Minimal Page-like object for filter_page / update_page."""

    def __init__(self, url="", content="", title=""):
        self.url = url
        self.content = content
        self.title = title
        self.matched_interests = None
        self.relevance_score = None


# ---------------------------------------------------------------------------
# ContentFilter.filter_url
# ---------------------------------------------------------------------------

class TestFilterUrl:
    def test_match_collects_interest_name(self):
        f = ContentFilter([_interest(url_patterns=(r"github\.com",))])
        r = f.filter_url("https://github.com/foo")
        assert r.matched is True
        assert r.matching_interests == {"py"}

    def test_no_match(self):
        f = ContentFilter([_interest(url_patterns=(r"github\.com",))])
        r = f.filter_url("https://example.com")
        assert r.matched is False
        assert r.matching_interests == set()

    def test_empty_url(self):
        f = ContentFilter([_interest(url_patterns=(r"github\.com",))])
        r = f.filter_url("")
        assert r.matched is False

    def test_unicode_url_no_crash(self):
        f = ContentFilter([_interest(url_patterns=(r"github\.com",))])
        r = f.filter_url("https://github.com/пéé")
        assert r.matched is True  # pattern still matches the ascii prefix

    def test_malformed_regex_suppressed(self):
        # A malformed pattern must be skipped (re.error suppressed), not raised.
        f = ContentFilter([_interest(url_patterns=(r"[unclosed",))])
        r = f.filter_url("https://github.com/x")
        assert r.matched is False

    def test_disabled_interest_ignored(self):
        f = ContentFilter([_interest(url_patterns=(r"github\.com",), enabled=False)])
        r = f.filter_url("https://github.com/x")
        assert r.matched is False


# ---------------------------------------------------------------------------
# ContentFilter.filter_content
# ---------------------------------------------------------------------------

class TestFilterContent:
    def test_single_keyword_match(self):
        f = ContentFilter([_interest(keywords=("python", "django"))])
        r = f.filter_content("just python here")
        assert r.matched is True
        assert r.matched_keywords == {"python"}
        assert r.matching_interests == {"py"}

    def test_score_accumulates_per_keyword(self):
        # Each matched keyword adds interest.priority (5) to the score.
        f = ContentFilter([_interest(keywords=("python", "django"), priority=5)])
        r = f.filter_content("I love python and django")
        assert r.matched is True
        assert r.score == 10.0
        assert r.matched_keywords == {"python", "django"}

    def test_empty_content_no_match(self):
        f = ContentFilter([_interest(keywords=("python",))])
        r = f.filter_content("")
        assert r.matched is False
        assert r.score == 0.0

    def test_title_is_searched_too(self):
        # filter_content lowercases f"{title} {content}"; a keyword in the
        # title must match even when absent from the body.
        f = ContentFilter([_interest(keywords=("python",))])
        r = f.filter_content("nothing here", title="Python guide")
        assert r.matched is True

    def test_case_insensitive(self):
        f = ContentFilter([_interest(keywords=("python",))])
        r = f.filter_content("PYTHON is great")
        assert r.matched is True

    def test_unicode_keyword(self):
        f = ContentFilter([_interest(keywords=("пéé",))])
        r = f.filter_content("this has пéé inside")
        assert r.matched is True

    def test_disabled_interest_ignored(self):
        f = ContentFilter([_interest(keywords=("python",), enabled=False)])
        r = f.filter_content("python")
        assert r.matched is False


# ---------------------------------------------------------------------------
# ContentFilter.filter_page  (URL-string vs Page-object duality)
# ---------------------------------------------------------------------------

class TestFilterPage:
    def test_url_string_only(self):
        f = ContentFilter([_interest(url_patterns=(r"github\.com",))])
        r = f.filter_page("https://github.com/foo")
        assert r.matched is True
        assert r.matching_interests == {"py"}

    def test_content_only_via_url_string(self):
        f = ContentFilter([_interest(keywords=("python",))])
        r = f.filter_page("https://example.com", content="python rocks")
        assert r.matched is True
        assert r.matched_keywords == {"python"}

    def test_page_object_reads_url_content_title(self):
        f = ContentFilter([_interest(keywords=("python",),
                                     url_patterns=(r"github\.com",))])
        p = _Page(url="https://github.com/foo", content="python is great")
        r = f.filter_page(p)
        assert r.matched is True
        assert r.matching_interests == {"py"}
        assert r.matched_keywords == {"python"}

    def test_page_object_no_match(self):
        f = ContentFilter([_interest(keywords=("python",))])
        p = _Page(url="https://example.com", content="nothing")
        r = f.filter_page(p)
        assert r.matched is False
        assert r.matching_interests == set()

    def test_passed_mirrors_matched(self):
        f = ContentFilter([_interest(keywords=("python",))])
        r = f.filter_page("https://example.com", content="python")
        assert r.passed is True
        r2 = f.filter_page("https://example.com", content="nope")
        assert r2.passed is False


# ---------------------------------------------------------------------------
# ContentFilter.update_page
# ---------------------------------------------------------------------------

class TestUpdatePage:
    def test_sets_matched_interests_and_score(self):
        f = ContentFilter([_interest(keywords=("python",), priority=5)])
        p = _Page(content="python")
        r = f.filter_page(p)
        f.update_page(p, r)
        assert p.matched_interests == ["py"]
        assert p.relevance_score == 5.0

    def test_noop_on_object_without_attrs(self):
        # update_page must not raise on an object lacking the attrs.
        class _Bare:
            pass
        f = ContentFilter([_interest(keywords=("python",))])
        r = FilterResult(matched=True, matching_interests={"py"}, score=3.0)
        f.update_page(_Bare(), r)  # must not raise


# ---------------------------------------------------------------------------
# ContentFilter.should_crawl
# ---------------------------------------------------------------------------

class TestShouldCrawl:
    def test_match(self):
        f = ContentFilter([_interest(url_patterns=(r"github\.com",))])
        assert f.should_crawl("https://github.com/x") is True

    def test_no_match(self):
        f = ContentFilter([_interest(url_patterns=(r"github\.com",))])
        assert f.should_crawl("https://example.com") is False

    def test_empty_patterns_crawl_everything(self):
        # No compiled patterns -> crawl everything (True).
        f = ContentFilter([])
        assert f.should_crawl("https://anything.example") is True

    def test_only_malformed_patterns_crawl_everything(self):
        # A malformed pattern is suppressed -> empty compiled list -> True.
        f = ContentFilter([_interest(url_patterns=(r"[unclosed",))])
        assert f.should_crawl("https://github.com/x") is True


# ---------------------------------------------------------------------------
# ContentFilter.extract_relevant_text
# ---------------------------------------------------------------------------

class TestExtractRelevantText:
    def test_short_text_returned_verbatim(self):
        f = ContentFilter([])
        assert f.extract_relevant_text("hello world", 500) == "hello world"

    def test_long_text_truncated_to_max_length(self):
        f = ContentFilter([])
        out = f.extract_relevant_text("word " * 200, 500)
        assert len(out) <= 500

    def test_max_length_zero_returns_empty(self):
        f = ContentFilter([])
        assert f.extract_relevant_text("hello world", 0) == ""

    def test_negative_max_length_does_not_crash(self):
        # len(text) <= -5 is False -> enters truncation branch; text[:-5] is a
        # valid (shorter) slice, so no exception and a shorter result.
        f = ContentFilter([])
        out = f.extract_relevant_text("hello world", -5)
        assert isinstance(out, str)
        assert len(out) < len("hello world")

    def test_breaks_at_word_boundary(self):
        f = ContentFilter([])
        out = f.extract_relevant_text("aaaa bbbb cccc dddd eeee", 10)
        # 10 chars = "aaaa bbbb c"; last space at index 9 (> 5) -> cut to
        # "aaaa bbbb".
        assert out == "aaaa bbbb"

    def test_no_space_in_half_returns_full_slice(self):
        f = ContentFilter([])
        # No space after the 50% mark -> no word-boundary cut.
        out = f.extract_relevant_text("a" * 20, 10)
        assert out == "a" * 10


# ---------------------------------------------------------------------------
# ContentFilter constructor: min_relevance_score is stored (benign dead param)
# ---------------------------------------------------------------------------

class TestConstructor:
    def test_min_relevance_score_stored(self):
        f = ContentFilter([_interest()], min_relevance_score=0.7)
        assert f.min_relevance_score == 0.7

    def test_default_min_relevance_score(self):
        f = ContentFilter([_interest()])
        assert f.min_relevance_score == 0.0


# ---------------------------------------------------------------------------
# ContentMatcher.matches_content
# ---------------------------------------------------------------------------

class TestContentMatcherMatchesContent:
    def test_any_mode(self):
        m = ContentMatcher(_interest(keywords=("python", "django")))
        assert m.matches_content("python only") is True

    def test_all_mode_requires_all(self):
        m = ContentMatcher(_interest(keywords=("python", "django"),
                                     mode=MatchMode.ALL))
        assert m.matches_content("python and django") is True
        assert m.matches_content("python only") is False

    def test_regex_mode(self):
        m = ContentMatcher(_interest(keywords=(r"\d+",), mode=MatchMode.REGEX))
        assert m.matches_content("has 42 here") is True
        assert m.matches_content("no digits") is False

    def test_regex_malformed_suppressed(self):
        m = ContentMatcher(_interest(keywords=(r"[unclosed",),
                                       mode=MatchMode.REGEX))
        assert m.matches_content("anything") is False

    def test_empty_text(self):
        m = ContentMatcher(_interest(keywords=("python",)))
        assert m.matches_content("") is False

    def test_empty_keywords(self):
        m = ContentMatcher(_interest(keywords=()))
        assert m.matches_content("python") is False

    def test_disabled_interest(self):
        m = ContentMatcher(_interest(keywords=("python",), enabled=False))
        assert m.matches_content("python") is False

    def test_case_insensitive(self):
        m = ContentMatcher(_interest(keywords=("python",)))
        assert m.matches_content("PYTHON") is True


# ---------------------------------------------------------------------------
# ContentMatcher.matches_url
# ---------------------------------------------------------------------------

class TestContentMatcherMatchesUrl:
    def test_match(self):
        m = ContentMatcher(_interest(url_patterns=(r"github\.com",)))
        assert m.matches_url("https://github.com/x") is True

    def test_no_match(self):
        m = ContentMatcher(_interest(url_patterns=(r"github\.com",)))
        assert m.matches_url("https://example.com") is False

    def test_empty_url(self):
        m = ContentMatcher(_interest(url_patterns=(r"github\.com",)))
        assert m.matches_url("") is False

    def test_malformed_regex_suppressed(self):
        m = ContentMatcher(_interest(url_patterns=(r"[unclosed",)))
        assert m.matches_url("https://github.com/x") is False

    def test_disabled_interest(self):
        m = ContentMatcher(_interest(url_patterns=(r"github\.com",),
                                     enabled=False))
        assert m.matches_url("https://github.com/x") is False


# ---------------------------------------------------------------------------
# ContentMatcher.relevance_score  (cap-at-priority invariant)
# ---------------------------------------------------------------------------

class TestContentMatcherRelevanceScore:
    def test_any_mode_capped_at_priority(self):
        # total=2 (python x2), num_kw=2 -> 2*5/2=5, min(5,5)=5.
        m = ContentMatcher(_interest(keywords=("python", "django"), priority=5))
        assert m.relevance_score("python python") == 5.0

    def test_any_mode_below_cap(self):
        # total=1, num_kw=2 -> 1*5/2=2.5.
        m = ContentMatcher(_interest(keywords=("python", "django"), priority=5))
        assert m.relevance_score("python") == 2.5

    def test_never_exceeds_priority(self):
        # Many occurrences must still cap at priority.
        m = ContentMatcher(_interest(keywords=("python",), priority=3))
        assert m.relevance_score("python " * 50) == 3.0

    def test_regex_mode_counts_matches(self):
        m = ContentMatcher(_interest(keywords=(r"\d+",), mode=MatchMode.REGEX,
                                     priority=5))
        # 3 numeric matches, num_kw=1 -> 3*5/1=15, cap at 5.
        assert m.relevance_score("a1 b2 c3") == 5.0

    def test_no_match_zero(self):
        m = ContentMatcher(_interest(keywords=("python",)))
        assert m.relevance_score("nothing") == 0.0

    def test_empty_text_zero(self):
        m = ContentMatcher(_interest(keywords=("python",)))
        assert m.relevance_score("") == 0.0

    def test_disabled_zero(self):
        m = ContentMatcher(_interest(keywords=("python",), enabled=False))
        assert m.relevance_score("python") == 0.0


# ---------------------------------------------------------------------------
# InterestFilter.matches / should_index / filter_content / get_matching_interests
# ---------------------------------------------------------------------------

class TestInterestFilter:
    def test_matches_picks_highest_priority(self):
        ifl = InterestFilter([
            _interest(name="low", keywords=("python",), priority=2),
            _interest(name="high", keywords=("python",), priority=9),
        ])
        best = ifl.matches("python python")
        assert best is not None
        assert best.name == "high"

    def test_matches_none_when_no_match(self):
        ifl = InterestFilter([_interest(keywords=("python",))])
        assert ifl.matches("nothing") is None

    def test_url_only_match_uses_priority_score(self):
        ifl = InterestFilter([_interest(name="u", keywords=("zzz",),
                                        url_patterns=(r"github\.com",),
                                        priority=7)])
        best = ifl.matches("no keyword here", "https://github.com/x")
        assert best is not None
        assert best.name == "u"

    def test_should_index(self):
        ifl = InterestFilter([_interest(keywords=("python",))])
        assert ifl.should_index("python") is True
        assert ifl.should_index("nothing") is False

    def test_filter_content_returns_dict(self):
        ifl = InterestFilter([_interest(keywords=("python",), priority=9)])
        out = ifl.filter_content("python")
        assert out == {"matched": True, "interest": "py", "score": 9}

    def test_filter_content_none_when_no_match(self):
        ifl = InterestFilter([_interest(keywords=("python",))])
        assert ifl.filter_content("nothing") is None

    def test_get_matching_interests_sorted_by_priority(self):
        ifl = InterestFilter([
            _interest(name="low", keywords=("python",), priority=2),
            _interest(name="high", keywords=("python",), priority=9),
        ])
        names = [i.name for i in ifl.get_matching_interests("python")]
        assert names == ["high", "low"]

    def test_empty_interests(self):
        ifl = InterestFilter([])
        assert ifl.matches("python") is None
        assert ifl.should_index("python") is False
        assert ifl.filter_content("python") is None
        assert ifl.get_matching_interests("python") == []

    def test_disabled_interests_excluded(self):
        ifl = InterestFilter([_interest(keywords=("python",), enabled=False)])
        assert ifl.matches("python") is None


# ---------------------------------------------------------------------------
# End-to-end CLI run (the filter package has no dedicated CLI command;
# exercise the installed CLI group's documented empty-index guard path).
# ---------------------------------------------------------------------------

class TestCliEndToEnd:
    def test_search_empty_index_guard(self, tmp_path):
        dd = str(tmp_path)
        runner = CliRunner()
        res = runner.invoke(main, ["search", "anything", "--data-dir", dd])
        assert res.exit_code == 0, res.output
        assert "No indexed content found" in res.output
