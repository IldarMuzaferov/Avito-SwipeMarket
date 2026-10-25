from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql+asyncpg://user:pass@localhost/avito_svayp"
    REDIS_URL: str = "redis://localhost"
    S3_ENDPOINT: str = "http://localhost:9000"
    S3_ACCESS_KEY: str = "minioadmin"
    S3_SECRET_KEY: str = "minioadmin"
    S3_BUCKET: str = "avito-svayp"
    SECRET_KEY: str = "supersecret"
    ALGORITHM: str = "HS256"
    AUTO_PUBLISH: bool = False

    class Config:
        env_file = ".env"

settings = Settings()