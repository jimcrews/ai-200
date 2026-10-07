import uvicorn

from cosmos_api.config import Settings


def main() -> None:
    """Entry point for `uv run cosmos-api`: serve the app via the factory."""
    settings = Settings()

    uvicorn.run(
        "cosmos_api.main:create_app",
        factory=True,
        host=settings.host,
        port=settings.port,
        reload=settings.reload,
    )
