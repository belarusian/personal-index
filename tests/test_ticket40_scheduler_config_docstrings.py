"""Test for TICKET-40: SchedulerConfig.to_dict() and from_dict() docstrings."""
from personal_index.models import SchedulerConfig


class TestSchedulerConfigDocstrings:
    """Test that SchedulerConfig methods have proper docstrings."""

    def test_to_dict_has_docstring(self):
        """to_dict should have a docstring."""
        assert SchedulerConfig.to_dict.__doc__ is not None
        assert len(SchedulerConfig.to_dict.__doc__.strip()) > 0

    def test_from_dict_has_docstring(self):
        """from_dict should have a docstring."""
        assert SchedulerConfig.from_dict.__doc__ is not None
        assert len(SchedulerConfig.from_dict.__doc__.strip()) > 0

    def test_to_dict_works(self):
        """to_dict should return a dict with expected keys."""
        config = SchedulerConfig(enabled=True, interval_hours=12)
        result = config.to_dict()
        assert isinstance(result, dict)
        assert result == {"enabled": True, "interval_hours": 12}

    def test_from_dict_works(self):
        """from_dict should create a SchedulerConfig from a dict."""
        data = {"enabled": True, "interval_hours": 12}
        config = SchedulerConfig.from_dict(data)
        assert isinstance(config, SchedulerConfig)
        assert config.enabled is True
        assert config.interval_hours == 12

    def test_from_dict_ignores_extra_keys(self):
        """from_dict should ignore keys not in dataclass fields."""
        data = {"enabled": True, "interval_hours": 12, "extra_key": "ignored"}
        config = SchedulerConfig.from_dict(data)
        assert config.enabled is True
        assert config.interval_hours == 12
