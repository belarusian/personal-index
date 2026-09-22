"""Cycle 376 PROBE: adversarial regression armor for ContentExtractor's
internal helpers, pinned DIRECTLY (the existing test_content_extractor_adversarial.py
exercises them only through the public extract() happy path).

Every pin asserts the ACTUAL current behavior (re-derived against main), so a
green run is regression armor; the docstrings are silent on these whitespace /
nested-tag / boundary edges, so none of these are contract violations.
"""

from __future__ import annotations

import os
from bs4 import BeautifulSoup

from personal_index.content_extractor import ContentExtractor


def _soup(html: str) -> BeautifulSoup:
    return BeautifulSoup(html, "html.parser")


# --- _extract_title -------------------------------------------------------

def test_extract_title_whitespace_og_content_suppresses_fallback():
    # A whitespace-only og:title content is truthy to .get(), so it is
    # returned stripped to "" and the <title> fallback is NOT reached.
    e = ContentExtractor()
    out = e._extract_title(
        _soup('<head><meta property="og:title" content="   "><title>Real</title></head>')
    )
    assert out == ""


def test_extract_title_empty_og_content_falls_back_to_title():
    # An empty-string og:title content is falsy -> falls through to <title>.
    e = ContentExtractor()
    out = e._extract_title(
        _soup('<head><meta property="og:title" content=""><title>Real</title></head>')
    )
    assert out == "Real"


def test_extract_title_nested_tags_in_title_kept_as_literal_text():
    # <title> is a raw-text element: html.parser keeps inner markup as literal
    # text, so .string returns the raw "<b>x</b>" string (not stripped of tags).
    e = ContentExtractor()
    out = e._extract_title(_soup("<head><title><b>x</b></title></head>"))
    assert out == "<b>x</b>"


def test_extract_title_whitespace_around_title_string_is_stripped():
    e = ContentExtractor()
    out = e._extract_title(_soup("<head><title>   Padded   </title></head>"))
    assert out == "Padded"


# --- _extract_meta --------------------------------------------------------

def test_extract_meta_whitespace_content_returns_empty():
    e = ContentExtractor()
    out = e._extract_meta(
        _soup('<meta name="description" content="   ">'), "description"
    )
    assert out == ""


def test_extract_meta_missing_name_returns_empty():
    e = ContentExtractor()
    out = e._extract_meta(_soup('<meta name="author" content="a">'), "description")
    assert out == ""


# --- _extract_meta_keywords -----------------------------------------------

def test_extract_meta_keywords_only_commas_yields_empty():
    e = ContentExtractor()
    out = e._extract_meta_keywords(_soup('<meta name="keywords" content=",, ,">'))
    assert out == []


def test_extract_meta_keywords_mixed_empty_segments_dropped():
    e = ContentExtractor()
    out = e._extract_meta_keywords(_soup('<meta name="keywords" content="a,,b">'))
    assert out == ["a", "b"]


# --- _extract_canonical ---------------------------------------------------

def test_extract_canonical_whitespace_href_returns_empty():
    e = ContentExtractor()
    out = e._extract_canonical(_soup('<link rel="canonical" href="   ">'))
    assert out == ""


# --- _extract_language ----------------------------------------------------

def test_extract_language_whitespace_lang_returns_empty():
    e = ContentExtractor()
    out = e._extract_language(_soup('<html lang="   "><head></head></html>'))
    assert out == ""


# --- _extract_headings ----------------------------------------------------

def test_extract_headings_whitespace_only_heading_dropped():
    e = ContentExtractor()
    out = e._extract_headings(_soup("<h1>   </h1><h2>ok</h2>"))
    assert out == ["ok"]


# --- _extract_links -------------------------------------------------------

def test_extract_links_whitespace_href_dropped():
    e = ContentExtractor()
    out = e._extract_links(_soup('<a href="   ">t</a>'))
    assert out == []


# --- _extract_images ------------------------------------------------------

def test_extract_images_whitespace_src_dropped():
    e = ContentExtractor()
    out = e._extract_images(_soup('<img src="   ">'))
    assert out == []


def test_extract_images_missing_alt_yields_empty_string():
    e = ContentExtractor()
    out = e._extract_images(_soup('<img src="x.png">'))
    assert out == [("", "x.png")]


# --- _extract_text --------------------------------------------------------

def test_extract_text_max_length_zero_yields_empty():
    out = ContentExtractor(max_text_length=0)._extract_text(_soup("<p>hello world</p>"))
    assert out == ""


def test_extract_text_exact_boundary_not_truncated():
    out = ContentExtractor(max_text_length=5)._extract_text(_soup("<p>abcde</p>"))
    assert out == "abcde"


def test_extract_text_one_over_boundary_truncated():
    out = ContentExtractor(max_text_length=5)._extract_text(_soup("<p>abcdef</p>"))
    assert out == "abcde"


# --- end-to-end CLI run (installed CLI) -----------------------------------

def test_cli_end_to_end_version():
    import subprocess
    import sys

    result = subprocess.run(
        [sys.executable, "-m", "personal_index.cli", "--version"],
        capture_output=True,
        text=True,
        cwd=os.getcwd(),
    )
    assert result.returncode == 0
    assert "0.1.0" in result.stdout
