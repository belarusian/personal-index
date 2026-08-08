"""Tests for URL classification."""

import pytest
from personal_index.url_classifier import URLClassifier, URLCategory, ClassificationResult


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
