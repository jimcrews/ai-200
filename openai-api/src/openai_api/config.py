from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """App settings, read from APP_* environment variables (or a local .env file)."""

    model_config = SettingsConfigDict(
        env_prefix="APP_", env_file=".env", extra="ignore"
    )

    app_name: str = "OpenAI API"
    environment: str = "local"
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"

    azure_openai_endpoint: str = ""
    azure_openai_api_key: str = ""
    llm_model_deployment_name: str = ""
    llm_max_tokens: int = 150
    llm_temperature: float = 0.7
    llm_top_p: float = 0.9

    # Used only by the `openai-api` command (see __init__.py)
    host: str = "127.0.0.1"
    port: int = 8000
    reload: bool = False
