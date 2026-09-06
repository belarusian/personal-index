"""Topic detection engine for content tagging."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import ClassVar

from personal_index.content_tagger.tag import Tag


@dataclass
class _TopicDefinition:
    name: str
    keywords: list[str]
    weight: float = 1.0


class TopicDetector:
    """Detects topics in text content using keyword matching."""

    DEFAULT_TOPICS: ClassVar[dict[str, list[str]]] = {
        "programming": [
            "programming", "code", "developer", "software", "algorithm",
            "function", "variable", "class", "object", "debug",
        ],
        "python": [
            "python", "pip", "virtualenv", "django", "flask", "pytest",
            "numpy", "pandas", "jupyter", "anaconda",
        ],
        "web_development": [
            "html", "css", "javascript", "react", "angular", "vue",
            "frontend", "backend", "api", "rest", "graphql",
        ],
        "machine_learning": [
            "machine learning", "deep learning", "neural network",
            "training", "model", "inference", "tensorflow", "pytorch",
            "classification", "regression", "supervised", "unsupervised",
        ],
        "ai": [
            "artificial intelligence", "ai", "nlp", "natural language",
            "computer vision", "chatbot", "llm", "transformer",
            "generative", "prompt",
        ],
        "data_science": [
            "data science", "analytics", "visualization", "dashboard",
            "etl", "data pipeline", "big data", "statistics",
            "dataframe", "dataset",
        ],
        "devops": [
            "docker", "kubernetes", "ci/cd", "deployment", "infrastructure",
            "terraform", "ansible", "monitoring", "logging", "aws",
            "azure", "gcp", "cloud",
        ],
        "security": [
            "security", "encryption", "authentication", "authorization",
            "vulnerability", "penetration testing", "firewall", "ssl",
            "tls", "oauth", "jwt",
        ],
        "database": [
            "database", "sql", "nosql", "mongodb", "postgresql",
            "redis", "elasticsearch", "query", "index", "schema",
            "migration", "orm",
        ],
        "mobile": [
            "mobile", "ios", "android", "swift", "kotlin", "flutter",
            "react native", "app store", "play store",
        ],
        "design": [
            "design", "ui", "ux", "user interface", "user experience",
            "wireframe", "prototype", "figma", "sketch", "color",
            "typography", "layout",
        ],
        "testing": [
            "testing", "unit test", "integration test", "e2e",
            "selenium", "cypress", "mock", "fixture", "assertion",
            "coverage", "tdd", "bdt",
        ],
        "performance": [
            "performance", "optimization", "caching", "benchmark",
            "profiling", "latency", "throughput", "scalability",
            "load testing", "stress test",
        ],
        "version_control": [
            "git", "github", "gitlab", "bitbucket", "branch",
            "merge", "commit", "pull request", "rebase", "tag",
        ],
        "blockchain": [
            "blockchain", "cryptocurrency", "bitcoin", "ethereum",
            "smart contract", "defi", "nft", "web3", "consensus",
        ],
        "cloud_computing": [
            "cloud", "serverless", "lambda", "s3", "ec2",
            "microservice", "container", "orchestration", "saas",
            "paas", "iaas",
        ],
        "networking": [
            "network", "tcp", "udp", "http", "https", "dns",
            "router", "switch", "firewall", "bandwidth", "protocol",
        ],
        "operating_system": [
            "linux", "windows", "macos", "unix", "kernel",
            "shell", "bash", "terminal", "systemd", "cron",
        ],
        "mathematics": [
            "mathematics", "calculus", "algebra", "linear algebra",
            "probability", "statistics", "geometry", "topology",
            "number theory", "optimization",
        ],
        "education": [
            "education", "learning", "tutorial", "course", "university",
            "degree", "certification", "bootcamp", "lecture",
        ],
    }

    def __init__(self) -> None:
        self._topics: dict[str, _TopicDefinition] = {}
        for name, keywords in self.DEFAULT_TOPICS.items():
            self._topics[name] = _TopicDefinition(name=name, keywords=keywords)

    def detect(self, text: str) -> list[Tag]:
        """Detect topics in the given text.

        Returns an empty list when ``text`` is falsy or whitespace-only.
        Otherwise, for each registered topic the total number of
        case-insensitive keyword occurrences (via ``re.findall``) is summed
        across all of the topic's keywords. A topic is emitted at most once,
        and only when that total is greater than zero. Each emitted
        ``Tag`` carries confidence ``min(0.5 + match_count * 0.1, 1.0)``
        rounded to two decimals, and the result is sorted by confidence
        descending.
        """
        if not text or not text.strip():
            return []

        text_lower = text.lower()
        seen: set[str] = set()
        results: list[Tag] = []

        for topic in self._topics.values():
            match_count = 0
            for keyword in topic.keywords:
                kw_lower = keyword.lower()
                count = len(re.findall(re.escape(kw_lower), text_lower))
                match_count += count

            if match_count > 0 and topic.name not in seen:
                seen.add(topic.name)
                confidence = min(0.5 + (match_count * 0.1), 1.0)
                results.append(Tag(name=topic.name, confidence=round(confidence, 2)))

        results.sort(key=lambda t: t.confidence, reverse=True)
        return results

    def add_topic(self, name: str, keywords: list[str], weight: float = 1.0) -> None:
        """Add a custom topic definition."""
        self._topics[name] = _TopicDefinition(name=name, keywords=keywords, weight=weight)

    def remove_topic(self, name: str) -> None:
        """Remove a topic definition."""
        self._topics.pop(name, None)

    def get_all_topics(self) -> list[str]:
        """Return all registered topic names."""
        return list(self._topics.keys())

    """Internal topic definition with keywords."""

