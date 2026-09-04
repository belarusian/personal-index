"""Tests for content enrichment module."""

from __future__ import annotations

from personal_index.content_enricher import ContentEnricher, EnrichedContent


class TestEnrichedContent:
    """Tests for EnrichedContent dataclass."""

    def test_default_values(self):
        content = EnrichedContent(title="Test", text="Hello world")
        assert content.word_count == 0
        assert content.reading_time == 0.0
        assert content.keywords == []
        assert content.language == "en"
        assert content.has_code is False
        assert content.sentiment_score == 0.0

    def test_to_dict(self):
        content = EnrichedContent(
            title="Test",
            text="Hello world",
            word_count=2,
            keywords=["hello", "world"],
        )
        d = content.to_dict()
        assert d["title"] == "Test"
        assert d["word_count"] == 2
        assert d["keywords"] == ["hello", "world"]
        assert "enriched_at" in d


class TestContentEnricher:
    """Tests for ContentEnricher class."""

    def setup_method(self):
        self.enricher = ContentEnricher()

    def test_enrich_basic(self):
        text = "Python is a great programming language for data science"
        enriched = self.enricher.enrich("Python Guide", text)
        assert enriched.title == "Python Guide"
        assert enriched.word_count > 0
        assert enriched.reading_time >= 1
        assert len(enriched.keywords) > 0

    def test_enrich_empty_text(self):
        enriched = self.enricher.enrich("Empty", "")
        assert enriched.word_count == 0
        assert enriched.keywords == []
        assert enriched.sentiment_score == 0.0

    def test_enrich_detects_code(self):
        html = "<html><body><pre>def hello(): pass</pre></body></html>"
        enriched = self.enricher.enrich("Code Page", "some text", html=html)
        assert enriched.has_code is True

    def test_enrich_detects_links(self):
        html = '<html><body><a href="http://example.com">link</a></body></html>'
        enriched = self.enricher.enrich("Link Page", "some text", html=html)
        assert enriched.has_links is True

    def test_enrich_detects_images(self):
        html = '<html><body><img src="photo.jpg" alt="photo"/></body></html>'
        enriched = self.enricher.enrich("Image Page", "some text", html=html)
        assert enriched.has_images is True

    def test_enrich_no_code_detection(self):
        html = "<html><body><p>Just text</p></body></html>"
        enriched = self.enricher.enrich("Text Page", "some text", html=html)
        assert enriched.has_code is False

    def test_enrich_positive_sentiment(self):
        text = "This is great and amazing and wonderful and excellent"
        enriched = self.enricher.enrich("Positive", text)
        assert enriched.sentiment_score > 0

    def test_enrich_negative_sentiment(self):
        text = "This is terrible and awful and horrible and worst"
        enriched = self.enricher.enrich("Negative", text)
        assert enriched.sentiment_score < 0

    def test_enrich_neutral_sentiment(self):
        text = "The cat sat on the mat near the window"
        enriched = self.enricher.enrich("Neutral", text)
        assert enriched.sentiment_score == 0.0

    def test_enrich_complexity_empty(self):
        enriched = self.enricher.enrich("Empty", "")
        assert enriched.complexity_score == 0.0

    def test_enrich_complexity_simple(self):
        text = "a a a a a a a a a a"
        enriched = self.enricher.enrich("Simple", text)
        assert enriched.complexity_score < 0.5

    def test_enrich_complexity_varied(self):
        text = "extraordinary magnificent extraordinary sophisticated vocabulary"
        enriched = self.enricher.enrich("Complex", text)
        assert enriched.complexity_score > 0.3

    def test_enrich_keywords_present(self):
        text = "python python python java javascript"
        enriched = self.enricher.enrich("Languages", text)
        assert "python" in enriched.keywords

    def test_enrich_reading_time(self):
        text = " ".join(["word"] * 200)  # 200 words
        enriched = self.enricher.enrich("Long", text)
        assert enriched.reading_time >= 1

    def test_batch_enrich(self):
        items = [
            ("Title 1", "Hello world"),
            ("Title 2", "Python is great"),
        ]
        results = self.enricher.batch_enrich(items)
        assert len(results) == 2
        assert results[0].title == "Title 1"
        assert results[1].title == "Title 2"

    def test_batch_enrich_empty(self):
        results = self.enricher.batch_enrich([])
        assert results == []

    def test_custom_top_n_keywords(self):
        enricher = ContentEnricher(top_n_keywords=3)
        text = "one two three four five six seven eight nine ten"
        enriched = enricher.enrich("Test", text)
        assert len(enriched.keywords) <= 3

    def test_enrich_script_detection(self):
        html = "<html><script>var x = 1;</script></html>"
        enriched = self.enricher.enrich("Script", "text", html=html)
        assert enriched.has_code is True

    def test_enrich_code_tag_detection(self):
        html = '<html><code>print("hello")</code></html>'
        enriched = self.enricher.enrich("Code", "text", html=html)
        assert enriched.has_code is True


