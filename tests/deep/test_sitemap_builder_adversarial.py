"""Cycle 189 PROBE: personal_index/sitemap_builder.py (never-probed subsystem).

Adversarial deep tests for SitemapEntry / SitemapBuilder:
  - SitemapEntry: priority clamping (out-of-range, boundary), last_modified
    auto-fill (None -> UTC now, tz-aware), explicit datetime preserved,
    to_element() sub-element contract (loc/lastmod/changefreq/priority).
  - SitemapBuilder: add_entry / add_entries (in-place, no dedup, order),
    url_count, clear, build() XML shape + declaration, build_sitemap_index,
    split_into_chunks (boundary, empty, chunk_size<=0), idempotence,
    XML escaping of special chars, unicode, whitespace.
  - End-to-end CLI smoke run (python -m personal_index --version).

DEFECT FILED (pinned xfail-strict, flip to hard passes on fix):
  QA-23: build() / build_sitemap_index() do NOT emit the sitemap namespace.
    `Element("urlset", nsmap=NSMAP)` treats `nsmap` as a literal XML attribute
    (ElementTree's Element has no `nsmap` parameter), so the serialized root is
    a bare `<urlset nsmap="{'': 'http://...'}">` with NO `xmlns` declaration.
    docs/content-sitemap.md promises "a <urlset> root (with the sitemap
    namespace)". Consequence: the package's own SitemapParser (which reads
    `ns:url` / `ns:loc` under the sitemap namespace) parses the builder's
    output to ZERO entries — the documented build->parse round-trip is broken.

Documented contract holes (docs/content-sitemap.md) NOT re-ticketed:
  hole 1 (MAX_SITEMAP_SIZE_BYTES never enforced), hole 4 (chunk_size==0
  ValueError) are documented design constraints; we pin the documented
  behavior, we do not file them as new defects.
"""

from __future__ import annotations

import subprocess
import sys
from datetime import datetime, timezone
from xml.etree.ElementTree import fromstring

import pytest

from personal_index.sitemap import SitemapParser
from personal_index.sitemap_builder import (
    SitemapBuilder,
    SitemapEntry,
    SM_NS,
)


# ---------------------------------------------------------------------------
# SitemapEntry — priority clamping
# ---------------------------------------------------------------------------
class TestEntryPriorityClamp:
    def test_priority_default(self):
        assert SitemapEntry(url="https://x.com/").priority == 0.5

    def test_priority_below_zero_clamped_to_zero(self):
        assert SitemapEntry(url="https://x.com/", priority=-1.0).priority == 0.0

    def test_priority_above_one_clamped_to_one(self):
        assert SitemapEntry(url="https://x.com/", priority=5.0).priority == 1.0

    def test_priority_boundary_zero(self):
        assert SitemapEntry(url="https://x.com/", priority=0.0).priority == 0.0

    def test_priority_boundary_one(self):
        assert SitemapEntry(url="https://x.com/", priority=1.0).priority == 1.0

    def test_priority_interior_preserved(self):
        assert SitemapEntry(url="https://x.com/", priority=0.7).priority == 0.7


# ---------------------------------------------------------------------------
# SitemapEntry — last_modified auto-fill / preservation
# ---------------------------------------------------------------------------
class TestEntryLastModified:
    def test_none_autofills_utc_now(self):
        before = datetime.now(timezone.utc)
        e = SitemapEntry(url="https://x.com/")
        after = datetime.now(timezone.utc)
        assert e.last_modified is not None
        assert e.last_modified.tzinfo is not None
        assert before <= e.last_modified <= after

    def test_none_never_none_invariant(self):
        # docs invariant: "Builder last_modified is never None (auto-filled)"
        e = SitemapEntry(url="https://x.com/", last_modified=None)
        assert e.last_modified is not None

    def test_explicit_datetime_preserved(self):
        dt = datetime(2020, 1, 2, 3, 4, 5, tzinfo=timezone.utc)
        e = SitemapEntry(url="https://x.com/", last_modified=dt)
        assert e.last_modified == dt

    def test_to_element_lastmod_format(self):
        dt = datetime(2020, 1, 2, 3, 4, 5, tzinfo=timezone.utc)
        e = SitemapEntry(url="https://x.com/", last_modified=dt)
        el = e.to_element()
        assert el.find("lastmod").text == "2020-01-02T03:04:05Z"


