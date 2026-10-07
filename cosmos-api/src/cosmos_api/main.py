import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from cosmos_api.config import Settings
from cosmos_api.routes import health

logger = logging.getLogger(__name__)


def create_app(settings: Settings | None = None) -> FastAPI:
    """Build and return a fully configured FastAPI app.

    Passing `settings` lets tests (or other environments) build an app
    with different configuration, without touching globals.
    """
    settings = settings or Settings()

    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper()),
        format="%(levelname)-9s %(name)s - %(message)s",
    )

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
        logger.info("Starting %s (%s)", settings.app_name, settings.environment)
        # Open DB pools / HTTP clients here
        yield
        # Close them here
        logger.info("Shutting down")

    app = FastAPI(title=settings.app_name, lifespan=lifespan)

    # Per-app state: every app instance gets its own settings and store
    app.state.settings = settings

    app.include_router(health.router)

    return app
