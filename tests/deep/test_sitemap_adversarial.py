"""Adversarial deep tests for personal_index.sitemap.

Contract source: personal_index/sitemap.py docstrings for SitemapEntry,
Sitemap, and SitemapParser. These tests pin the documented behavior against
adversarial inputs: empty / whitespace / unicode / duplicate / out-of-range
values, namespace vs no-namespace XML, relative URL resolution, priority
parsing, changefreq filtering, the documented "skip on ValueError OR
TypeError" claim in get_recent_entries, the inclusive ``days`` boundary, and
one end-to-end CLI run (init + status).

Functions armored:
  SitemapEntry.is_valid, Sitemap.url_count/sitemap_count/get_urls,
  SitemapParser.parse, _resolve_sitemap_url, _parse_sitemap_index_items,
  _parse_url_element, parse_text_sitemap, filter_by_priority,
  filter_by_changefreq, get_recent_entries.
"""

from __future__ import annotations


from personal_index.sitemap import Sitemap, SitemapEntry, SitemapParser

NS = "http://www.sitemaps.org/schemas/sitemap/0.9"


def _url_xml(loc: str, lastmod: str | None = None, changefreq: str | None = None,
             priority: str | None = None, ns: bool = True) -> str:
    """Build a minimal <urlset> with a single <url> entry."""
    pfx = f"xmlns='{NS}'" if ns else ""
    parts = [f"<urlset {pfx}>", "  <url>", f"    <loc>{loc}</loc>"]
    if lastmod is not None:
        parts.append(f"    <lastmod>{lastmod}</lastmod>")
    if changefreq is not None:
        parts.append(f"    <changefreq>{changefreq}</changefreq>")
    if priority is not None:
        parts.append(f"    <priority>{priority}</priority>")
    parts += ["  </url>", "</urlset>"]
    return "\n".join(parts)


# --- SitemapEntry.is_valid --------------------------------------------------

def test_is_valid_http_https():
    assert SitemapEntry("http://a.com").is_valid() is True
    assert SitemapEntry("https://a.com/x").is_valid() is True


def test_is_valid_rejects_non_http():
    assert SitemapEntry("ftp://a.com").is_valid() is False
    assert SitemapEntry("a.com").is_valid() is False
    assert SitemapEntry("").is_valid() is False


def test_is_valid_rejects_whitespace_only():
    assert SitemapEntry("   ").is_valid() is False


def test_is_valid_rejects_scheme_trick():
    # "https://" prefix check is a startswith, not a scheme parse
    assert SitemapEntry("https://").is_valid() is True  # documented: startswith
    assert SitemapEntry("httpx://a.com").is_valid() is False


# --- Sitemap properties -----------------------------------------------------

def test_url_count_and_get_urls_filter_invalid():
    sm = Sitemap(entries=[
        SitemapEntry("https://a.com/ok"),
        SitemapEntry("ftp://a.com/bad"),
        SitemapEntry(""),
    ])
    assert sm.url_count == 3
    assert sm.get_urls() == ["https://a.com/ok"]


def test_sitemap_count():
    sm = Sitemap(sitemaps=["https://a.com/s1", "https://a.com/s2"])
    assert sm.sitemap_count == 2


def test_empty_sitemap_defaults():
    sm = Sitemap()
    assert sm.url_count == 0
    assert sm.sitemap_count == 0
    assert sm.get_urls() == []
    assert sm.source_url == ""


# --- SitemapParser.parse: guard inputs --------------------------------------

def test_parse_empty_string():
    p = SitemapParser()
    sm = p.parse("", source_url="https://src.com/sitemap.xml")
    assert sm.url_count == 0
    assert sm.source_url == "https://src.com/sitemap.xml"


def test_parse_none():
    p = SitemapParser()
    sm = p.parse(None)  # type: ignore[arg-type]
    assert sm.url_count == 0


def test_parse_whitespace_only():
    p = SitemapParser()
    sm = p.parse("   \n\t  ")
    # whitespace is truthy -> ET_fromstring raises -> empty Sitemap
    assert sm.url_count == 0


