from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        # Try both the API working directory and the repo root
        env_file=(".env.local", "../../.env.local"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Street Manager
    street_manager_api_key: str = ""
    street_manager_base_url: str = "https://api.sandbox.manage-roadworks.service.gov.uk"
    street_manager_sqs_queue_url: str = ""

    # AWS (SQS consumer for SM-001)
    aws_region: str = "eu-west-2"
    aws_access_key_id: str = ""
    aws_secret_access_key: str = ""

    # Database
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/streetsense"

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # Anthropic
    anthropic_api_key: str = ""

    # OS Data Hub
    os_api_key: str = ""

    # Mapbox (read by frontend; backend may need for geocoding fallback)
    next_public_mapbox_token: str = ""


settings = Settings()
