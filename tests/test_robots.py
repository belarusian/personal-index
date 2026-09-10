"""Tests for robots.txt parser."""

from personal_index.crawler.robots import RobotsParser, parse_robots_txt


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

    def test_robots_parser_parse_populates_policies(self):
        """ARCH-23: parse() must store policy in _policies keyed by domain."""
        parser = RobotsParser()
        parser.parse("User-agent: *\nDisallow: /private\n", "https://example.com")
        # Per-domain branch is exercised: domain present in policy store
        assert "example.com" in parser._policies
        # can_fetch returns False for disallowed path via per-domain branch
        assert parser.can_fetch("https://example.com/private/x") is False
        # And True for allowed path
        assert parser.can_fetch("https://example.com/public/x") is True

    def test_empty_disallow_does_not_disallow_all(self):
        """ARCH-23: bare Disallow: (empty value) must not disallow the site."""
        policy = parse_robots_txt("User-agent: *\nDisallow:\n", "https://example.com")
        assert policy.can_fetch("https://example.com/anything") is True
        # Normal Disallow still works
        policy2 = parse_robots_txt("User-agent: *\nDisallow: /private\n", "https://example.com")
        assert policy2.can_fetch("https://example.com/private/x") is False
        assert policy2.can_fetch("https://example.com/public/x") is True