def test_parse_malformed_xml_returns_empty():
    p = SitemapParser()
    sm = p.parse("<urlset><url><loc>unclosed", source_url="https://src.com")
    assert sm.url_count == 0
    assert sm.source_url == "https://src.com"


def test_parse_unicode_loc():
    p = SitemapParser()
    sm = p.parse(_url_xml("https://a.com/ünïcödé"))
    assert sm.url_count == 1
    assert sm.entries[0].loc == "https://a.com/ünïcödé"


# --- SitemapParser.parse: namespace handling --------------------------------

def test_parse_namespaced_urlset():
    p = SitemapParser()
    sm = p.parse(_url_xml("https://a.com/p", ns=True))
    assert sm.url_count == 1
    assert sm.entries[0].loc == "https://a.com/p"


def test_parse_no_namespace_urlset():
    # no-namespace <urlset> has no ns:url children -> 0 entries (documented:
    # parse() only iterates ns:url children)
    p = SitemapParser()
    sm = p.parse(_url_xml("https://a.com/p", ns=False))
    assert sm.url_count == 0


def test_parse_duplicate_urls_preserved():
    p = SitemapParser()
    xml = (f"<urlset xmlns='{NS}'>"
           "<url><loc>https://a.com/p</loc></url>"
           "<url><loc>https://a.com/p</loc></url>"
           "</urlset>")
    sm = p.parse(xml)
    assert sm.url_count == 2  # duplicates are NOT deduped by the parser


# --- _parse_url_element: priority / changefreq / lastmod --------------------

def test_parse_priority_float():
    p = SitemapParser()
    sm = p.parse(_url_xml("https://a.com/p", priority="0.9"))
    assert sm.entries[0].priority == 0.9


def test_parse_priority_invalid_falls_back_to_default():
    p = SitemapParser()
    sm = p.parse(_url_xml("https://a.com/p", priority="not-a-number"))
    assert sm.entries[0].priority == 0.5


def test_parse_priority_out_of_range_stored_as_is():
    # contract: no range validation; float() is applied verbatim
    p = SitemapParser()
    sm = p.parse(_url_xml("https://a.com/p", priority="5.0"))
    assert sm.entries[0].priority == 5.0


def test_parse_missing_priority_defaults():
    p = SitemapParser()
    sm = p.parse(_url_xml("https://a.com/p"))
    assert sm.entries[0].priority == 0.5


def test_parse_changefreq_default_monthly():
    p = SitemapParser()
    sm = p.parse(_url_xml("https://a.com/p"))
    assert sm.entries[0].changefreq == "monthly"


def test_parse_changefreq_explicit():
    p = SitemapParser()
    sm = p.parse(_url_xml("https://a.com/p", changefreq="daily"))
    assert sm.entries[0].changefreq == "daily"


def test_parse_lastmod_stripped():
    p = SitemapParser()
    sm = p.parse(_url_xml("https://a.com/p", lastmod="  2026-01-01T00:00:00Z  "))
    assert sm.entries[0].lastmod == "2026-01-01T00:00:00Z"


def test_parse_missing_loc_returns_none_entry():
    p = SitemapParser()
    xml = f"<urlset xmlns='{NS}'>  <url>  </url></urlset>"
    sm = p.parse(xml)
    assert sm.url_count == 0


# --- _resolve_sitemap_url / sitemap index -----------------------------------

def test_resolve_sitemap_url_absolute_passthrough():
    p = SitemapParser()
    assert p._resolve_sitemap_url("https://a.com/s.xml", "https://src.com/base") == "https://a.com/s.xml"


def test_resolve_sitemap_url_relative_joined():
    p = SitemapParser()
    assert p._resolve_sitemap_url("s.xml", "https://src.com/base") == "https://src.com/s.xml"


def test_resolve_sitemap_url_no_source_returns_loc():
    p = SitemapParser()
    assert p._resolve_sitemap_url("s.xml", "") == "s.xml"


