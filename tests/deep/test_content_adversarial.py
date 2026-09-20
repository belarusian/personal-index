"""Adversarial deep tests for personal_index/content.py (Cycle 301).

Targets: extract_content, remove_stopwords, compute_tf, _extract_title,
_extract_meta_desc, _extract_meta_keywords, _extract_headings,
_extract_text, _extract_links, _detect_language.

Contract notes (from source):
- _extract_links filters out mailto:/javascript:/data:/tel: and does NOT deduplicate
- _extract_headings prefixes with "hN: " format
- _extract_meta_keywords does NOT deduplicate
- _detect_language defaults to "en", splits on "-" (region stripped), html tag only
- _extract_title returns raw text (no script tag removal)
"""
import pytest
from bs4 import BeautifulSoup
from personal_index.content import (
    extract_content,
    remove_stopwords,
    compute_tf,
    _extract_title,
    _extract_meta_desc,
    _extract_meta_keywords,
    _extract_headings,
    _extract_text,
    _extract_links,
    _detect_language,
)


class TestExtractContent:
    def test_empty_html(self):
        result = extract_content("", "http://example.com")
        assert result.title == ""
        assert result.text == ""

    def test_whitespace_only_html(self):
        result = extract_content("   \n\t  ", "http://example.com")
        assert result.title == ""
        assert result.text == ""

    def test_unicode_title(self):
        html = '<html><head><title>日本語タイトル</title></head><body><p>本文</p></body></html>'
        result = extract_content(html, "http://example.com")
        assert result.title == "日本語タイトル"

    def test_emoji_in_content(self):
        html = '<html><body><p>Hello 🌍 World 🚀</p></body></html>'
        result = extract_content(html, "http://example.com")
        assert "🌍" in result.text
        assert "🚀" in result.text

    def test_duplicate_meta_tags(self):
        html = '''<html><head>
            <meta name="description" content="first">
            <meta name="description" content="second">
        </head><body><p>content</p></body></html>'''
        result = extract_content(html, "http://example.com")
        # Should pick one (first), not crash
        assert result.meta_description in ("first", "second")

    def test_malformed_html(self):
        html = '<html><head><title>unclosed'
        result = extract_content(html, "http://example.com")
        assert result.title == "unclosed"

    def test_none_url(self):
        result = extract_content("<html><body>test</body></html>", None)
        assert result.url is None

    def test_relative_links_resolved(self):
        html = '<html><body><a href="/page">link</a></body></html>'
        result = extract_content(html, "http://example.com/base")
        assert "http://example.com/page" in result.links

    def test_headings_have_level_prefix(self):
        html = '<html><body><h1>Main</h1><h2>Sub</h2><p>text</p></body></html>'
        result = extract_content(html, "http://example.com")
        assert "h1: Main" in result.headings
        assert "h2: Sub" in result.headings

    def test_no_headings(self):
        html = '<html><body><p>just text</p></body></html>'
        result = extract_content(html, "http://example.com")
        assert result.headings == []

    def test_links_not_deduplicated(self):
        """Contract: _extract_links does NOT deduplicate."""
        html = '<html><body><a href="/a">1</a><a href="/a">2</a></body></html>'
        result = extract_content(html, "http://example.com")
        assert result.links.count("http://example.com/a") == 2

    def test_mailto_links_filtered(self):
        """Contract: mailto: links are filtered out."""
        html = '<html><body><a href="mailto:test@example.com">email</a></body></html>'
        result = extract_content(html, "http://example.com")
        assert "mailto:test@example.com" not in result.links

    def test_javascript_links_filtered(self):
        html = '<html><body><a href="javascript:void(0)">click</a></body></html>'
        result = extract_content(html, "http://example.com")
        assert "javascript:void(0)" not in result.links

    def test_data_links_filtered(self):
        html = '<html><body><a href="data:text/plain,hello">data</a></body></html>'
        result = extract_content(html, "http://example.com")
        assert "data:text/plain,hello" not in result.links

    def test_tel_links_filtered(self):
        html = '<html><body><a href="tel:+1234567890">call</a></body></html>'
        result = extract_content(html, "http://example.com")
        assert "tel:+1234567890" not in result.links

    def test_language_default_en(self):
        """Contract: default language is 'en' when no lang attribute."""
        html = '<html><body>text</body></html>'
        result = extract_content(html, "http://example.com")
        assert result.language == "en"

    def test_language_region_stripped(self):
        """Contract: _detect_language splits on '-' (region stripped)."""
        html = '<html lang="en-US"><body>text</body></html>'
        result = extract_content(html, "http://example.com")
        assert result.language == "en"

    def test_language_ja(self):
        html = '<html lang="ja"><body>text</body></html>'
        result = extract_content(html, "http://example.com")
        assert result.language == "ja"

    def test_content_length_matches_text(self):
        html = '<html><body><p>hello world</p></body></html>'
        result = extract_content(html, "http://example.com")
        assert result.content_length == len(result.text)

    def test_status_code_passed_through(self):
        result = extract_content("<html><body>test</body></html>", "http://example.com", status_code=404)
        assert result.status_code == 404


