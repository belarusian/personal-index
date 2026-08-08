"""Migration 002: Add full-text search indexes and bookmarks."""

version = 2
name = "add_indexes"
description = "Add full-text search indexes and bookmarks table"


def up(db):
    """Add indexes and bookmarks table."""
    if hasattr(db, "execute"):
        db.execute("""
            CREATE TABLE IF NOT EXISTS bookmarks (
                id TEXT PRIMARY KEY,
                url TEXT NOT NULL,
                title TEXT DEFAULT '',
                description TEXT DEFAULT '',
                tags TEXT DEFAULT '[]',
                created_at TEXT,
                updated_at TEXT
            )
        """)
        db.execute("CREATE INDEX IF NOT EXISTS idx_bookmarks_url ON bookmarks(url)")
        db.execute("""
            CREATE TABLE IF NOT EXISTS crawl_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                url TEXT NOT NULL,
                status_code INTEGER,
                error TEXT DEFAULT '',
                duration_ms REAL,
                crawled_at TEXT
            )
        """)
        db.execute("CREATE INDEX IF NOT EXISTS idx_crawl_log_url ON crawl_log(url)")
        db.execute("CREATE INDEX IF NOT EXISTS idx_crawl_log_at ON crawl_log(crawled_at)")


def down(db):
    """Drop indexes and bookmarks table."""
    if hasattr(db, "execute"):
        db.execute("DROP INDEX IF EXISTS idx_crawl_log_at")
        db.execute("DROP INDEX IF EXISTS idx_crawl_log_url")
        db.execute("DROP TABLE IF EXISTS crawl_log")
        db.execute("DROP INDEX IF EXISTS idx_bookmarks_url")
        db.execute("DROP TABLE IF EXISTS bookmarks")
