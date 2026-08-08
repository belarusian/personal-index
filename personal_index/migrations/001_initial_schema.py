"""Migration 001: Initial schema for pages and interests."""

version = 1
name = "initial_schema"
description = "Create initial tables for pages and interests"


def up(db):
    """Create initial schema."""
    if hasattr(db, "execute"):
        db.execute("""
            CREATE TABLE IF NOT EXISTS pages (
                id TEXT PRIMARY KEY,
                url TEXT NOT NULL UNIQUE,
                title TEXT DEFAULT '',
                content TEXT DEFAULT '',
                domain TEXT DEFAULT '',
                status_code INTEGER DEFAULT 200,
                content_length INTEGER DEFAULT 0,
                language TEXT DEFAULT 'en',
                crawled_at TEXT,
                keywords TEXT DEFAULT '[]',
                matched_interests TEXT DEFAULT '[]'
            )
        """)
        db.execute("""
            CREATE TABLE IF NOT EXISTS interests (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                value TEXT DEFAULT '',
                keywords TEXT DEFAULT '[]',
                topics TEXT DEFAULT '[]',
                url_patterns TEXT DEFAULT '[]',
                priority REAL DEFAULT 1.0,
                enabled INTEGER DEFAULT 1
            )
        """)
        db.execute("""
            CREATE TABLE IF NOT EXISTS migration_log (
                version INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                applied_at TEXT NOT NULL
            )
        """)
        db.execute("CREATE INDEX IF NOT EXISTS idx_pages_domain ON pages(domain)")
        db.execute("CREATE INDEX IF NOT EXISTS idx_pages_url ON pages(url)")


def down(db):
    """Drop initial schema."""
    if hasattr(db, "execute"):
        db.execute("DROP TABLE IF EXISTS migration_log")
        db.execute("DROP TABLE IF EXISTS interests")
        db.execute("DROP TABLE IF EXISTS pages")
