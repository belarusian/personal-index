"""Test that dead code get_pinned_content and is_content_pinned are removed."""
import ast
import unittest


class TestDeadCodeRemoved(unittest.TestCase):
    """Verify TICKET-102: dead code functions are removed from content_pin.py."""

    def test_is_content_pinned_removed(self):
        """is_content_pinned should no longer be importable."""
        with self.assertRaises(ImportError):
            from personal_index.content_pin import is_content_pinned  # noqa: F401

    def test_get_pinned_content_removed(self):
        """get_pinned_content should no longer be importable."""
        with self.assertRaises(ImportError):
            from personal_index.content_pin import get_pinned_content  # noqa: F401

    def test_no_dead_functions_in_source(self):
        """Verify the functions don't exist in the source code."""
        with open("personal_index/content_pin.py") as f:
            source = f.read()
        tree = ast.parse(source)

        func_names = []
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                func_names.append(node.name)

        self.assertNotIn("is_content_pinned", func_names)
        self.assertNotIn("get_pinned_content", func_names)

    def test_remaining_functions_still_work(self):
        """Ensure pin_content and unpin_content still work after removal."""
        import os
        import tempfile

        from personal_index.content_pin import ContentPinner

        # Use a temp file to avoid polluting the default storage
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            tmp_path = f.name

        try:
            pinner = ContentPinner(storage_path=tmp_path)
            self.assertTrue(pinner.pin("test_item", reason="test"))
            self.assertTrue(pinner.is_pinned("test_item"))
            self.assertTrue(pinner.unpin("test_item"))
            self.assertFalse(pinner.is_pinned("test_item"))
        finally:
            os.unlink(tmp_path)


if __name__ == "__main__":
    unittest.main()
