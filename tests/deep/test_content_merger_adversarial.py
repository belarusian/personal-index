"""Adversarial deep tests for personal_index.content_merger.

Cycle 164 (VALIDATOR).

Two purposes:
1. VERIFY ARCH-34 (Status: IMPLEMENTED, Option A — validate at construction):
   an unrecognized ``strategy`` must raise ``ValueError`` at construction,
   never silently fall through to ``concatenate``.
2. PROBE the module with adversarial inputs (None/empty/whitespace/unicode/
   duplicate/out-of-range), round-trips, idempotence, and one end-to-end
   CLI run.
"""

from __future__ import annotations

import pytest

from personal_index.content_merger import (
    ContentMerger,
    MergedContent,
    MergeSource,
)


def _src(
    url: str = "https://example.com",
    title: str = "T",
    content: str = "C",
    tags: list | None = None,
    priority: int = 0,
    metadata: dict | None = None,
) -> MergeSource:
    return MergeSource(
        url=url,
        title=title,
        content=content,
        tags=tags or [],
        priority=priority,
        metadata=metadata or {},
    )


# ---------------------------------------------------------------------------
# 1. VERIFY ARCH-34 — Option A: validate strategy at construction
# ---------------------------------------------------------------------------

class TestArch34StrategyValidation:
    """ARCH-34: unrecognized strategy must raise, never silently concatenate."""

    @pytest.mark.parametrize(
        "bad",
        [
            "longst",            # typo
            "CONCATENATE",       # case variant
            "Longest",           # case variant
            "highest-priority",  # wrong separator
            "unique-paragraphs", # wrong separator
            "",                  # empty
            "   ",               # whitespace
            "concatenate ",      # trailing space
            "concatenate\n",     # newline
            "concatenate\t",     # tab
            "concatenate\u00a0", # non-breaking space
            "concatenat\u00e9",  # unicode lookalike
            "concatenate\u200b", # zero-width space
        ],
    )
    def test_unrecognized_strategy_raises(self, bad: str):
        with pytest.raises(ValueError):
            ContentMerger(strategy=bad)

    def test_none_strategy_raises(self):
        with pytest.raises(ValueError):
            ContentMerger(strategy=None)  # type: ignore[arg-type]

    @pytest.mark.parametrize(
        "good",
        ["concatenate", "longest", "highest_priority", "unique_paragraphs"],
    )
    def test_valid_strategies_accepted(self, good: str):
        m = ContentMerger(strategy=good)
        assert m.strategy == good

    def test_default_strategy_is_concatenate(self):
        assert ContentMerger().strategy == "concatenate"

    def test_error_message_names_rejected_value(self):
        with pytest.raises(ValueError) as ei:
            ContentMerger(strategy="longst")
        assert "longst" in str(ei.value)


# ---------------------------------------------------------------------------
# 2. PROBE — adversarial merge inputs
# ---------------------------------------------------------------------------

