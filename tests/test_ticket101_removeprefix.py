"""Test that str.removeprefix() is used instead of conditional slice in url_dedup.py."""
import ast
import unittest


class TestRemoveprefixUsage(unittest.TestCase):
    """Verify FURB188 fix: use removeprefix instead of startswith + slice."""

    def test_no_conditional_www_slice(self):
        """Ensure no 'if domain.startswith("www."): domain = domain[4:]' patterns exist."""
        with open("personal_index/url_dedup.py") as f:
            source = f.read()

        # Check that the old pattern doesn't exist
        self.assertNotIn(
            'if domain.startswith("www."):',
            source,
            "Old startswith+slice pattern should be replaced with removeprefix"
        )
        self.assertNotIn(
            "domain = domain[4:]",
            source,
            "Old domain[4:] slice should be replaced with removeprefix"
        )

        # Check that removeprefix is used
        self.assertIn(
            'domain.removeprefix("www.")',
            source,
            "Should use domain.removeprefix('www.') instead"
        )

    def test_url_deduplicator_www_removal(self):
        """Ensure www. removal still works correctly after the fix."""
        from personal_index.url_dedup import URLDeduplicator

        dedup = URLDeduplicator()

        # Test that www. prefix is properly removed during normalization
        url_with_www = "https://www.example.com/page"
        url_without_www = "https://example.com/page"

        norm_with = dedup.normalize_url(url_with_www)
        norm_without = dedup.normalize_url(url_without_www)

        self.assertEqual(norm_with, norm_without, "www. should be stripped during normalization")

    def test_url_deduplicator_add_url_www(self):
        """Ensure add_url properly handles www. prefix."""
        from personal_index.url_dedup import URLDeduplicator

        dedup = URLDeduplicator()

        # Add URL with www.
        result1 = dedup.add_url("https://www.example.com/page")
        self.assertFalse(result1.is_duplicate)

        # Adding same URL without www. should be detected as duplicate
        result2 = dedup.add_url("https://example.com/page")
        self.assertTrue(result2.is_duplicate)

    def test_get_domain_urls_www(self):
        """Ensure get_domain_urls works with www. prefix."""
        from personal_index.url_dedup import URLDeduplicator

        dedup = URLDeduplicator()
        dedup.add_url("https://www.example.com/page1")
        dedup.add_url("https://example.com/page2")

        # Both should be retrievable
        urls_with_www = dedup.get_domain_urls("www.example.com")
        urls_without_www = dedup.get_domain_urls("example.com")

        # After removeprefix, both should resolve to the same domain
        self.assertEqual(len(urls_with_www), len(urls_without_www))


if __name__ == "__main__":
    unittest.main()
