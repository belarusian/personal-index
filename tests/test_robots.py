"""Tests for robots.txt parser."""

from personal_index.crawler.robots import RobotsParser


class TestRobotsParser:
    def test_parse_basic_allow(self):
        parser = RobotsParser()
        parser.parse("User-agent: *\nAllow: /")
        assert parser.can_fetch("https://example.com/page") is True

    def test_parse_disallow(self):
        parser = RobotsParser()
        parser.parse("User-agent: *\nDisallow: /private/")
        assert parser.can_fetch("https://example.com/private/secret") is False
        assert parser.can_fetch("https://example.com/public/page") is True

    def test_parse_specific_agent(self):
        parser = RobotsParser()
        parser.parse(
            "User-agent: GoodBot\nAllow: /\n"
            "User-agent: *\nDisallow: /"
        )
        assert parser.can_fetch("https://example.com/page", "GoodBot") is True
        assert parser.can_fetch("https://example.com/page", "BadBot") is False

    def test_parse_wildcard_pattern(self):
        parser = RobotsParser()
        parser.parse("User-agent: *\nDisallow: /api/*")
        assert parser.can_fetch("https://example.com/api/v1") is False
        assert parser.can_fetch("https://example.com/blog/post") is True

    def test_parse_anchor_pattern(self):
        parser = RobotsParser()
        parser.parse("User-agent: *\nDisallow: /tmp$")
        assert parser.can_fetch("https://example.com/tmp") is False
        assert parser.can_fetch("https://example.com/tmp/file") is True

    def test_empty_parser_allows_all(self):
        parser = RobotsParser()
        assert parser.can_fetch("https://example.com/anything") is True

    def test_parse_comments_ignored(self):
        parser = RobotsParser()
        parser.parse("# This is a comment\nUser-agent: *\nDisallow: /admin/")
        assert parser.can_fetch("https://example.com/admin") is False

    def test_parse_blank_lines_ignored(self):
        parser = RobotsParser()
        parser.parse("User-agent: *\n\nDisallow: /secret\n\n")
        assert parser.can_fetch("https://example.com/secret") is False

    def test_most_specific_rule_wins(self):
        parser = RobotsParser()
        parser.parse(
            "User-agent: *\n"
            "Disallow: /private/\n"
            "Allow: /private/public/"
        )
        assert parser.can_fetch("https://example.com/private/hidden") is False
        assert parser.can_fetch("https://example.com/private/public/page") is True

    def test_parse_no_rules(self):
        parser = RobotsParser()
        parser.parse("")
        assert parser.can_fetch("https://example.com/page") is True

    def test_parse_only_comments(self):
        parser = RobotsParser()
        parser.parse("# Just a comment\n# Another comment")
        assert parser.can_fetch("https://example.com/page") is True
