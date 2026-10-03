import uvicorn

from openai_api.config import Settings


def main() -> None:
    """Entry point for `uv run openai-api`: serve the app via the factory."""
    settings = Settings()
    uvicorn.run(
        "openai_api.main:create_app",
        factory=True,
        host=settings.host,
        port=settings.port,
        reload=settings.reload,
    )
