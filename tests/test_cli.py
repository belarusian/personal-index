"""Tests for the CLI module."""

import pytest
from personal_index.cli import build_parser, main, format_search_result
from personal_index.index import Document, SearchResult


class TestFormatSearchResult:
    def test_format_basic(self):
        doc = Document(url="https://example.com", title="Test Page", content="Some content here")
        result = SearchResult(document=doc, score=0.95, matched_terms=["test"])
        output = format_search_result(result, 1)
        assert "1." in output
        assert "Test Page" in output
        assert "https://example.com" in output
        assert "test" in output

    def test_format_no_title(self):
        doc = Document(url="https://example.com", content="Some content")
        result = SearchResult(document=doc, score=0.5)
        output = format_search_result(result, 2)
        assert "2." in output
        assert "https://example.com" in output


class TestBuildParser:
    def test_parser_created(self):
        parser = build_parser()
        assert parser.prog == "personal-index"

    def test_add_interest_subparser(self):
        parser = build_parser()
        args = parser.parse_args(["add-interest", "-n", "python", "-k", "python", "code"])
        assert args.command == "add-interest"
        assert args.name == "python"
        assert args.keywords == ["python", "code"]

    def test_search_subparser(self):
        parser = build_parser()
        args = parser.parse_args(["search", "python", "-l", "5"])
        assert args.command == "search"
        assert args.query == "python"
        assert args.limit == 5

    def test_crawl_subparser(self):
        parser = build_parser()
        args = parser.parse_args(["crawl", "https://example.com", "-d", "5"])
        assert args.command == "crawl"
        assert args.url == "https://example.com"
        assert args.depth == 5

    def test_stats_subparser(self):
        parser = build_parser()
        args = parser.parse_args(["stats"])
        assert args.command == "stats"

    def test_list_interests_subparser(self):
        parser = build_parser()
        args = parser.parse_args(["list-interests"])
        assert args.command == "list-interests"

    def test_remove_interest_subparser(self):
        parser = build_parser()
        args = parser.parse_args(["remove-interest", "python"])
        assert args.command == "remove-interest"
        assert args.name == "python"


class TestMain:
    def test_main_no_command(self, capsys):
        result = main([])
        assert result == 0
        captured = capsys.readouterr()
        assert "usage:" in captured.out.lower() or "personal-index" in captured.out.lower()

    def test_main_list_interests_empty(self, capsys):
        result = main(["list-interests"])
        assert result == 0
        captured = capsys.readouterr()
        assert "No interests" in captured.out

    def test_main_add_interest(self, capsys):
        result = main(["add-interest", "-n", "test", "-k", "keyword"])
        assert result == 0
        captured = capsys.readouterr()
        assert "Added interest: test" in captured.out

    def test_main_search_empty_index(self, capsys):
        result = main(["search", "python"])
        assert result == 0
        captured = capsys.readouterr()
        assert "No results found" in captured.out

    def test_main_stats_empty(self, capsys):
        result = main(["stats"])
        assert result == 0
        captured = capsys.readouterr()
        assert "Total documents: 0" in captured.out
