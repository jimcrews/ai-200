from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """App settings, read from APP_* environment variables (or a local .env file)."""

    model_config = SettingsConfigDict(
        env_prefix="APP_", env_file=".env", extra="ignore"
    )

    app_name: str = "FastAPI Factory"
    environment: str = "local"
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"

    # Used only by the `fastapi-factory` command (see __init__.py)
    host: str = "127.0.0.1"
    port: int = 8000
    reload: bool = False
