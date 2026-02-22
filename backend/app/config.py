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

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
