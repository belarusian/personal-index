"""Content deduplication - backward compatibility shim.

This module re-exports from content_dedup to maintain backward compatibility.
New code should import from personal_index.content_dedup directly.
"""

from __future__ import annotations

from personal_index.content_dedup import (
    AddItemResult,
    BatchDedupReport,
    ContentDeduplicator,
    DedupConfig,
    DeduplicationEngine,
    DedupResult,
    DocumentHash,
    DuplicateGroup,
    SimilarityMethod,
    find_duplicates,
    remove_duplicates,
)

__all__ = [
    "AddItemResult",
    "BatchDedupReport",
    "ContentDeduplicator",
    "DedupConfig",
    "DedupResult",
    "DeduplicationEngine",
    "DocumentHash",
    "DuplicateGroup",
    "SimilarityMethod",
    "find_duplicates",
    "remove_duplicates",
]