class TestMergeAdversarial:
    def test_merge_empty_returns_none(self):
        assert ContentMerger().merge([]) is None

    def test_merge_single_empty_content(self):
        r = ContentMerger().merge([_src(content="")])
        assert r is not None
        assert r.content == ""
        assert r.source_count == 1

    def test_merge_all_empty_content_concatenate(self):
        r = ContentMerger(strategy="concatenate").merge(
            [_src(content=""), _src(content="   ")]
        )
        assert r is not None
        # whitespace-only content is falsy after strip -> no content
        assert r.content == ""

    def test_merge_whitespace_only_content_stripped(self):
        r = ContentMerger(strategy="concatenate").merge(
            [_src(content="  hello  "), _src(content="world")]
        )
        assert r is not None
        assert "hello" in r.content
        assert "world" in r.content
        # leading/trailing whitespace stripped per source
        assert r.content.startswith("hello")

    def test_merge_unicode_content_roundtrip(self):
        text = "héllo wörld — ünïcode ✓"
        r = ContentMerger(strategy="concatenate").merge([_src(content=text)])
        assert r is not None
        assert r.content == text

    def test_merge_unicode_tags_normalized(self):
        r = ContentMerger(strategy="concatenate").merge(
            [_src(tags=["Python", "python", "Web", "web"])]
        )
        assert r is not None
        assert r.tags == ["python", "web"]  # deduped + lowercased + sorted

    def test_merge_duplicate_urls_tracked(self):
        r = ContentMerger().merge(
            [_src(url="https://a.com"), _src(url="https://a.com")]
        )
        assert r is not None
        assert r.source_count == 2
        assert r.sources == ["https://a.com", "https://a.com"]

    def test_merge_non_string_tags_dropped_not_crash(self):
        r = ContentMerger().merge([_src(tags=[1, "ok", None, 3.0])])  # type: ignore[list-item]
        assert r is not None
        assert r.tags == ["ok"]

    def test_merge_none_metadata_value(self):
        r = ContentMerger().merge([_src(metadata={"a": None, "b": 1})])
        assert r is not None
        assert r.metadata == {"a": None, "b": 1}

    def test_merge_metadata_higher_priority_wins(self):
        r = ContentMerger().merge(
            [
                _src(url="https://low.com", priority=1, metadata={"author": "Low"}),
                _src(url="https://high.com", priority=10, metadata={"author": "High"}),
            ]
        )
        assert r is not None
        assert r.metadata["author"] == "High"

    def test_merge_negative_priority_out_of_range(self):
        r = ContentMerger(strategy="highest_priority").merge(
            [
                _src(url="https://a.com", content="A", priority=-5),
                _src(url="https://b.com", content="B", priority=-1),
            ]
        )
        assert r is not None
        # -1 > -5 so B is primary
        assert r.url == "https://b.com"
        assert r.content == "B"

    def test_merge_huge_priority_no_overflow(self):
        r = ContentMerger(strategy="highest_priority").merge(
            [
                _src(url="https://a.com", content="A", priority=10**12),
                _src(url="https://b.com", content="B", priority=1),
            ]
        )
        assert r is not None
        assert r.url == "https://a.com"

    def test_merge_longest_tie_breaks_to_first_max(self):
        # equal-length content: max() returns the first encountered
        r = ContentMerger(strategy="longest").merge(
            [
                _src(url="https://a.com", content="AAAA"),
                _src(url="https://b.com", content="BBBB"),
            ]
        )
        assert r is not None
        assert r.content in ("AAAA", "BBBB")
        assert r.merge_strategy == "longest"

    def test_merge_unique_paragraphs_dedup_case_ws(self):
        r = ContentMerger(strategy="unique_paragraphs").merge(
            [
                _src(content="Hello World\n\nSecond"),
                _src(content="  hello world  \n\nThird"),
            ]
        )
        assert r is not None
        assert r.content.count("Hello World") == 1
        assert "Second" in r.content
        assert "Third" in r.content

    def test_merge_unique_paragraphs_all_blank(self):
        r = ContentMerger(strategy="unique_paragraphs").merge(
            [_src(content="\n\n   \n\n")]
        )
        assert r is not None
        assert r.content == ""

    def test_merge_title_falls_back_to_best(self):
        r = ContentMerger().merge(
            [
                _src(url="https://a.com", title="", content="A"),
                _src(url="https://b.com", title="Longer Title", content="B"),
            ]
        )
        assert r is not None
        assert r.title == "Longer Title"

    def test_merge_all_empty_titles(self):
        r = ContentMerger().merge([_src(title=""), _src(title="")])
        assert r is not None
        assert r.title == ""


# ---------------------------------------------------------------------------
# 3. PROBE — idempotence / round-trip / property checks
# ---------------------------------------------------------------------------

