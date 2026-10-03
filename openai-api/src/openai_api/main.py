import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from openai import AsyncOpenAI

from openai_api.api.routes import agent, health
from openai_api.config import Settings

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
        app.state.openai_client = None
        if settings.azure_openai_api_key and settings.azure_openai_endpoint:
            app.state.openai_client = AsyncOpenAI(
                api_key=settings.azure_openai_api_key,
                base_url=settings.azure_openai_endpoint,
            )
        else:
            logger.warning("Azure OpenAI not configured; /run will return 500")
        yield
        if app.state.openai_client is not None:
            await app.state.openai_client.close()
        logger.info("Shutting down")

    app = FastAPI(title=settings.app_name, lifespan=lifespan)

    # Per-app state: every app instance gets its own settings and store
    app.state.settings = settings

    app.include_router(health.router)
    app.include_router(agent.router)

    return app
