from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        # Try both the API working directory and the repo root
        env_file=(".env.local", "../../.env.local"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Street Manager — JWT auth (ADR-026)
    sm_email: str = ""
    sm_password: str = ""
    sm_base_url: str = "https://api.manage-roadworks.service.gov.uk"
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

    # OS Data Hub (OAuth 2.0 client credentials — Project ID / Project Secret)
    os_client_id: str = ""
    os_client_secret: str = ""

    # Mapbox (read by frontend; backend may need for geocoding fallback)
    next_public_mapbox_token: str = ""

    # Public base URL of this API — used for webhook registration reference
    # Development: ngrok tunnel URL  →  Production: Hetzner domain (e.g. https://api.YOUR_DOMAIN)
    # Street Manager sends events to {public_api_url}/webhooks/{permits|activities|section58}
    public_api_url: str = "http://localhost:8000"

    # Runtime environment — set ENVIRONMENT=production in .env.prod on Hetzner
    environment: str = "development"

    # NUAR (Phase 4+)
    nuar_api_key: str = ""
    nuar_base_url: str = "https://api.nuar.uk"

    # D-TRO (Phase 6+, ADR-027) — credentials from DfT D-TRO portal
    # DTRO_KEY     → OAuth2 clientId  (sent to /v1/oauth-generator)
    # DTRO_SECRET  → OAuth2 clientSecret
    # DTRO_APP_ID  → portal registration UUID (not the OAuth clientId)
    # Legacy aliases: DTRO_CLIENT_ID / DTRO_CLIENT_SECRET still accepted
    dtro_app_id: str = ""          # Portal registration UUID — NOT the OAuth2 clientId
    dtro_key: str = ""             # HTTP Basic Auth username (apiKey from DfT portal)
    dtro_secret: str = ""          # HTTP Basic Auth password (apiSecret from DfT portal)
    dtro_client_id: str = ""       # Legacy alias (maps to dtro_key role)
    dtro_client_secret: str = ""   # Legacy alias for dtro_secret
    # Base URL must include the /v1 path prefix (confirmed from official Postman collection).
    # Integration: https://dtro-integration.dft.gov.uk/v1
    # Production:  https://dtro.dft.gov.uk/v1
    dtro_base_url: str = "https://dtro-integration.dft.gov.uk/v1"

    # CORS — comma-separated list of allowed origins
    # Production: set ALLOWED_ORIGINS=https://streetsenseai-web.vercel.app,http://localhost:3000
    # Vercel preview deployments are always allowed via allow_origin_regex in main.py
    allowed_origins: str = "http://localhost:3000,http://localhost:8000"

    # Admin (development only)
    admin_api_key: str = ""          # If blank, admin endpoints are unprotected (local dev only)
    admin_username: str = "admin"
    admin_password: str = "streetsense2026"


settings = Settings()
