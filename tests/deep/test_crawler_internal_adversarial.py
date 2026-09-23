"""Deep-pin regression armor for personal_index.crawler internal helpers.

Targets the underscore-prefixed helpers on the Crawler class plus the
CrawlerConfig round-trip, pinning edge cases (empty, boundary, negative,
unicode, None) so a silent behavior change in the crawl guard path is caught.
"""

from __future__ import annotations


from personal_index.crawler import Crawler, CrawlerConfig
from personal_index.models import CrawledPage


def _crawler(**cfg):
    return Crawler(config=CrawlerConfig(**cfg))


# --- _get_domain -----------------------------------------------------------

def test_get_domain_http():
    assert _crawler()._get_domain("http://example.com/a/b") == "example.com"


def test_get_domain_https_with_port():
    assert _crawler()._get_domain("https://sub.example.com:8080/x") == "sub.example.com:8080"


def test_get_domain_empty_string():
    assert _crawler()._get_domain("") == ""


def test_get_domain_no_scheme_relative():
    # urlparse of a bare relative path yields empty netloc
    assert _crawler()._get_domain("/relative/path") == ""


def test_get_domain_unicode_host():
    assert _crawler()._get_domain("http://exämple.com/") == "exämple.com"


# --- _should_crawl ---------------------------------------------------------

def test_should_crawl_empty_url_false():
    assert _crawler()._should_crawl("") is False


def test_should_crawl_none_url_false():
    # not url -> False guard path
    assert _crawler()._should_crawl(None) is False


def test_should_crawl_bad_scheme_false():
    assert _crawler()._should_crawl("ftp://example.com/x") is False


def test_should_crawl_javascript_scheme_false():
    assert _crawler()._should_crawl("javascript:alert(1)") is False


def test_should_crawl_valid_http_true():
    assert _crawler()._should_crawl("http://example.com/") is True


def test_should_crawl_visited_false():
    c = _crawler()
    c._visited.add("http://example.com/")
    assert c._should_crawl("http://example.com/") is False


def test_should_crawl_max_pages_reached_false():
    c = _crawler(max_pages=0)
    assert c._should_crawl("http://example.com/") is False


def test_should_crawl_blocked_extension_false():
    c = _crawler()
    assert c._should_crawl("http://example.com/file.pdf") is False


def test_should_crawl_blocked_extension_case_insensitive():
    c = _crawler()
    # path is lowercased before the endswith check
    assert c._should_crawl("http://example.com/FILE.PDF") is False


def test_should_crawl_allowed_domains_match_true():
    c = _crawler(allowed_domains=["example.com"])
    assert c._should_crawl("http://example.com/x") is True


def test_should_crawl_allowed_domains_mismatch_false():
    c = _crawler(allowed_domains=["other.com"])
    assert c._should_crawl("http://example.com/x") is False


# --- _extract_links --------------------------------------------------------

def test_extract_links_basic():
    c = _crawler()
    html = '<a href="/a">a</a><a href="/b">b</a>'
    links = c._extract_links(html, "http://example.com/")
    assert links == ["http://example.com/a", "http://example.com/b"]


def test_extract_links_skips_javascript():
    c = _crawler()
    html = '<a href="javascript:void(0)">x</a><a href="/ok">ok</a>'
    links = c._extract_links(html, "http://example.com/")
    assert links == ["http://example.com/ok"]


def test_extract_links_skips_mailto():
    c = _crawler()
    html = '<a href="mailto:a@b.com">m</a>'
    assert c._extract_links(html, "http://example.com/") == []


def test_extract_links_empty_html():
    c = _crawler()
    assert c._extract_links("", "http://example.com/") == []


def test_extract_links_no_anchor_tags():
    c = _crawler()
    assert c._extract_links("<p>no links here</p>", "http://example.com/") == []


# --- _extract_content ------------------------------------------------------

def test_extract_content_title_and_text():
    c = _crawler()
    html = "<html><head><title>  My Title  </title></head><body><p>Hello world</p></body></html>"
    page = c._extract_content(html, "http://example.com/")
    assert page.title == "My Title"
    assert "Hello world" in page.content
    assert page.url == "http://example.com/"


def test_extract_content_strips_scripts():
    c = _crawler()
    html = "<html><head><script>var x=1;</script></head><body><p>Real</p></body></html>"
    page = c._extract_content(html, "http://example.com/")
    assert "var x=1" not in page.content
    assert "Real" in page.content


def test_extract_content_meta_description():
    c = _crawler()
    html = '<html><head><meta name="description" content="  A desc  "></head><body>t</body></html>'
    page = c._extract_content(html, "http://example.com/")
    assert page.meta_description == "A desc"


def test_extract_content_empty_html():
    c = _crawler()
    page = c._extract_content("", "http://example.com/")
    assert page.title == ""
    assert page.content == ""
    assert page.meta_description == ""


def test_extract_content_whitespace_collapsed():
    c = _crawler()
    html = "<html><body><p>a   b\n\t c</p></body></html>"
    page = c._extract_content(html, "http://example.com/")
    assert "a b c" in page.content


# --- _filter_by_interests --------------------------------------------------

def test_filter_no_interest_store_true():
    c = _crawler()
    assert c._filter_by_interests(CrawledPage(url="http://x/")) is True


def test_filter_with_interest_store_no_match():
    class _Store:
        def list_all(self):
            return []
    c = _crawler()
    c.interest_store = _Store()
    page = CrawledPage(url="http://x/", content="nothing")
    assert c._filter_by_interests(page) is False
    assert page.matched_interests == []


def test_filter_with_interest_store_match():
    class _Interest:
        name = "python"
        def matches(self, content, url):
            return "python" in content
    class _Store:
        def list_all(self):
            return [_Interest()]
    c = _crawler()
    c.interest_store = _Store()
    page = CrawledPage(url="http://x/", content="learn python")
    assert c._filter_by_interests(page) is True
    assert page.matched_interests == ["python"]


# --- CrawlerConfig round-trip ---------------------------------------------

def test_config_to_dict_roundtrip():
    cfg = CrawlerConfig(max_depth=5, max_pages=42, delay=0.5)
    restored = CrawlerConfig.from_dict(cfg.to_dict())
    assert restored.max_depth == 5
    assert restored.max_pages == 42
    assert restored.delay == 0.5


def test_config_from_dict_ignores_unknown_keys():
    restored = CrawlerConfig.from_dict({"max_depth": 7, "bogus_key": "x"})
    assert restored.max_depth == 7
    assert not hasattr(restored, "bogus_key")


def test_config_from_dict_empty_dict_defaults():
    restored = CrawlerConfig.from_dict({})
    assert restored.max_depth == 3
    assert restored.max_pages == 100