def test_parse_sitemap_index_namespaced():
    p = SitemapParser()
    xml = (f"<sitemapindex xmlns='{NS}'>"
           "<sitemap><loc>https://a.com/s1.xml</loc></sitemap>"
           "<sitemap><loc>https://a.com/s2.xml</loc></sitemap>"
           "</sitemapindex>")
    sm = p.parse(xml)
    assert sm.sitemaps == ["https://a.com/s1.xml", "https://a.com/s2.xml"]
    assert sm.url_count == 0


def test_parse_sitemap_index_relative_resolved():
    p = SitemapParser()
    xml = (f"<sitemapindex xmlns='{NS}'>"
           "<sitemap><loc>sub/s1.xml</loc></sitemap>"
           "</sitemapindex>")
    sm = p.parse(xml, source_url="https://src.com/sitemap.xml")
    assert sm.sitemaps == ["https://src.com/sub/s1.xml"]


# --- parse_text_sitemap -----------------------------------------------------

def test_parse_text_sitemap_basic():
    p = SitemapParser()
    sm = p.parse_text_sitemap("https://a.com/1\nhttps://a.com/2\n")
    assert sm.get_urls() == ["https://a.com/1", "https://a.com/2"]


def test_parse_text_sitemap_skips_comments_and_blank():
    p = SitemapParser()
    sm = p.parse_text_sitemap("# comment\n\nhttps://a.com/1\n   \n")
    assert sm.get_urls() == ["https://a.com/1"]


def test_parse_text_sitemap_empty():
    p = SitemapParser()
    assert p.parse_text_sitemap("").get_urls() == []


def test_parse_text_sitemap_relative_resolved():
    p = SitemapParser()
    sm = p.parse_text_sitemap("a/1\na/2", base_url="https://src.com/base")
    assert sm.get_urls() == ["https://src.com/a/1", "https://src.com/a/2"]


def test_parse_text_sitemap_rejects_non_http():
    p = SitemapParser()
    sm = p.parse_text_sitemap("ftp://a.com/1\nhttps://a.com/2")
    assert sm.get_urls() == ["https://a.com/2"]


# --- filter_by_priority / filter_by_changefreq ------------------------------

def test_filter_by_priority_inclusive_boundary():
    p = SitemapParser()
    sm = Sitemap(entries=[
        SitemapEntry("https://a.com/low", priority=0.4),
        SitemapEntry("https://a.com/eq", priority=0.5),
        SitemapEntry("https://a.com/high", priority=0.9),
    ])
    out = p.filter_by_priority(sm, min_priority=0.5)
    assert [e.loc for e in out] == ["https://a.com/eq", "https://a.com/high"]


def test_filter_by_changefreq_exact_match():
    p = SitemapParser()
    sm = Sitemap(entries=[
        SitemapEntry("https://a.com/d", changefreq="daily"),
        SitemapEntry("https://a.com/m", changefreq="monthly"),
    ])
    out = p.filter_by_changefreq(sm, freq="daily")
    assert [e.loc for e in out] == ["https://a.com/d"]


def test_filter_by_changefreq_case_sensitive():
    p = SitemapParser()
    sm = Sitemap(entries=[SitemapEntry("https://a.com/d", changefreq="Daily")])
    assert p.filter_by_changefreq(sm, freq="daily") == []


# --- get_recent_entries -----------------------------------------------------

def test_get_recent_entries_recent_included():
    p = SitemapParser()
    sm = Sitemap(entries=[SitemapEntry("https://a.com/p", lastmod="2099-01-01T00:00:00Z")])
    out = p.get_recent_entries(sm, days=30)
    assert [e.loc for e in out] == ["https://a.com/p"]


def test_get_recent_entries_old_excluded():
    p = SitemapParser()
    sm = Sitemap(entries=[SitemapEntry("https://a.com/p", lastmod="2000-01-01T00:00:00Z")])
    assert p.get_recent_entries(sm, days=30) == []


def test_get_recent_entries_none_lastmod_skipped():
    p = SitemapParser()
    sm = Sitemap(entries=[SitemapEntry("https://a.com/p", lastmod=None)])
    assert p.get_recent_entries(sm, days=30) == []


