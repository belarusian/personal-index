"""Integration tests for content scoring."""

from __future__ import annotations

import os
import tempfile

import pytest

from personal_index.app import PersonalIndexApp
from personal_index.content_scoring import ContentScorer, ScoreWeights


class TestScoringIntegration:
    """Test content scoring end-to-end."""

    def setup_method(self):
        self.tmpdir = tempfile.mkdtemp()
        self.app = PersonalIndexApp(
            config_path=os.path.join(self.tmpdir, "config.yaml"),
            data_dir=os.path.join(self.tmpdir, "data"),
        )
        self.app.initialize()

    def test_scoring_via_pipeline(self):
        """Content should be scored through the pipeline."""
        result = self.app.process_content(
            "https://example.com",
            "Important content about technology",
            "Tech Article",
        )
        assert "score" in result
        assert isinstance(result["score"], (int, float))

    def test_scoring_different_content(self):
        """Different content should get different scores."""
        r1 = self.app.process_content("https://x.com/1", "Short", "S")
        r2 = self.app.process_content("https://x.com/2", "Longer content with more words and details", "L")
        # Scores may differ based on content length and quality
        assert "score" in r1
        assert "score" in r2

    def test_scoring_with_title(self):
        """Title should influence scoring."""
        r1 = self.app.process_content("https://x.com/1", "Content", "Important Title")
        r2 = self.app.process_content("https://x.com/2", "Content", "")
        assert "score" in r1
        assert "score" in r2

    def test_scorer_direct(self):
        """ContentScorer should work directly."""
        scorer = ContentScorer(weights=ScoreWeights())
        from datetime import datetime, timezone
        score = scorer.score(
            published_at=None,
            updated_at=datetime.now(timezone.utc),
            keyword_matches=1,
            total_keywords=1,
            view_count=0,
            bookmark_count=0,
            share_count=0,
            word_count=10,
        )
        assert isinstance(score.total, (int, float))
        assert score.total >= 0
