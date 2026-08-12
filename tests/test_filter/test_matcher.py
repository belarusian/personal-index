"""Tests for content matching and filtering."""


from personal_index.config.models import Interest, MatchMode
from personal_index.filter.matcher import ContentMatcher, InterestFilter


class TestContentMatcher:
    def test_any_match_single_keyword(self):
        interest = Interest(name="test", keywords=["python"])
        matcher = ContentMatcher(interest)
        assert matcher.matches_content("I love python programming")

    def test_any_match_multiple_keywords(self):
        interest = Interest(name="test", keywords=["python", "rust"])
        matcher = ContentMatcher(interest)
        assert matcher.matches_content("rust is great")
        assert matcher.matches_content("python is great")

    def test_all_match_requires_all(self):
        interest = Interest(name="test", keywords=["python", "django"], match_mode=MatchMode.ALL)
        matcher = ContentMatcher(interest)
        assert matcher.matches_content("python and django are great")
        assert not matcher.matches_content("python is great")

    def test_disabled_interest(self):
        interest = Interest(name="test", keywords=["python"], enabled=False)
        matcher = ContentMatcher(interest)
        assert not matcher.matches_content("python is great")

    def test_no_keywords(self):
        interest = Interest(name="test", keywords=[])
        matcher = ContentMatcher(interest)
        assert not matcher.matches_content("anything")

    def test_case_insensitive(self):
        interest = Interest(name="test", keywords=["Python"])
        matcher = ContentMatcher(interest)
        assert matcher.matches_content("python is great")
        assert matcher.matches_content("PYTHON is great")

    def test_url_pattern_match(self):
        interest = Interest(name="test", url_patterns=[r"example\.com"])
        matcher = ContentMatcher(interest)
        assert matcher.matches_url("https://example.com/page")
        assert not matcher.matches_url("https://other.com/page")

    def test_url_pattern_disabled(self):
        interest = Interest(name="test", url_patterns=[r"example\.com"], enabled=False)
        matcher = ContentMatcher(interest)
        assert not matcher.matches_url("https://example.com/page")

    def test_relevance_score_basic(self):
        interest = Interest(name="test", keywords=["python"], priority=5)
        matcher = ContentMatcher(interest)
        score = matcher.relevance_score("python python python")
        assert score > 0

    def test_relevance_score_no_match(self):
        interest = Interest(name="test", keywords=["python"])
        matcher = ContentMatcher(interest)
        assert matcher.relevance_score("no match here") == 0.0

    def test_relevance_score_max(self):
        interest = Interest(name="test", keywords=["test"], priority=10)
        matcher = ContentMatcher(interest)
        score = matcher.relevance_score("test test test test test test test test test test")
        assert score <= 10.0

    def test_regex_match_mode(self):
        interest = Interest(name="test", keywords=[r"py\w+"], match_mode=MatchMode.REGEX)
        matcher = ContentMatcher(interest)
        assert matcher.matches_content("python is great")
        assert not matcher.matches_content("java is great")


class TestInterestFilter:
    def test_init_with_interests(self):
        interests = [
            Interest(name="python", keywords=["python"]),
            Interest(name="rust", keywords=["rust"]),
        ]
        f = InterestFilter(interests)
        assert len(f._matchers) == 2

    def test_init_filters_disabled(self):
        interests = [
            Interest(name="python", keywords=["python"], enabled=True),
            Interest(name="rust", keywords=["rust"], enabled=False),
        ]
        f = InterestFilter(interests)
        assert len(f._matchers) == 1

    def test_matches_returns_best(self):
        interests = [
            Interest(name="python", keywords=["python"], priority=5),
            Interest(name="rust", keywords=["rust"], priority=8),
        ]
        f = InterestFilter(interests)
        result = f.matches("rust programming language")
        assert result is not None
        assert result.name == "rust"

    def test_matches_returns_none(self):
        interests = [Interest(name="python", keywords=["python"])]
        f = InterestFilter(interests)
        result = f.matches("nothing here")
        assert result is None

    def test_get_matching_interests_sorted(self):
        interests = [
            Interest(name="python", keywords=["python"], priority=3),
            Interest(name="rust", keywords=["rust"], priority=8),
        ]
        f = InterestFilter(interests)
        results = f.get_matching_interests("rust and python")
        assert len(results) == 2
        assert results[0].name == "rust"  # Higher priority first

    def test_should_index(self):
        interests = [Interest(name="python", keywords=["python"])]
        f = InterestFilter(interests)
        assert f.should_index("python is great")
        assert not f.should_index("nothing here")

    def test_filter_content_returns_details(self):
        interests = [Interest(name="python", keywords=["python"])]
        f = InterestFilter(interests)
        result = f.filter_content("python is great")
        assert result is not None
        assert result["matched"] is True
        assert result["interest"] == "python"

    def test_filter_content_returns_none(self):
        interests = [Interest(name="python", keywords=["python"])]
        f = InterestFilter(interests)
        result = f.filter_content("nothing here")
        assert result is None

    def test_url_matching(self):
        interests = [Interest(name="test", url_patterns=[r"example\.com"])]
        f = InterestFilter(interests)
        result = f.matches("any content", url="https://example.com/page")
        assert result is not None
        assert result.name == "test"
