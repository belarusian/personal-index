"""Adversarial deep tests for personal_index.formatter.

Contract source: personal_index/formatter.py docstrings for the pure string
helpers. These tests pin the documented behavior against adversarial inputs:
empty / whitespace / unicode / duplicate / out-of-range values, boundary
thresholds (59.9/60/3599.9/3600 for duration; 1023/1024/1048575/1048576 for
file size), the documented "result is always at most max_length characters"
truncate claim (including the max_length < 3 no-ellipsis carve-out), the
documented "each source position is matched at most once / longest-first"
highlight claim (substring terms, regex-special terms, case sensitivity,
duplicates), format_table empty-input and ragged-row handling, and one
end-to-end CLI run (init + search on an empty index).

Functions armored:
  format_table, format_duration, format_file_size, format_timestamp,
  truncate, highlight.
"""

from __future__ import annotations

from personal_index.formatter import (
    format_duration,
    format_file_size,
    format_table,
    format_timestamp,
    highlight,
    truncate,
)


# --- format_duration --------------------------------------------------------

def test_format_duration_seconds_below_60():
    assert format_duration(0) == "0.0s"
    assert format_duration(59.9) == "59.9s"
    assert format_duration(1.5) == "1.5s"


def test_format_duration_minutes_boundary():
    # 60 is the first value in the minutes band (seconds < 60 is exclusive).
    assert format_duration(60) == "1.0m"
    assert format_duration(3599.9) == "60.0m"


def test_format_duration_hours_boundary():
    # 3600 is the first value in the hours band.
    assert format_duration(3600) == "1.0h"
    assert format_duration(7200) == "2.0h"


def test_format_duration_negative_out_of_range():
    # Negative seconds fall into the < 60 band and are formatted as seconds.
    assert format_duration(-5) == "-5.0s"


# --- format_file_size -------------------------------------------------------

def test_format_file_size_bytes_below_1024():
    assert format_file_size(0) == "0B"
    assert format_file_size(1023) == "1023B"


def test_format_file_size_kb_boundary():
    assert format_file_size(1024) == "1.0KB"
    assert format_file_size(1048575) == "1024.0KB"


def test_format_file_size_mb_boundary():
    assert format_file_size(1048576) == "1.0MB"


def test_format_file_size_gb_boundary():
    assert format_file_size(1024 ** 3) == "1.0GB"


def test_format_file_size_negative_out_of_range():
    # Negative bytes fall into the < 1024 band and are formatted as bytes.
    assert format_file_size(-5) == "-5B"


# --- format_timestamp -------------------------------------------------------

def test_format_timestamp_none_and_empty():
    assert format_timestamp(None) == "N/A"
    assert format_timestamp("") == "N/A"


def test_format_timestamp_iso_datetime():
    assert format_timestamp("2024-01-15T10:30:00") == "2024-01-15 10:30:00"


def test_format_timestamp_iso_date_only():
    # A bare ISO date parses and renders at midnight.
    assert format_timestamp("2024-01-15") == "2024-01-15 00:00:00"


def test_format_timestamp_unparseable_returns_original():
    # The documented fallback: an unparseable string is returned unchanged.
    assert format_timestamp("garbage") == "garbage"
    assert format_timestamp("not-a-date") == "not-a-date"


# --- truncate ---------------------------------------------------------------

def test_truncate_short_text_unchanged():
    assert truncate("", 100) == ""
    assert truncate("hello", 100) == "hello"
    # Exactly at the limit is not truncated.
    assert truncate("hello", 5) == "hello"


def test_truncate_adds_ellipsis_and_respects_max_length():
    out = truncate("hello world", 10)
    assert out.endswith("...")
    assert len(out) <= 10
    assert out == "hello w..."


def test_truncate_max_length_below_3_no_ellipsis():
    # Documented carve-out: no room for the three-dot ellipsis, so the text is
    # cut to exactly max_length characters.
    assert truncate("hello world", 0) == ""
    assert truncate("hello world", 1) == "h"
    assert truncate("hello world", 2) == "he"