class TestRemoveStopwords:
    def test_empty_list(self):
        assert remove_stopwords([]) == []

    def test_all_stopwords(self):
        assert remove_stopwords(["the", "a", "an", "is", "are"]) == []

    def test_no_stopwords(self):
        assert remove_stopwords(["hello", "world"]) == ["hello", "world"]

    def test_mixed_case(self):
        result = remove_stopwords(["The", "quick", "brown", "fox"])
        assert "quick" in result
        assert "brown" in result
        assert "fox" in result

    def test_unicode_tokens(self):
        result = remove_stopwords(["the", "日本語", "is", "test"])
        assert "日本語" in result
        assert "test" in result

    def test_duplicate_tokens(self):
        result = remove_stopwords(["the", "the", "word", "the"])
        assert result == ["word"]

    def test_custom_stopwords(self):
        result = remove_stopwords(["hello", "world"], stopwords={"hello"})
        assert result == ["world"]

    def test_none_stopwords_uses_default(self):
        result = remove_stopwords(["the", "word"], stopwords=None)
        assert result == ["word"]


class TestComputeTf:
    def test_empty_tokens(self):
        assert compute_tf([]) == {}

    def test_single_token(self):
        tf = compute_tf(["hello"])
        assert tf["hello"] == 1.0

    def test_uniform_distribution(self):
        tf = compute_tf(["a", "b", "c"])
        for token in ["a", "b", "c"]:
            assert tf[token] == pytest.approx(1.0 / 3.0)

    def test_duplicate_tokens(self):
        tf = compute_tf(["a", "a", "b"])
        assert tf["a"] == pytest.approx(2.0 / 3.0)
        assert tf["b"] == pytest.approx(1.0 / 3.0)

    def test_sum_to_one(self):
        tokens = ["a", "b", "c", "a", "b"]
        tf = compute_tf(tokens)
        assert sum(tf.values()) == pytest.approx(1.0)

    def test_unicode_tokens(self):
        tf = compute_tf(["日本語", "test"])
        assert "日本語" in tf
        assert "test" in tf


class TestExtractTitle:
    def test_no_title_tag(self):
        soup = BeautifulSoup("<html><body>content</body></html>", "html.parser")
        assert _extract_title(soup) == ""

    def test_empty_title_tag(self):
        soup = BeautifulSoup("<html><head><title></title></head></html>", "html.parser")
        assert _extract_title(soup) == ""

    def test_whitespace_title(self):
        soup = BeautifulSoup("<html><head><title>   </title></head></html>", "html.parser")
        assert _extract_title(soup) == ""

    def test_title_with_whitespace(self):
        soup = BeautifulSoup("<html><head><title>  Real Title  </title></head></html>", "html.parser")
        assert _extract_title(soup) == "Real Title"


class TestExtractMetaDesc:
    def test_no_meta_desc(self):
        soup = BeautifulSoup("<html><head></head></html>", "html.parser")
        assert _extract_meta_desc(soup) == ""

    def test_empty_meta_desc(self):
        soup = BeautifulSoup('<html><head><meta name="description" content=""></head></html>', "html.parser")
        assert _extract_meta_desc(soup) == ""

    def test_meta_desc_whitespace(self):
        soup = BeautifulSoup('<html><head><meta name="description" content="  desc  "></head></html>', "html.parser")
        assert _extract_meta_desc(soup) == "desc"


class TestExtractMetaKeywords:
    def test_no_meta_keywords(self):
        soup = BeautifulSoup("<html><head></head></html>", "html.parser")
        assert _extract_meta_keywords(soup) == []

    def test_empty_meta_keywords(self):
        soup = BeautifulSoup('<html><head><meta name="keywords" content=""></head></html>', "html.parser")
        assert _extract_meta_keywords(soup) == []

    def test_single_keyword(self):
        soup = BeautifulSoup('<html><head><meta name="keywords" content="python"></head></html>', "html.parser")
        assert _extract_meta_keywords(soup) == ["python"]

    def test_multiple_keywords(self):
        soup = BeautifulSoup('<html><head><meta name="keywords" content="python, programming, code"></head></html>', "html.parser")
        assert _extract_meta_keywords(soup) == ["python", "programming", "code"]

    def test_keywords_with_whitespace(self):
        soup = BeautifulSoup('<html><head><meta name="keywords" content="  python ,  programming  "></head></html>', "html.parser")
        assert _extract_meta_keywords(soup) == ["python", "programming"]

    def test_unicode_keywords(self):
        soup = BeautifulSoup('<html><head><meta name="keywords" content="python, 日本語"></head></html>', "html.parser")
        assert "日本語" in _extract_meta_keywords(soup)


