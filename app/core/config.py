from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    DATABASE_URL: str = "postgresql+asyncpg://user:pass@localhost:5432/avito_svayp"
    REDIS_URL: str = "redis://localhost"
    S3_ENDPOINT: str = "http://localhost:9000"
    S3_PUBLIC_ENDPOINT: str = "http://localhost:9000"
    S3_ACCESS_KEY: str = "minioadmin"
    S3_SECRET_KEY: str = "minioadmin"
    S3_BUCKET: str = "avito-svayp"
    SECRET_KEY: str = "development-only-change-me"
    ALGORITHM: str = "HS256"
    AUTO_PUBLISH: bool = False
    FRONTEND_ORIGIN: str = "http://localhost:3000"
    PUBLIC_BASE_URL: str = "http://localhost:8000"
    INTERNAL_API_KEY: str = "development-internal-key"
    ADMIN_API_KEY: str = "development-admin-key"
    MOCK_PAYMENT_BASE_URL: str = "https://pay.example.com"
    PAYMENT_WEBHOOK_SECRET: str = "development-payment-webhook-secret"
    SQL_ECHO: bool = False

settings = Settings()