class TestMergeIdempotenceAndRoundTrip:
    def test_merge_is_idempotent_on_result(self):
        """Merging the same sources twice yields identical results."""
        sources = [
            _src(url="https://a.com", content="A", tags=["x"], priority=1),
            _src(url="https://b.com", content="B", tags=["y"], priority=2),
        ]
        m = ContentMerger(strategy="concatenate")
        r1 = m.merge(sources)
        r2 = m.merge(sources)
        assert r1 is not None and r2 is not None
        assert r1.to_dict() == r2.to_dict()

    def test_merged_content_to_dict_roundtrip(self):
        r = ContentMerger(strategy="longest").merge(
            [_src(url="https://a.com", content="Longer content here", tags=["a"])]
        )
        assert r is not None
        d = r.to_dict()
        assert d["url"] == r.url
        assert d["content"] == r.content
        assert d["merge_strategy"] == "longest"
        assert d["source_count"] == 1
        # reconstruct an equivalent dataclass
        rebuilt = MergedContent(
            url=d["url"],
            title=d["title"],
            content=d["content"],
            tags=d["tags"],
            metadata=d["metadata"],
            source_count=d["source_count"],
            sources=d["sources"],
            merge_strategy=d["merge_strategy"],
        )
        assert rebuilt.to_dict() == d

    def test_property_source_count_equals_len_sources(self):
        for n in (1, 2, 5, 10):
            sources = [_src(url=f"https://s{i}.com", content=f"C{i}") for i in range(n)]
            r = ContentMerger().merge(sources)
            assert r is not None
            assert r.source_count == n
            assert len(r.sources) == n

    def test_property_tags_always_sorted_lower_deduped(self):
        r = ContentMerger().merge(
            [_src(tags=["Zeta", "alpha", "Zeta", "Beta", "alpha"])]
        )
        assert r is not None
        assert r.tags == sorted(r.tags)
        assert r.tags == ["alpha", "beta", "zeta"]


# ---------------------------------------------------------------------------
# 4. End-to-end CLI run (installed entry point)
# ---------------------------------------------------------------------------

def test_end_to_end_cli_init_and_stats(tmp_path):
    """End-to-end: init a data dir and run stats through the installed CLI."""
    from click.testing import CliRunner

    from personal_index.cli import main

    runner = CliRunner()
    dd = str(tmp_path / "data")
    r = runner.invoke(main, ["init", "--data-dir", dd])
    assert r.exit_code == 0, r.output
    assert "Initialized" in r.output

    r = runner.invoke(main, ["stats", "--data-dir", dd, "--format", "json"])
    assert r.exit_code == 0, r.output
    import json as _json

    payload = _json.loads(r.output)
    assert payload["indexed_pages"] == 0
    assert payload["interests"] == 0
    assert payload["total_tags"] == 0


# ---------------------------------------------------------------------------
# 5. PROBE cycle 368 — additional adversarial edge cases + QA-76 defect pin
# ---------------------------------------------------------------------------

class TestMergeConcatPhantomSeparator:
    """QA-76: concatenate must skip whitespace-only sources, not inject a
    phantom ``---`` separator for them. The merge() docstring promises to join
    **non-empty** content; _merge_concatenate guards on raw truthiness so a
    whitespace-only source survives the guard and is appended as ""."""

    def test_concatenate_whitespace_only_source_injects_phantom_separator(self):
        r = ContentMerger(strategy="concatenate").merge(
            [
                _src(url="https://a.com", content="A"),
                _src(url="https://ws.com", content="   "),
                _src(url="https://b.com", content="B"),
            ]
        )
        assert r is not None
        # per docs: whitespace-only source is empty after strip -> skipped
        assert r.content == "A\n\n---\n\nB"
        assert r.content.count("---") == 1


