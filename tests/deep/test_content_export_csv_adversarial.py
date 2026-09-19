"""Adversarial deep tests for personal_index/content_export_csv.py.

Targets the public surface of CSVExporter / ExportFormat / ExportStats:
_format_value edge cases, CSV/TSV quoting+escaping round-trips, column
discovery order, header handling, limit/offset guards, format dispatch,
get_stats, export_to_file, and an end-to-end CLI export run.

QA-46: export() clamps a negative ``limit`` to 0 (documented in the method
docstring and docs/content_export_csv.md) but applies NO floor clamp to
``offset``. ``filtered = ...[offset:]`` therefore leaks Python
negative-slice semantics: ``offset=-1`` returns the LAST row, ``offset=-2``
returns the last two rows. This violates the binding negative-slice rule in
docs/CONTRACTS.md, which explicitly names "the offset form" and requires a
non-positive caller-supplied bound to yield the same empty result as the
zero bound. Pinned with xfail-strict below (the guard is one-sided: cap
present, floor missing).
"""

from __future__ import annotations

import csv
import io
import json
import os
from datetime import datetime

import pytest
from click.testing import CliRunner

from personal_index.cli import main
from personal_index.content_export_csv import CSVExporter, ExportFormat
from personal_index.index import SearchIndex
from personal_index.models import CrawledPage


@pytest.fixture
def exporter() -> CSVExporter:
    return CSVExporter()


def _data_rows(out: str, header: str | None = None) -> list[str]:
    """Return non-empty lines, dropping the header line if present."""
    lines = [ln for ln in out.splitlines() if ln]
    if header is not None and lines and lines[0] == header:
        lines = lines[1:]
    return lines


class TestFormatValue:
    """_format_value edge cases (the value->str coercion contract)."""

    def test_none_is_empty_string(self, exporter: CSVExporter) -> None:
        assert exporter._format_value(None) == ""

    def test_bool_is_str(self, exporter: CSVExporter) -> None:
        assert exporter._format_value(True) == "True"
        assert exporter._format_value(False) == "False"

    def test_numeric_passthrough(self, exporter: CSVExporter) -> None:
        assert exporter._format_value(0) == "0"
        assert exporter._format_value(-5) == "-5"
        assert exporter._format_value(1.5) == "1.5"

    def test_datetime_is_isoformat(self, exporter: CSVExporter) -> None:
        assert exporter._format_value(datetime(2020, 1, 2, 3, 4, 5)) == "2020-01-02T03:04:05"

    def test_list_joined_with_semicolon(self, exporter: CSVExporter) -> None:
        assert exporter._format_value([1, 2]) == "1; 2"
        assert exporter._format_value(("a", "b")) == "a; b"

    def test_empty_list_is_empty_string(self, exporter: CSVExporter) -> None:
        assert exporter._format_value([]) == ""

    def test_dict_is_json(self, exporter: CSVExporter) -> None:
        assert exporter._format_value({"a": 1}) == '{"a": 1}'
        assert exporter._format_value({}) == "{}"

    def test_unicode_preserved(self, exporter: CSVExporter) -> None:
        assert exporter._format_value("héllo wörld 日本語") == "héllo wörld 日本語"


class TestCsvQuotingRoundTrip:
    """Embedded commas/quotes/newlines must survive a csv.reader round-trip."""

    def test_embedded_comma_quoted(self, exporter: CSVExporter) -> None:
        out = exporter.export([{"id": "1", "title": "a,b"}])
        rows = list(csv.reader(io.StringIO(out)))
        assert rows[1][1] == "a,b"

    def test_embedded_quote_escaped(self, exporter: CSVExporter) -> None:
        out = exporter.export([{"id": "1", "title": 'say "hi"'}])
        rows = list(csv.reader(io.StringIO(out)))
        assert rows[1][1] == 'say "hi"'

    def test_embedded_newline_round_trips(self, exporter: CSVExporter) -> None:
        out = exporter.export([{"id": "1", "title": "line1\nline2"}])
        rows = list(csv.reader(io.StringIO(out)))
        assert rows[1][1] == "line1\nline2"

    def test_all_specials_together(self, exporter: CSVExporter) -> None:
        val = 'a,b "c"\nd'
        out = exporter.export([{"id": "1", "title": val}])
        rows = list(csv.reader(io.StringIO(out)))
        assert rows[1][1] == val

    def test_tsv_embedded_tab_quoted(self, exporter: CSVExporter) -> None:
        out = exporter.export([{"id": "1", "title": "a\tb"}], export_format=ExportFormat.TSV)
        rows = list(csv.reader(io.StringIO(out), delimiter="\t"))
        assert rows[1][1] == "a\tb"


