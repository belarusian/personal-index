"""Tests for URL classification."""

from personal_index.url_classifier import ClassificationResult, URLCategory, URLClassifier


class TestClassificationResult:
    def test_creation(self):
        r = ClassificationResult(url="http://example.com", category=URLCategory.PAGE)
        assert r.url == "http://example.com"
        assert r.category == URLCategory.PAGE
        assert r.confidence == 0.5


class TestURLClassifier:
    def test_classify_page(self):
        c = URLClassifier()
        result = c.classify("http://example.com/about")
        assert result.category == URLCategory.PAGE

    def test_classify_api(self):
        c = URLClassifier()
        result = c.classify("http://example.com/api/users")
        assert result.category == URLCategory.API

    def test_classify_api_json(self):
        c = URLClassifier()
        result = c.classify("http://example.com/data.json")
        assert result.category == URLCategory.API

    def test_classify_media_image(self):
        c = URLClassifier()
        result = c.classify("http://example.com/photo.jpg")
        assert result.category == URLCategory.MEDIA

    def test_classify_media_video(self):
        c = URLClassifier()
        result = c.classify("http://example.com/video.mp4")
        assert result.category == URLCategory.MEDIA

    def test_classify_document(self):
        c = URLClassifier()
        result = c.classify("http://example.com/report.pdf")
        assert result.category == URLCategory.DOCUMENT

    def test_classify_feed(self):
        c = URLClassifier()
        result = c.classify("http://example.com/feed.rss")
        assert result.category == URLCategory.FEED

    def test_classify_static(self):
        c = URLClassifier()
        result = c.classify("http://example.com/style.css")
        assert result.category == URLCategory.STATIC

    def test_classify_redirect(self):
        c = URLClassifier()
        result = c.classify("http://example.com/redirect?url=http://other.com")
        assert result.category == URLCategory.REDIRECT

    def test_classify_batch(self):
        c = URLClassifier()
        results = c.classify_batch([
            "http://example.com/page",
            "http://example.com/api/data",
            "http://example.com/img.png",
        ])
        assert len(results) == 3
        assert results[0].category == URLCategory.PAGE
        assert results[1].category == URLCategory.API
        assert results[2].category == URLCategory.MEDIA

    def test_get_category_counts(self):
        c = URLClassifier()
        urls = [
            "http://example.com/page1",
            "http://example.com/page2",
            "http://example.com/api/data",
            "http://example.com/img.png",
        ]
        counts = c.get_category_counts(urls)
        assert counts["page"] == 2
        assert counts["api"] == 1
        assert counts["media"] == 1

    def test_confidence_values(self):
        c = URLClassifier()
        api_result = c.classify("http://example.com/api/v1/users")
        assert api_result.confidence >= 0.8

    def test_reasons_present(self):
        c = URLClassifier()
        result = c.classify("http://example.com/page")
        assert len(result.reasons) > 0


def test_url_classifier_module_docstring_and_imports():
    """Verify module has proper docstring before imports (E402 fix)."""
    import personal_index.url_classifier as mod
    assert mod.__doc__ == "URL classification for categorizing crawled URLs."
    # Verify the module imports correctly without E402 issues
    assert hasattr(mod, "URLClassifier")
    assert hasattr(mod, "URLCategory")


class TestClassifyDataDriven:
    """Tests verifying the data-driven classify refactor."""

    def test_classify_iterates_all_rules(self):
        """classify() should try all rules in order and return first match."""
        c = URLClassifier()
        # Redirect rule is first — should match before others
        result = c.classify("http://example.com/redirect?url=http://other.com")
        assert result.category == URLCategory.REDIRECT

        # Feed rule is second
        result = c.classify("http://example.com/feed.rss")
        assert result.category == URLCategory.FEED

        # API rule is third
        result = c.classify("http://example.com/api/users")
        assert result.category == URLCategory.API

        # Static rule is fourth
        result = c.classify("http://example.com/style.css")
        assert result.category == URLCategory.STATIC

        # Media rule is fifth
        result = c.classify("http://example.com/photo.jpg")
        assert result.category == URLCategory.MEDIA

        # Document rule is sixth
        result = c.classify("http://example.com/report.pdf")
        assert result.category == URLCategory.DOCUMENT

    def test_classify_default_page(self):
        """classify() returns PAGE with 0.5 confidence when no rule matches."""
        c = URLClassifier()
        result = c.classify("http://example.com/about")
        assert result.category == URLCategory.PAGE
        assert result.confidence == 0.5
        assert "no specific pattern matched" in result.reasons

class TestURLClassifierClassifyPinning:
    """Pinning tests for URLClassifier.classify exact contract."""

    def test_classify_returns_classification_result_never_none(self):
        c = URLClassifier()
        result = c.classify("http://example.com")
        assert isinstance(result, ClassificationResult)
        assert result is not None

    def test_classify_preserves_url_as_is(self):
        c = URLClassifier()
        url = "HTTP://Example.COM/Path/To/Page"
        result = c.classify(url)
        assert result.url == url

    def test_classify_confidence_values_per_category(self):
        c = URLClassifier()
        # REDIRECT confidence 0.8
        r = c.classify("http://example.com/redirect?url=x")
        assert r.category == URLCategory.REDIRECT
        assert r.confidence == 0.8
        # FEED confidence 0.9
        r = c.classify("http://example.com/feed.rss")
        assert r.category == URLCategory.FEED
        assert r.confidence == 0.9
        # API confidence 0.85
        r = c.classify("http://example.com/api/")
        assert r.category == URLCategory.API
        assert r.confidence == 0.85
        # STATIC confidence 0.9
        r = c.classify("http://example.com/style.css")
        assert r.category == URLCategory.STATIC
        assert r.confidence == 0.9
        # MEDIA confidence 0.85
        r = c.classify("http://example.com/photo.jpg")
        assert r.category == URLCategory.MEDIA
        assert r.confidence == 0.85
        # DOCUMENT confidence 0.85
        r = c.classify("http://example.com/doc.pdf")
        assert r.category == URLCategory.DOCUMENT
        assert r.confidence == 0.85
        # PAGE default confidence 0.5
        r = c.classify("http://example.com/page")
        assert r.category == URLCategory.PAGE
        assert r.confidence == 0.5

    def test_classify_default_page_reason(self):
        c = URLClassifier()
        result = c.classify("http://example.com/about")
        assert result.category == URLCategory.PAGE
        assert result.confidence == 0.5
        assert result.reasons == ["no specific pattern matched"]

    def test_classify_reasons_is_single_element_list(self):
        c = URLClassifier()
        result = c.classify("http://example.com/api/")
        assert isinstance(result.reasons, list)
        assert len(result.reasons) == 1
        assert result.reasons[0] == "matches API pattern"

    def test_classify_pattern_order_precedence(self):
        c = URLClassifier()
        # URL matching both redirect and feed patterns should pick redirect (first)
        url = "http://example.com/redirect?url=http://example.com/feed.rss"
        result = c.classify(url)
        assert result.category == URLCategory.REDIRECT
        assert result.confidence == 0.8

    def test_classify_case_insensitive_matching(self):
        c = URLClassifier()
        result = c.classify("HTTP://EXAMPLE.COM/API/USERS")
        assert result.category == URLCategory.API
        assert result.confidence == 0.85
