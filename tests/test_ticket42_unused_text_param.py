"""Test for TICKET-42: text parameter in _build_reasons() is unused."""
import inspect
from personal_index.content_categorizer import ContentCategorizer, TopicScore


class TestUnusedTextParam:
    """Test that the unused text parameter is properly marked."""

    def test_text_param_is_prefixed_with_underscore(self):
        """The unused text parameter should be prefixed with underscore."""
        sig = inspect.signature(ContentCategorizer._build_reasons)
        params = list(sig.parameters.keys())
        assert "_text" in params, f"Expected '_text' in params, got {params}"
        assert "text" not in params, f"'text' should be renamed to '_text', got {params}"

    def test_build_reasons_works_with_empty_scores(self):
        """_build_reasons should return a reason when no scores provided."""
        categorizer = ContentCategorizer()
        reasons = categorizer._build_reasons([], "some text")
        assert isinstance(reasons, list)
        assert len(reasons) > 0

    def test_build_reasons_works_with_scores(self):
        """_build_reasons should return reasons based on topic scores."""
        categorizer = ContentCategorizer()
        scores = [
            TopicScore(
                topic="technology",
                score=0.9,
                matched_keywords=["python", "code"],
                signal_sources=["text"],
            )
        ]
        reasons = categorizer._build_reasons(scores, "some text")
        assert isinstance(reasons, list)
        assert len(reasons) > 0
        assert "technology" in reasons[0]