class TestMergeCycle368Armor:
    """Cycle 368 regression armor: behaviors the cycle-164 file does not pin."""

    def test_longest_tie_breaks_to_first_in_priority_order(self):
        # equal length, equal priority: stable sort keeps input order, max()
        # returns the first encountered max -> "AAAA"
        r = ContentMerger(strategy="longest").merge(
            [
                _src(url="https://a.com", content="AAAA"),
                _src(url="https://b.com", content="BBBB"),
            ]
        )
        assert r is not None
        assert r.content == "AAAA"

    def test_highest_priority_empty_primary_does_not_fall_back(self):
        # highest_priority uses primary.content verbatim; an empty primary is
        # NOT replaced by a non-empty lower-priority source.
        r = ContentMerger(strategy="highest_priority").merge(
            [
                _src(url="https://hi.com", content="", priority=10),
                _src(url="https://lo.com", content="X", priority=1),
            ]
        )
        assert r is not None
        assert r.content == ""
        assert r.url == "https://hi.com"

    def test_metadata_equal_priority_first_wins(self):
        # _merge_metadata iterates priority-desc and keeps the first value for
        # a key; on equal priority the stable order makes the first source win.
        r = ContentMerger().merge(
            [
                _src(url="https://a.com", priority=5, metadata={"k": "first"}),
                _src(url="https://b.com", priority=5, metadata={"k": "second"}),
            ]
        )
        assert r is not None
        assert r.metadata["k"] == "first"

    def test_metadata_disjoint_keys_all_present(self):
        r = ContentMerger().merge(
            [
                _src(url="https://a.com", priority=3, metadata={"a": 1}),
                _src(url="https://b.com", priority=2, metadata={"b": 2}),
                _src(url="https://c.com", priority=1, metadata={"c": 3}),
            ]
        )
        assert r is not None
        assert r.metadata == {"a": 1, "b": 2, "c": 3}

    def test_unique_paragraphs_preserves_first_seen_casing(self):
        # dedup is case-insensitive but the kept paragraph keeps first casing
        r = ContentMerger(strategy="unique_paragraphs").merge(
            [
                _src(url="https://a.com", content="Hello"),
                _src(url="https://b.com", content="HELLO"),
            ]
        )
        assert r is not None
        assert r.content == "Hello"

    def test_unique_paragraphs_source_count_and_sources(self):
        r = ContentMerger(strategy="unique_paragraphs").merge(
            [
                _src(url="https://a.com", content="P1"),
                _src(url="https://b.com", content="P2"),
            ]
        )
        assert r is not None
        assert r.source_count == 2
        assert set(r.sources) == {"https://a.com", "https://b.com"}

    def test_concatenate_single_source_has_no_separator(self):
        r = ContentMerger(strategy="concatenate").merge(
            [_src(url="https://a.com", content="only")]
        )
        assert r is not None
        assert r.content == "only"
        assert "---" not in r.content

    def test_concatenate_empty_plus_real_skips_empty(self):
        # an empty (falsy) source is skipped; only the real content remains
        r = ContentMerger(strategy="concatenate").merge(
            [
                _src(url="https://a.com", content=""),
                _src(url="https://b.com", content="A"),
            ]
        )
        assert r is not None
        assert r.content == "A"
        assert r.content.count("---") == 0

    def test_highest_priority_tags_aggregated_from_all_sources(self):
        r = ContentMerger(strategy="highest_priority").merge(
            [
                _src(url="https://hi.com", content="H", priority=9, tags=["hi"]),
                _src(url="https://lo.com", content="L", priority=1, tags=["lo"]),
            ]
        )
        assert r is not None
        assert r.tags == ["hi", "lo"]

    def test_longest_tags_aggregated_from_all_sources(self):
        r = ContentMerger(strategy="longest").merge(
            [
                _src(url="https://a.com", content="longest content", tags=["a"]),
                _src(url="https://b.com", content="x", tags=["b"]),
            ]
        )
        assert r is not None
        assert r.tags == ["a", "b"]

    def test_best_title_longest_non_empty_wins(self):
        r = ContentMerger().merge(
            [
                _src(url="https://a.com", title="", content="A", priority=5),
                _src(url="https://b.com", title="Short", content="B", priority=4),
                _src(url="https://c.com", title="A Much Longer Title", content="C", priority=3),
            ]
        )
        assert r is not None
        # primary (priority 5) has empty title -> falls back to longest non-empty
        assert r.title == "A Much Longer Title"

    def test_best_title_unicode_length(self):
        r = ContentMerger().merge(
            [
                _src(url="https://a.com", title="ascii", content="A", priority=5),
                _src(url="https://b.com", title="日本語のタイトル", content="B", priority=4),
            ]
        )
        assert r is not None
        # primary empty? no, primary title is "ascii" (priority 5) -> used
        assert r.title == "ascii"

    def test_empty_string_url_preserved(self):
        r = ContentMerger().merge([_src(url="", content="A")])
        assert r is not None
        assert r.url == ""

    def test_merge_source_to_dict_roundtrip(self):
        src = MergeSource(
            url="https://a.com",
            title="T",
            content="C",
            tags=["x"],
            metadata={"k": "v"},
            priority=7,
        )
        d = src.to_dict()
        assert d == {
            "url": "https://a.com",
            "title": "T",
            "content": "C",
            "tags": ["x"],
            "metadata": {"k": "v"},
            "priority": 7,
        }
        rebuilt = MergeSource(**d)
        assert rebuilt.to_dict() == d

    def test_merge_strategy_field_matches_strategy(self):
        for strat in ("concatenate", "longest", "highest_priority", "unique_paragraphs"):
            r = ContentMerger(strategy=strat).merge(
                [_src(url="https://a.com", content="A")]
            )
            assert r is not None
            assert r.merge_strategy == strat
