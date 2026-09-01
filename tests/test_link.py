"""Tests for content link data model."""

from personal_index.content_linker.link import Link, LinkType


class TestLinkType:
    def test_values(self):
        assert LinkType.TOPIC.value == "topic"
        assert LinkType.KEYWORD.value == "keyword"
        assert LinkType.DOMAIN.value == "domain"
        assert LinkType.TEMPORAL.value == "temporal"
        assert LinkType.CONTENT.value == "content"


class TestLink:
    def test_creation(self):
        link = Link(source_id="s1", target_id="t1")
        assert link.link_type == LinkType.CONTENT
        assert link.score == 0.5

    def test_custom_type_and_score(self):
        link = Link(source_id="s1", target_id="t1", link_type=LinkType.TOPIC, score=0.9)
        assert link.link_type == LinkType.TOPIC
        assert link.score == 0.9

    def test_to_dict(self):
        link = Link(source_id="s1", target_id="t1", link_type=LinkType.TOPIC, score=0.8)
        d = link.to_dict()
        assert d == {
            "source_id": "s1",
            "target_id": "t1",
            "link_type": "topic",
            "score": 0.8,
        }

    def test_from_dict(self):
        d = {"source_id": "s1", "target_id": "t1", "link_type": "topic", "score": 0.7}
        link = Link.from_dict(d)
        assert link.source_id == "s1"
        assert link.target_id == "t1"
        assert link.link_type == LinkType.TOPIC
        assert link.score == 0.7

    def test_from_dict_minimal(self):
        d = {"source_id": "s1", "target_id": "t1"}
        link = Link.from_dict(d)
        assert link.link_type == LinkType.CONTENT
        assert link.score == 0.5

    def test_equality_same(self):
        l1 = Link("s1", "t1", LinkType.TOPIC, 0.8)
        l2 = Link("s1", "t1", LinkType.TOPIC, 0.8)
        assert l1 == l2

    def test_equality_different_type(self):
        l1 = Link("s1", "t1", LinkType.TOPIC, 0.8)
        l2 = Link("s1", "t1", LinkType.KEYWORD, 0.8)
        assert l1 != l2

    def test_equality_different_score(self):
        l1 = Link("s1", "t1", LinkType.TOPIC, 0.8)
        l2 = Link("s1", "t1", LinkType.TOPIC, 0.9)
        assert l1 != l2

    def test_equality_not_link(self):
        link = Link("s1", "t1")
        assert link != "not a link"

    def test_roundtrip(self):
        link = Link("s1", "t1", LinkType.DOMAIN, 0.6)
        l2 = Link.from_dict(link.to_dict())
        assert link == l2
