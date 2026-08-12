"""Tests for TICKET-63: exception chain preservation (raise ... from err)."""

import pytest

from personal_index.serializer import (
    DeserializationError,
    SerializationConfig,
    SerializationError,
    Serializer,
)


class TestExceptionChains:
    """Verify that re-raised exceptions preserve the original traceback."""

    def test_serialization_error_preserves_cause(self):
        """SerializationError should chain from the original TypeError/ValueError."""
        config = SerializationConfig(default_handler=False)
        serializer = Serializer(config=config)

        class Unserializable:
            pass

        with pytest.raises(SerializationError) as exc_info:
            serializer.to_json(Unserializable())

        assert exc_info.value.__cause__ is not None
        assert isinstance(exc_info.value.__cause__, (TypeError, ValueError))

    def test_deserialization_error_preserves_cause(self):
        """DeserializationError should chain from the original JSONDecodeError."""
        serializer = Serializer()
        with pytest.raises(DeserializationError) as exc_info:
            serializer.from_json("not valid json {{{")

        assert exc_info.value.__cause__ is not None
        assert isinstance(exc_info.value.__cause__, Exception)
