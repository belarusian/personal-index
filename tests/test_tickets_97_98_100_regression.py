"""Regression tests for already-fixed tickets TICKET-97, TICKET-98, TICKET-100."""
import ast
import unittest


class TestTicket97SuppressImport(unittest.TestCase):
    """Verify TICKET-97: suppress is properly imported in crawler/robots.py."""

    def test_suppress_imported(self):
        """suppress should be imported from contextlib."""
        with open("personal_index/crawler/robots.py") as f:
            source = f.read()
        self.assertIn("from contextlib import suppress", source)

    def test_suppress_used(self):
        """suppress should be used in the module."""
        with open("personal_index/crawler/robots.py") as f:
            source = f.read()
        self.assertIn("with suppress(ValueError):", source)

    def test_no_f821_error(self):
        """No F821 (undefined name) errors for suppress."""
        with open("personal_index/crawler/robots.py") as f:
            source = f.read()
        tree = ast.parse(source)

        # Check that suppress is imported
        imports = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                if node.module == "contextlib":
                    for alias in node.names:
                        imports.add(alias.name)
        self.assertIn("suppress", imports)


class TestTicket98DuplicateSetItem(unittest.TestCase):
    """Verify TICKET-98: no duplicate items in sets in content_enricher.py."""

    def test_no_duplicate_set_items(self):
        """No duplicate values in any set literal."""
        with open("personal_index/content_enricher.py") as f:
            source = f.read()
        tree = ast.parse(source)

        for node in ast.walk(tree):
            if isinstance(node, ast.Set):
                values = []
                for elt in node.elts:
                    if isinstance(elt, ast.Constant):
                        values.append(elt.value)
                self.assertEqual(
                    len(values), len(set(values)),
                    f"Duplicate values found in set at line {node.lineno}: {values}"
                )

    def test_negative_words_no_duplicate_wrong(self):
        """'wrong' should appear only once in NEGATIVE_WORDS."""
        from personal_index.content_enricher import ContentEnricher
        negative_words = ContentEnricher.NEGATIVE_WORDS
        # Count occurrences - since it's a set, duplicates are impossible
        # but we verify the set is valid
        self.assertIsInstance(negative_words, set)
        self.assertIn("wrong", negative_words)


class TestTicket100MisleadingLstrip(unittest.TestCase):
    """Verify TICKET-100: no misleading lstrip in url_dedup.py."""

    def test_no_b005_lstrip_in_url_dedup(self):
        """url_dedup.py should not have lstrip() calls that could be misleading."""
        with open("personal_index/url_dedup.py") as f:
            source = f.read()
        # B005 flags .lstrip() on strings (not .lstrip('.'))
        # url_dedup.py should not have any lstrip calls
        self.assertNotIn(".lstrip(", source)

    def test_www_removal_uses_removeprefix(self):
        """www. removal should use removeprefix, not lstrip."""
        with open("personal_index/url_dedup.py") as f:
            source = f.read()
        self.assertIn('removeprefix("www.")', source)


if __name__ == "__main__":
    unittest.main()
