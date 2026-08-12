"""Test that unused encoding variables are properly ignored in content_type.py."""
import ast
import unittest


class TestUnusedEncoding(unittest.TestCase):
    """Verify RUF059 fix: no unused unpacked variables in content_type.py."""

    def test_no_unused_encoding_variable(self):
        """Ensure mimetypes.guess_type unpacks to (_,) not (encoding,) when unused."""
        with open("personal_index/content_type.py") as f:
            source = f.read()
        tree = ast.parse(source)

        # Find all assignments where mimetypes.guess_type is unpacked
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Tuple) and len(target.elts) == 2 and isinstance(node.value, ast.Call):
                        # Check if the value is a call to mimetypes.guess_type
                            func = node.value.func
                            if isinstance(func, ast.Attribute) and func.attr == "guess_type":
                                # Second element should be underscore (unused)
                                second = target.elts[1]
                                if isinstance(second, ast.Name):
                                    self.assertEqual(
                                        second.id, "_",
                                        f"Line {node.lineno}: unused variable should be '_' not '{second.id}'"
                                    )

    def test_content_type_detector_works(self):
        """Ensure the module still works after the fix."""
        from personal_index.content_type import ContentTypeDetector

        detector = ContentTypeDetector()
        info = detector.detect_from_url("https://example.com/file.txt")
        self.assertEqual(info.category, "text")
        self.assertTrue(info.is_text)

        info = detector.detect_from_url("https://example.com/file.pdf")
        self.assertEqual(info.category, "document")
        self.assertTrue(info.is_document)

        info = detector.detect_from_filename("document.pdf")
        self.assertEqual(info.category, "document")

        info = detector.detect_from_extension(".jpg")
        self.assertTrue(info.is_media)


if __name__ == "__main__":
    unittest.main()
