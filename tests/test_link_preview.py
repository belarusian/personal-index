"""Tests for the link_preview module."""

from __future__ import annotations

from personal_index.link_preview import LinkPreview, LinkPreviewGenerator


class TestLinkPreviewDataclass:
    def test_default_values(self):
        preview = LinkPreview()
        assert preview.title == ""
        assert preview.description == ""
        assert preview.image_url == ""
        assert preview.site_name == ""
        assert preview.type == ""
        assert preview.url == ""
        assert preview.twitter_card == ""
        assert preview.locale == ""

    def test_custom_values(self):
        preview = LinkPreview(
            title="My Site",
            description="A great site",
            image_url="http://example.com/img.png",
            site_name="Example",
            type="website",
            url="http://example.com",
            twitter_card="summary_large_image",
            locale="en_US",
        )
        assert preview.title == "My Site"
        assert preview.description == "A great site"
        assert preview.image_url == "http://example.com/img.png"
        assert preview.site_name == "Example"
        assert preview.type == "website"
        assert preview.url == "http://example.com"
        assert preview.twitter_card == "summary_large_image"
        assert preview.locale == "en_US"


class TestLinkPreviewGenerator:
    def _make_html(self, head_extra: str = "", body_extra: str = "") -> str:
        return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <title>Default Title</title>
    <meta name="description" content="Default description">
    {head_extra}
</head>
<body>
    <p>Some content</p>
    {body_extra}
</body>
</html>"""

    def test_full_og_tags(self):
        html = self._make_html("""
            <meta property="og:title" content="OG Title">
            <meta property="og:description" content="OG Description">
            <meta property="og:image" content="http://example.com/og.png">
            <meta property="og:url" content="http://example.com/page">
            <meta property="og:type" content="article">
            <meta property="og:site_name" content="Example Site">
            <meta property="og:locale" content="en_US">
        """)
        generator = LinkPreviewGenerator()
        preview = generator.generate(html, "http://example.com")
        assert preview.title == "OG Title"
        assert preview.description == "OG Description"
        assert preview.image_url == "http://example.com/og.png"
        assert preview.url == "http://example.com/page"
        assert preview.type == "article"
        assert preview.site_name == "Example Site"
        assert preview.locale == "en_US"

    def test_partial_og_tags(self):
        html = self._make_html("""
            <meta property="og:title" content="Only Title">
        """)
        generator = LinkPreviewGenerator()
        preview = generator.generate(html, "http://example.com")
        assert preview.title == "Only Title"
        assert preview.description == "Default description"
        assert preview.image_url == ""

    def test_twitter_card_tags(self):
        html = self._make_html("""
            <meta name="twitter:card" content="summary_large_image">
            <meta name="twitter:title" content="Twitter Title">
            <meta name="twitter:description" content="Twitter Desc">
            <meta name="twitter:image" content="http://example.com/tw.png">
        """)
        generator = LinkPreviewGenerator()
        preview = generator.generate(html, "http://example.com")
        assert preview.twitter_card == "summary_large_image"
        assert preview.title == "Twitter Title"
        assert preview.description == "Twitter Desc"
        assert preview.image_url == "http://example.com/tw.png"

    def test_og_takes_priority_over_twitter(self):
        html = self._make_html("""
            <meta property="og:title" content="OG Title">
            <meta property="og:description" content="OG Desc">
            <meta property="og:image" content="http://example.com/og.png">
            <meta name="twitter:card" content="summary">
            <meta name="twitter:title" content="Twitter Title">
            <meta name="twitter:description" content="Twitter Desc">
            <meta name="twitter:image" content="http://example.com/tw.png">
        """)
        generator = LinkPreviewGenerator()
        preview = generator.generate(html, "http://example.com")
        assert preview.title == "OG Title"
        assert preview.description == "OG Desc"
        assert preview.image_url == "http://example.com/og.png"
        assert preview.twitter_card == "summary"

    def test_fallback_to_standard_meta(self):
        html = self._make_html("")
        generator = LinkPreviewGenerator()
        preview = generator.generate(html, "http://example.com")
        assert preview.title == "Default Title"
        assert preview.description == "Default description"

    def test_fallback_to_title_tag(self):
        html = """<!DOCTYPE html>
        <html><head><title>Just a Title</title></head><body><p>Content</p></body></html>"""
        generator = LinkPreviewGenerator()
        preview = generator.generate(html, "http://example.com")
        assert preview.title == "Just a Title"
        assert preview.description == ""

    def test_empty_html(self):
        generator = LinkPreviewGenerator()
        preview = generator.generate("", "http://example.com")
        assert preview.title == ""
        assert preview.description == ""
        assert preview.image_url == ""

    def test_relative_image_url_resolved(self):
        html = self._make_html("""
            <meta property="og:image" content="/images/logo.png">
        """)
        generator = LinkPreviewGenerator()
        preview = generator.generate(html, "http://example.com")
        assert preview.image_url == "http://example.com/images/logo.png"

    def test_twitter_card_type_extraction(self):
        html = self._make_html("""
            <meta name="twitter:card" content="summary">
        """)
        generator = LinkPreviewGenerator()
        preview = generator.generate(html, "http://example.com")
        assert preview.twitter_card == "summary"

    def test_og_locale_extraction(self):
        html = self._make_html("""
            <meta property="og:locale" content="fr_FR">
        """)
        generator = LinkPreviewGenerator()
        preview = generator.generate(html, "http://example.com")
        assert preview.locale == "fr_FR"

    def test_og_site_name_extraction(self):
        html = self._make_html("""
            <meta property="og:site_name" content="My Awesome Site">
        """)
        generator = LinkPreviewGenerator()
        preview = generator.generate(html, "http://example.com")
        assert preview.site_name == "My Awesome Site"

    def test_og_type_extraction(self):
        html = self._make_html("""
            <meta property="og:type" content="profile">
        """)
        generator = LinkPreviewGenerator()
        preview = generator.generate(html, "http://example.com")
        assert preview.type == "profile"

    def test_og_title_priority_over_title_tag(self):
        html = """<!DOCTYPE html>
        <html><head>
            <title>HTML Title</title>
            <meta property="og:title" content="OG Title">
        </head><body><p>Content</p></body></html>"""
        generator = LinkPreviewGenerator()
        preview = generator.generate(html, "http://example.com")
        assert preview.title == "OG Title"

    def test_og_description_priority_over_meta_description(self):
        html = """<!DOCTYPE html>
        <html><head>
            <meta name="description" content="Standard Desc">
            <meta property="og:description" content="OG Desc">
        </head><body><p>Content</p></body></html>"""
        generator = LinkPreviewGenerator()
        preview = generator.generate(html, "http://example.com")
        assert preview.description == "OG Desc"

    def test_no_base_url(self):
        html = self._make_html("""
            <meta property="og:title" content="Test">
            <meta property="og:image" content="/img.png">
        """)
        generator = LinkPreviewGenerator()
        preview = generator.generate(html, "")
        assert preview.title == "Test"
        assert preview.image_url == "/img.png"

    def test_whitespace_stripped(self):
        html = self._make_html("""
            <meta property="og:title" content="  Spaced Title  ">
            <meta property="og:description" content="  Spaced Desc  ">
        """)
        generator = LinkPreviewGenerator()
        preview = generator.generate(html, "http://example.com")
        assert preview.title == "Spaced Title"
        assert preview.description == "Spaced Desc"
