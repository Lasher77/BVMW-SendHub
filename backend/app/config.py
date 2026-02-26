from pydantic_settings import BaseSettings
from typing import Literal


class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql://sendhub:sendhub@localhost:5432/sendhub"
    STORAGE_BACKEND: Literal["local", "s3"] = "local"
    STORAGE_LOCAL_BASE: str = "./storage"
    AWS_ACCESS_KEY_ID: str = ""
    AWS_SECRET_ACCESS_KEY: str = ""
    AWS_REGION: str = "eu-central-1"
    S3_BUCKET: str = "sendhub-files"
    SECRET_KEY: str = "dev-secret-key"
    ENVIRONMENT: str = "development"

    # E-Mail / SMTP
    SMTP_HOST: str = ""
    SMTP_PORT: int = 587
    SMTP_USERNAME: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM_EMAIL: str = "noreply@sendhub.local"
    SMTP_FROM_NAME: str = "BVMW SendHub"
    SMTP_USE_TLS: bool = True
    EMAIL_NOTIFICATIONS_ENABLED: bool = False
    APP_BASE_URL: str = "http://localhost:3000"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
