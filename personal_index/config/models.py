"""Configuration data models for personal-index."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class CrawlConfig:
    """Crawler configuration."""
    max_depth: int = 5
    politeness_delay: float = 1.0
    rate_limit: int = 10
    respect_robots_txt: bool = True
    timeout: int = 30
    user_agent: str = "personal-index/0.1.0"
    max_pages_per_domain: int = 100
    allowed_extensions: list[str] = field(default_factory=lambda: [".html", ".htm", ".xml"])
    follow_redirects: bool = True
    max_redirects: int = 5

    def validate(self) -> list[str]:
        """Validate configuration values."""
        errors = []
        if self.max_depth < 0:
            errors.append("max_depth must be >= 0")
        if self.politeness_delay < 0:
            errors.append("politeness_delay must be >= 0")
        if self.rate_limit < 1:
            errors.append("rate_limit must be >= 1")
        if self.timeout < 1:
            errors.append("timeout must be >= 1")
        return errors


@dataclass
class IndexConfig:
    """Search index configuration."""
    enable_stemming: bool = True
    index_path: str = ".personal_index"
    min_term_length: int = 2
    max_index_size: int = 100000
    enable_fuzzy_search: bool = True
    fuzzy_threshold: float = 0.8

    def validate(self) -> list[str]:
        """Validate configuration values."""
        errors = []
        if self.min_term_length < 1:
            errors.append("min_term_length must be >= 1")
        if self.max_index_size < 1:
            errors.append("max_index_size must be >= 1")
        if not 0 <= self.fuzzy_threshold <= 1:
            errors.append("fuzzy_threshold must be between 0 and 1")
        return errors


@dataclass
class SchedulerConfig:
    """Scheduler configuration."""
    enabled: bool = False
    interval_hours: int = 24
    max_concurrent_jobs: int = 3
    retry_count: int = 3
    retry_delay_seconds: int = 60
    log_file: str = ".personal_index/scheduler.log"

    def validate(self) -> list[str]:
        """Validate configuration values."""
        errors = []
        if self.interval_hours < 1:
            errors.append("interval_hours must be >= 1")
        if self.max_concurrent_jobs < 1:
            errors.append("max_concurrent_jobs must be >= 1")
        return errors


@dataclass
class NotificationConfig:
    """Notification configuration."""
    enabled: bool = False
    email: str = ""
    webhook_url: str = ""
    min_score: float = 0.5
    digest_interval_hours: int = 24

    def validate(self) -> list[str]:
        """Validate configuration values."""
        errors = []
        if self.enabled and not self.email and not self.webhook_url:
            errors.append("email or webhook_url required when notifications enabled")
        return errors


@dataclass
class ExportConfig:
    """Export configuration."""
    default_format: str = "markdown"
    output_dir: str = "exports"
    include_scores: bool = True
    include_tags: bool = True
    max_items: int = 1000

    def validate(self) -> list[str]:
        """Validate configuration values."""
        errors = []
        if self.default_format not in ("markdown", "csv", "json"):
            errors.append(f"unknown export format: {self.default_format}")
        return errors


@dataclass
class AppConfig:
    """Top-level application configuration."""
    data_dir: str = ".personal_index"
    config_dir: str = ""
    crawl: CrawlConfig = field(default_factory=CrawlConfig)
    index: IndexConfig = field(default_factory=IndexConfig)
    scheduler: SchedulerConfig = field(default_factory=SchedulerConfig)
    notifications: NotificationConfig = field(default_factory=NotificationConfig)
    export: ExportConfig = field(default_factory=ExportConfig)
    interests: list = field(default_factory=list)
    log_level: str = "INFO"

    def validate(self) -> list[str]:
        """Validate all configuration sections."""
        errors = []
        errors.extend(self.crawl.validate())
        errors.extend(self.index.validate())
        errors.extend(self.scheduler.validate())
        errors.extend(self.notifications.validate())
        errors.extend(self.export.validate())
        return errors

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        from dataclasses import asdict
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> AppConfig:
        """Create AppConfig from dictionary."""
        crawl_data = data.get("crawler", data.get("crawl", {}))
        index_data = data.get("index", {})
        scheduler_data = data.get("scheduler", {})
        notifications_data = data.get("notifications", {})
        export_data = data.get("export", {})

        return cls(
            data_dir=data.get("data_dir", ".personal_index"),
            config_dir=data.get("config_dir", ""),
            crawl=CrawlConfig(**crawl_data),
            index=IndexConfig(**index_data),
            scheduler=SchedulerConfig(**scheduler_data),
            notifications=NotificationConfig(**notifications_data),
            export=ExportConfig(**export_data),
            interests=data.get("interests", []),
            log_level=data.get("log_level", "INFO"),
        )