# ---------------------------------------------------------------------------
# SitemapEntry — to_element sub-element contract
# ---------------------------------------------------------------------------
class TestEntryToElement:
    def test_tag_is_url(self):
        assert SitemapEntry(url="https://x.com/").to_element().tag == "url"

    def test_exactly_four_subelements(self):
        el = SitemapEntry(url="https://x.com/").to_element()
        assert len(list(el)) == 4
        assert [c.tag for c in el] == ["loc", "lastmod", "changefreq", "priority"]

    def test_loc_text_is_url(self):
        el = SitemapEntry(url="https://x.com/a").to_element()
        assert el.find("loc").text == "https://x.com/a"

    def test_changefreq_default_monthly(self):
        el = SitemapEntry(url="https://x.com/").to_element()
        assert el.find("changefreq").text == "monthly"

    def test_changefreq_custom(self):
        el = SitemapEntry(url="https://x.com/", change_frequency="daily").to_element()
        assert el.find("changefreq").text == "daily"

    def test_priority_one_decimal(self):
        el = SitemapEntry(url="https://x.com/", priority=0.75).to_element()
        assert el.find("priority").text == "0.8"  # f"{0.75:.1f}" -> "0.8"

    def test_priority_zero_one_decimal(self):
        el = SitemapEntry(url="https://x.com/", priority=0.0).to_element()
        assert el.find("priority").text == "0.0"


# ---------------------------------------------------------------------------
# SitemapBuilder — add / count / clear
# ---------------------------------------------------------------------------
class TestBuilderAdd:
    def test_empty_url_count(self):
        assert SitemapBuilder().url_count == 0

    def test_add_entry_increments(self):
        b = SitemapBuilder()
        b.add_entry("https://x.com/1")
        b.add_entry("https://x.com/2")
        assert b.url_count == 2

    def test_add_entries_in_place_no_dedup(self):
        b = SitemapBuilder()
        b.add_entry("https://x.com/1")
        batch = [SitemapEntry(url="https://x.com/1"), SitemapEntry(url="https://x.com/2")]
        b.add_entries(batch)
        # no de-duplication: the duplicate "1" is kept
        assert b.url_count == 3
        assert [e.url for e in b.entries] == [
            "https://x.com/1",
            "https://x.com/1",
            "https://x.com/2",
        ]

    def test_add_entries_preserves_order(self):
        b = SitemapBuilder()
        b.add_entries([SitemapEntry(url=f"https://x.com/{i}") for i in range(5)])
        assert [e.url for e in b.entries] == [f"https://x.com/{i}" for i in range(5)]

    def test_add_entries_empty_list_noop(self):
        b = SitemapBuilder()
        b.add_entries([])
        assert b.url_count == 0

    def test_clear_empties_in_place(self):
        b = SitemapBuilder()
        b.add_entry("https://x.com/1")
        entries_ref = b.entries
        b.clear()
        assert b.url_count == 0
        assert entries_ref == []  # same list object, cleared in place

    def test_add_after_clear(self):
        b = SitemapBuilder()
        b.add_entry("https://x.com/1")
        b.clear()
        b.add_entry("https://x.com/2")
        assert b.url_count == 1
        assert b.entries[0].url == "https://x.com/2"


# ---------------------------------------------------------------------------
# SitemapBuilder — build() XML shape (namespace-independent invariants)
# ---------------------------------------------------------------------------
class TestBuilderBuild:
    def test_build_returns_bytes(self):
        b = SitemapBuilder()
        b.add_entry("https://x.com/1")
        assert isinstance(b.build(), bytes)

    def test_build_xml_declaration_prefix(self):
        b = SitemapBuilder()
        b.add_entry("https://x.com/1")
        out = b.build().decode("utf-8")
        assert out.startswith('<?xml version="1.0" encoding="UTF-8"?>\n')

    def test_build_root_localname_is_urlset(self):
        b = SitemapBuilder()
        b.add_entry("https://x.com/1")
        root = fromstring(b.build())
        assert root.tag.split("}")[-1] == "urlset"

    def test_build_one_url_per_entry(self):
        b = SitemapBuilder()
        for i in range(3):
            b.add_entry(f"https://x.com/{i}")
        root = fromstring(b.build())
        # count <url> children regardless of namespace
        urls = [c for c in root if c.tag.split("}")[-1] == "url"]
        assert len(urls) == 3

    def test_build_empty_urlset(self):
        b = SitemapBuilder()
        root = fromstring(b.build())
        assert root.tag.split("}")[-1] == "urlset"
        assert [c for c in root if c.tag.split("}")[-1] == "url"] == []

    def test_build_is_pure_read(self):
        b = SitemapBuilder()
        b.add_entry("https://x.com/1")
        b.build()
        b.build()
        assert b.url_count == 1  # build does not mutate entries

    def test_build_idempotent_bytes(self):
        b = SitemapBuilder()
        b.add_entry("https://x.com/1")
        assert b.build() == b.build()


