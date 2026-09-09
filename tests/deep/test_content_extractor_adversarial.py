"""Adversarial deep tests for personal_index.content_extractor.

Contract source: module docstrings + ExtractedContent dataclass.
Probes extract() guards, title precedence, meta handling, headings/links/images,
text normalization/truncation, word_count, readability scoring, and idempotence.
"""

from __future__ import annotations

import os


from personal_index.content_extractor import ContentExtractor, ExtractedContent


def make_extractor(max_len=100000):
    return ContentExtractor(max_text_length=max_len)


def test_extract_empty_html_returns_defaults():
    ex = make_extractor()
    out = ex.extract("")
    assert isinstance(out, ExtractedContent)
    assert out.title == ""
    assert out.text == ""
    assert out.word_count == 0


def test_extract_none_returns_defaults():
    ex = make_extractor()
    out = ex.extract(None)  # type: ignore[arg-type]
    assert out.title == ""
    assert out.text == ""


def test_extract_whitespace_only():
    ex = make_extractor()
    out = ex.extract("   \n\t  ")
    assert out.title == ""
    assert out.text == ""


def test_extract_title_og_preferred():
    html = '<html><head><meta property="og:title" content="OG Title"><title>HTML Title</title></head></html>'
    out = make_extractor().extract(html)
    assert out.title == "OG Title"


def test_extract_title_fallback():
    html = '<html><head><title>HTML Title</title></head></html>'
    out = make_extractor().extract(html)
    assert out.title == "HTML Title"


def test_extract_title_missing():
    html = '<html><head></head></html>'
    out = make_extractor().extract(html)
    assert out.title == ""


def test_extract_meta_description():
    html = '<meta name="description" content="  Desc  ">'
    out = make_extractor().extract(html)
    assert out.meta_description == "Desc"


def test_extract_meta_keywords_split():
    html = '<meta name="keywords" content="a, b , ,c, ">'
    out = make_extractor().extract(html)
    assert out.meta_keywords == ["a", "b", "c"]


def test_extract_meta_keywords_missing():
    html = '<html></html>'
    out = make_extractor().extract(html)
    assert out.meta_keywords == []


def test_extract_author():
    html = '<meta name="author" content="Alice">'
    out = make_extractor().extract(html)
    assert out.author == "Alice"


def test_extract_canonical():
    html = '<link rel="canonical" href="https://example.com/page">'
    out = make_extractor().extract(html)
    assert out.canonical_url == "https://example.com/page"


def test_extract_language():
    html = '<html lang="en-US"><head></head></html>'
    out = make_extractor().extract(html)
    assert out.language == "en-US"


def test_extract_headings_nonempty():
    html = '<h1>Title</h1><h2></h2><h3>Sub</h3>'
    out = make_extractor().extract(html)
    assert out.headings == ["Title", "Sub"]


def test_extract_links_text_href():
    html = '<a href="https://a.com">Link</a><a href="">Empty</a><a>No href</a>'
    out = make_extractor().extract(html)
    assert out.links == [("Link", "https://a.com")]


def test_extract_images_alt_src():
    html = '<img src="i.png" alt="Alt"><img src=""><img alt="No src">'
    out = make_extractor().extract(html)
    assert out.images == [("Alt", "i.png")]


def test_extract_text_normalizes_whitespace():
    html = '<p>  Hello   world \n\n  </p>'
    out = make_extractor().extract(html)
    assert out.text == "Hello world"


def test_extract_text_truncates_to_max():
    long_text = "a " * 10000
    html = f"<p>{long_text}</p>"
    ex = make_extractor(max_len=100)
    out = ex.extract(html)
    assert len(out.text) <= 100


def test_extract_word_count_matches_text():
    html = "<p>one two three</p>"
    out = make_extractor().extract(html)
    assert out.word_count == 3
    assert out.text.split() == ["one", "two", "three"]


def test_extract_script_style_removed_from_text():
    html = "<script>var x=1</script><style>body{}</style><p>Visible</p>"
    out = make_extractor().extract(html)
    assert "var x=1" not in out.text
    assert "body" not in out.text
    assert out.text == "Visible"


def test_extract_title_not_in_body_text():
    html = "<title>Page Title</title><p>Body</p>"
    out = make_extractor().extract(html)
    assert out.title == "Page Title"
    assert "Page Title" not in out.text
    assert out.text == "Body"


def test_extract_readability_score_empty():
    ex = make_extractor()
    content = ExtractedContent(text="", word_count=0)
    assert ex.extract_readability_score(content) == 0.0


def test_extract_readability_score_short_text():
    ex = make_extractor()
    content = ExtractedContent(text="a " * 49, word_count=49)
    assert ex.extract_readability_score(content) == 0.0


def test_extract_readability_score_components():
    ex = make_extractor()
    # 600 words -> length score 0.4, 4 headings -> 0.4, meta present -> 0.3 => capped at 1.0
    text = "word " * 600
    content = ExtractedContent(text=text, headings=["h1","h2","h3","h4"], meta_description="desc")
    score = ex.extract_readability_score(content)
    assert 0.0 < score <= 1.0


def test_extract_readability_score_no_meta():
    ex = make_extractor()
    text = "word " * 600
    content = ExtractedContent(text=text, headings=[], meta_description="")
    score = ex.extract_readability_score(content)
    # length 0.4, headings 0, meta 0 => 0.4
    assert abs(score - 0.4) < 1e-9


def test_extract_idempotent():
    html = "<title>T</title><p>Body</p>"
    ex = make_extractor()
    out1 = ex.extract(html)
    out2 = ex.extract(html)
    assert out1.title == out2.title
    assert out1.text == out2.text
    assert out1.headings == out2.headings


def test_extract_unicode_no_crash():
    html = "<html><head><title>Привет</title></head><body>Текст с юникодом</body></html>"
    out = make_extractor().extract(html)
    assert out.title == "Привет"
    assert "Текст" in out.text


def test_extract_duplicate_headings_preserved():
    html = "<h1>A</h1><h1>A</h1>"
    out = make_extractor().extract(html)
    assert out.headings == ["A", "A"]


def test_extract_links_duplicate():
    html = '<a href="/a">X</a><a href="/a">X</a>'
    out = make_extractor().extract(html)
    assert out.links == [("X", "/a"), ("X", "/a")]


def test_cli_end_to_end_version(tmp_path):
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


def test_cli_end_to_end_init(tmp_path):
    import subprocess
    import sys
    data_dir = tmp_path / "data"
    config = tmp_path / "config.yaml"
    result = subprocess.run(
        [sys.executable, "-m", "personal_index.cli", "init", "--data-dir", str(data_dir), "--config", str(config)],
        capture_output=True,
        text=True,
        cwd=os.getcwd(),
    )
    assert result.returncode == 0
    assert data_dir.exists()
    assert config.exists()
