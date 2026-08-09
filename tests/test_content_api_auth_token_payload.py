"""Tests for token payload."""

from __future__ import annotations

import time
import pytest
from personal_index.content_api_auth import TokenPayload


class TestTokenPayload:
    def test_default_values(self):
        p = TokenPayload(user_id="user1")
        assert p.permissions == []
        assert p.expires_in == 3600

    def test_custom_values(self):
        p = TokenPayload(user_id="user1", permissions=["read"], expires_in=1800)
        assert p.expires_in == 1800

    def test_serialization(self):
        p = TokenPayload(user_id="user1", permissions=["read"])
        d = p.to_dict()
        assert d["user_id"] == "user1"
        assert d["permissions"] == ["read"]
        assert "created_at" in d

    def test_timestamp_set(self):
        before = time.time()
        p = TokenPayload(user_id="user1")
        after = time.time()
        assert before <= p.created_at <= after
