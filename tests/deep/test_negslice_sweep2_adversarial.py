"""QA-5: negative-slice "top N / limit" leak - SECOND class sweep (9 new sites).

The QA-4 sweep (13 sites, now CLOSED) fixed one set of public "top N / limit"
functions that leaked Python negative-slice semantics: a negative bound returned
``list[:-1]`` (all-but-last) instead of an empty list, while the ``0`` guard
correctly returned ``[]``.

A whole-codebase re-sweep of the slicing idiom
(``grep -rnE '\\[:[a-z_]+\\]' personal_index/``) found 9 FURTHER public
"top N / limit" sites of the SAME class that were NOT in the QA-4 sweep and
still leak. Each test below asserts the CORRECT contract (negative bound ->
empty) and is pinned xfail-strict so the suite stays green while the defect
exists. When the implementer adds the ``if N <= 0: return []`` guard, each test
flips to a hard pass (remove the xfail marker).

Sites (all confirmed leaking at HEAD):
  1. content_categorizer.CategorizationResult.top_n(n)          -> topics[:n]
  2. content_linker/similarity.SimilarityEngine.find_similar(limit) -> results[:limit]
  3. search_facets/facet_builder.FacetBuilder.build(max_values) -> facet.values[:max_values]
  4. content_digest.DigestGenerator.generate(max_entries_per_section) -> entries[:max_per_section]
  5. formatter.format_search_results(limit)                     -> results[:limit]
  6. content_export_csv.CSVExporter.export(limit)               -> filtered[:limit]
  7. cli.py list_pages (CLI `list --limit`)                     -> sorted(...)[:limit]
  8. cli.py top (CLI `top --limit`)                             -> sorted(...)[:limit]
  9. cli_top.py top_pages (CLI `top` alt impl)                  -> list_pages()[:limit]

Expected per docs/contract: a negative bound is out-of-range and must yield an
empty result, consistent with the ``0`` guard.
"""

from __future__ import annotations

import os

import pytest
from click.testing import CliRunner

from personal_index.cli import main
from personal_index.content_categorizer import (
    CategorizationResult,
    TopicScore,
)
from personal_index.content_digest import DigestEntry, DigestGenerator
from personal_index.content_export_csv import CSVExporter
from personal_index.content_linker.similarity import SimilarityEngine
from personal_index.formatter import format_search_results
from personal_index.index import SearchIndex
from personal_index.models import CrawledPage
from personal_index.search_facets.facet_builder import FacetBuilder


def _categorization_result() -> CategorizationResult:
    return CategorizationResult(
        primary_topic="a",
        topics=[
            TopicScore(topic="a", score=5.0),
            TopicScore(topic="b", score=3.0),
            TopicScore(topic="c", score=1.0),
        ],
    )


