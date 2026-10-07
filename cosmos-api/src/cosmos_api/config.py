from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """App settings, read from APP_* environment variables (or a local .env file)."""

    model_config = SettingsConfigDict(
        env_prefix="APP_", env_file=".env", extra="ignore"
    )

    app_name: str = "Cosmos API"
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
    llm_max_tokens: int = 150
    llm_temperature: float = 0.7
    llm_top_p: float = 0.9
    embedding_model_deployment_name: str = ""

    # Cosmos DB - see deploy_cosmosdb.bicep outputs
    cosmos_db_endpoint: str = ""
    cosmos_primary_key: str = ""
    cosmos_db_name: str = ""
    cosmos_container_name: str = ""

    # Vector search
    vector_search_top_k: int = 5
    vector_search_similarity_threshold: float | None = None  # None = no filtering
