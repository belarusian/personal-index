"""Tests for TICKET-98, TICKET-99, TICKET-100 fixes."""

from __future__ import annotations

import ast
import inspect
import textwrap

# ---------------------------------------------------------------------------
# TICKET-98: Fix duplicate set item in content_enricher.py (B033)
# ---------------------------------------------------------------------------

def test_negative_words_no_duplicates():
    """NEGATIVE_WORDS set must not contain duplicate entries."""
    from personal_index.content_enricher import ContentEnricher

    source = inspect.getsource(ContentEnricher)
    tree = ast.parse(textwrap.dedent(source))
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == "ContentEnricher":
            for item in node.body:
                if isinstance(item, ast.Assign):
                    for target in item.targets:
                        if isinstance(target, ast.Name) and target.id == "NEGATIVE_WORDS":
                            strings = []
                            for elt in item.value.elts:
                                if isinstance(elt, ast.Constant) and isinstance(elt.value, str):
                                    strings.append(elt.value)
                            assert len(strings) == len(set(strings)), (
                                f"Duplicate entries in NEGATIVE_WORDS: "
                                f"{[s for s in strings if strings.count(s) > 1]}"
                            )
                            return
    assert False, "Could not find NEGATIVE_WORDS in source"


def test_negative_words_wrong_appears_once():
    """The word 'wrong' should appear exactly once in NEGATIVE_WORDS."""
    from personal_index.content_enricher import ContentEnricher
    source = inspect.getsource(ContentEnricher)
    tree = ast.parse(textwrap.dedent(source))
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == "ContentEnricher":
            for item in node.body:
                if isinstance(item, ast.Assign):
                    for target in item.targets:
                        if isinstance(target, ast.Name) and target.id == "NEGATIVE_WORDS":
                            strings = [
                                elt.value for elt in item.value.elts
                                if isinstance(elt, ast.Constant) and isinstance(elt.value, str)
                            ]
                            assert strings.count("wrong") == 1, (
                                f"'wrong' appears {strings.count('wrong')} times, expected 1"
                            )
                            return


# ---------------------------------------------------------------------------
# TICKET-99: Fix unused unpacked variable in content_type.py (RUF059)
# ---------------------------------------------------------------------------

def test_detect_from_url_no_unused_encoding():
    """detect_from_url should not unpack an unused 'encoding' variable."""
    from personal_index.content_type import ContentTypeDetector
    source = inspect.getsource(ContentTypeDetector.detect_from_url)
    tree = ast.parse(textwrap.dedent(source))
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Tuple):
                    names = [
                        t.id for t in target.elts if isinstance(t, ast.Name)
                    ]
                    if "encoding" in names:
                        assert False, (
                            f"Unused variable 'encoding' unpacked in detect_from_url: {names}"
                        )


def test_detect_from_filename_no_unused_encoding():
    """detect_from_filename should not unpack an unused 'encoding' variable."""
    from personal_index.content_type import ContentTypeDetector
    source = inspect.getsource(ContentTypeDetector.detect_from_filename)
    tree = ast.parse(textwrap.dedent(source))
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Tuple):
                    names = [
                        t.id for t in target.elts if isinstance(t, ast.Name)
                    ]
                    if "encoding" in names:
                        assert False, (
                            f"Unused variable 'encoding' unpacked in detect_from_filename: {names}"
                        )


# ---------------------------------------------------------------------------
# TICKET-100: Fix misleading lstrip with multi-character string in url_dedup.py (B005)
# ---------------------------------------------------------------------------

def test_get_domain_urls_uses_removeprefix_not_lstrip():
    """get_domain_urls should use removeprefix, not lstrip, for 'www.' removal."""
    from personal_index.url_dedup import URLDeduplicator
    source = inspect.getsource(URLDeduplicator.get_domain_urls)
    assert "lstrip" not in source, (
        "get_domain_urls still uses lstrip for 'www.' removal"
    )
    assert "removeprefix" in source, (
        "get_domain_urls should use removeprefix for 'www.' removal"
    )


def test_get_domain_urls_www_prefix_preserved():
    """Domains starting with 'www' should not be mangled by lstrip."""
    from personal_index.url_dedup import URLDeduplicator

    dedup = URLDeduplicator()
    dedup.add_url("https://www.example.com/page1")

    results = dedup.get_domain_urls("www.example.com")
    assert len(results) == 1, (
        f"Expected 1 URL for 'www.example.com', got {len(results)}: {results}"
    )

    results = dedup.get_domain_urls("example.com")
    assert len(results) == 1, (
        f"Expected 1 URL for 'example.com', got {len(results)}: {results}"
    )


def test_get_domain_urls_does_not_mangle_w_prefix():
    """lstrip('www.') would mangle 'ww.example.com' to 'example.com'.
    removeprefix('www.') correctly leaves it unchanged."""
    from personal_index.url_dedup import URLDeduplicator

    dedup = URLDeduplicator()
    dedup.add_url("https://ww.example.com/page1")

    results = dedup.get_domain_urls("ww.example.com")
    assert len(results) == 1, (
        f"Expected 1 URL for 'ww.example.com', got {len(results)}: {results}"
    )

    results = dedup.get_domain_urls("example.com")
    assert len(results) == 0, (
        f"Expected 0 URLs for 'example.com', got {len(results)}: {results}"
    )