class TestExtractHeadings:
    def test_no_headings(self):
        soup = BeautifulSoup("<html><body><p>text</p></body></html>", "html.parser")
        assert _extract_headings(soup) == []

    def test_mixed_heading_levels(self):
        soup = BeautifulSoup("<html><body><h1>A</h1><h3>B</h3><h2>C</h2></body></html>", "html.parser")
        headings = _extract_headings(soup)
        assert "h1: A" in headings
        assert "h2: C" in headings
        assert "h3: B" in headings

    def test_heading_with_nested_tags(self):
        soup = BeautifulSoup("<html><body><h1>Title <span>Subtitle</span></h1></body></html>", "html.parser")
        headings = _extract_headings(soup)
        assert "Title" in headings[0]
        assert "Subtitle" in headings[0]

    def test_h4_h5_h6_not_extracted(self):
        """Contract: only h1-h3 are extracted."""
        soup = BeautifulSoup("<html><body><h4>Deep</h4><h5>Deeper</h5><h6>Deepest</h6></body></html>", "html.parser")
        assert _extract_headings(soup) == []


class TestExtractText:
    def test_empty_body(self):
        soup = BeautifulSoup("<html><body></body></html>", "html.parser")
        assert _extract_text(soup) == ""

    def test_script_and_style_removed(self):
        soup = BeautifulSoup("<html><body><script>var x=1;</script><style>.cls{}</style><p>real text</p></body></html>", "html.parser")
        text = _extract_text(soup)
        assert "var x=1" not in text
        assert ".cls{}" not in text
        assert "real text" in text

    def test_nav_footer_header_removed(self):
        soup = BeautifulSoup("<html><body><nav>nav text</nav><footer>footer</footer><header>header</header><p>main</p></body></html>", "html.parser")
        text = _extract_text(soup)
        assert "nav text" not in text
        assert "footer" not in text
        assert "header" not in text
        assert "main" in text

    def test_whitespace_normalization(self):
        soup = BeautifulSoup("<html><body><p>line1</p><p>line2</p></body></html>", "html.parser")
        text = _extract_text(soup)
        assert "line1" in text
        assert "line2" in text


class TestExtractLinks:
    def test_no_links(self):
        soup = BeautifulSoup("<html><body><p>text</p></body></html>", "html.parser")
        assert _extract_links(soup, "http://example.com") == []

    def test_absolute_link(self):
        soup = BeautifulSoup('<html><body><a href="http://other.com">link</a></body></html>', "html.parser")
        links = _extract_links(soup, "http://example.com")
        assert "http://other.com" in links

    def test_relative_link(self):
        soup = BeautifulSoup('<html><body><a href="/path">link</a></body></html>', "html.parser")
        links = _extract_links(soup, "http://example.com")
        assert "http://example.com/path" in links

    def test_anchor_link(self):
        soup = BeautifulSoup('<html><body><a href="#section">anchor</a></body></html>', "html.parser")
        links = _extract_links(soup, "http://example.com/page")
        assert "http://example.com/page#section" in links

    def test_empty_href_ignored(self):
        soup = BeautifulSoup('<html><body><a href="">empty</a></body></html>', "html.parser")
        assert _extract_links(soup, "http://example.com") == []


class TestDetectLanguage:
    def test_lang_on_html_tag(self):
        soup = BeautifulSoup('<html lang="en"><body>text</body></html>', "html.parser")
        assert _detect_language(soup) == "en"

    def test_html_lang_takes_precedence_over_body(self):
        """Contract: only html tag is checked, not body."""
        soup = BeautifulSoup('<html lang="en"><body lang="ja">text</body></html>', "html.parser")
        assert _detect_language(soup) == "en"


class TestExtractedContentMethods:
    def test_get_searchable_text(self):
        result = extract_content("<html><head><title>T</title></head><body><h1>H</h1><p>P</p></body></html>", "http://example.com")
        searchable = result.get_searchable_text()
        assert "T" in searchable
        assert "H" in searchable
        assert "P" in searchable

    def test_get_keywords_strips_heading_prefix(self):
        result = extract_content("<html><body><h1>Python Tutorial</h1></body></html>", "http://example.com")
        keywords = result.get_keywords()
        assert "python" in keywords
        assert "tutorial" in keywords
        # h1 prefix should be stripped
        assert "h1" not in keywords

    def test_get_keywords_deduplicates(self):
        result = extract_content("<html><body><h1>Python</h1><p>Python</p></body></html>", "http://example.com")
        keywords = result.get_keywords()
        assert keywords.count("python") == 1


class TestCliEndToEnd:
    def test_extract_via_cli_import(self):
        """End-to-end: import and use extract_content through the module's public API."""
        from personal_index import content
        result = content.extract_content("<html><body><p>CLI test</p></body></html>", "http://test.com")
        assert "CLI test" in result.text