class TestEnrichedContentDatetime:
    """Tests for timezone-aware datetime in EnrichedContent."""

    def test_enriched_at_is_timezone_aware(self):
        """enriched_at should be timezone-aware (UTC), not naive."""
        from personal_index.content_enricher import EnrichedContent
        content = EnrichedContent(title="Test", text="Hello world")
        assert content.enriched_at.tzinfo is not None, "enriched_at should be timezone-aware"

    def test_enriched_at_is_utc(self):
        """enriched_at should be in UTC timezone."""
        from datetime import timezone

        from personal_index.content_enricher import EnrichedContent
        content = EnrichedContent(title="Test", text="Hello world")
        assert content.enriched_at.tzinfo == timezone.utc, "enriched_at should be UTC"

    def test_enriched_at_no_deprecation_warning(self):
        """Creating EnrichedContent should not trigger deprecation warnings."""
        import warnings

        from personal_index.content_enricher import EnrichedContent
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            EnrichedContent(title="Test", text="Hello world")
            deprecation_warnings = [x for x in w if issubclass(x.category, DeprecationWarning)]
            assert len(deprecation_warnings) == 0, f"Expected no deprecation warnings, got: {[str(x.message) for x in deprecation_warnings]}"


class TestEnrichDocstringContract:
    """Regression: enrich docstring must not over-promise (TICKET-340)."""

    def test_docstring_does_not_claim_language_is_computed(self):
        """The enrich docstring must not claim 'computed metadata' wholesale.

        The body computes word_count, reading_time, keywords,
        has_code/has_links/has_images, sentiment_score and complexity_score,
        but the EnrichedContent.language field is NEVER computed — it stays at
        its dataclass default 'en'. The docstring must therefore not claim
        'computed metadata' (which would imply language is computed); it should
        enumerate what IS computed (TICKET-340).
        """
        import inspect

        from personal_index.content_enricher import ContentEnricher

        src = inspect.getsource(ContentEnricher.enrich)
        assert "computed metadata" not in src
        assert "computed metrics, keywords, sentiment, and complexity" in src

    def test_class_docstring_does_not_claim_computed_metadata(self):
        """The class docstring must not claim 'computed metadata' either."""
        import inspect

        from personal_index.content_enricher import ContentEnricher

        src = inspect.getsource(ContentEnricher)
        assert "computed metadata" not in src
        assert "computed metrics, keywords, sentiment, and complexity" in src

    def test_language_is_not_computed_by_enrich(self):
        """Behavior unchanged: enrich leaves language at its default 'en'.

        enrich never assigns enriched.language, so after enriching non-English
        text the language field must still be the default 'en' (proving the
        doc fix is doc-only and language is not computed).
        """
        enricher = ContentEnricher()
        text = "Bonjour le monde. Ceci est un test en français."
        enriched = enricher.enrich("Titre", text)
        assert enriched.language == "en"
