"""Content ratings module - rate saved items 1-5 stars."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple


@dataclass
class Rating:
    """A user rating for a content item (1-5 stars)."""

    content_id: str
    score: float
    comment: str = ""
    author: str = ""
    rating_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    updated_at: Optional[str] = None

    def __post_init__(self) -> None:
        """Validate score is between 1 and 5."""
        if self.score < 1 or self.score > 5:
            raise ValueError(f"Rating score must be between 1 and 5, got {self.score}")

    def __repr__(self) -> str:
        return f"Rating(content_id={self.content_id!r}, score={self.score})"

    def star_string(self) -> str:
        """Return a visual star representation."""
        full = int(self.score)
        half = self.score - full >= 0.5
        empty = 5 - full - (1 if half else 0)
        return "★" * full + ("½" if half else "") + "☆" * empty

    def to_dict(self) -> dict:
        """Serialize to dictionary."""
        return {
            "rating_id": self.rating_id,
            "content_id": self.content_id,
            "score": self.score,
            "comment": self.comment,
            "author": self.author,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Rating":
        """Deserialize from dictionary."""
        return cls(
            rating_id=data.get("rating_id", uuid.uuid4().hex[:12]),
            content_id=data["content_id"],
            score=data["score"],
            comment=data.get("comment", ""),
            author=data.get("author", ""),
            created_at=data.get("created_at", datetime.now(timezone.utc).isoformat()),
            updated_at=data.get("updated_at"),
        )


@dataclass
class RatingStats:
    """Statistics about ratings."""

    total_ratings: int = 0
    average_score: float = 0.0
    distribution: Dict[int, int] = field(default_factory=dict)
    highest_rated: List[Rating] = field(default_factory=list)
    lowest_rated: List[Rating] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "total_ratings": self.total_ratings,
            "average_score": self.average_score,
            "distribution": self.distribution,
            "highest_rated": [r.to_dict() for r in self.highest_rated],
            "lowest_rated": [r.to_dict() for r in self.lowest_rated],
        }


class RatingStore:
    """Manages user ratings for content items."""

    def __init__(self) -> None:
        self._ratings: Dict[str, Rating] = {}

    def rate(
        self,
        content_id: str,
        score: float,
        comment: str = "",
        author: str = "",
    ) -> Rating:
        """Rate a content item. Updates if already rated."""
        if score < 1 or score > 5:
            raise ValueError(f"Rating score must be between 1 and 5, got {score}")

        if content_id in self._ratings:
            existing = self._ratings[content_id]
            existing.score = score
            existing.comment = comment or existing.comment
            existing.updated_at = datetime.now(timezone.utc).isoformat()
            return existing

        rating = Rating(
            content_id=content_id,
            score=score,
            comment=comment,
            author=author,
        )
        self._ratings[content_id] = rating
        return rating

    def get_rating(self, content_id: str) -> Optional[Rating]:
        """Get the rating for a content item."""
        return self._ratings.get(content_id)

    def remove_rating(self, content_id: str) -> bool:
        """Remove a rating. Returns True if rating existed."""
        if content_id in self._ratings:
            del self._ratings[content_id]
            return True
        return False

    def list_rated_content(
        self,
        sort_by: str = "score",
        reverse: bool = True,
    ) -> List[Rating]:
        """List all rated content items."""
        ratings = list(self._ratings.values())
        if sort_by == "score":
            ratings.sort(key=lambda r: r.score, reverse=reverse)
        elif sort_by == "date":
            ratings.sort(key=lambda r: r.created_at, reverse=reverse)
        return ratings

    def get_average_rating(self) -> float:
        """Get the average rating across all rated content."""
        if not self._ratings:
            return 0.0
        return sum(r.score for r in self._ratings.values()) / len(self._ratings)

    def get_rating_distribution(self) -> Dict[int, int]:
        """Get the distribution of ratings by score bucket."""
        dist: Dict[int, int] = {}
        for rating in self._ratings.values():
            bucket = int(rating.score)
            dist[bucket] = dist.get(bucket, 0) + 1
        return dist

    def get_stats(self) -> RatingStats:
        """Get comprehensive rating statistics."""
        stats = RatingStats()
        stats.total_ratings = len(self._ratings)

        if self._ratings:
            stats.average_score = self.get_average_rating()
            stats.distribution = self.get_rating_distribution()

            sorted_ratings = sorted(
                self._ratings.values(), key=lambda r: r.score, reverse=True
            )
            stats.highest_rated = sorted_ratings[:5]
            stats.lowest_rated = sorted_ratings[-5:]

        return stats

    def get_rated_by_min_score(self, min_score: float) -> List[Rating]:
        """Get all ratings with score >= min_score."""
        return [r for r in self._ratings.values() if r.score >= min_score]

    def get_rated_by_max_score(self, max_score: float) -> List[Rating]:
        """Get all ratings with score <= max_score."""
        return [r for r in self._ratings.values() if r.score <= max_score]

    def get_rated_by_author(self, author: str) -> List[Rating]:
        """Get all ratings by a specific author."""
        return [r for r in self._ratings.values() if r.author == author]

    def get_rated_with_comments(self) -> List[Rating]:
        """Get all ratings that have comments."""
        return [r for r in self._ratings.values() if r.comment]

    def bulk_rate(self, ratings: List[Tuple[str, float]]) -> None:
        """Rate multiple content items at once. Skips invalid scores."""
        for content_id, score in ratings:
            try:
                self.rate(content_id, score)
            except ValueError:
                continue

    def clear(self) -> None:
        """Remove all ratings."""
        self._ratings.clear()

    def serialize(self) -> List[dict]:
        """Serialize all ratings to a list of dicts."""
        return [r.to_dict() for r in self._ratings.values()]

    def deserialize(self, data: List[dict]) -> None:
        """Deserialize ratings from a list of dicts."""
        self.clear()
        for item in data:
            rating = Rating.from_dict(item)
            self._ratings[rating.content_id] = rating
