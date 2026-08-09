"""Tests for REST API pagination helpers."""

from __future__ import annotations

import pytest
from personal_index.content_api_rest import PaginatedResponse


class TestPaginationHelpers:
    def test_first_page(self):
        resp = PaginatedResponse(items=[1, 2], total=5, page=1, page_size=2)
        assert resp.page == 1
        assert resp.total_pages == 3

    def test_last_page(self):
        resp = PaginatedResponse(items=[5], total=5, page=3, page_size=2)
        assert resp.page == 3
        assert resp.total_pages == 3

    def test_middle_page(self):
        resp = PaginatedResponse(items=[3, 4], total=5, page=2, page_size=2)
        assert resp.page == 2

    def test_single_page(self):
        resp = PaginatedResponse(items=[1], total=1, page=1, page_size=10)
        assert resp.total_pages == 1

    def test_has_next_page(self):
        resp = PaginatedResponse(items=[1, 2], total=5, page=1, page_size=2)
        assert resp.page < resp.total_pages

    def test_no_next_page(self):
        resp = PaginatedResponse(items=[5], total=5, page=3, page_size=2)
        assert resp.page >= resp.total_pages