def test_get_recent_entries_invalid_date_skipped():
    p = SitemapParser()
    sm = Sitemap(entries=[SitemapEntry("https://a.com/p", lastmod="not-a-date")])
    assert p.get_recent_entries(sm, days=30) == []


def test_get_recent_entries_z_suffix_handled():
    p = SitemapParser()
    sm = Sitemap(entries=[SitemapEntry("https://a.com/p", lastmod="2099-01-01T00:00:00Z")])
    assert len(p.get_recent_entries(sm, days=30)) == 1


def test_get_recent_entries_inclusive_days_boundary():
    # contract: "(cutoff - lastmod).days <= days" is inclusive
    from datetime import datetime, timedelta, timezone
    p = SitemapParser()
    exactly = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()
    sm = Sitemap(entries=[SitemapEntry("https://a.com/p", lastmod=exactly)])
    assert len(p.get_recent_entries(sm, days=30)) == 1


# --- DEFECT: get_recent_entries naive lastmod (QA-14) -----------------------

def test_get_recent_entries_naive_lastmod_skipped_per_docstring():
    """QA-14: docstring says entries whose lastmod raises TypeError are
    skipped, but a timezone-NAIVE lastmod (no Z / no offset) parses fine via
    fromisoformat, then (cutoff - lastmod) raises TypeError OUTSIDE the
    try/except -> the whole call crashes instead of skipping the entry.

    Expected-per-docs: the naive entry is skipped and the aware entry is
    returned. Actual: TypeError propagates.
    """
    p = SitemapParser()
    sm = Sitemap(entries=[
        SitemapEntry("https://a.com/naive", lastmod="2099-01-01T00:00:00"),
        SitemapEntry("https://a.com/aware", lastmod="2099-01-01T00:00:00Z"),
    ])
    out = p.get_recent_entries(sm, days=30)
    assert [e.loc for e in out] == ["https://a.com/aware"]


# --- end-to-end CLI run -----------------------------------------------------

def test_end_to_end_cli_init_and_status(tmp_path):
    """End-to-end: init + status on an empty index (exit 0, no crash)."""
    from click.testing import CliRunner
    from personal_index.cli import main

    runner = CliRunner()
    dd = str(tmp_path / "data")
    r = runner.invoke(main, ["init", "--data-dir", dd])
    assert r.exit_code == 0, r.output
    assert "Initialized" in r.output

    r = runner.invoke(main, ["status", "--data-dir", dd])
    assert r.exit_code == 0, r.output


# --- additional armor: edge cases verified against the contract -------------

def test_parse_priority_nan_stored_and_excluded_by_filter():
    # contract: float() applied verbatim (no range/NaN validation); NaN is
    # not >= 0.5 so it is excluded by filter_by_priority
    p = SitemapParser()
    sm = p.parse(_url_xml("https://a.com/p", priority="nan"))
    assert sm.entries[0].priority != sm.entries[0].priority  # NaN
    assert p.filter_by_priority(sm, min_priority=0.5) == []


def test_parse_text_sitemap_crlf_line_endings():
    p = SitemapParser()
    sm = p.parse_text_sitemap("https://a.com/1\r\nhttps://a.com/2\r\n")
    assert sm.get_urls() == ["https://a.com/1", "https://a.com/2"]


def test_resolve_sitemap_url_protocol_relative():
    p = SitemapParser()
    assert p._resolve_sitemap_url("//a.com/s.xml", "https://src.com/base") == "https://a.com/s.xml"


def test_parse_urlset_with_nested_sitemapindex_child():
    # contract: if the root contains an ns:sitemapindex child, parse()
    # delegates to the index parser and returns sitemaps (not url entries)
    p = SitemapParser()
    xml = (f"<urlset xmlns='{NS}'>"
           "<sitemapindex>"
           "<sitemap><loc>https://a.com/s1</loc></sitemap>"
           "</sitemapindex>"
           "</urlset>")
    sm = p.parse(xml)
    assert sm.sitemaps == ["https://a.com/s1"]
    assert sm.url_count == 0
