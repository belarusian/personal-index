"""Test for TICKET-44: 'format' parameter shadows Python builtin."""
import inspect
from personal_index.content_export_csv import CSVExporter
from personal_index.export_markdown import MarkdownExporter


class TestBuiltinShadowing:
    """Test that 'format' is not used as a parameter name."""

    def test_csv_export_no_format_param(self):
        """CSVExporter.export should not use 'format' as param name."""
        sig = inspect.signature(CSVExporter.export)
        params = list(sig.parameters.keys())
        assert "format" not in params, f"'format' shadows builtin, found in {params}"
        assert "export_format" in params, f"Expected 'export_format' in {params}"

    def test_markdown_export_no_format_param(self):
        """MarkdownExporter.export should not use 'format' as param name."""
        sig = inspect.signature(MarkdownExporter.export)
        params = list(sig.parameters.keys())
        assert "format" not in params, f"'format' shadows builtin, found in {params}"
        assert "export_format" in params, f"Expected 'export_format' in {params}"

    def test_csv_export_still_works(self):
        """CSVExporter.export should still work with export_format."""
        exporter = CSVExporter()
        items = [{"title": "Test", "url": "https://example.com"}]
        result = exporter.export(items)
        assert isinstance(result, str)
        assert "Test" in result

    def test_markdown_export_still_works(self):
        """MarkdownExporter.export should still work with export_format."""
        exporter = MarkdownExporter()
        items = [{"title": "Test", "url": "https://example.com"}]
        result = exporter.export(items, export_format=None)
        assert isinstance(result, str)
        assert "Test" in result