class TestNegativeSliceSweep2:
    """Each test asserts the correct contract; xfail-strict while the leak exists."""

    @pytest.mark.xfail(strict=True, reason="QA-5 site 1: top_n(-1) leaks all-but-last")
    def test_categorization_result_top_n_negative(self):
        r = _categorization_result()
        assert r.top_n(-1) == []
        assert r.top_n(0) == []
        assert len(r.top_n(2)) == 2

    @pytest.mark.xfail(strict=True, reason="QA-5 site 2: find_similar(limit=-1) leaks all-but-last")
    def test_similarity_find_similar_negative(self):
        s = SimilarityEngine()
        items = [("a", "hello world"), ("b", "hello there"), ("c", "goodbye")]
        assert s.find_similar("hello", items, threshold=0.0, limit=-1) == []
        assert s.find_similar("hello", items, threshold=0.0, limit=0) == []

    @pytest.mark.xfail(strict=True, reason="QA-5 site 3: build(max_values=-1) leaks all-but-last")
    def test_facet_builder_build_negative(self):
        b = FacetBuilder()
        items = [{"tag": "a"}, {"tag": "b"}, {"tag": "c"}]
        f = b.build(items, ["tag"], max_values=-1)
        assert f["tag"].values == []
        f0 = b.build(items, ["tag"], max_values=0)
        assert f0["tag"].values == []

    @pytest.mark.xfail(strict=True, reason="QA-5 site 4: generate(max=-1) leaks all-but-last")
    def test_digest_generate_negative(self):
        g = DigestGenerator()
        for i in range(3):
            g.add_entry(
                DigestEntry(
                    url=f"http://x{i}", title=f"t{i}", summary="s",
                    score=1.0, source="src",
                )
            )
        d = g.generate(group_by="none", max_entries_per_section=-1)
        assert d.sections[0].entries == []
        d0 = g.generate(group_by="none", max_entries_per_section=0)
        assert d0.sections[0].entries == []

    @pytest.mark.xfail(strict=True, reason="QA-5 site 5: format_search_results(limit=-1) leaks all-but-last")
    def test_format_search_results_negative(self):
        from personal_index.index import SearchResult

        rs = [
            SearchResult(url=f"http://x{i}", title=f"t{i}", relevance_score=0.5)
            for i in range(3)
        ]
        assert format_search_results(rs, -1).count("http://") == 0
        assert format_search_results(rs, 0).count("http://") == 0

    @pytest.mark.xfail(strict=True, reason="QA-5 site 6: CSVExporter.export(limit=-1) leaks all-but-last")
    def test_csv_exporter_negative(self):
        e = CSVExporter()
        items = [{"a": str(i)} for i in range(3)]
        # limit=-1 must yield no data rows (only header, if any)
        out = e.export(items, limit=-1)
        data_rows = [ln for ln in out.splitlines() if ln and ln != "a"]
        assert data_rows == []
        out0 = e.export(items, limit=0)
        data_rows0 = [ln for ln in out0.splitlines() if ln and ln != "a"]
        assert data_rows0 == []


def _seed_index(dd: str) -> None:
    idx = SearchIndex(db_path=os.path.join(dd, "search_index.json"))
    for i in range(3):
        idx.add_page(CrawledPage(url=f"http://x{i}", title=f"t{i}", content="c"))


class TestCliNegativeLimitEndToEnd:
    """End-to-end CLI runs (installed CLI) for the `list` and `top` commands."""

    @pytest.mark.xfail(strict=True, reason="QA-5 site 7: CLI `list --limit -1` leaks all-but-last")
    def test_cli_list_negative_limit(self, tmp_path):
        dd = str(tmp_path / "data")
        _seed_index(dd)
        result = CliRunner().invoke(main, ["list", "--limit", "-1", "--data-dir", dd])
        assert result.exit_code == 0, result.output
        # negative limit must behave like limit=0 (no pages)
        assert result.output.count("http://") == 0

    @pytest.mark.xfail(strict=True, reason="QA-5 site 8: CLI `top --limit -1` leaks all-but-last")
    def test_cli_top_negative_limit(self, tmp_path):
        dd = str(tmp_path / "data")
        _seed_index(dd)
        result = CliRunner().invoke(main, ["top", "--limit", "-1", "--data-dir", dd])
        assert result.exit_code == 0, result.output
        assert result.output.count("http://") == 0

    def test_cli_list_zero_limit_clean(self, tmp_path):
        """The 0 guard already works - clean armor (not xfail)."""
        dd = str(tmp_path / "data")
        _seed_index(dd)
        result = CliRunner().invoke(main, ["list", "--limit", "0", "--data-dir", dd])
        assert result.exit_code == 0, result.output
        assert result.output.count("http://") == 0

    def test_cli_list_valid_limit_clean(self, tmp_path):
        """Valid limit returns exactly that many - clean armor (not xfail)."""
        dd = str(tmp_path / "data")
        _seed_index(dd)
        result = CliRunner().invoke(main, ["list", "--limit", "2", "--data-dir", dd])
        assert result.exit_code == 0, result.output
        assert result.output.count("http://") == 2
