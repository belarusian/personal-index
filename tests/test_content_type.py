"""Tests for content type detection module."""

from __future__ import annotations

import pytest

from personal_index.content_type import (
    ContentType,
    ContentTypeDetector,
    ContentAnalysis,
)


class TestContentTypeDetector:
    """Tests for ContentTypeDetector class."""

    def setup_method(self):
        self.detector = ContentTypeDetector()

    def test_detect_empty(self):
        result = self.detector.detect("")
        assert result.content_type == ContentType.UNKNOWN
        assert result.confidence == 0.0

    def test_detect_none(self):
        result = self.detector.detect(None)
        assert result.content_type == ContentType.UNKNOWN

    def test_detect_html(self):
        html = "<html><head><title>Test</title></head><body><p>Hello</p></body></html>"
        result = self.detector.detect(html)
        assert result.content_type == ContentType.HTML

    def test_detect_json(self):
        json_str = '{"key": "value", "items": [1, 2, 3]}'
        result = self.detector.detect(json_str)
        assert result.content_type == ContentType.JSON

    def test_detect_xml(self):
        xml = "<?xml version='1.0'?><root><item>test</item></root>"
        result = self.detector.detect(xml)
        assert result.content_type == ContentType.XML

    def test_detect_csv(self):
        csv_data = "name,age,city\nAlice,30,NYC\nBob,25,LA\nCharlie,35,Chicago"
        result = self.detector.detect(csv_data)
        assert result.content_type == ContentType.CSV

    def test_detect_markdown(self):
        md = "# Heading\n\nSome text\n\n## Subheading\n\n- item 1\n- item 2"
        result = self.detector.detect(md)
        assert result.content_type == ContentType.MARKDOWN

    def test_detect_python_code(self):
        code = "def hello():\n    print('world')\n\nclass Foo:\n    def bar(self):\n        return True"
        result = self.detector.detect(code)
        assert result.content_type == ContentType.CODE
        assert result.language == "python"

    def test_detect_javascript_code(self):
        code = "const x = 1;\nlet y = 'hello';\nconsole.log(x);\narr.map(x => x * 2)"
        result = self.detector.detect(code)
        assert result.content_type == ContentType.CODE
        assert result.language == "javascript"

    def test_detect_plain_text(self):
        text = "This is just some plain text with no special formatting or patterns."
        result = self.detector.detect(text)
        assert result.content_type == ContentType.TEXT

    def test_detect_word_count(self):
        text = "one two three four five"
        result = self.detector.detect(text)
        assert result.word_count == 5

    def test_detect_char_count(self):
        text = "hello"
        result = self.detector.detect(text)
        assert result.char_count == 5

    def test_detect_line_count(self):
        text = "line1\nline2\nline3"
        result = self.detector.detect(text)
        assert result.line_count == 3

    def test_detect_from_headers_html(self):
        result = self.detector.detect_from_headers("text/html; charset=utf-8", "<html></html>")
        assert result.content_type == ContentType.HTML
        assert result.confidence == 0.9

    def test_detect_from_headers_json(self):
        result = self.detector.detect_from_headers("application/json", '{"a": 1}')
        assert result.content_type == ContentType.JSON

    def test_detect_from_headers_unknown(self):
        result = self.detector.detect_from_headers("application/octet-stream", "data")
        assert result.content_type == ContentType.UNKNOWN

    def test_detect_from_headers_empty(self):
        result = self.detector.detect_from_headers("", "some text")
        assert result.content_type == ContentType.TEXT

    def test_detect_sql(self):
        sql = "SELECT * FROM users WHERE id = 1; INSERT INTO logs VALUES (1);"
        result = self.detector.detect(sql)
        assert result.content_type == ContentType.CODE
        assert result.language == "sql"

    def test_detect_typescript(self):
        ts = "const x: string = 'hello';\ninterface User { name: string; }\ntype Id = number;"
        result = self.detector.detect(ts)
        assert result.content_type == ContentType.CODE
        assert result.language == "typescript"

    def test_detect_java(self):
        java = "public class Main {\n    public static void main(String[] args) {\n        System.out.println(\"hi\");\n    }\n}"
        result = self.detector.detect(java)
        assert result.content_type == ContentType.CODE
        assert result.language == "java"

    def test_detect_rust(self):
        rust = "fn main() {\n    let mut x: Option<i32> = Some(42);\n    use std::vec::Vec;\n}"
        result = self.detector.detect(rust)
        assert result.content_type == ContentType.CODE
        assert result.language == "rust"

    def test_detect_go(self):
        go = "package main\nimport \"fmt\"\nfunc main() {\n    fmt.Println(\"hi\")\n}"
        result = self.detector.detect(go)
        assert result.content_type == ContentType.CODE
        assert result.language == "go"

    def test_detect_c(self):
        c = "#include <stdio.h>\nint main() {\n    printf(\"hello\");\n    return 0;\n}"
        result = self.detector.detect(c)
        assert result.content_type == ContentType.CODE
        assert result.language == "c"

    def test_confidence_range(self):
        result = self.detector.detect("some text")
        assert 0.0 <= result.confidence <= 1.0

    def test_metadata_in_header_detection(self):
        result = self.detector.detect_from_headers("text/html", "<html></html>")
        assert "content_type_header" in result.metadata
