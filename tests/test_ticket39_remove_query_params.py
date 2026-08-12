"""Test for TICKET-39: remove_query_params() return type mismatch fix."""
from personal_index.url_utils import remove_query_params


class TestRemoveQueryParamsReturnType:
    """Test that remove_query_params always returns str, never None."""

    def test_returns_str_on_valid_url(self):
        """Normal case: returns a string."""
        result = remove_query_params("https://example.com?utm_source=test", ["utm_source"])
        assert isinstance(result, str)
        assert result == "https://example.com"

    def test_returns_str_on_no_params(self):
        """When params is empty, returns original URL as str."""
        result = remove_query_params("https://example.com?foo=bar", [])
        assert isinstance(result, str)
        assert result == "https://example.com?foo=bar"

    def test_returns_str_on_none_params(self):
        """When params is None, returns original URL as str."""
        result = remove_query_params("https://example.com?foo=bar", None)
        assert isinstance(result, str)
        assert result == "https://example.com?foo=bar"

    def test_returns_str_on_invalid_url(self):
        """On exception (invalid URL), returns original URL string, not None."""
        # This should not raise and should return a str
        result = remove_query_params("", ["foo"])
        assert isinstance(result, str)
        assert result is not None

    def test_never_returns_none(self):
        """remove_query_params must never return None."""
        # Test various edge cases
        for url in ["", "not-a-url", "://broken", None if False else "valid"]:
            result = remove_query_params(url, ["param"])
            assert result is not None, f"remove_query_params returned None for url={url!r}"
