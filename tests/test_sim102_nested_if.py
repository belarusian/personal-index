"""Tests for TICKET-70: SIM102 - nested if statements flattened."""

from personal_index.api.rate_limit_middleware import RateLimitRule
from personal_index.auth.sessions import SessionStore
from personal_index.crawler.robots import RobotsParser, RobotsPolicy, RobotsRule


class TestRateLimitRuleMatches:
    def test_matches_with_path_pattern(self):
        rule = RateLimitRule(path_pattern="/api/", max_requests=10, window_seconds=60)
        assert rule.matches("GET", "/api/users") is True
        assert rule.matches("GET", "/other") is False

    def test_matches_without_path_pattern(self):
        rule = RateLimitRule(path_pattern=None, max_requests=10, window_seconds=60)
        assert rule.matches("GET", "/anything") is True

    def test_matches_with_method_filter(self):
        rule = RateLimitRule(path_pattern="/api/", methods=["POST"], max_requests=10, window_seconds=60)
        assert rule.matches("POST", "/api/data") is True
        assert rule.matches("GET", "/api/data") is False


class TestSessionStoreActiveCount:
    def test_active_sessions_count(self):
        store = SessionStore(default_ttl=3600, cleanup_interval=3600)
        store.create_session(user_id="user1")
        count = store.get_active_count(user_id="user1")
        assert count >= 1

    def test_active_sessions_all_users(self):
        store = SessionStore(default_ttl=3600, cleanup_interval=3600)
        store.create_session(user_id="user1")
        store.create_session(user_id="user2")
        count = store.get_active_count(user_id=None)
        assert count >= 2


class TestRobotsPolicy:
    def test_can_fetch_basic(self):
        policy = RobotsPolicy(domain="example.com")
        assert policy.can_fetch("https://example.com/page.html") is True

    def test_can_fetch_with_rules(self):
        policy = RobotsPolicy(domain="example.com")
        rule = RobotsRule(user_agent="*", allowed=False, pattern="/private/")
        policy.rules.append(rule)
        assert policy.can_fetch("https://example.com/private/secret") is False
        assert policy.can_fetch("https://example.com/public/page") is True


class TestRobotsParser:
    def test_can_fetch_basic(self):
        parser = RobotsParser()
        assert parser.can_fetch("https://example.com/page.html") is True

    def test_can_fetch_with_disallow(self):
        parser = RobotsParser()
        robots_txt = "User-agent: *\nDisallow: /private/"
        parser.parse(robots_txt, "https://example.com")
        assert parser.can_fetch("https://example.com/private/secret") is False
        assert parser.can_fetch("https://example.com/public/page") is True
