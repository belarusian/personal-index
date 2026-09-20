"""VERIFY deep tests for ARCH-62/63/64/65 (cycle 214, VALIDATOR).

Each ticket at `Status: IMPLEMENTED` is pinned against its implemented
contract on current main, plus one adversarial input the contract implies.
No product-code changes (validator role). If any test is RED it documents a
real contract violation -> file a QA ticket (do NOT fix product code).

  ARCH-62  link_analyzer: negative `max_anchor_length` clamps to 0; the
           0-path yields `{'': 1}` (an empty anchor IS counted); the counting
           idiom is unchanged (guard on the stripped, pre-truncation anchor).
  ARCH-63  defensive-load guard (CLASS): `DomainManager._load` and
           `ContentPinner._load` degrade to the empty state on ANY malformed
           (non-dict) value and never raise out of construction.
  ARCH-64  text_utils.read_time_minutes: `wpm <= 0 -> 0` (no ZeroDivisionError,
           no bogus 1); `wpm > 0 -> ceil(count/wpm)`.
  ARCH-65  negative-slice "top N / limit" guard, OFFSET form:
           `content_summarizer.summarize(max_sentences<=0) -> sentences==[]`
           and `content_search.SearchIndex.search(limit<=0) -> results==[]`
           (no all-but-last leak); plus one end-to-end CLI run through the
           installed `personal-index search` command.
"""

from __future__ import annotations

import json
import os

from click.testing import CliRunner, Result

from personal_index.cli import main
from personal_index.content_pin import ContentPinner
from personal_index.content_search import SearchIndex as ContentSearchIndex
from personal_index.content_summarizer import summarize
from personal_index.domains import DomainManager
from personal_index.index import SearchIndex as CliSearchIndex
from personal_index.link_analyzer import LinkAnalyzer
from personal_index.models import IndexedPage
from personal_index.text_utils import read_time_minutes


# ---------------------------------------------------------------------------
# ARCH-62 — link_analyzer negative max_anchor_length clamp
# ---------------------------------------------------------------------------
class TestVerifyArch62LinkAnalyzerClamp:
    def test_negative_clamped_to_zero_yields_empty_anchor(self):
        # max_anchor_length=-1 clamps to 0; a non-empty anchor is truncated to
        # '' and counted as '' -> {'': 1} (identical to max_anchor_length=0).
        a = LinkAnalyzer(base_domain="example.com", max_anchor_length=-1)
        r = a.analyze(
            "http://example.com/",
            [{"url": "http://ext.com/x", "text": "hello"}],
        )
        assert r.stats.anchor_text_distribution == {"": 1}

    def test_negative_matches_zero_adversarial(self):
        # -100 (large negative) must behave identically to 0 for a multi-word
        # anchor; the pre-fix negative slice would have dropped the last 100
        # chars (here the whole anchor) rather than clamping to ''.
        neg = LinkAnalyzer(base_domain="example.com", max_anchor_length=-100)
        zero = LinkAnalyzer(base_domain="example.com", max_anchor_length=0)
        links = [{"url": "http://ext.com/x", "text": "hello world"}]
        assert (
            neg.analyze("http://example.com/", links).stats.anchor_text_distribution
            == zero.analyze("http://example.com/", links).stats.anchor_text_distribution
            == {"": 1}
        )

    def test_positive_unchanged(self):
        # max_anchor_length=100 (default) truncates nothing for a short anchor.
        a = LinkAnalyzer(base_domain="example.com", max_anchor_length=100)
        r = a.analyze(
            "http://example.com/",
            [{"url": "http://ext.com/x", "text": "hello"}],
        )
        assert r.stats.anchor_text_distribution == {"hello": 1}

    def test_whitespace_anchor_not_counted(self):
        # A whitespace-only anchor fails the guard on the stripped anchor `a`
        # and is NOT counted at all (distribution is empty, not {'': 1}).
        a = LinkAnalyzer(base_domain="example.com", max_anchor_length=0)
        r = a.analyze(
            "http://example.com/",
            [{"url": "http://ext.com/x", "text": "   "}],
        )
        assert r.stats.anchor_text_distribution == {}


# ---------------------------------------------------------------------------
# ARCH-63 — defensive-load guard (CLASS): domains + content_pin
# ---------------------------------------------------------------------------
class TestVerifyArch63DefensiveLoad:
    def test_domains_non_dict_value_degrades_to_empty(self, tmp_path):
        # A well-formed-but-wrong-shape value (a string, not a mapping) must
        # yield the empty state and NOT raise out of construction.
        f = tmp_path / "rules.json"
        f.write_text(json.dumps({"example.com": "notadict"}))
        mgr = DomainManager(rules_file=str(f))  # must not raise
        assert mgr.list_rules() == []

    def test_domains_normal_case_populated(self, tmp_path):
        # Alongside the guard: a valid rule yields the populated state.
        f = tmp_path / "rules.json"
        f.write_text(json.dumps({"example.com": {"domain": "example.com", "allowed": True}}))
        mgr = DomainManager(rules_file=str(f))
        assert len(mgr.list_rules()) == 1

    def test_content_pin_non_dict_value_degrades_to_empty(self, tmp_path):
        # A non-dict value in the persisted mapping must yield the empty state
        # and NOT raise out of construction (pre-fix: AttributeError from .get).
        f = tmp_path / "pinned.json"
        f.write_text(json.dumps({"a": "notadict"}))
        pinner = ContentPinner(storage_path=str(f))  # must not raise
        assert pinner.get_pinned_items() == []

    def test_content_pin_normal_case_populated(self, tmp_path):
        # Alongside the guard: a valid pinned item yields the populated state.
        f = tmp_path / "pinned.json"
        f.write_text(json.dumps({"a": {"pinned_at": "2026-01-01", "reason": "r"}}))
        pinner = ContentPinner(storage_path=str(f))
        assert len(pinner.get_pinned_items()) == 1


