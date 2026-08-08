import os
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

# Resolve path to .env.local relative to this config file location
_env_path = Path(__file__).parent.parent / ".env.local"

class Settings(BaseSettings):
    project_name: str = "AgroSaaS"
    version: str = "0.1.0"

    database_url: str = "sqlite+aiosqlite:///./agrosaas.db"
    redis_url: str = "redis://localhost:6379/0"
    db_pool_size: int = 3
    db_max_overflow: int = 2
    db_pool_timeout: int = 15
    session_cache_ttl_seconds: int = 300

    jwt_secret_key: str = "super_secret_for_development_change_in_production"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24 * 7 # 7 days

    # Stripe Config
    stripe_secret_key: str = ""
    stripe_webhook_secret: str = ""

    # Asaas Config
    asaas_api_key: str = ""
    asaas_api_url: str = "https://sandbox.asaas.com/api/v3"
    asaas_webhook_token: str = ""

    # Pagamentos Webhook (mock/genérico)
    pagamentos_webhook_secret: str = ""
    frontend_url: str = "http://localhost:3000"
    storage_public_base_url: str = ""
    # A API não deve executar o worker no processo web por padrão. Ambientes
    # que realmente hospedam o worker precisam habilitá-lo explicitamente.
    run_embedded_jobs: bool = False
    integrations_secret_key: str = ""
    allow_origins: list[str] = [
        "http://localhost:3000",
        "http://localhost:3001",
        "http://localhost:3002",
        "http://localhost:3003",
        "http://localhost:3004",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:3001",
        "http://127.0.0.1:3002",
        "http://127.0.0.1:3003",
        "http://127.0.0.1:3004",
        "http://0.0.0.0:3000",
        "http://0.0.0.0:3001",
        "http://0.0.0.0:3002",
        "http://0.0.0.0:3003",
        "http://0.0.0.0:3004",
        "http://local.agrosass.com.br:3000",
        "http://local.agrosass.com.br:3001",
    ]

    # Storage Config (local | s3 | minio)
    storage_backend: str = "local"
    storage_local_path: str = "/tmp/agrosaas_uploads"
    s3_bucket: str = ""
    s3_region: str = "us-east-1"
    s3_access_key: str = ""
    s3_secret_key: str = ""
    s3_endpoint_url: str = ""  # MinIO: http://localhost:9000
    storage_max_file_mb: int = 50

    # SMTP Config
    smtp_host: str = "smtp.mailtrap.io"
    smtp_port: int = 2525
    smtp_user: str = ""
    smtp_pass: str = ""
    mail_from: str = "noreply@agrosaas.com.br"

    # Sankhya Gateway Config
    sankhya_environment: str = "producao"
    sankhya_api_base_url: str = ""
    sankhya_auth_url: str = ""
    sankhya_client_id: str = ""
    sankhya_client_secret: str = ""
    sankhya_x_token: str = ""

    model_config = SettingsConfigDict(
        env_file=str(_env_path),
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()
