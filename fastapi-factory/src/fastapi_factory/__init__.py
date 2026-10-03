import uvicorn

from fastapi_factory.config import Settings


def main() -> None:
    """Entry point for `uv run fastapi-factory`: serve the app via the factory."""
    settings = Settings()
    uvicorn.run(
        "fastapi_factory.main:create_app",
        factory=True,
        host=settings.host,
        port=settings.port,
        reload=settings.reload,
    )
