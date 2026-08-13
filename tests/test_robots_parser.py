"""Tests for personal_index.robots_parser."""


from personal_index.robots_parser import (
    RobotsPolicy,
    RobotsRule,
    is_allowed,
    parse_robots_txt,
)


class TestRobotsRule:
    """Tests for RobotsRule."""

    def test_create_rule(self):
        rule = RobotsRule(user_agent="*", allowed=False, pattern="/private")
        assert rule.user_agent == "*"
        assert rule.allowed is False
        assert rule.pattern == "/private"


class TestRobotsPolicy:
    """Tests for RobotsPolicy."""

    def test_empty_policy_allows_all(self):
        policy = RobotsPolicy(domain="example.com")
        assert policy.can_fetch("https://example.com/anything") is True

    def test_disallow_all(self):
        policy = RobotsPolicy(
            domain="example.com",
            rules=[RobotsRule(user_agent="*", allowed=False, pattern="*")],
        )
        assert policy.can_fetch("https://example.com/page") is False

    def test_allow_specific(self):
        policy = RobotsPolicy(
            domain="example.com",
            rules=[
                RobotsRule(user_agent="*", allowed=False, pattern="*"),
                RobotsRule(user_agent="*", allowed=True, pattern="/public"),
            ],
        )
        assert policy.can_fetch("https://example.com/public/page") is True
        assert policy.can_fetch("https://example.com/private") is False

    def test_specific_user_agent(self):
        policy = RobotsPolicy(
            domain="example.com",
            rules=[
                RobotsRule(user_agent="*", allowed=False, pattern="/secret"),
                RobotsRule(user_agent="Googlebot", allowed=True, pattern="/secret"),
            ],
        )
        assert policy.can_fetch("https://example.com/secret", "Googlebot") is True
        assert policy.can_fetch("https://example.com/secret", "personal-index") is False

    def test_crawl_delay(self):
        policy = RobotsPolicy(
            domain="example.com",
            rules=[],
            crawl_delay=5.0,
        )
        assert policy.crawl_delay == 5.0

    def test_sitemap_urls(self):
        policy = RobotsPolicy(
            domain="example.com",
            rules=[],
            sitemap_urls=["https://example.com/sitemap.xml"],
        )
        assert "https://example.com/sitemap.xml" in policy.sitemap_urls


class TestParseRobotsTxt:
    """Tests for parse_robots_txt."""

    def test_parse_basic_disallow(self):
        text = """User-agent: *
Disallow: /admin
"""
        policy = parse_robots_txt(text, "https://example.com")
        assert len(policy.rules) == 1
        assert policy.rules[0].allowed is False
        assert policy.rules[0].pattern == "/admin"

    def test_parse_allow(self):
        text = """User-agent: *
Disallow: /
Allow: /public
"""
        policy = parse_robots_txt(text, "https://example.com")
        assert len(policy.rules) == 2

    def test_parse_crawl_delay(self):
        text = """User-agent: *
Crawl-delay: 10
Disallow: /private
"""
        policy = parse_robots_txt(text, "https://example.com")
        assert policy.crawl_delay == 10.0

    def test_parse_sitemap(self):
        text = """User-agent: *
Sitemap: https://example.com/sitemap.xml
Disallow: /admin
"""
        policy = parse_robots_txt(text, "https://example.com")
        assert "https://example.com/sitemap.xml" in policy.sitemap_urls

    def test_parse_comments(self):
        text = """# This is a comment
User-agent: *
# Another comment
Disallow: /admin
"""
        policy = parse_robots_txt(text, "https://example.com")
        assert len(policy.rules) == 1

    def test_parse_empty(self):
        policy = parse_robots_txt("", "https://example.com")
        assert policy.rules == []

    def test_parse_multiple_user_agents(self):
        text = """User-agent: Googlebot
Disallow: /no-google

User-agent: *
Disallow: /private
"""
        policy = parse_robots_txt(text, "https://example.com")
        assert len(policy.rules) == 2

    def test_parse_wildcard_pattern(self):
        text = """User-agent: *
Disallow: /tmp*
"""
        policy = parse_robots_txt(text, "https://example.com")
        assert policy.can_fetch("https://example.com/tmp/file") is False
        assert policy.can_fetch("https://example.com/page") is True

    def test_parse_end_anchor(self):
        text = """User-agent: *
Disallow: /search$
"""
        policy = parse_robots_txt(text, "https://example.com")
        assert policy.can_fetch("https://example.com/search") is False
        assert policy.can_fetch("https://example.com/search/page") is True