def test_truncate_max_length_3_is_ellipsis_only():
    # max_length == 3 leaves room for exactly the ellipsis.
    assert truncate("hello world", 3) == "..."


def test_truncate_negative_max_length_clamped_to_zero():
    assert truncate("hello world", -5) == ""


def test_truncate_unicode_counts_characters_not_bytes():
    # The contract is about character count, so a unicode string is truncated
    # by code points and the result never exceeds max_length characters.
    out = truncate("héllo wörld", 8)
    assert len(out) <= 8
    assert out.endswith("...")


def test_truncate_property_never_exceeds_max_length():
    for text in ["", "a", "abc", "hello world", "x" * 500, "üñïçødé " * 40]:
        for ml in range(0, 12):
            assert len(truncate(text, ml)) <= ml


# --- highlight --------------------------------------------------------------

def test_highlight_no_terms_returns_text():
    assert highlight("text", []) == "text"
    # Empty-string terms are filtered out, leaving no terms.
    assert highlight("text", [""]) == "text"


def test_highlight_no_match_returns_text():
    assert highlight("no match here", ["cat"]) == "no match here"


def test_highlight_wraps_each_occurrence():
    assert highlight("cat cat cat", ["cat"]) == "**cat** **cat** **cat**"


def test_highlight_longest_first_substring_not_rematched():
    # Documented: a term that is a substring of another is not re-matched
    # inside the longer term's inserted markers.
    assert highlight("catalog cat", ["cat", "catalog"]) == "**catalog** **cat**"
    assert highlight("cat catalog", ["cat", "catalog"]) == "**cat** **catalog**"


def test_highlight_duplicate_terms_no_double_wrap():
    # Duplicate terms collapse to a single alternation branch.
    assert highlight("cat", ["cat", "cat"]) == "**cat**"


def test_highlight_regex_special_terms_are_escaped():
    # A term containing regex metacharacters must match literally, not as a
    # pattern. 'a.c*' as a regex would match 'a.c'; escaped it matches only
    # the literal string 'a.c*'.
    assert highlight("a.c", ["a.c*"]) == "a.c"
    assert highlight("a.c*", ["a.c*"]) == "**a.c***"


def test_highlight_case_sensitive():
    assert highlight("CAT cat", ["cat"]) == "CAT **cat**"


def test_highlight_unicode_text():
    assert highlight("über cat", ["cat"]) == "über **cat**"


# --- format_table -----------------------------------------------------------

def test_format_table_empty_inputs():
    assert format_table([], []) == ""
    assert format_table(["a"], []) == ""
    assert format_table([], [["x"]]) == ""


def test_format_table_basic_alignment():
    out = format_table(["A", "B"], [["1", "2"], ["3", "4"]])
    lines = out.split("\n")
    assert lines[0] == "A | B"
    assert lines[1] == "--+--"
    assert lines[2] == "1 | 2"
    assert lines[3] == "3 | 4"


def test_format_table_ragged_rows_padded_and_truncated():
    # A row shorter than the headers is padded with spaces; a row longer than
    # the headers has its extra cells dropped.
    out = format_table(["A", "B"], [["1"], ["2", "3", "4"]])
    lines = out.split("\n")
    assert lines[2] == "1 |  "
    assert lines[3] == "2 | 3"


def test_format_table_column_width_driven_by_widest_cell():
    out = format_table(["A", "B"], [["1", "longer"]])
    lines = out.split("\n")
    # The separator width must match the widest cell in each column.
    assert lines[1] == "--+-------"


# --- end-to-end CLI run -----------------------------------------------------

def test_end_to_end_cli_init_and_search_empty_index(tmp_path):
    """End-to-end: init + search on an empty index (exit 0, no crash)."""
    from click.testing import CliRunner
    from personal_index.cli import main

    runner = CliRunner()
    dd = str(tmp_path / "data")
    r = runner.invoke(main, ["init", "--data-dir", dd])
    assert r.exit_code == 0, r.output
    assert "Initialized" in r.output

    r = runner.invoke(main, ["search", "python", "--data-dir", dd, "--format", "json"])
    assert r.exit_code == 0, r.output
    assert "No indexed content found" in r.output
