import unittest
from personal_index.content_pin import pin_content, unpin_content


class TestPin(unittest.TestCase):
    def test_pin(self):
        self.assertTrue(pin_content("item_id"))

    def test_unpin(self):
        self.assertTrue(unpin_content("item_id"))


class TestDeadCodeRemoved(unittest.TestCase):
    """Verify dead code functions have been removed from content_pin."""

    def test_is_content_pinned_removed(self):
        """is_content_pinned was dead code — should no longer exist."""
        from personal_index import content_pin
        self.assertFalse(hasattr(content_pin, "is_content_pinned"))

    def test_get_pinned_content_removed(self):
        """get_pinned_content was dead code — should no longer exist."""
        from personal_index import content_pin
        self.assertFalse(hasattr(content_pin, "get_pinned_content"))


if __name__ == "__main__":
    unittest.main()
