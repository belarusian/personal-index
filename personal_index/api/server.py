"""FastAPI server for personal-index REST API."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import Any

from personal_index.config.loader import load_config
from personal_index.config.models import AppConfig

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app):
    """Application lifespan handler for startup/shutdown events."""
    logger.info("API server starting up")
    app.state.config = load_config()
    yield
    logger.info("API server shutting down")


def create_app(
    config: AppConfig | None = None,
    middleware: list | None = None,
) -> Any:
    """Create and configure the FastAPI application.

    Args:
        config: Optional application configuration.
        middleware: Optional list of middleware factories.

    Returns:
        Configured FastAPI application instance.
    """
    try:
        from fastapi import FastAPI
    except ImportError as err:
        raise ImportError(
            "fastapi is required for the API server. "
            "Install with: pip install fastapi uvicorn"
        ) from err

    app = FastAPI(
        title="Personal Index API",
        description="REST API for the personal web search engine",
        version="0.1.0",
        lifespan=lifespan,
    )

    if config:
        app.state.config = config

    # Apply any additional middleware
    if middleware:
        for mw_factory in middleware:
            mw_factory(app)

    return app
