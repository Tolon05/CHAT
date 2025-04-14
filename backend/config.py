import os
from pydantic import BaseSettings

class Settings(BaseSettings):
    DATABASE_URL: str = "sqlite+aiosqlite:///./app.db"
    SECRET_KEY: str = os.getenv("SECRET_KEY", "some_secret_key")
    EMAIL: str = os.getenv("EMAIL")
    EMAIL_PASSWORD: str = os.getenv("EMAIL_PASSWORD")
    REDIS_HOST: str = os.getenv("REDIS_HOST", "localhost")
    REDIS_PORT: int = os.getenv("REDIS_PORT", 6379)
    CELERY_BROKER_URL: str = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0")
    
    class Config:
        env_file = ".env"

settings = Settings()
