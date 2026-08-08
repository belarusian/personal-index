"""Tests for core data models."""

import pytest
from datetime import datetime, timezone
from personal_index.models import URL, Page, PageStatus


class TestURL:
    def test_create_url(self):
        url = URL(url="https://example.com/page")
        assert url.url == "https://example.com/page"
        assert url.depth == 0
        assert url.status == PageStatus.PENDING

    def test_extract_domain(self):
        url = URL(url="https://www.example.com/path/to/page")
        assert url.domain == "www.example.com"

    def test_extract_domain_with_port(self):
        url = URL(url="https://example.com:8080/page")
        assert url.domain == "example.com"

    def test_url_id_is_deterministic(self):
        url1 = URL(url="https://example.com")
        url2 = URL(url="https://example.com")
        assert url1.id == url2.id

    def test_url_id_is_unique(self):
        url1 = URL(url="https://example.com/page1")
        url2 = URL(url="https://example.com/page2")
        assert url1.id != url2.id

    def test_to_dict(self):
        url = URL(url="https://example.com")
        data = url.to_dict()
        assert data["url"] == "https://example.com"
        assert data["status"] == "pending"

    def test_from_dict(self):
        data = {
            "url": "https://example.com",
            "depth": 2,
            "status": "crawled",
            "domain": "example.com",
            "parent_url": "https://example.com/",
            "crawled_at": "2024-01-01T00:00:00",
            "error": None,
        }
        url = URL.from_dict(data)
        assert url.url == "https://example.com"
        assert url.depth == 2
        assert url.status == PageStatus.CRAWLED


class TestPage:
    def test_create_page(self):
        page = Page(url="https://example.com")
        assert page.url == "https://example.com"
        assert page.title == ""
        assert page.content == ""
        assert page.links == []

    def test_page_with_content(self):
        page = Page(
            url="https://example.com",
            title="Example",
            content="Hello world",
            links=["https://example.com/other"],
        )
        assert page.title == "Example"
        assert page.content == "Hello world"
        assert len(page.links) == 1

    def test_page_id(self):
        page = Page(url="https://example.com")
        assert len(page.id) == 16

    def test_to_dict(self):
        page = Page(url="https://example.com", title="Test")
        data = page.to_dict()
        assert data["title"] == "Test"
        assert data["relevance_score"] == 0.0

    def test_from_dict(self):
        data = {
            "url": "https://example.com",
            "title": "Test",
            "content": "Hello",
            "links": [],
            "crawled_at": "2024-01-01T00:00:00",
            "status_code": 200,
            "content_type": "text/html",
            "content_length": 100,
            "matched_interests": ["AI"],
            "relevance_score": 0.8,
        }
        page = Page.from_dict(data)
        assert page.title == "Test"
        assert page.relevance_score == 0.8
        assert "AI" in page.matched_interests


class TestPageStatus:
    def test_all_statuses_exist(self):
        assert PageStatus.PENDING.value == "pending"
        assert PageStatus.CRAWLED.value == "crawled"
        assert PageStatus.FAILED.value == "failed"
        assert PageStatus.SKIPPED.value == "skipped"
        assert PageStatus.BLOCKED.value == "blocked"