# ---------------------------------------------------------------------------
# SitemapBuilder — build_sitemap_index (namespace-independent invariants)
# ---------------------------------------------------------------------------
class TestBuilderSitemapIndex:
    def test_index_root_localname(self):
        b = SitemapBuilder()
        root = fromstring(b.build_sitemap_index(["https://x.com/s1.xml"]))
        assert root.tag.split("}")[-1] == "sitemapindex"

    def test_index_one_sitemap_per_url(self):
        b = SitemapBuilder()
        root = fromstring(b.build_sitemap_index(["https://x.com/s1.xml", "https://x.com/s2.xml"]))
        sitemaps = [c for c in root if c.tag.split("}")[-1] == "sitemap"]
        assert len(sitemaps) == 2
        locs = [
            c.find("loc").text if c.find("loc") is not None else c.find(f"{{{SM_NS}}}loc").text
            for c in sitemaps
        ]
        assert locs == ["https://x.com/s1.xml", "https://x.com/s2.xml"]

    def test_index_empty(self):
        b = SitemapBuilder()
        root = fromstring(b.build_sitemap_index([]))
        assert root.tag.split("}")[-1] == "sitemapindex"
        assert [c for c in root if c.tag.split("}")[-1] == "sitemap"] == []

    def test_index_declaration_prefix(self):
        b = SitemapBuilder()
        out = b.build_sitemap_index(["https://x.com/s1.xml"]).decode("utf-8")
        assert out.startswith('<?xml version="1.0" encoding="UTF-8"?>\n')


# ---------------------------------------------------------------------------
# SitemapBuilder — split_into_chunks
# ---------------------------------------------------------------------------
class TestBuilderSplit:
    def test_split_empty(self):
        assert SitemapBuilder().split_into_chunks(2) == []

    def test_split_exact_multiple(self):
        b = SitemapBuilder()
        for i in range(4):
            b.add_entry(f"https://x.com/{i}")
        chunks = b.split_into_chunks(2)
        assert [len(c) for c in chunks] == [2, 2]

    def test_split_uneven(self):
        b = SitemapBuilder()
        for i in range(5):
            b.add_entry(f"https://x.com/{i}")
        chunks = b.split_into_chunks(2)
        assert [len(c) for c in chunks] == [2, 2, 1]

    def test_split_larger_than_total(self):
        b = SitemapBuilder()
        for i in range(3):
            b.add_entry(f"https://x.com/{i}")
        chunks = b.split_into_chunks(10)
        assert [len(c) for c in chunks] == [3]

    def test_split_preserves_order_across_chunks(self):
        b = SitemapBuilder()
        for i in range(5):
            b.add_entry(f"https://x.com/{i}")
        flat = [e.url for c in b.split_into_chunks(2) for e in c]
        assert flat == [f"https://x.com/{i}" for i in range(5)]

    def test_split_default_chunk_size(self):
        b = SitemapBuilder()
        for i in range(3):
            b.add_entry(f"https://x.com/{i}")
        chunks = b.split_into_chunks()
        assert [len(c) for c in chunks] == [3]

    def test_split_chunk_size_zero_raises_valueerror(self):
        # contract hole 4 (documented): range(0, n, 0) -> ValueError
        b = SitemapBuilder()
        b.add_entry("https://x.com/1")
        with pytest.raises(ValueError):
            b.split_into_chunks(0)

    def test_split_chunk_size_negative_returns_empty(self):
        # range(0, n, -1) is empty -> no chunks (documents current behavior)
        b = SitemapBuilder()
        b.add_entry("https://x.com/1")
        assert b.split_into_chunks(-1) == []