class TestColumnDiscoveryAndHeader:
    """Column ordering, missing-column handling, header options."""

    def test_default_columns_first_then_sorted(self, exporter: CSVExporter) -> None:
        items = [{"zzz": "1", "id": "1", "title": "a", "mmm": "2"}]
        header = exporter.export(items).splitlines()[0]
        assert header == "id,title,mmm,zzz"

    def test_missing_column_is_empty_string(self, exporter: CSVExporter) -> None:
        out = exporter.export([{"id": "1"}], columns=["id", "title", "url"])
        rows = list(csv.reader(io.StringIO(out)))
        assert rows[1] == ["1", "", ""]

    def test_include_header_false(self, exporter: CSVExporter) -> None:
        out = exporter.export([{"id": "1", "title": "a"}], include_header=False)
        assert out == "1,a\n"

    def test_column_names_rename(self, exporter: CSVExporter) -> None:
        out = exporter.export([{"id": "1", "title": "a"}], column_names={"id": "ID", "title": "TITLE"})
        assert out.splitlines()[0] == "ID,TITLE"

    def test_column_names_missing_key_falls_back(self, exporter: CSVExporter) -> None:
        out = exporter.export([{"id": "1", "title": "a"}], column_names={"id": "ID"})
        assert out.splitlines()[0] == "ID,title"


class TestLimitOffsetGuards:
    """The negative-slice guard class: limit is clamped, offset must be too."""

    def test_negative_limit_clamped_to_zero(self, exporter: CSVExporter) -> None:
        items = [{"a": str(i)} for i in range(3)]
        out = exporter.export(items, limit=-1)
        assert _data_rows(out, "a") == []
        out0 = exporter.export(items, limit=0)
        assert _data_rows(out0, "a") == []

    def test_positive_offset_valid(self, exporter: CSVExporter) -> None:
        items = [{"id": str(i)} for i in range(3)]
        out = exporter.export(items, offset=1, limit=1)
        assert _data_rows(out, "id") == ["1"]

    def test_offset_beyond_range_is_empty(self, exporter: CSVExporter) -> None:
        items = [{"id": str(i)} for i in range(3)]
        assert exporter.export(items, offset=5) == ""

    @pytest.mark.xfail(
        strict=True,
        reason="QA-46: negative offset leaks Python negative-slice semantics "
        "(offset=-1 returns the last row); the binding negative-slice rule in "
        "docs/CONTRACTS.md requires a non-positive offset to yield the same "
        "empty result as offset=0. The guard is one-sided: limit is clamped, "
        "offset is not.",
    )
    def test_negative_offset_clamped_to_zero(self, exporter: CSVExporter) -> None:
        items = [{"id": str(i)} for i in range(3)]
        # offset=-1 must behave like offset=0 (all rows), NOT list[-1:] (last row).
        out = exporter.export(items, offset=-1)
        assert _data_rows(out, "id") == ["0", "1", "2"]
        out2 = exporter.export(items, offset=-2)
        assert _data_rows(out2, "id") == ["0", "1", "2"]


