"""Tests for the interest management module."""

from personal_index.interests import Interest, InterestStore


class TestInterest:
    def test_create_interest(self):
        interest = Interest(name="python", keywords=["python", "programming"])
        assert interest.name == "python"
        assert interest.keywords == ["python", "programming"]
        assert interest.enabled is True
        assert interest.priority == 5  # Default priority from models.py

    def test_to_dict_and_from_dict(self):
        interest = Interest(name="ai", keywords=["ai", "ml"], priority=3)
        data = interest.to_dict()
        restored = Interest.from_dict(data)
        assert restored.name == "ai"
        assert restored.priority == 3

    def test_custom_priority(self):
        interest = Interest(name="news", priority=5)
        assert interest.priority == 5


class TestInterestStore:
    def test_add_interest(self, tmp_path):
        store = InterestStore(store_path=str(tmp_path / "interests.json"))
        interest = Interest(name="tech", keywords=["technology"])
        store.add(interest)
        assert store.get("tech") is not None
        assert store.get("tech").keywords == ["technology"]

    def test_remove_interest(self, tmp_path):
        store = InterestStore(store_path=str(tmp_path / "interests.json"))
        store.add(Interest(name="tech", keywords=["technology"]))
        result = store.remove("tech")
        assert result is True
        assert store.get("tech") is None

    def test_remove_nonexistent(self, tmp_path):
        store = InterestStore(store_path=str(tmp_path / "interests.json"))
        result = store.remove("nonexistent")
        assert result is False

    def test_list_all(self, tmp_path):
        store = InterestStore(store_path=str(tmp_path / "interests.json"))
        store.add(Interest(name="tech", keywords=["technology"]))
        store.add(Interest(name="science", keywords=["science"]))
        assert len(store.list_all()) == 2

    def test_get_enabled(self, tmp_path):
        store = InterestStore(store_path=str(tmp_path / "interests.json"))
        store.add(Interest(name="tech", enabled=True))
        store.add(Interest(name="disabled", enabled=False))
        assert len(store.get_enabled()) == 1

    def test_toggle(self, tmp_path):
        store = InterestStore(store_path=str(tmp_path / "interests.json"))
        store.add(Interest(name="tech", enabled=True))
        result = store.toggle("tech")
        assert result.enabled is False

    def test_persistence(self, tmp_path):
        path = str(tmp_path / "interests.json")
        store = InterestStore(store_path=path)
        store.add(Interest(name="test", keywords=["test"]))

        store2 = InterestStore(store_path=path)
        assert store2.get("test").keywords == ["test"]

    def test_get_all_keywords(self, tmp_path):
        store = InterestStore(store_path=str(tmp_path / "interests.json"))
        store.add(Interest(name="a", keywords=["Python", "Java"]))
        store.add(Interest(name="b", keywords=["JavaScript"]))
        keywords = store.get_all_keywords()
        assert "python" in keywords
        assert "java" in keywords
        assert "javascript" in keywords

    def test_get_all_url_patterns(self, tmp_path):
        store = InterestStore(store_path=str(tmp_path / "interests.json"))
        store.add(Interest(name="news", url_patterns=[r"https://news\.example\.com/.*"]))
        patterns = store.get_all_url_patterns()
        assert len(patterns) == 1
        assert patterns[0].match("https://news.example.com/article")

    def test_get_all_topics(self, tmp_path):
        store = InterestStore(store_path=str(tmp_path / "interests.json"))
        store.add(Interest(name="a", topics=["AI", "ML"]))
        topics = store.get_all_topics()
        assert "ai" in topics
        assert "ml" in topics

    def test_empty_store(self, tmp_path):
        store = InterestStore(store_path=str(tmp_path / "interests.json"))
        assert len(store.list_all()) == 0
        assert store.get_all_keywords() == set()

    def test_toggle_nonexistent(self, tmp_path):
        store = InterestStore(store_path=str(tmp_path / "interests.json"))
        result = store.toggle("nonexistent")
        assert result is None

    def test_get_nonexistent(self, tmp_path):
        store = InterestStore(store_path=str(tmp_path / "interests.json"))
        assert store.get("nonexistent") is None

    def test_replace_interest(self, tmp_path):
        store = InterestStore(store_path=str(tmp_path / "interests.json"))
        store.add(Interest(name="tech", keywords=["old"]))
        store.add(Interest(name="tech", keywords=["new"]))
        assert store.get("tech").keywords == ["new"]
        assert len(store.list_all()) == 1

    def test_no_store_path(self):
        store = InterestStore()
        store.add(Interest(name="tech", keywords=["tech"]))
        assert store.get("tech") is not None
        assert len(store.list_all()) == 1

    def test_invalid_json_file(self, tmp_path):
        path = tmp_path / "interests.json"
        path.write_text("not valid json")
        store = InterestStore(store_path=str(path))
        assert len(store.list_all()) == 0

    def test_empty_keywords(self):
        interest = Interest(name="empty")
        assert interest.keywords == []

    def test_enabled_default(self):
        interest = Interest(name="default")
        assert interest.enabled is True

    def test_disabled_interest(self):
        interest = Interest(name="disabled", enabled=False)
        assert interest.enabled is False

    def test_empty_topics(self):
        interest = Interest(name="notopics")
        assert interest.topics == []

    def test_empty_url_patterns(self):
        interest = Interest(name="nopatterns")
        assert interest.url_patterns == []