# ---------------------------------------------------------------------------
# SitemapBuilder — XML escaping / unicode / whitespace (namespace-independent)
# ---------------------------------------------------------------------------
class TestBuilderEscaping:
    def _loc(self, b: SitemapBuilder) -> str:
        root = fromstring(b.build())
        url = [c for c in root if c.tag.split("}")[-1] == "url"][0]
        loc = [c for c in url if c.tag.split("}")[-1] == "loc"][0]
        assert loc.text is not None
        return loc.text

    def test_ampersand_escaped_and_roundtrips(self):
        b = SitemapBuilder()
        b.add_entry("https://x.com/?a=1&b=2")
        raw = b.build().decode("utf-8")
        assert "&amp;" in raw  # raw & must be escaped in serialized XML
        assert self._loc(b) == "https://x.com/?a=1&b=2"

    def test_angle_brackets_escaped(self):
        b = SitemapBuilder()
        b.add_entry("https://x.com/?q=<tag>")
        raw = b.build().decode("utf-8")
        assert "<tag>" not in raw  # must be escaped, not raw
        assert self._loc(b) == "https://x.com/?q=<tag>"

    def test_unicode_url_roundtrip(self):
        b = SitemapBuilder()
        b.add_entry("https://x.com/путь/道")
        assert self._loc(b) == "https://x.com/путь/道"

    def test_whitespace_url_preserved(self):
        b = SitemapBuilder()
        b.add_entry("https://x.com/a b")
        assert self._loc(b) == "https://x.com/a b"


# ---------------------------------------------------------------------------
# QA-23 — the namespace defect (xfail-strict pins; flip to hard passes on fix)
# docs/content-sitemap.md: "build() -> bytes — a <urlset> root (with the
# sitemap namespace)". The code emits a bare <urlset> with a literal
# nsmap="{'': ...}" attribute and no xmlns declaration, so the package's own
# SitemapParser (which reads ns:url / ns:loc) parses it to ZERO entries.
# ---------------------------------------------------------------------------
class TestQA23Namespace:
    def test_build_root_carries_sitemap_namespace(self):
        b = SitemapBuilder()
        b.add_entry("https://x.com/1")
        root = fromstring(b.build())
        assert root.tag == f"{{{SM_NS}}}urlset"

    def test_build_no_literal_nsmap_attribute(self):
        """The nsmap dict must not leak as a literal XML attribute."""
        b = SitemapBuilder()
        b.add_entry("https://x.com/1")
        raw = b.build().decode("utf-8")
        assert "nsmap=" not in raw
        assert "xmlns" in raw  # a real namespace declaration must be present

    def test_build_url_children_namespaced(self):
        b = SitemapBuilder()
        for i in range(3):
            b.add_entry(f"https://x.com/{i}")
        root = fromstring(b.build())
        assert len(root.findall(f"{{{SM_NS}}}url")) == 3

    def test_index_root_carries_sitemap_namespace(self):
        b = SitemapBuilder()
        root = fromstring(b.build_sitemap_index(["https://x.com/s1.xml"]))
        assert root.tag == f"{{{SM_NS}}}sitemapindex"

    def test_roundtrip_through_parser_recovers_urls(self):
        """build() -> SitemapParser.parse() must recover the same URLs."""
        b = SitemapBuilder()
        urls = [f"https://x.com/page/{i}" for i in range(4)]
        for u in urls:
            b.add_entry(u, change_frequency="weekly", priority=0.9)
        parsed = SitemapParser().parse(b.build().decode("utf-8"))
        assert parsed.get_urls() == urls

    def test_roundtrip_preserves_changefreq(self):
        b = SitemapBuilder()
        b.add_entry("https://x.com/a", change_frequency="hourly")
        parsed = SitemapParser().parse(b.build().decode("utf-8"))
        assert parsed.entries[0].changefreq == "hourly"

    def test_roundtrip_preserves_priority(self):
        b = SitemapBuilder()
        b.add_entry("https://x.com/a", priority=0.3)
        parsed = SitemapParser().parse(b.build().decode("utf-8"))
        assert parsed.entries[0].priority == 0.3

    def test_roundtrip_lastmod_present(self):
        b = SitemapBuilder()
        b.add_entry("https://x.com/a")
        parsed = SitemapParser().parse(b.build().decode("utf-8"))
        assert parsed.entries[0].lastmod is not None
        assert parsed.entries[0].lastmod.endswith("Z")


# ---------------------------------------------------------------------------
# End-to-end CLI smoke run
# ---------------------------------------------------------------------------
class TestCliSmoke:
    def test_cli_version_runs(self):
        proc = subprocess.run(
            [sys.executable, "-m", "personal_index", "--version"],
            capture_output=True,
            text=True,
            timeout=60,
        )
        assert proc.returncode == 0
        assert "version" in proc.stdout.lower()
