"""Tests for TICKET-9: Verify dead modules have been removed."""
import os
import unittest


class TestDeadModulesRemoved(unittest.TestCase):
    """Verify dead modules are removed and remaining code still works."""

    def test_api_routes_removed(self):
        """api/routes.py should be removed."""
        self.assertFalse(
            os.path.exists("personal_index/api/routes.py"),
            "personal_index/api/routes.py should not exist",
        )

    def test_content_favicon_removed(self):
        """content_favicon.py should be removed."""
        self.assertFalse(
            os.path.exists("personal_index/content_favicon.py"),
            "personal_index/content_favicon.py should not exist",
        )

    def test_content_import_html_removed(self):
        """content_import_html.py should be removed."""
        self.assertFalse(
            os.path.exists("personal_index/content_import_html.py"),
            "personal_index/content_import_html.py should not exist",
        )

    def test_content_social_preview_removed(self):
        """content_social_preview.py should be removed."""
        self.assertFalse(
            os.path.exists("personal_index/content_social_preview.py"),
            "personal_index/content_social_preview.py should not exist",
        )

    def test_content_thumbnail_removed(self):
        """content_thumbnail.py should be removed."""
        self.assertFalse(
            os.path.exists("personal_index/content_thumbnail.py"),
            "personal_index/content_thumbnail.py should not exist",
        )

    def test_crawl_stats_removed(self):
        """crawl_stats.py should be removed."""
        self.assertFalse(
            os.path.exists("personal_index/crawl_stats.py"),
            "personal_index/crawl_stats.py should not exist",
        )

    def test_migrations_preserved(self):
        """Migration files should be preserved (loaded dynamically)."""
        self.assertTrue(
            os.path.exists("personal_index/migrations/001_initial_schema.py"),
            "Migration files should be preserved",
        )
        self.assertTrue(
            os.path.exists("personal_index/migrations/002_add_indexes.py"),
            "Migration files should be preserved",
        )

    def test_remaining_modules_import(self):
        """Core modules should still import correctly."""
        from personal_index import cli, config, formatter
        self.assertIsNotNone(config)
        self.assertIsNotNone(formatter)
        self.assertIsNotNone(cli)


if __name__ == "__main__":
    unittest.main()
