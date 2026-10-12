from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """App settings, read from APP_* environment variables (or a local .env file)."""

    model_config = SettingsConfigDict(
        env_prefix="APP_", env_file=".env", extra="ignore"
    )

    app_name: str = "Redis API"
    environment: str = "local"
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"

    # see __init__.py
    host: str = "127.0.0.1"
    port: int = 8000
    reload: bool = False

    # Azure OpenAI (Foundry) - see deploy_foundry.bicep outputs
    azure_openai_endpoint: str = ""
    azure_openai_api_key: str = ""
    llm_model_deployment_name: str = ""
    embedding_model_deployment_name: str = ""

    llm_max_tokens: int = 300
    llm_temperature: float = 0.2
    llm_top_p: float = 0.9

    # Azure Managed Redis - see deploy_redis.bicep outputs
    redis_host: str = ""
    redis_port: int = 10000
    redis_access_key: str = ""

    vector_search_top_k: int = 5
    vector_search_similarity_threshold: float | None = None  # None = no filtering
