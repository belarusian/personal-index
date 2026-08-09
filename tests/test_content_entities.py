"""Tests for content_entities - named entity recognition."""

from __future__ import annotations

import pytest
from personal_index.content_entities import (
    Entity,
    EntityType,
    EntityResult,
    EntityExtractor,
    EntityConfig,
    EntityMention,
    EntityFrequency,
)


class TestEntityType:
    def test_entity_types_exist(self):
        assert EntityType.PERSON is not None
        assert EntityType.ORGANIZATION is not None
        assert EntityType.LOCATION is not None
        assert EntityType.DATE is not None
        assert EntityType.NUMBER is not None
        assert EntityType.URL is not None
        assert EntityType.EMAIL is not None
        assert EntityType.MONEY is not None
        assert EntityType.PERCENTAGE is not None
        assert EntityType.PRODUCT is not None
        assert EntityType.TECHNOLOGY is not None
        assert EntityType.UNKNOWN is not None


class TestEntity:
    def test_entity_creation(self):
        entity = Entity(text="John", type=EntityType.PERSON, confidence=0.9)
        assert entity.text == "John"
        assert entity.type == EntityType.PERSON
        assert entity.confidence == 0.9

    def test_entity_defaults(self):
        entity = Entity(text="test", type=EntityType.UNKNOWN)
        assert entity.confidence == 0.5

    def test_entity_mentions(self):
        entity = Entity(text="Google", type=EntityType.ORGANIZATION, confidence=0.95)
        entity.add_mention(0, 6)
        entity.add_mention(20, 26)
        assert len(entity.mentions) == 2

    def test_entity_count(self):
        entity = Entity(text="Google", type=EntityType.ORGANIZATION, confidence=0.95)
        entity.add_mention(0, 6)
        entity.add_mention(20, 26)
        assert entity.count == 2


class TestEntityExtractor:
    def test_extract_person(self):
        extractor = EntityExtractor()
        result = extractor.extract("John Smith works at Google.")
        assert isinstance(result, EntityResult)

    def test_extract_organization(self):
        extractor = EntityExtractor()
        result = extractor.extract("Google is a technology company.")
        assert isinstance(result, EntityResult)

    def test_extract_location(self):
        extractor = EntityExtractor()
        result = extractor.extract("New York is a big city.")
        assert isinstance(result, EntityResult)

    def test_extract_date(self):
        extractor = EntityExtractor()
        result = extractor.extract("The meeting is on January 15, 2024.")
        assert isinstance(result, EntityResult)

    def test_extract_url(self):
        extractor = EntityExtractor()
        result = extractor.extract("Visit https://example.com for more info.")
        assert isinstance(result, EntityResult)
        urls = [e for e in result.entities if e.type == EntityType.URL]
        assert len(urls) >= 1

    def test_extract_email(self):
        extractor = EntityExtractor()
        result = extractor.extract("Contact us at test@example.com.")
        assert isinstance(result, EntityResult)
        emails = [e for e in result.entities if e.type == EntityType.EMAIL]
        assert len(emails) >= 1

    def test_extract_money(self):
        extractor = EntityExtractor()
        result = extractor.extract("The price is $100.")
        assert isinstance(result, EntityResult)
        money = [e for e in result.entities if e.type == EntityType.MONEY]
        assert len(money) >= 1

    def test_extract_percentage(self):
        extractor = EntityExtractor()
        result = extractor.extract("The growth was 25% this year.")
        assert isinstance(result, EntityResult)
        pct = [e for e in result.entities if e.type == EntityType.PERCENTAGE]
        assert len(pct) >= 1

    def test_extract_empty(self):
        extractor = EntityExtractor()
        result = extractor.extract("")
        assert isinstance(result, EntityResult)
        assert len(result.entities) == 0

    def test_extract_numbers(self):
        extractor = EntityExtractor()
        result = extractor.extract("There are 42 items and 100 users.")
        numbers = [e for e in result.entities if e.type == EntityType.NUMBER]
        assert len(numbers) >= 1

    def test_extract_batch(self):
        extractor = EntityExtractor()
        texts = ["John works at Google.", "Visit https://example.com"]
        results = extractor.extract_batch(texts)
        assert len(results) == 2
        assert all(isinstance(r, EntityResult) for r in results)

    def test_extract_with_config(self):
        config = EntityConfig(extract_numbers=False)
        extractor = EntityExtractor(config=config)
        result = extractor.extract("There are 42 items.")
        numbers = [e for e in result.entities if e.type == EntityType.NUMBER]
        assert len(numbers) == 0

    def test_get_entities_by_type(self):
        extractor = EntityExtractor()
        result = extractor.extract("John works at Google in New York.")
        persons = result.get_by_type(EntityType.PERSON)
        orgs = result.get_by_type(EntityType.ORGANIZATION)
        assert isinstance(persons, list)
        assert isinstance(orgs, list)

    def test_entity_frequency(self):
        extractor = EntityExtractor()
        result = extractor.extract("Google Google Google is great.")
        freq = result.get_frequency()
        assert isinstance(freq, list)

    def test_extract_technology(self):
        extractor = EntityExtractor()
        result = extractor.extract("Python and JavaScript are popular languages.")
        tech = [e for e in result.entities if e.type == EntityType.TECHNOLOGY]
        assert len(tech) >= 1


class TestEntityConfig:
    def test_config_defaults(self):
        config = EntityConfig()
        assert config.extract_numbers is True
        assert config.extract_urls is True
        assert config.extract_emails is True

    def test_config_custom(self):
        config = EntityConfig(extract_numbers=False, extract_urls=False)
        assert config.extract_numbers is False
        assert config.extract_urls is False


class TestEntityMention:
    def test_mention_creation(self):
        mention = EntityMention(start=0, end=6, context="Hello world")
        assert mention.start == 0
        assert mention.end == 6
        assert mention.context == "Hello world"


class TestEntityFrequency:
    def test_frequency_creation(self):
        freq = EntityFrequency(entity="Google", count=3, type=EntityType.ORGANIZATION)
        assert freq.entity == "Google"
        assert freq.count == 3
        assert freq.type == EntityType.ORGANIZATION