class TestIsAllowed:
    """Tests for is_allowed."""

    def test_allowed(self):
        policy = RobotsPolicy(
            domain="example.com",
            rules=[RobotsRule(user_agent="*", allowed=True, pattern="*")],
        )
        assert is_allowed("https://example.com/page", policy) is True

    def test_disallowed(self):
        policy = RobotsPolicy(
            domain="example.com",
            rules=[RobotsRule(user_agent="*", allowed=False, pattern="/admin")],
        )
        assert is_allowed("https://example.com/admin", policy) is False


class TestParseDirective:
    """Tests for _parse_directive helper."""

    def test_user_agent_directive(self):
        from personal_index.robots_parser import _parse_directive

        policy = RobotsPolicy(domain="example.com")
        agent, rules = _parse_directive(
            "User-agent: Googlebot", None, policy, []
        )
        assert agent == "Googlebot"
        assert rules == []

    def test_disallow_directive(self):
        from personal_index.robots_parser import _parse_directive

        policy = RobotsPolicy(domain="example.com")
        agent, rules = _parse_directive(
            "Disallow: /admin", "Googlebot", policy, []
        )
        assert agent == "Googlebot"
        assert len(rules) == 1
        assert rules[0].allowed is False
        assert rules[0].pattern == "/admin"

    def test_allow_directive(self):
        from personal_index.robots_parser import _parse_directive

        policy = RobotsPolicy(domain="example.com")
        agent, rules = _parse_directive(
            "Allow: /public", "*", policy, []
        )
        assert agent == "*"
        assert len(rules) == 1
        assert rules[0].allowed is True
        assert rules[0].pattern == "/public"

    def test_crawl_delay_directive(self):
        from personal_index.robots_parser import _parse_directive

        policy = RobotsPolicy(domain="example.com")
        agent, rules = _parse_directive(
            "Crawl-delay: 10", "*", policy, []
        )
        assert policy.crawl_delay == 10.0

    def test_sitemap_directive(self):
        from personal_index.robots_parser import _parse_directive

        policy = RobotsPolicy(domain="example.com")
        agent, rules = _parse_directive(
            "Sitemap: https://example.com/sitemap.xml", "*", policy, []
        )
        assert "https://example.com/sitemap.xml" in policy.sitemap_urls

    def test_user_agent_switches_rules(self):
        from personal_index.robots_parser import _parse_directive

        policy = RobotsPolicy(domain="example.com")
        # First agent with a rule
        agent, rules = _parse_directive(
            "User-agent: Googlebot", None, policy, []
        )
        agent, rules = _parse_directive(
            "Disallow: /no-google", agent, policy, rules
        )
        # Switch to new agent — previous rules should be flushed to policy
        agent, rules = _parse_directive(
            "User-agent: Bingbot", agent, policy, rules
        )
        assert agent == "Bingbot"
        assert rules == []
        assert len(policy.rules) == 1
        assert policy.rules[0].user_agent == "Googlebot"

    def test_disallow_without_agent_ignored(self):
        from personal_index.robots_parser import _parse_directive

        policy = RobotsPolicy(domain="example.com")
        agent, rules = _parse_directive(
            "Disallow: /admin", None, policy, []
        )
        assert agent is None
        assert rules == []
