"""ARCH-73 VERIFY: FuzzySearcher.highlight_html must HTML-entity-escape the
searched text (XSS class) while preserving <mark> highlighting, and the plain
`highlight` path must remain byte-for-byte unchanged (ANSI, no escaping).

Pins the 5 acceptance criteria in tickets/ARCH-73.md plus adversarial inputs
the contract implies (all 5 special chars, unicode, empty, out-of-range /
negative / duplicate indices, no-double-escape property, idempotence, and the
search_with_highlight html=True/False split).
"""

from __future__ import annotations

import html

from personal_index.fuzzy_search import FuzzySearcher


S = FuzzySearcher()


# --- AC 1: no raw < > & " ' from the input text --------------------------

def test_ac1_xss_pin_no_raw_script():
    out = S.highlight_html("<script>alert(1)</script>", [0])
    assert "<script>" not in out
    assert "</script>" not in out
    # The < and > are entity-escaped (the leading < is wrapped in <mark>).
    assert "&lt;" in out
    assert "&gt;" in out
    assert "<mark>&lt;</mark>" in out


def test_ac1_all_five_special_chars_escaped():
    text = "&<>\"'"
    out = S.highlight_html(text, [])
    assert out == html.escape(text)
    assert "&amp;" in out
    assert "&lt;" in out
    assert "&gt;" in out
    assert "&quot;" in out
    assert "&#x27;" in out
    # No raw < > " ' survives (the & in the output is only inside entities).
    for ch in "<>\"'":
        assert ch not in out


def test_ac1_property_stripping_marks_equals_html_escape():
    """For ANY text and ANY indices, removing the <mark> wrappers must yield
    exactly html.escape(text) - the single-escape contract, no double-escape."""
    for text in ["abc", "&<>\"'", "<script>alert(1)</script>", "café ☕",
                 "a&b", "x", ""]:
        for indices in [[], [0], [0, 1, 2], list(range(len(text))),
                        [len(text) + 50], [-1], [0, 0]]:
            out = S.highlight_html(text, indices)
            stripped = out.replace("<mark>", "").replace("</mark>", "")
            assert stripped == html.escape(text), (text, indices, out)


def test_ac1_no_double_escaping():
    """Escaping must be applied exactly once: the output must not contain the
    escaped form of an already-escaped entity (e.g. &amp;amp;)."""
    out = S.highlight_html("a & b", [2])
    assert "&amp;" in out
    assert "&amp;amp;" not in out
    assert "&lt;" not in out  # no < in input, so no <mark> leakage either


# --- AC 2: matched indices still wrapped in <mark> around escaped chars ---

def test_ac2_mark_wraps_escaped_char():
    # '&' at index 1 must be wrapped: a<mark>&amp;</mark>b
    out = S.highlight_html("a&b", [1])
    assert out == "a<mark>&amp;</mark>b"


def test_ac2_mark_count_matches_indices():
    out = S.highlight_html("hello", [0, 2, 4])
    assert out.count("<mark>") == 3
    assert out.count("</mark>") == 3


def test_ac2_mark_around_angle_bracket():
    out = S.highlight_html("<b>", [0])
    assert out == "<mark>&lt;</mark>b&gt;"
    # Mark both ends:
    assert S.highlight_html("<b>", [0, 2]) == "<mark>&lt;</mark>b<mark>&gt;</mark>"


# --- AC 3: not-indices guard returns the ESCAPED text, not raw -----------

def test_ac3_guard_empty_indices_returns_escaped():
    assert S.highlight_html("<b>x</b>", []) == "&lt;b&gt;x&lt;/b&gt;"
    assert S.highlight_html("a & b", []) == "a &amp; b"


def test_ac3_guard_is_not_raw():
    out = S.highlight_html("<script>", [])
    assert out != "<script>"
    assert out == "&lt;script&gt;"


# --- AC 4: plain highlight path byte-for-byte unchanged (ANSI, no escape) -

def test_ac4_plain_path_ansi_unchanged():
    out = S.highlight("a&b", [1])
    assert out == "a\033[1m&\033[0mb"
    # No HTML entities on the plain path.
    assert "&amp;" not in out
    assert "&lt;" not in out


def test_ac4_plain_path_empty_indices_unchanged():
    assert S.highlight("<script>", []) == "<script>"


# --- AC 5: search_with_highlight html=True escaped+marked, html=False -----

def test_ac5_search_with_highlight_html_true_escaped():
    res = S.search_with_highlight("script", ["<script>alert(1)</script>"], html=True)
    assert len(res) == 1
    match, highlighted = res[0]
    assert "<script>" not in highlighted
    assert "&lt;" in highlighted
    if match.matched_indices:
        assert "<mark>" in highlighted


def test_ac5_search_with_highlight_html_false_plain():
    res = S.search_with_highlight("script", ["<script>alert(1)</script>"], html=False)
    assert len(res) == 1
    match, highlighted = res[0]
    # Plain path: raw text preserved (no HTML entities), ANSI wrapping.
    assert "&lt;" not in highlighted
    assert "&gt;" not in highlighted
    assert "<" in highlighted
    assert ">" in highlighted
    assert "\033[1m" in highlighted


# --- adversarial: unicode / empty / out-of-range / negative / duplicate ---

def test_adv_unicode_escaped_and_marked():
    out = S.highlight_html("café ☕ <x>", [7])
    # '<' at index 8 must be escaped and wrapped.
    assert "<x>" not in out
    assert "&lt;" in out
    assert "<mark>" in out
    # Non-ASCII passes through untouched (html.escape leaves them alone).
    assert "café ☕ " in out


def test_adv_empty_text():
    assert S.highlight_html("", []) == ""
    assert S.highlight_html("", [0, 1]) == ""


def test_adv_out_of_range_index_ignored():
    # Index 100 on a 3-char text: no mark, but still fully escaped.
    out = S.highlight_html("a&b", [100])
    assert out == "a&amp;b"
    assert "<mark>" not in out


def test_adv_negative_index_ignored():
    out = S.highlight_html("a&b", [-1])
    assert out == "a&amp;b"
    assert "<mark>" not in out


def test_adv_duplicate_indices_single_mark():
    out = S.highlight_html("a&b", [1, 1])
    assert out == "a<mark>&amp;</mark>b"
    assert out.count("<mark>") == 1


def test_adv_all_indices_wrapped_still_escaped():
    text = "a&b"
    out = S.highlight_html(text, [0, 1, 2])
    assert out == "<mark>a</mark><mark>&amp;</mark><mark>b</mark>"


def test_adv_idempotence_of_stripping():
    """Applying the escape contract is stable: re-deriving from the stripped
    output reproduces the same escaped text (no drift)."""
    text = "a & <b> 'c' \"d\""
    out = S.highlight_html(text, [0, 4, 8])
    stripped = out.replace("<mark>", "").replace("</mark>", "")
    assert stripped == html.escape(text)
    # Re-running highlight_html on the stripped (already-escaped) text with no
    # indices must not corrupt it further into a different shape than a fresh
    # escape of the same string.
    assert S.highlight_html(stripped, []) == html.escape(stripped)