class TestFormatDispatch:
    """Format dispatch and JSON round-trips."""

    def test_json_round_trip(self, exporter: CSVExporter) -> None:
        items = [{"id": "1", "title": "a,b", "url": 'say "hi"'}]
        out = exporter.export(items, export_format=ExportFormat.JSON)
        assert json.loads(out) == items

    def test_json_lines_round_trip(self, exporter: CSVExporter) -> None:
        items = [{"id": "1", "title": "a"}, {"id": "2", "title": "b"}]
        out = exporter.export(items, export_format=ExportFormat.JSON_LINES)
        parsed = [json.loads(ln) for ln in out.splitlines() if ln]
        assert parsed == items

    def test_tsv_forces_tab_delimiter(self, exporter: CSVExporter) -> None:
        out = exporter.export([{"id": "1", "title": "a"}], export_format=ExportFormat.TSV)
        assert out == "id\ttitle\n1\ta\n"

    def test_empty_items_is_empty_string(self, exporter: CSVExporter) -> None:
        assert exporter.export([]) == ""
        assert exporter.export([], include_header=True) == ""


class TestGetStatsAndFile:
    """get_stats and export_to_file contracts."""

    def test_get_stats_empty(self, exporter: CSVExporter) -> None:
        assert exporter.get_stats([]) == {"total_items": 0, "columns": 0, "column_names": []}

    def test_get_stats_counts_unique_columns(self, exporter: CSVExporter) -> None:
        stats = exporter.get_stats([{"id": "1", "title": "a"}, {"id": "2", "extra": "z"}])
        assert stats["total_items"] == 2
        assert stats["columns"] == 3
        assert stats["column_names"] == ["extra", "id", "title"]

    def test_export_to_file_round_trip(self, exporter: CSVExporter, tmp_path: object) -> None:
        p = os.path.join(str(tmp_path), "out.csv")
        exporter.export_to_file([{"id": "1", "title": "héllo"}], p)
        with open(p, encoding="utf-8") as f:
            assert f.read() == "id,title\n1,héllo\n"

    def test_export_to_file_encoding_kwarg(self, exporter: CSVExporter, tmp_path: object) -> None:
        p = os.path.join(str(tmp_path), "out.csv")
        exporter.export_to_file([{"id": "1", "title": "héllo"}], p, encoding="utf-8")
        with open(p, encoding="utf-8") as f:
            assert "héllo" in f.read()


class TestOversizedAndEdge:
    """Large rows and non-serializable-ish values must not raise."""

    def test_oversized_row(self, exporter: CSVExporter) -> None:
        big = {"id": "1", "title": "x" * 10000}
        out = exporter.export([big])
        assert len(out) > 10000
        rows = list(csv.reader(io.StringIO(out)))
        assert rows[1][1] == "x" * 10000

    def test_many_rows(self, exporter: CSVExporter) -> None:
        items = [{"id": str(i), "title": f"t{i}"} for i in range(500)]
        out = exporter.export(items)
        assert len(_data_rows(out, "id,title")) == 500

    def test_duplicate_items(self, exporter: CSVExporter) -> None:
        items = [{"id": "1", "title": "a"}, {"id": "1", "title": "a"}]
        out = exporter.export(items)
        assert len(_data_rows(out, "id,title")) == 2


class TestCliExportEndToEnd:
    """End-to-end run through the installed CLI export command."""

    def test_cli_export_csv(self, tmp_path: object) -> None:
        dd = str(tmp_path)
        idx = SearchIndex(db_path=os.path.join(dd, "search_index.json"))
        for i in range(3):
            idx.add_page(CrawledPage(url=f"http://x{i}", title=f"t{i}", content="c"))
        result = CliRunner().invoke(main, ["export", "--format", "csv", "--data-dir", dd])
        assert result.exit_code == 0, result.output
        assert "http://x0" in result.output
        assert "http://x2" in result.output

    def test_cli_export_empty_index(self, tmp_path: object) -> None:
        dd = str(tmp_path)
        SearchIndex(db_path=os.path.join(dd, "search_index.json"))
        result = CliRunner().invoke(main, ["export", "--format", "csv", "--data-dir", dd])
        assert result.exit_code == 0, result.output
        assert "No indexed content" in result.output
