"""Tests for personal_index.robots."""

import pytest
from unittest.mock import patch, MagicMock

from personal_index.robots import RobotsParser, RobotsRule


class TestRobotsRule:
    def test_exact_match(self):
        rule = RobotsRule(user_agent="*", allowed=False, path_pattern="/admin")
        assert rule.matches_path("/admin") is True
        assert rule.matches_path("/admin/") is False
        assert rule.matches_path("/other") is False

    def test_wildcard_match(self):
        rule = RobotsRule(user_agent="*", allowed=False, path_pattern="/private/*")
        assert rule.matches_path("/private/page") is True
        assert rule.matches_path("/private/deep/page") is True
        assert rule.matches_path("/public/page") is False

    def test_empty_path(self):
        rule = RobotsRule(user_agent="*", allowed=True, path_pattern="")
        assert rule.matches_path("/anything") is False

    def test_star_pattern(self):
        rule = RobotsRule(user_agent="*", allowed=True, path_pattern="*")
        assert rule.matches_path("/anything") is True
        assert rule.matches_path("/") is True


class TestRobotsParser:
    def test_parse_basic_disallow(self):
        parser = RobotsParser()
        rules = parser.parse("""
User-agent: *
Disallow: /admin
Disallow: /private
""")
        assert len(rules) == 2
        assert not rules[0].allowed
        assert rules[0].path_pattern == "/admin"

    def test_parse_allow(self):
        parser = RobotsParser()
        rules = parser.parse("""
User-agent: *
Allow: /public
Disallow: /private
""")
        assert len(rules) == 2
        assert rules[0].allowed is True
        assert rules[0].path_pattern == "/public"

    def test_parse_empty_disallow(self):
        """Empty Disallow means everything is allowed."""
        parser = RobotsParser()
        rules = parser.parse("""
User-agent: *
Disallow:
""")
        assert len(rules) == 1
        assert rules[0].allowed is True
        assert rules[0].path_pattern == "*"

    def test_parse_multiple_user_agents(self):
        parser = RobotsParser()
        rules = parser.parse("""
User-agent: *
Disallow: /private

User-agent: Googlebot
Allow: /public
Disallow: /admin
""")
        assert len(rules) == 3
        assert rules[0].user_agent == "*"
        assert rules[2].user_agent == "Googlebot"

    def test_parse_comments_ignored(self):
        parser = RobotsParser()
        rules = parser.parse("""
# This is a comment
User-agent: *
# Another comment
Disallow: /admin
""")
        assert len(rules) == 1

    def test_parse_empty_content(self):
        parser = RobotsParser()
        rules = parser.parse("")
        assert len(rules) == 0

    def test_parse_whitespace_only(self):
        parser = RobotsParser()
        rules = parser.parse("   \n   \n   ")
        assert len(rules) == 0

    @patch("requests.Session.get")
    def test_fetch_robots_txt_success(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = "User-agent: *\nDisallow: /admin"
        mock_get.return_value = mock_response

        parser = RobotsParser()
        content = parser.fetch_robots_txt("https://example.com/page")
        assert content == "User-agent: *\nDisallow: /admin"

    @patch("requests.Session.get")
    def test_fetch_robots_txt_not_found(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_get.return_value = mock_response

        parser = RobotsParser()
        content = parser.fetch_robots_txt("https://example.com/page")
        assert content is None

    @patch("requests.Session.get")
    def test_fetch_robots_txt_error(self, mock_get):
        mock_get.side_effect = Exception("Network error")

        parser = RobotsParser()
        content = parser.fetch_robots_txt("https://example.com/page")
        assert content is None

    def test_is_allowed_no_robots_txt(self):
        """Without robots.txt, everything should be allowed."""
        parser = RobotsParser()
        parser._cache["example.com"] = []
        assert parser.is_allowed("https://example.com/anything") is True

    def test_is_allowed_with_disallow(self):
        parser = RobotsParser()
        parser._cache["example.com"] = [
            RobotsRule(user_agent="*", allowed=False, path_pattern="/admin"),
        ]
        assert parser.is_allowed("https://example.com/admin") is False
        assert parser.is_allowed("https://example.com/public") is True

    def test_is_allowed_with_allow(self):
        parser = RobotsParser()
        parser._cache["example.com"] = [
            RobotsRule(user_agent="*", allowed=True, path_pattern="/public"),
            RobotsRule(user_agent="*", allowed=False, path_pattern="/*"),
        ]
        assert parser.is_allowed("https://example.com/public") is True
        assert parser.is_allowed("https://example.com/private") is False

    def test_is_allowed_most_specific_match(self):
        """Most specific (longest) matching rule wins."""
        parser = RobotsParser()
        parser._cache["example.com"] = [
            RobotsRule(user_agent="*", allowed=False, path_pattern="/*"),
            RobotsRule(user_agent="*", allowed=True, path_pattern="/public/*"),
        ]
        assert parser.is_allowed("https://example.com/public/page") is True
        assert parser.is_allowed("https://example.com/private/page") is False

    def test_clear_cache(self):
        parser = RobotsParser()
        parser._cache["example.com"] = []
        parser.clear_cache()
        assert len(parser._cache) == 0
