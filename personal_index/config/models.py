"""Configuration data models — re-exported from personal_index.models."""

from __future__ import annotations

from personal_index.models import Interest, MatchMode

# Re-export for backward compatibility
__all__ = [
    "Interest",
    "MatchMode",
]