# ---------------------------------------------------------------------------
# ARCH-64 — text_utils.read_time_minutes guard-the-raw-divisor
# ---------------------------------------------------------------------------
class TestVerifyArch64ReadTime:
    def test_zero_wpm_returns_zero(self):
        # wpm=0 must short-circuit to 0 (no ZeroDivisionError).
        assert read_time_minutes("word " * 300, wpm=0) == 0

    def test_negative_wpm_returns_zero(self):
        # wpm<0 must return 0 (no bogus 1 from max(1, negative)).
        assert read_time_minutes("word " * 300, wpm=-5) == 0

    def test_positive_wpm_ceil(self):
        # wpm>0 -> ceil(count/wpm); 1000 words / 200 wpm = 5.
        assert read_time_minutes("word " * 1000, wpm=200) == 5

    def test_positive_wpm_ceil_rounds_up(self):
        # Adversarial: 1001 words / 200 wpm = 5.005 -> ceil = 6 (not round=5).
        assert read_time_minutes("word " * 1001, wpm=200) == 6


# ---------------------------------------------------------------------------
# ARCH-65 — negative-slice "top N / limit" guard, OFFSET form
# ---------------------------------------------------------------------------
class TestVerifyArch65NegativeSlice:
    def test_summarize_negative_max_sentences_empty(self):
        # max_sentences=-1 must yield sentences==[] (NOT all-but-last of 6).
        text = " ".join(f"Sentence number {i} talks about quantum physics." for i in range(6))
        r = summarize(text, max_sentences=-1)
        assert r.sentences == []
        assert r.summary == ""
        assert r.word_count_summary == 0

    def test_summarize_zero_max_sentences_empty(self):
        # max_sentences=0 (already correct) still yields sentences==[].
        text = " ".join(f"Sentence number {i} talks about quantum physics." for i in range(6))
        r = summarize(text, max_sentences=0)
        assert r.sentences == []

    def test_summarize_positive_max_sentences(self):
        # max_sentences=3 -> exactly 3 sentences (scoring path, 6 > 3).
        text = " ".join(f"Sentence number {i} talks about quantum physics." for i in range(6))
        r = summarize(text, max_sentences=3)
        assert len(r.sentences) == 3

    def test_search_negative_limit_empty(self):
        # limit=-1 must yield results==[] (NOT all-but-last of 3) while total
        # is still the full match count.
        idx = ContentSearchIndex()
        for i in range(3):
            idx.add_item({"id": f"i{i}", "content": f"quantum document {i}"})
        r = idx.search("quantum", limit=-1)
        assert r["results"] == []
        assert r["total"] == 3
        assert r["query"] == "quantum"

    def test_search_zero_limit_empty(self):
        # limit=0 (already correct) yields results==[] with full total.
        idx = ContentSearchIndex()
        for i in range(3):
            idx.add_item({"id": f"i{i}", "content": f"quantum document {i}"})
        r = idx.search("quantum", limit=0)
        assert r["results"] == []
        assert r["total"] == 3

    def test_search_positive_limit_offset(self):
        # limit=2, offset=0 -> first 2 ranked results (offset form).
        idx = ContentSearchIndex()
        for i in range(3):
            idx.add_item({"id": f"i{i}", "content": f"quantum document {i}"})
        r = idx.search("quantum", limit=2, offset=0)
        assert len(r["results"]) == 2
        assert r["total"] == 3


# ---------------------------------------------------------------------------
# ARCH-65 — end-to-end CLI run through the installed `personal-index search`
# ---------------------------------------------------------------------------
class TestVerifyArch65CliEndToEnd:
    def _make_index(self, data_dir: str) -> None:
        idx = CliSearchIndex(db_path=os.path.join(data_dir, "search_index.json"))
        idx.add_page(
            IndexedPage(
                url="http://example.com/quantum",
                title="Quantum computing",
                content="Quantum computing is a new field of quantum physics.",
            )
        )

    def _invoke(self, args: list[str], data_dir: str) -> Result:
        runner = CliRunner(isolate_filesystem=False)
        return runner.invoke(main, ["search", *args, "--data-dir", data_dir])

    def test_cli_search_negative_limit_no_results(self, tmp_path):
        # End-to-end: a negative --limit must yield no results (no all-but-last
        # leak through the installed CLI), exit 0.
        dd = str(tmp_path)
        self._make_index(dd)
        res = self._invoke(["quantum", "--limit", "-1"], dd)
        assert res.exit_code == 0
        assert "No results found" in res.output

    def test_cli_search_positive_limit_returns_result(self, tmp_path):
        # Alongside the guard: a positive --limit returns the matching page.
        dd = str(tmp_path)
        self._make_index(dd)
        res = self._invoke(["quantum", "--limit", "5"], dd)
        assert res.exit_code == 0
        assert "Quantum computing" in res.output
