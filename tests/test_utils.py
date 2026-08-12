"""Tests for utility functions."""

# Re-export from root url_utils
from personal_index.text_utils import tokenize
from personal_index.utils import (
    compute_relevance_score,
    extract_domain,
    extract_links,
    extract_meta_description,
    extract_text_content,
    extract_title,
    is_same_domain,
    normalize_url,
)


class TestNormalizeUrl:
    def test_valid_url(self):
        assert normalize_url("https://example.com/page") == "https://example.com/page"

    def test_url_with_fragment(self):
        assert normalize_url("https://example.com/page#section") == "https://example.com/page"

    def test_relative_url_with_base(self):
        result = normalize_url("/page", "https://example.com")
        assert result == "https://example.com/page"

    def test_invalid_scheme(self):
        assert normalize_url("ftp://example.com") is None

    def test_empty_url(self):
        assert normalize_url("") is None

    def test_none_url(self):
        assert normalize_url(None) is None

    def test_whitespace_url(self):
        assert normalize_url("  ") is None


class TestExtractDomain:
    def test_simple_domain(self):
        assert extract_domain("https://example.com/page") == "example.com"

    def test_subdomain(self):
        assert extract_domain("https://www.example.com/page") == "www.example.com"

    def test_domain_with_port(self):
        assert extract_domain("https://example.com:8080/page") == "example.com"


class TestIsSameDomain:
    def test_same_domain(self):
        assert is_same_domain("https://example.com/a", "https://example.com/b") is True

    def test_different_domain(self):
        assert is_same_domain("https://example.com", "https://other.com") is False

    def test_subdomain_different(self):
        assert is_same_domain("https://www.example.com", "https://example.com") is False


class TestExtractLinks:
    def test_extract_simple_links(self):
        html = '<a href="https://example.com/page">Link</a>'
        links = extract_links(html, "https://example.com")
        assert "https://example.com/page" in links

    def test_extract_relative_links(self):
        html = '<a href="/page">Link</a>'
        links = extract_links(html, "https://example.com")
        assert "https://example.com/page" in links

    def test_skip_javascript_links(self):
        html = '<a href="javascript:void(0)">Click</a>'
        links = extract_links(html, "https://example.com")
        assert len(links) == 0

    def test_skip_mailto_links(self):
        html = '<a href="mailto:test@example.com">Email</a>'
        links = extract_links(html, "https://example.com")
        assert len(links) == 0

    def test_multiple_links(self):
        html = '<a href="/a">A</a><a href="/b">B</a>'
        links = extract_links(html, "https://example.com")
        assert len(links) == 2


class TestExtractTitle:
    def test_extract_title(self):
        html = "<html><head><title>My Page</title></head></html>"
        assert extract_title(html) == "My Page"

    def test_no_title(self):
        html = "<html><head></head></html>"
        assert extract_title(html) == ""


class TestExtractMetaDescription:
    def test_extract_description(self):
        html = '<meta name="description" content="A test description">'
        assert extract_meta_description(html) == "A test description"

    def test_no_description(self):
        html = "<html></html>"
        assert extract_meta_description(html) == ""


class TestExtractTextContent:
    def test_extract_text(self):
        html = "<p>Hello <b>world</b></p>"
        assert "Hello world" == extract_text_content(html)

    def test_remove_scripts(self):
        html = "<p>Text</p><script>alert('xss')</script>"
        result = extract_text_content(html)
        assert "alert" not in result
        assert "xss" not in result

    def test_remove_styles(self):
        html = "<p>Text</p><style>.red { color: red; }</style>"
        result = extract_text_content(html)
        assert "color" not in result


class TestTokenize:
    def test_simple_tokenize(self):
        assert tokenize("Hello World") == ["hello", "world"]

    def test_with_numbers(self):
        assert tokenize("Version 2.0") == ["version", "2", "0"]

    def test_hyphenated_words(self):
        assert tokenize("well-known") == ["well-known"]

    def test_empty_string(self):
        assert tokenize("") == []


class TestComputeRelevanceScore:
    def test_matching_keyword(self):
        score = compute_relevance_score(
            "This is about machine learning",
            ["machine learning"],
        )
        assert score > 0

    def test_no_match(self):
        score = compute_relevance_score(
            "This is about cooking",
            ["machine learning"],
        )
        assert score == 0.0

    def test_title_bonus(self):
        score_with_title = compute_relevance_score(
            "Some text here",
            ["machine learning"],
            title="Machine Learning Guide",
        )
        score_without_title = compute_relevance_score(
            "Some text here",
            ["machine learning"],
            title="",
        )
        assert score_with_title > score_without_title

    def test_priority_affects_score(self):
        score_low = compute_relevance_score(
            "machine learning is great",
            ["machine learning"],
            priority=1,
        )
        score_high = compute_relevance_score(
            "machine learning is great",
            ["machine learning"],
            priority=10,
        )
        assert score_high >= score_low

    def test_empty_keywords(self):
        score = compute_relevance_score("some text", [])
        assert score == 0.0

    def test_empty_text(self):
        score = compute_relevance_score("", ["keyword"])
        assert score == 0.0
